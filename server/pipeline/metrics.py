from prometheus_client import Counter, Histogram, Gauge

# Core exchange counters
exchanges_total = Counter("signet_exchanges_total", "Total verified exchanges")
denied_total = Counter("signet_denied_total", "Total denied exchanges", ["reason"])
forward_total = Counter("signet_forward_total", "Total forwarded exchanges", ["host"])
idempotent_hits_total = Counter("signet_idempotent_hits_total", "Total idempotency cache hits")

# Fallback / repair counters
repair_attempts_total = Counter("signet_repair_attempts_total", "Total repair attempts")
repair_success_total = Counter("signet_repair_success_total", "Successful repairs producing valid JSON")
fallback_used_total = Counter("signet_fallback_used_total", "Total fallback used")
semantic_violation_total = Counter("signet_semantic_violation_total", "Semantic invariant violations during fallback repair")

# Billing / usage counters
vex_units_total = Counter("signet_vex_units_total", "Total Verified Exchange (VEx) units billed")
fu_tokens_total = Counter("signet_fu_tokens_total", "Total Fallback Unit (FU) tokens consumed")
billing_enqueue_total = Counter("signet_billing_enqueue_total", "Billing enqueue operations", ["type"])  # type=vex|fu

# Latency histograms
latency_total_hist = Histogram("signet_exchange_total_latency_seconds", "End-to-end exchange latency seconds")
phase_latency_hist = Histogram("signet_exchange_phase_latency_seconds", "Per-phase exchange latency seconds", ["phase"])

# Gauges for reserved capacity (updated opportunistically; set to last seen values)
reserved_vex_capacity = Gauge("signet_reserved_vex_capacity", "Reserved VEx capacity per tenant", ["tenant"])
reserved_fu_capacity = Gauge("signet_reserved_fu_capacity", "Reserved FU capacity per tenant", ["tenant"])

def update_reserved_capacity(tenant: str, vex: int, fu: int):
	"""Helper to publish reserved capacity gauges."""
	try:
		reserved_vex_capacity.labels(tenant=tenant).set(vex)
		reserved_fu_capacity.labels(tenant=tenant).set(fu)
	except Exception:
		# Never let metrics errors break the request path
		pass

