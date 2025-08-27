#!/usr/bin/env python3
"""
Signet Protocol Billing Management

Enterprise-grade billing with token-level metering,
reserved capacity, tiered pricing, and Stripe integration.
"""

import time
from typing import Dict, Any, Optional, List, NamedTuple
from datetime import datetime, timezone

from .storage import StorageBackend


class BillingResult(NamedTuple):
    """Result of billing check"""
    allowed: bool
    reason: Optional[str] = None
    remaining_vex: Optional[int] = None
    remaining_fu: Optional[int] = None


class UsageRecord(NamedTuple):
    """Usage record for billing"""
    tenant_id: str
    usage_type: str  # 'vex' or 'fu'
    amount: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class BillingManager:
    """Manages billing, metering, and usage tracking"""
    
    def __init__(self, storage: StorageBackend):
        self.storage = storage
    
    async def check_limits(self, api_key: str) -> BillingResult:
        """Check if tenant is within billing limits"""
        try:
            # Get tenant configuration
            tenant_config = await self.storage.get_tenant_config(api_key)
            if not tenant_config:
                # Default limits for new tenants
                tenant_config = {
                    'vex_limit': 1000,
                    'fu_limit': 5000,
                    'billing_enabled': True
                }
            
            if not tenant_config.get('billing_enabled', True):
                return BillingResult(allowed=True)
            
            # Get current usage
            current_usage = await self.storage.get_current_usage(api_key)
            
            vex_used = current_usage.get('vex_used', 0)
            fu_used = current_usage.get('fu_used', 0)
            
            vex_limit = tenant_config.get('vex_limit', 1000)
            fu_limit = tenant_config.get('fu_limit', 5000)
            
            # Check VEx limit
            if vex_used >= vex_limit:
                return BillingResult(
                    allowed=False,
                    reason=f"VEx limit exceeded: {vex_used}/{vex_limit}"
                )
            
            # Check FU limit
            if fu_used >= fu_limit:
                return BillingResult(
                    allowed=False,
                    reason=f"FU limit exceeded: {fu_used}/{fu_limit}"
                )
            
            return BillingResult(
                allowed=True,
                remaining_vex=vex_limit - vex_used,
                remaining_fu=fu_limit - fu_used
            )
            
        except Exception as e:
            # Log error but allow request (fail open for billing)
            print(f"Billing check error: {e}")
            return BillingResult(allowed=True, reason="billing_error")
    
    async def record_usage(
        self,
        api_key: str,
        usage_type: str,
        amount: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record usage for billing"""
        usage_record = UsageRecord(
            tenant_id=api_key,
            usage_type=usage_type,
            amount=amount,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
        
        await self.storage.record_usage(usage_record)
    
    async def get_usage_summary(
        self,
        api_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage summary for tenant"""
        return await self.storage.get_usage_summary(api_key, start_date, end_date)
    
    async def calculate_charges(
        self,
        api_key: str,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate charges for billing period"""
        # Get tenant configuration
        tenant_config = await self.storage.get_tenant_config(api_key)
        if not tenant_config:
            return {'total_charges': 0, 'line_items': []}
        
        # Get usage for period
        usage_summary = await self.get_usage_summary(
            api_key, billing_period_start, billing_period_end
        )
        
        line_items = []
        total_charges = 0
        
        # Calculate VEx charges
        vex_used = usage_summary.get('vex_used', 0)
        vex_reserved = tenant_config.get('vex_reserved', 0)
        vex_overage = max(0, vex_used - vex_reserved)
        
        if vex_overage > 0:
            vex_price = self._get_tiered_price(
                vex_overage,
                tenant_config.get('vex_overage_tiers', [])
            )
            vex_charges = vex_overage * vex_price
            total_charges += vex_charges
            
            line_items.append({
                'type': 'vex_overage',
                'quantity': vex_overage,
                'unit_price': vex_price,
                'total': vex_charges
            })
        
        # Calculate FU charges
        fu_used = usage_summary.get('fu_used', 0)
        fu_reserved = tenant_config.get('fu_reserved', 0)
        fu_overage = max(0, fu_used - fu_reserved)
        
        if fu_overage > 0:
            fu_price = self._get_tiered_price(
                fu_overage,
                tenant_config.get('fu_overage_tiers', [])
            )
            fu_charges = fu_overage * fu_price
            total_charges += fu_charges
            
            line_items.append({
                'type': 'fu_overage',
                'quantity': fu_overage,
                'unit_price': fu_price,
                'total': fu_charges
            })
        
        return {
            'total_charges': total_charges,
            'line_items': line_items,
            'usage_summary': usage_summary,
            'billing_period': {
                'start': billing_period_start.isoformat(),
                'end': billing_period_end.isoformat()
            }
        }
    
    def _get_tiered_price(self, quantity: int, tiers: List[Dict[str, Any]]) -> float:
        """Calculate tiered pricing"""
        if not tiers:
            return 0.01  # Default price
        
        # Find applicable tier
        for tier in sorted(tiers, key=lambda x: x.get('threshold', 0)):
            if quantity >= tier.get('threshold', 0):
                return tier.get('price_per_unit', 0.01)
        
        return tiers[0].get('price_per_unit', 0.01)
    
    async def create_stripe_invoice(
        self,
        api_key: str,
        charges: Dict[str, Any],
        stripe_customer_id: str
    ) -> Optional[str]:
        """Create Stripe invoice (requires Stripe integration)"""
        try:
            import stripe
            
            # Create invoice items
            for item in charges['line_items']:
                stripe.InvoiceItem.create(
                    customer=stripe_customer_id,
                    amount=int(item['total'] * 100),  # Convert to cents
                    currency='usd',
                    description=f"Signet {item['type']}: {item['quantity']} units"
                )
            
            # Create and finalize invoice
            invoice = stripe.Invoice.create(
                customer=stripe_customer_id,
                auto_advance=True
            )
            
            return invoice.id
            
        except Exception as e:
            print(f"Stripe invoice creation failed: {e}")
            return None