import urllib.request
import json
import datetime
from models import db, FxRateCache

OFFLINE_RATES = {
    'INR': 1.0,
    'USD': 83.5,
    'EUR': 90.5,
    'GBP': 106.0,
    'JPY': 0.53,
    'CAD': 61.5,
    'AUD': 55.0,
    'AED': 22.7,
    'SGD': 62.0
}

def get_rate(from_currency: str, to_currency: str = 'INR') -> float:
    """Fetch the exchange rate from from_currency to to_currency.
    
    Tries DB cache first, then API, and falls back to offline rates if both fail.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return 1.0
        
    # Check if DB cache has a recent rate (less than 12 hours old)
    now = datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(hours=12)
    
    try:
        cached = FxRateCache.query.filter(
            FxRateCache.from_currency == from_currency,
            FxRateCache.to_currency == to_currency,
            FxRateCache.updated_at >= cutoff
        ).first()
        if cached:
            return cached.rate
    except Exception as e:
        print(f"[FX Cache Check Error] {e}")

    # Fetch from API
    api_url = f"https://open.er-api.com/v6/latest/{from_currency}"
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("result") == "success" and "rates" in data:
                rate = data["rates"].get(to_currency)
                if rate is not None:
                    # Update or insert into cache
                    try:
                        existing = FxRateCache.query.filter_by(
                            from_currency=from_currency,
                            to_currency=to_currency
                        ).first()
                        if existing:
                            existing.rate = rate
                            existing.updated_at = now
                        else:
                            new_rate = FxRateCache(
                                from_currency=from_currency,
                                to_currency=to_currency,
                                rate=rate,
                                updated_at=now
                            )
                            db.session.add(new_rate)
                        db.session.commit()
                    except Exception as db_err:
                        db.session.rollback()
                        print(f"[FX Cache Save Error] {db_err}")
                    return float(rate)
    except Exception as api_err:
        print(f"[FX API Fetch Error] {api_err} - Falling back to older cache or offline rate")

    # If API fails, try to get ANY cached rate, even if older than 12 hours
    try:
        any_cached = FxRateCache.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency
        ).first()
        if any_cached:
            return any_cached.rate
    except Exception as e:
        pass

    # Offline fallback logic
    if from_currency in OFFLINE_RATES and to_currency in OFFLINE_RATES:
        inr_per_from = OFFLINE_RATES[from_currency]
        inr_per_to = OFFLINE_RATES[to_currency]
        return inr_per_from / inr_per_to

    return 1.0

def convert_to_base(amount: float, from_currency: str) -> float:
    """Convert amount in from_currency to INR (base currency)."""
    if not amount:
        return 0.0
    rate = get_rate(from_currency, 'INR')
    return amount * rate
