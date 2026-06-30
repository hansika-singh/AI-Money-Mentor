import requests
import time

CRYPTO_CACHE = {}
CACHE_EXPIRY = 300  # 5 minutes

def get_crypto_price_multi(symbols):
    """Fetch real-time prices for multiple symbols from CryptoCompare public API"""
    if not symbols:
        return {}
        
    symbols = [s.strip().upper() for s in symbols]
    
    # Check cache first
    now = time.time()
    uncached_symbols = []
    prices = {}
    
    for sym in symbols:
        if sym in CRYPTO_CACHE:
            cached_data, timestamp = CRYPTO_CACHE[sym]
            if now - timestamp < CACHE_EXPIRY:
                prices[sym] = cached_data
                continue
        uncached_symbols.append(sym)
        
    if not uncached_symbols:
        return prices
        
    try:
        # Fetch from CryptoCompare
        syms_str = ",".join(uncached_symbols)
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={syms_str}&tsyms=USD,INR"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if response.status_code == 200 and isinstance(data, dict) and "Response" not in data:
            for sym in uncached_symbols:
                if sym in data:
                    price_info = {
                        "USD": float(data[sym].get("USD", 0.0)),
                        "INR": float(data[sym].get("INR", 0.0))
                    }
                    CRYPTO_CACHE[sym] = (price_info, now)
                    prices[sym] = price_info
                else:
                    # Fallback for unrecognized coins
                    fallback_info = {"USD": 0.0, "INR": 0.0}
                    prices[sym] = fallback_info
        else:
            # Fallback if API rate limited or error
            for sym in uncached_symbols:
                prices[sym] = {"USD": 0.0, "INR": 0.0}
    except Exception as e:
        print("Crypto API Error:", e)
        for sym in uncached_symbols:
            prices[sym] = {"USD": 0.0, "INR": 0.0}
            
    return prices

def get_crypto_price(symbol):
    prices = get_crypto_price_multi([symbol])
    return prices.get(symbol.upper(), {"USD": 0.0, "INR": 0.0})

def get_mock_defi_portfolio(wallet_address):
    """
    Generate mock DeFi portfolio holdings for a given wallet address
    for demonstration and visual excellence.
    """
    # Simple hash-like seed based on address length/chars to make it deterministic
    seed = sum(ord(c) for c in wallet_address) % 5
    
    protocols = [
        {
            "protocol": "Aave V3",
            "type": "Lending",
            "asset": "ETH",
            "balance": 1.45 + (seed * 0.2),
            "apy": 3.4,
            "value_usd": 0.0
        },
        {
            "protocol": "Uniswap V3",
            "type": "Liquidity Pool",
            "asset": "USDC/ETH LP",
            "balance": 1000.0 + (seed * 250.0),
            "apy": 12.5,
            "value_usd": 1000.0 + (seed * 250.0)
        },
        {
            "protocol": "Lido",
            "type": "Liquid Staking",
            "asset": "stETH",
            "balance": 2.5 + (seed * 0.5),
            "apy": 3.8,
            "value_usd": 0.0
        },
        {
            "protocol": "MakerDAO",
            "type": "Savings",
            "asset": "sDAI",
            "balance": 500.0 + (seed * 100.0),
            "apy": 5.0,
            "value_usd": 500.0 + (seed * 100.0)
        }
    ]
    
    # Get current ETH price
    eth_price = get_crypto_price("ETH").get("USD", 3500.0)
    if eth_price == 0.0:
        eth_price = 3500.0
        
    total_value = 0.0
    for p in protocols:
        if p["asset"] in ("ETH", "stETH"):
            p["value_usd"] = round(p["balance"] * eth_price, 2)
        total_value += p["value_usd"]
        
    return {
        "wallet": wallet_address,
        "total_value_usd": round(total_value, 2),
        "protocols": protocols
    }
