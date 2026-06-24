import yfinance as yf
import re
import time
import pandas as pd

STOCK_CACHE = {}
CACHE_EXPIRY = 600  # 10 minutes in seconds

DIVIDEND_CACHE = {}
DIVIDEND_CACHE_EXPIRY = 3600  # 1 hour in seconds


def get_stock_price(symbol):
    try:
        # Clean input
        symbol = symbol.strip().upper()
        
        # Security sanitization check: only allow alphanumeric, dots, hyphens, and underscores
        if not symbol or not re.match(r"^[A-Z0-9.\-_]+$", symbol):
            return {"error": "Invalid stock symbol format"}

        now = time.time()
        if symbol in STOCK_CACHE:
            cached_res, timestamp = STOCK_CACHE[symbol]
            if now - timestamp < CACHE_EXPIRY:
                return cached_res

        # Try finding as is first (especially for global stocks like AAPL, MSFT)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="30d")

        # If empty and no dot in symbol, try appending .NS for Indian stocks
        if hist.empty and "." not in symbol:
            symbol_ns = symbol + ".NS"
            stock = yf.Ticker(symbol_ns)
            hist = stock.history(period="30d")
            if not hist.empty:
                symbol = symbol_ns

        if hist.empty:
            return {"error": "Invalid stock symbol or no data found"}

        # Current Price
        price = hist["Close"].iloc[-1]

        # Format history for frontend charting
        history_data = []
        for idx, row in hist.iterrows():
            history_data.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(row["Close"], 2)
            })

        # Get metrics with safe fallbacks
        metrics = {
            "high_52w": "N/A",
            "low_52w": "N/A",
            "market_cap": "N/A",
            "pe_ratio": "N/A"
        }

        try:
            info = stock.info
            if info:
                metrics["high_52w"] = info.get("fiftyTwoWeekHigh", "N/A")
                metrics["low_52w"] = info.get("fiftyTwoWeekLow", "N/A")
                metrics["market_cap"] = info.get("marketCap", "N/A")
                metrics["pe_ratio"] = info.get("trailingPE", "N/A")
        except Exception as info_err:
            print(f"Info fetch failed for {symbol}: {info_err}")

        # Get news safely
        news_data = []
        try:
            news = stock.news
            if news:
                news_data = news
        except Exception:
            pass
        predicted_tomorrow = predict_stock(symbol)

        ret = {
            "symbol": symbol,
            "price": round(price, 2),
            "history": history_data,
            "Predicted Price":predicted_tomorrow.get("Predicted Price",0),
            "metrics": metrics,
            "news": news_data
        }
        STOCK_CACHE[symbol] = (ret, time.time())
        return ret

    except Exception as e:
        return {"error": str(e)}

def get_stock_dividends(symbol):
    try:
        symbol = symbol.strip().upper()
        if not symbol or not re.match(r"^[A-Z0-9.\-_]+$", symbol):
            return []

        now = time.time()
        if symbol in DIVIDEND_CACHE:
            cached_res, timestamp = DIVIDEND_CACHE[symbol]
            if now - timestamp < DIVIDEND_CACHE_EXPIRY:
                return cached_res

        # Try finding as is first
        stock = yf.Ticker(symbol)
        try:
            divs = stock.dividends
        except Exception:
            divs = None

        # If empty and no dot in symbol, try appending .NS
        if (divs is None or divs.empty) and "." not in symbol:
            symbol_ns = symbol + ".NS"
            stock = yf.Ticker(symbol_ns)
            try:
                divs = stock.dividends
            except Exception:
                divs = None

        if divs is None or divs.empty:
            ret = []
        else:
            ret = []
            for idx, val in zip(divs.index, divs.values):
                ret.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "amount": float(val)
                })

        DIVIDEND_CACHE[symbol] = (ret, time.time())
        return ret
    except Exception as e:
        print(f"Error fetching dividends for {symbol}: {e}")
        return []
#-------stock predictor --------#
def predict_stock(symbol):
    
    symbol = symbol.strip().upper().replace("$", "")
    if not symbol or not re.match(r"^[A-Z0-9.\-_]+$", symbol):
      return {"error": "Invalid stock symbol format"}
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d", interval="1d")
    if df.empty and "." not in symbol:
        symbol = symbol + ".NS"
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d", interval="1d")
            
    if df.empty:
        raise ValueError(f"History could not be found for {symbol}")
      
    df=df.reset_index()
    df["SMA_7"] = df["Close"].rolling(window=7).mean()
    df["SMA_30"] = df["Close"].rolling(window=30).mean()
    df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std()
    df["Bollinger_Upper"] = df["BB_Middle"] + (df["BB_Std"] * 2)
    df["Bollinger_Lower"] = df["BB_Middle"] - (df["BB_Std"] * 2)
    df["Sentiment_Score"]=0.0
    latest_data=df.iloc[-1]
    today_close=latest_data["Close"]

    #-----rules------#
    score=0
    if latest_data["SMA_7"]>latest_data["SMA_30"]:
        score+=1
    else:
        score-=1
        
    if latest_data["RSI"]<30:
        score+=1
    elif latest_data["RSI"]>70:
        score-=1

    if latest_data["MACD"]>0:
        score+=1
    else:
        score-=1

    if latest_data["Bollinger_Upper"]<latest_data["Close"]:
        score-=1
    elif latest_data["Bollinger_Lower"]>latest_data["Close"]:
        score+=1

    if latest_data["EMA_12"]>latest_data["EMA_26"]:
        score+=1
    else:
        score-=1

    signal=score/5
    MAX_BOUND=0.05
    try:
        predicted_return = signal*MAX_BOUND
        predicted_tomorrow_price = float(today_close*(1+predicted_return))
        print(predicted_return)
    except Exception as e:
        print(f"There is some error:{e}")
        predicted_tomorrow_price=0
    return {"Predicted Price":predicted_tomorrow_price}
    
            
    
    

