import requests
import argparse
import time
from functools import wraps
from threading import Lock

# Rate Limiter decorator - once every 2 secs
def rate_limiter(min_interval=2.0):
    def decorator(func):
        state = {             # mutable closure
            "t": 0.0,         # timestamp of last call
            "result": None    # cached order-book data
        }
        lock = Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Read from the cache if within the interval
            with lock:
                if (now - state["t"] < min_interval) and (state["result"] is not None):
                    return state["result"]

            result = func(*args, **kwargs)

            # Update cache under the lock
            with lock:
                state["t"] = now
                state["result"] = result
            return result

        return wrapper
    return decorator

# Coinbase orderbook
@rate_limiter()
def fetch_coinbase_orderbook():
    url = "https://api.exchange.coinbase.com/products/BTC-USD/book?level=2"
    response = requests.get(url, timeout=5)
    data = response.json()

    # Normalize format to [price (float), size (float)]
    bids = [[float(price), float(size)] for price, size, _ in data['bids']]
    asks = [[float(price), float(size)] for price, size, _ in data['asks']]
    
    return bids, asks

# Gemini orderbook
@rate_limiter()
def fetch_gemini_orderbook():
    url = "https://api.gemini.com/v1/book/BTCUSD"
    response = requests.get(url, timeout=5)
    data = response.json()

    # Normalize format to [price (float), size (float)]
    bids = [[float(entry['price']), float(entry['amount'])] for entry in data['bids']]
    asks = [[float(entry['price']), float(entry['amount'])] for entry in data['asks']]

    return bids, asks

# Sort and combine orderbooks
def aggregate_orderbooks(bid_lists, ask_lists):
    all_bids = sorted([entry for sublist in bid_lists for entry in sublist], key=lambda x: -x[0])
    all_asks = sorted([entry for sublist in ask_lists for entry in sublist], key=lambda x: x[0])
    return all_bids, all_asks

# Compute total cost to buy qty BTC from asks
def compute_buy_cost(asks, qty):
    total_cost = 0.0
    remaining = qty

    for price, size in asks:
        available = min(size, remaining)
        total_cost += available * price
        remaining -= available
        if remaining <= 0:
            break

    if remaining > 0:
        raise ValueError("Insufficient liquidity to buy the requested quantity.")
    return total_cost

# Compute total revenue from selling qty BTC to bids
def compute_sell_revenue(bids, qty):
    total_revenue = 0.0
    remaining = qty

    for price, size in bids:
        available = min(size, remaining)
        total_revenue += available * price
        remaining -= available
        if remaining <= 0:
            break

    if remaining > 0:
        raise ValueError("Insufficient liquidity to sell the requested quantity.")
    return total_revenue

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qty', type=float, default=10.0)
    args = parser.parse_args()
    qty = args.qty

    try:
        coinbase_bids, coinbase_asks = fetch_coinbase_orderbook()
    except Exception as e:
        print(f"Failed to fetch from Coinbase: {e}")
        coinbase_bids, coinbase_asks = [], []


    # Secondary requests to validate the rate limiter + caching 
    # try:
    #     coinbase_bids2, coinbase_asks2 = fetch_coinbase_orderbook()
    # except Exception as e:
    #     print(f"Failed to fetch from Coinbase: {e}")
    #     coinbase_bids2, coinbase_asks2 = [], []

    try:
        gemini_bids, gemini_asks = fetch_gemini_orderbook()
    except Exception as e:
        print(f"Failed to fetch from Gemini: {e}")
        gemini_bids, gemini_asks = [], []

    # try:
    #     gemini_bids2, gemini_asks2 = fetch_gemini_orderbook()
    # except Exception as e:
    #     print(f"Failed to fetch from Gemini: {e}")
    #     gemini_bids2, gemini_asks2 = [], []

    if not (coinbase_bids or gemini_bids):
        print("No bid data available from any exchange.")
        return
    if not (coinbase_asks or gemini_asks):
        print("No ask data available from any exchange.")
        return


    all_bids, all_asks = aggregate_orderbooks([coinbase_bids, gemini_bids], [coinbase_asks, gemini_asks])

    try:
        buy_cost = compute_buy_cost(all_asks, qty)
        print(f"To buy {qty} BTC: ${buy_cost:,.2f}")
    except ValueError as e:
        print(f"Buy Error: {e}")

    try:
        sell_revenue = compute_sell_revenue(all_bids, qty)
        print(f"To sell {qty} BTC: ${sell_revenue:,.2f}")
    except ValueError as e:
        print(f"Sell Error: {e}")

if __name__ == "__main__":
    main()
