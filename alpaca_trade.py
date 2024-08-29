from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data import StockHistoricalDataClient, StockTradesRequest
from alpaca.data.live import StockDataStream
from settings import api_key, api_secret, base_url, asset_list
from datetime import datetime, timedelta
from alpaca_trade_api import REST
import pandas_ta as ta
import math, time

api = REST(api_key, api_secret, base_url, api_version="v2")

interval_fast = 10
interval_slow = 50
max_price = 10000


### Calculate pause
def get_pause():
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_min = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    pause = math.ceil((next_min - now).seconds)
    return pause


### Trade
def trade(asset_list):
    for asset in asset_list:
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        df = asset["yfticker"].history(start=start_date, interval="1m")

        df["SMA_fast"] = ta.sma(df["Close"], interval_fast)
        df["SMA_slow"] = ta.sma(df["Close"], interval_slow)

        price = df.iloc[-1]["Close"]
        if price > max_price:
            quantity = 1
        else:
            quantity = int(max_price / price)

        if df.iloc[-1]["SMA_fast"] > df.iloc[-1]["SMA_slow"] and not asset["holding"]:

            # Execute trade
            api.submit_order(
                symbol=asset["ticker"],
                qty=quantity,
                side="buy",
                type="market",
                time_in_force="day",
            )

            asset["holding"] = True
            print(f"Buy {asset['ticker']} @ {price}")
        elif df.iloc[-1]["SMA_fast"] < df.iloc[-1]["SMA_slow"] and asset["holding"]:

            # Execute trade
            api.submit_order(
                symbol=asset["ticker"],
                qty=quantity,
                side="sell",
                type="market",
                time_in_force="day",
            )

            asset["holding"] = False
            print(f"Sell {asset['ticker']} @ {price}")


while True:
    trade(asset_list)
    time.sleep(get_pause())
