import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge

from .metrics import update_reserved_capacity
from .storage import Storage

billing_enqueued = Counter("signet_billing_enqueued_total", "Billing events enqueued", ["type"])
reserved_capacity_gauge = Gauge(
    "signet_reserved_capacity", "Reserved capacity by tenant and type", ["tenant", "type"]
)
overage_charges = Counter(
    "signet_overage_charges_total", "Overage charges applied", ["tenant", "type", "tier"]
)


class ReservedCapacity:
    """Configuration for reserved monthly capacity and overage tiers"""

    def __init__(self, config: dict[str, Any]):
        self.vex_reserved = config.get("vex_reserved", 0)
        self.fu_reserved = config.get("fu_reserved", 0)

        # Overage tiers: list of {"threshold": int, "price_per_unit": float, "stripe_item": str}
        self.vex_overage_tiers = config.get("vex_overage_tiers", [])
        self.fu_overage_tiers = config.get("fu_overage_tiers", [])

        # Stripe items for reserved capacity billing
        self.vex_reserved_item = config.get("vex_reserved_item")
        self.fu_reserved_item = config.get("fu_reserved_item")


class UsageTracker:
    """Track monthly usage against reserved capacity"""

    def __init__(self, storage: Storage):
        self.storage = storage

    def get_monthly_usage(self, tenant: str, year: int, month: int) -> dict[str, int]:
        """Get VEx and FU usage for a specific month"""
        # In a real implementation, this would query the usage_ledger table
        # For now, return mock data
        return {"vex_used": 0, "fu_used": 0}

    def calculate_overage(
        self, reserved: ReservedCapacity, usage: dict[str, int]
    ) -> dict[str, Any]:
        """Calculate overage charges based on tiers"""
        vex_overage = max(0, usage["vex_used"] - reserved.vex_reserved)
        fu_overage = max(0, usage["fu_used"] - reserved.fu_reserved)

        vex_charges = self._calculate_tier_charges(vex_overage, reserved.vex_overage_tiers)
        fu_charges = self._calculate_tier_charges(fu_overage, reserved.fu_overage_tiers)

        return {
            "vex_overage": vex_overage,
            "fu_overage": fu_overage,
            "vex_charges": vex_charges,
            "fu_charges": fu_charges,
            "total_overage_cost": sum(c["cost"] for c in vex_charges + fu_charges),
        }

    def _calculate_tier_charges(self, overage_units: int, tiers: list) -> list:
        """Calculate charges across multiple pricing tiers"""
        if not overage_units or not tiers:
            return []

        charges = []
        remaining = overage_units

        for tier in sorted(tiers, key=lambda t: t["threshold"]):
            if remaining <= 0:
                break

            tier_units = min(remaining, tier["threshold"])
            if tier_units > 0:
                charges.append(
                    {
                        "tier_threshold": tier["threshold"],
                        "units": tier_units,
                        "price_per_unit": tier["price_per_unit"],
                        "cost": tier_units * tier["price_per_unit"],
                        "stripe_item": tier["stripe_item"],
                    }
                )
                remaining -= tier_units

        # Handle unlimited tier (remaining units)
        if remaining > 0 and tiers:
            last_tier = tiers[-1]
            charges.append(
                {
                    "tier_threshold": "unlimited",
                    "units": remaining,
                    "price_per_unit": last_tier["price_per_unit"],
                    "cost": remaining * last_tier["price_per_unit"],
                    "stripe_item": last_tier["stripe_item"],
                }
            )

        return charges


