# BTC-USD Order-Book Aggregator

A light-weight command-line tool that fetches order books from Coinbase Pro and Gemini, applies a per-exchange 2s rate-limit (with caching), and tells you the best total price to buy or sell a given quantity of BTC.

This was made for CoinRoutes

## Implementation Highlights:

- Used a decorator with an internal closure to enforce the 2-second rate limit, using locks to prevent race conditions
- Requests made within the rate-limit interval read from data cache
- Converted both exchange responses into [[price, size], ...] lists, ideal for inclusion of more data sets
- Wrapped each fetch and parse in try/except so malformed data from one exchange does not stop the entire script.

## Command Line Setup and execution

```bash
# Clone the repo
git clone https://github.com/MichaelC1999/CoinRoutes-Orderbook.git CoinRoutes-Orderbook && cd CoinRoutes-Orderbook

# Start venv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install the dependency
pip install requests

# Run
python orderbook_aggregator.py
python orderbook_aggregator.py --qty 2
```
