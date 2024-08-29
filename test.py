import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict
from settings import asset_list

### PARAMETERS ###
interval_fast = 10
interval_slow = 50
tradelog = []
initial_balance = 100000
balance = initial_balance
max_price = 10000


### BACK TEST ###
def backtest(asset_list, start_date, end_date):
    global balance
    data = {}

    for asset in asset_list:
        df = asset["yfticker"].history(start=start_date, end=end_date, interval="1d")

        df["SMA_fast"] = ta.sma(df["Close"], interval_fast)
        df["SMA_slow"] = ta.sma(df["Close"], interval_slow)

        # Create dataset of tickers and corresponding dataframes
        data[asset["ticker"]] = df

    portfolio_value = {}

    # Loop through each interval
    for i in range(0, len(df)):
        date = data[asset["ticker"]].iloc[i].names

        # Loop through each asset
        for asset in asset_list:
            df = data[asset["ticker"]]
            price = df.iloc[i]["Close"]
            # Buy logic
            if df.iloc[i]["SMA_fast"] > df.iloc[i]["SMA_slow"] and not asset["holding"]:
                # Calculate max acceptable quantity of shares
                if price > max_price:
                    quantity = 1
                else:
                    quantity = int(max_price / price)

                # Log trade
                tradelog.append(
                    {
                        "date": date,
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

                # print(f"Buy {quantity} shares of {asset['ticker']} @ {price}")

            # Sell logic
            elif df.iloc[i]["SMA_fast"] < df.iloc[i]["SMA_slow"] and asset["holding"]:
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
                balance += quantity * price
                # print(f"Sell {quantity} shares of {asset['ticker']} @ {price}")

        # Calculate portfolio value at EOD
        daily_portfolio_value = balance
        for asset in asset_list:
            if asset["holding"]:
                daily_portfolio_value += (
                    asset["quantity"] * data[asset["ticker"]].iloc[i]["Close"]
                )

        # Assign value to i days after start_date
        portfolio_value[date] = daily_portfolio_value

    # Set final balance equal to last day
    final_balance = portfolio_value[data[asset["ticker"]].iloc[-1].name]

    return portfolio_value, final_balance


### Print results
def print_summary(list_of_trades):
    results = ""

    trades_by_date = defaultdict(list)
    for trade in list_of_trades:
        trade_date = trade["date"].date()
        trades_by_date[trade_date].append(trade)

    for trade_date, list_of_trades in trades_by_date.items():
        buy_summary = []
        sell_summary = []

        for trade in list_of_trades:
            action = f"{trade['quantity']} shares of {trade['ticker']}"
            if trade["side"] == "buy":
                buy_summary.append(action)
            elif trade["side"] == "sell":
                sell_summary.append(action)

        date = trade_date.strftime("%-m/%-d/%y")
        buy_summary_str = "bought " + ", ".join(buy_summary) if buy_summary else ""
        sell_summary_str = "sold " + ", ".join(sell_summary) if sell_summary else ""

        summary = f"{date}: {buy_summary_str}{' and ' if buy_summary and sell_summary else ''}{sell_summary_str}"
        print(summary)


### Run Test ###

start_date = "2023-08-28"
end_date = "2024-08-28"

portfolio_value, final_balance = backtest(asset_list, start_date, end_date)
portfolio_df = pd.DataFrame.from_dict(
    portfolio_value, orient="index", columns=["Portfolio_Value"]
)
print(portfolio_df.head(5))

# print_summary(tradelog)
print("Final Portfolio:")
for asset in asset_list:
    print(f"{asset['ticker']}: {asset['quantity']} shares")

print(f"\nInitial Balance: ${initial_balance}")
print(f"Final Cash Balance: ${balance}")
print(f"Final Portfolio Value: ${final_balance}")
print(
    f"Total Return: {((final_balance - initial_balance) / initial_balance) * 100:.2f}%"
)

# Plot results against SPY
portfolio_df["Daily_Return"] = portfolio_df["Portfolio_Value"].pct_change()
portfolio_df["Cumulative_Return"] = (1 + portfolio_df["Daily_Return"]).cumprod()

spy_data = yf.Ticker("SPY").history(start=start_date, end=end_date, interval="1d")
spy_data["Daily_Return"] = spy_data["Close"].pct_change()
spy_data["Cumulative_Return"] = (1 + spy_data["Daily_Return"]).cumprod()

plt.figure(figsize=(12, 6))
plt.plot(
    portfolio_df.index,
    portfolio_df["Cumulative_Return"],
    label="SMA Strategy",
)
plt.plot(spy_data.index, spy_data["Cumulative_Return"], label="SPY")
plt.xlabel("Date")
plt.ylabel("Cumulative Returns")
plt.legend()
plt.title("Strategy vs SPY Cumulative Returns")
plt.show()
