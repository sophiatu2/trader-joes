import pandas_ta as ta
import time
import math
from datetime import datetime, timedelta
from settings import asset_list

### PARAMETERS ###
interval_fast = 10
interval_slow = 50
interval = "1d"
tradelog = []
initial_balance = 100000
balance = initial_balance
max_price = 10000

start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")


### Calculate pause
def get_pause():
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_min = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    pause = math.ceil((next_min - now).seconds)
    return pause


### Trade
def trade(asset_list, start_date):
    for asset in asset_list:
        df = asset["yfticker"].history(start=start_date, interval=interval)

        df["SMA_fast"] = ta.sma(df["Close"], interval_fast)
        df["SMA_slow"] = ta.sma(df["Close"], interval_slow)

        price = df.iloc[-1]["Close"]

        # Buy
        if df.iloc[-1]["SMA_fast"] > df.iloc[-1]["SMA_slow"] and not asset["holding"]:
            # Calculate max acceptable quantity of shares
            if price > max_price:
                quantity = 1
            else:
                quantity = int(max_price / price)

            # Log trade
            tradelog.append(
                {
                    "date": datetime.now(),
                    "ticker": asset["ticker"],
                    "side": "buy",
                    "price": price,
                    "quantity": quantity,
                }
            )

            # Adjust portfolio
            asset["holding"] = True
            asset["quantity"] = quantity
            balance -= quantity * price

            print(f"Buy {quantity} shares of {asset['ticker']} @ {price}")

        # Sell
        elif df.iloc[-1]["SMA_fast"] < df.iloc[-1]["SMA_slow"] and asset["holding"]:
            quantity = asset["quantity"]
            # Log trade
            tradelog.append(
                {
                    "date": datetime.now(),
                    "ticker": asset["ticker"],
                    "side": "sell",
                    "price": price,
                    "quantity": quantity,
                }
            )

            # Adjust portflio
            asset["holding"] = False
            asset["quantity"] = 0
            banace += quantity * price
            print(f"Sell {quantity} shares of {asset['ticker']} @ {price}")


### REAL-TIME TRADE SIMULATION ###
while True:
    trade(asset_list, start_date)
    time.sleep(get_pause())