class BillingBuffer:
    def __init__(
        self, storage: Storage, stripe_api_key: str | None, reserved_config_path: str | None = None
    ):
        self.storage = storage
        self.enabled = bool(stripe_api_key)
        self.usage_tracker = UsageTracker(storage)

        if self.enabled:
            import stripe

            stripe.api_key = stripe_api_key
            self.stripe = stripe
        else:
            self.stripe = None

        # Load reserved capacity configuration
        self.reserved_configs = self._load_reserved_configs(reserved_config_path)

    def _load_reserved_configs(self, config_path: str | None) -> dict[str, ReservedCapacity]:
        """Load reserved capacity configurations from file"""
        if not config_path or not os.path.exists(config_path):
            return {}

        try:
            with open(config_path) as f:
                configs = json.load(f)

            result = {}
            for tenant, config in configs.items():
                result[tenant] = ReservedCapacity(config)

                # Update legacy + new Prometheus metrics
                reserved_capacity_gauge.labels(tenant=tenant, type="vex").set(
                    config.get("vex_reserved", 0)
                )
                reserved_capacity_gauge.labels(tenant=tenant, type="fu").set(
                    config.get("fu_reserved", 0)
                )
                update_reserved_capacity(
                    tenant, config.get("vex_reserved", 0), config.get("fu_reserved", 0)
                )

            return result
        except Exception as e:
            print(f"Warning: Failed to load reserved capacity config: {e}")
            return {}

    def enqueue_vex(
        self, api_key: str, stripe_item: str | None, units: int = 1, tenant: str | None = None
    ):
        if not (self.enabled and stripe_item):
            return

        # Check for reserved capacity and overage billing
        if tenant and tenant in self.reserved_configs:
            billing_item, billing_units = self._calculate_vex_billing(tenant, units)
            if billing_item:
                self.storage.enqueue_billing(api_key, billing_item, billing_units, int(time.time()))
        else:
            # Standard per-unit billing
            self.storage.enqueue_billing(api_key, stripe_item, units, int(time.time()))

        billing_enqueued.labels(type="vex").inc()

    def enqueue_fu(
        self, api_key: str, stripe_item: str | None, tokens: int, tenant: str | None = None
    ):
        if not (self.enabled and stripe_item and tokens > 0):
            return

        # Check for reserved capacity and overage billing
        if tenant and tenant in self.reserved_configs:
            billing_item, billing_units = self._calculate_fu_billing(tenant, tokens)
            if billing_item:
                self.storage.enqueue_billing(api_key, billing_item, billing_units, int(time.time()))
        else:
            # Standard per-token billing
            self.storage.enqueue_billing(api_key, stripe_item, tokens, int(time.time()))

        billing_enqueued.labels(type="fu").inc()

    def _calculate_vex_billing(self, tenant: str, units: int) -> tuple[str | None, int]:
        """Calculate VEx billing considering reserved capacity"""
        reserved = self.reserved_configs.get(tenant)
        if not reserved:
            return None, 0

        now = datetime.now(timezone.utc)
        usage = self.usage_tracker.get_monthly_usage(tenant, now.year, now.month)

        # If within reserved capacity, no additional billing
        if usage["vex_used"] + units <= reserved.vex_reserved:
            return None, 0

        # Calculate overage
        overage_units = max(0, (usage["vex_used"] + units) - reserved.vex_reserved)
        if overage_units > 0:
            # Find appropriate tier
            for tier in reserved.vex_overage_tiers:
                if overage_units <= tier["threshold"]:
                    overage_charges.labels(tenant=tenant, type="vex", tier=tier["threshold"]).inc()
                    return tier["stripe_item"], overage_units

        return None, 0

    def _calculate_fu_billing(self, tenant: str, tokens: int) -> tuple[str | None, int]:
        """Calculate FU billing considering reserved capacity"""
        reserved = self.reserved_configs.get(tenant)
        if not reserved:
            return None, 0

        now = datetime.now(timezone.utc)
        usage = self.usage_tracker.get_monthly_usage(tenant, now.year, now.month)

        # If within reserved capacity, no additional billing
        if usage["fu_used"] + tokens <= reserved.fu_reserved:
            return None, 0

        # Calculate overage
        overage_tokens = max(0, (usage["fu_used"] + tokens) - reserved.fu_reserved)
        if overage_tokens > 0:
            # Find appropriate tier
            for tier in reserved.fu_overage_tiers:
                if overage_tokens <= tier["threshold"]:
                    overage_charges.labels(tenant=tenant, type="fu", tier=tier["threshold"]).inc()
                    return tier["stripe_item"], overage_tokens

        return None, 0

    def generate_monthly_report(self, tenant: str, year: int, month: int) -> dict[str, Any]:
        """Generate monthly usage and billing report"""
        if tenant not in self.reserved_configs:
            return {"error": "No reserved capacity configured for tenant"}

        reserved = self.reserved_configs[tenant]
        usage = self.usage_tracker.get_monthly_usage(tenant, year, month)
        overage_calc = self.usage_tracker.calculate_overage(reserved, usage)

        return {
            "tenant": tenant,
            "period": f"{year}-{month:02d}",
            "reserved_capacity": {"vex": reserved.vex_reserved, "fu": reserved.fu_reserved},
            "actual_usage": usage,
            "overage_analysis": overage_calc,
            "within_reserved": {
                "vex": usage["vex_used"] <= reserved.vex_reserved,
                "fu": usage["fu_used"] <= reserved.fu_reserved,
            },
        }

    def flush_once(self, batch_size: int = 100, max_retries: int = 5):
        if not self.enabled:
            return {"flushed": 0, "enabled": False}
        items = self.storage.dequeue_billing_batch(batch_size)
        if not items:
            return {"flushed": 0, "enabled": True}
        ok_ids, retry_ids = [], []
        for it in items:
            try:
                self.stripe.UsageRecord.create(
                    quantity=it["units"],
                    timestamp=it["ts"],
                    action="increment",
                    subscription_item=it["stripe_item"],
                )
                ok_ids.append(it["id"])
            except Exception:
                if it["retries"] + 1 >= max_retries:
                    ok_ids.append(it["id"])  # drop
                else:
                    retry_ids.append(it["id"])
        if ok_ids:
            self.storage.delete_billing_items(ok_ids)
        if retry_ids:
            self.storage.bump_billing_retries(retry_ids)
        return {"flushed": len(ok_ids), "retries": len(retry_ids), "enabled": True}
