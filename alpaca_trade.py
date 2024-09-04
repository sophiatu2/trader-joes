from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data import StockHistoricalDataClient, StockTradesRequest
from alpaca.data.live import StockDataStream
from settings import api_key, api_secret, base_url, tickers
from datetime import datetime, timedelta
from alpaca_trade_api import REST
import yfinance as yf
import pandas_ta as ta
import math, time

api = REST(api_key, api_secret, base_url, api_version="v2")

# Get current portfolio
account = api.get_account()
cash = float(account.cash)
positions = api.list_positions()

asset_list = []
for position in positions:
    asset_list.append(
        {
            "ticker": position.symbol,
            "yfticker": yf.Ticker(position.symbol),  # Assuming you're using yfinance
            "holding": True,
            "quantity": int(position.qty),  # Convert the quantity from string to int
        }
    )

# Append other tickers
existing_tickers = {asset["ticker"] for asset in asset_list}
for ticker in tickers:
    if ticker not in existing_tickers:
        asset_list.append(
            {
                "ticker": ticker,
                "yfticker": yf.Ticker(ticker),
                "holding": False,
                "quantity": 0,
            }
        )

interval_fast = 10
interval_slow = 50
interval = "1m"
max_price = 10000


### Calculate pause
def get_pause():
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_int = now.replace(second=0, microsecond=0) + timedelta(
        minutes=1
    )  # change this depending on interval
    pause = math.ceil((next_int - now).seconds)
    return pause


### Trade
def trade(asset_list, cash):
    for asset in asset_list:
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        df = asset["yfticker"].history(start=start_date, interval=interval)

        # Calculate averages
        df["SMA_fast"] = ta.sma(df["Close"], interval_fast)
        df["SMA_slow"] = ta.sma(df["Close"], interval_slow)

        # Drop values that are NA
        df.dropna(subset=["SMA_fast", "SMA_slow"], inplace=True)

        price = df.iloc[-1]["Close"]

        # Buy
        if (
            df.iloc[-1]["SMA_fast"] > df.iloc[-1]["SMA_slow"]
            and not asset["holding"]
            and cash > price
        ):
            # Set max acceptable quantity of shares
            if cash > max_price:
                quantity = int(max_price / price)
            else:
                quantity = int(cash / price)

            # Execute trade
            api.submit_order(
                symbol=asset["ticker"],
                qty=quantity,
                side="buy",
                type="market",
                time_in_force="day",
            )

            # Adjust portfolio
            asset["holding"] = True
            asset["quantity"] = quantity
            cash -= quantity * price
            print(f"Buy {quantity} shares of {asset['ticker']} @ {price}\n")

        # Sell
        elif df.iloc[-1]["SMA_fast"] < df.iloc[-1]["SMA_slow"] and asset["holding"]:
            # Set quantity
            quantity = asset["quantity"]

            # Execute trade
            api.submit_order(
                symbol=asset["ticker"],
                qty=quantity,
                side="sell",
                type="market",
                time_in_force="day",
            )

            # Adjust portfolio
            asset["holding"] = False
            asset["quantity"] = 0
            cash += quantity * price
            print(f"Sell {quantity} shares of {asset['ticker']} @ {price}\n")

    return asset_list, cash


while True:
    asset_list, cash = trade(asset_list, cash)
    time.sleep(get_pause())
