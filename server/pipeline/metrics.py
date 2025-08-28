from prometheus_client import Counter, Histogram

exchanges_total = Counter("signet_exchanges_total", "Total verified exchanges")
denied_total = Counter("signet_denied_total", "Total denied exchanges", ["reason"])
forward_total = Counter("signet_forward_total", "Total forwarded exchanges", ["host"])
repair_attempts_total = Counter("signet_repair_attempts_total", "Total repair attempts")
fallback_used_total = Counter("signet_fallback_used_total", "Total fallback used")
latency_hist = Histogram("signet_exchange_latency_seconds", "Exchange latency seconds", ["phase"])
