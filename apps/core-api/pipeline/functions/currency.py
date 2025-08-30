from decimal import ROUND_DOWN, Decimal

MINOR_UNITS = {"USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "CNY": 2, "AUD": 2, "CAD": 2, "INR": 2}


def to_minor(amount, currency: str) -> int:
    currency = (currency or "").upper()
    scale = MINOR_UNITS.get(currency, 2)
    d = Decimal(str(amount))
    q = Decimal(10) ** scale
    minor = int((d * q).to_integral_exact(rounding=ROUND_DOWN))
    return minor
