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
import csv
import os

api = REST(api_key, api_secret, base_url, api_version="v2")

# Get current portfolio
account = api.get_account()
cash = float(account.cash)
positions = api.list_positions()

print(f"Cash: ${cash}")

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

### Parameters
interval_fast = 10
interval_slow = 50
interval = "1m"
max_price = 10000
trade_log_file = "trade_log.csv"


### Check if market is open
def is_market_open():
    clock = api.get_clock()
    return clock.is_open


### Wait until market is open
def wait_until_open():
    clock = api.get_clock()
    open_time = clock.next_open
    current_time = clock.timestamp

    wait_time = (open_time - current_time).total_seconds()
    if wait_time > 0:
        print(f"Market is closed. Sleeping for {wait_time} seconds")
        time.sleep(wait_time)


### Calculate pause
def get_pause():
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_int = now.replace(second=0, microsecond=0) + timedelta(
        minutes=1
    )  # change this depending on interval
    pause = math.ceil((next_int - now).seconds)
    return pause


### Initialize csv log file
def initialize_trade_log(file_path):
    if not os.path.exists(file_path):
        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Date", "Ticker", "Action", "Quantity", "Price", "Cash Balance"]
            )


### Log trade in csv file
def log_trade(file_path, ticker, action, quantity, price, cash):
    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ticker,
                action,
                quantity,
                price,
                cash,
            ]
        )


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
            and cash >= price
        ):
            # Set max acceptable quantity of shares
            if cash >= max_price:
                quantity = int(max_price / price)
            else:
                quantity = int(cash / price)

            if quantity > 0:
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
                # print(f"Buy {quantity} shares of {asset['ticker']} @ {price}\n")
                log_trade(trade_log_file, asset["ticker"], "Buy", quantity, price, cash)

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
            # print(f"Sell {quantity} shares of {asset['ticker']} @ {price}\n")
            log_trade(trade_log_file, asset["ticker"], "Sell", quantity, price, cash)

    return asset_list, cash


### MAIN ###
initialize_trade_log(trade_log_file)

while True:
    if is_market_open():
        asset_list, cash = trade(asset_list, cash)
        time.sleep(get_pause())
    else:
        wait_until_open()
