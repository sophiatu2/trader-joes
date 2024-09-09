from settings import api_key, api_secret, base_url, tickers
from datetime import datetime, timedelta
from alpaca_trade_api import REST
from google.cloud import storage
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import math, time
import csv
import os


def get_portfolio(api):
    """Set up initial portfolio"""

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
                "yfticker": yf.Ticker(
                    position.symbol
                ),  # Assuming you're using yfinance
                "holding": True,
                "quantity": int(
                    position.qty
                ),  # Convert the quantity from string to int
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

    return asset_list, cash


def is_market_open(api):
    """Check if market is open"""
    clock = api.get_clock()
    return clock.is_open


def wait_until_open(api):
    """Wait until market is open"""
    clock = api.get_clock()
    open_time = clock.next_open
    current_time = clock.timestamp

    wait_time = (open_time - current_time).total_seconds()
    if wait_time > 0:
        print(f"Market is closed. Sleeping for {wait_time} seconds")
        time.sleep(wait_time)


### Calculate pause
def get_pause():
    """Calculate pause until next minute"""
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_int = now.replace(second=0, microsecond=0) + timedelta(
        minutes=1
    )  # change this depending on interval
    pause = math.ceil((next_int - now).seconds)
    return pause


def initialize_trade_log(file_path):
    """Create trade log at file_path if it does not exist"""
    if not os.path.exists(file_path):
        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Date", "Ticker", "Action", "Quantity", "Price", "Cash Balance"]
            )


def log_trade(file_path, ticker, action, quantity, price, cash):
    """Log trade to csv file at file_path"""
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


### For cloud
def log_to_gcs(file_name, trade_data, bucket):
    """Log trade to GCS"""
    df = pd.DataFrame(trade_data)
    csv_data = df.to_csv(index=False)

    blob = bucket.blob(file_name)
    blob.upload_from_string(csv_data)


### Trade
def trade(
    asset_list,
    cash,
    interval,
    interval_fast,
    interval_slow,
    max_price,
    api,
    bucket,
    trade_log_file,
):
    """Trade based on provided parameters"""
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

                # For terminal
                print(f"Buy {quantity} shares of {asset['ticker']} @ {price}\n")

                # For csv
                # log_trade(trade_log_file, asset["ticker"], "buy", quantity, price, cash)

                # For cloud
                trade_data = [
                    {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "ticker": asset["ticker"],
                        "side": "buy",
                        "quantity:": quantity,
                        "price": price,
                        "cash": cash,
                    }
                ]
                log_to_gcs(trade_log_file, trade_data, bucket)

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

            # For terminal
            print(f"Sell {quantity} shares of {asset['ticker']} @ {price}\n")

            # For csv
            # log_trade(trade_log_file, asset["ticker"], "Sell", quantity, price, cash)

            # For cloud
            trade_data = [
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "ticker": asset["ticker"],
                    "side": "sell",
                    "quantity:": quantity,
                    "price": price,
                    "cash": cash,
                }
            ]
            log_to_gcs(trade_log_file, trade_data, bucket)

    return asset_list, cash


### MAIN ###
def alpaca_trade():
    """Set parameters and trade while the market is open"""
    ### Parameters
    interval_fast = 10
    interval_slow = 50
    interval = "1m"
    max_price = 10000
    trade_log_file = "trade_log.csv"

    api = REST(api_key, api_secret, base_url, api_version="v2")
    asset_list, cash = get_portfolio(api)

    # For cloud
    bucket_name = "trader_joes"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # For local
    # initialize_trade_log(trade_log_file)

    # Run once
    if is_market_open(api):
        trade(
            asset_list,
            cash,
            interval,
            interval_fast,
            interval_slow,
            max_price,
            api,
            bucket,
            trade_log_file,
        )
    else:
        print("Market is closed. Exiting.")
        exit(0)

    # Run in a loop
    # while True:
    #     if is_market_open(api):
    #         asset_list, cash = trade(
    #             asset_list,
    #             cash,
    #             interval,
    #             interval_fast,
    #             interval_slow,
    #             max_price,
    #             api,
    #             bucket,
    #             trade_log_file,
    #         )
    #         # pause until next minute
    #         time.sleep(get_pause())
    #     else:
    #         # if the market is closed, wait until next open
    #         wait_until_open(api)


if __name__ == "__main__":
    alpaca_trade()
