import pandas_ta as ta
import time
import math
import smtplib
from datetime import datetime, timedelta
from settings import asset_list, email, password
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

### PARAMETERS ###
interval_fast = 10
interval_slow = 50
interval = "1d"
tradelog = []
cash = 952.30  # Cash
max_price = 10000

start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")


### Calculate pause
def get_pause():
    ### Calculates difference between now and the next minute
    now = datetime.now()
    next_int = now.replace(second=0, microsecond=0) + timedelta(days=1)
    pause = math.ceil((next_int - now).seconds)
    return pause


### Trade
def trade(asset_list, start_date, cash):
    instruction = ""
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
            cash -= quantity * price

            instruction += f"Buy {quantity} shares of {asset['ticker']} @ {price}\n"

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
            cash += quantity * price
            instruction += f"Sell {quantity} shares of {asset['ticker']} @ {price}\n"

        else:
            quantity = asset["quantity"]
            instruction += f"Hold {quantity} shares of {asset['ticker']} @ {price}\n"

    return instruction


### Send email to self
def send_email(email, password, message):
    msg = MIMEMultipart()

    msg["From"] = email
    msg["To"] = email
    msg["Subject"] = datetime.today().strftime("%Y-%m-%d") + " Trader Joes"

    msg.attach(MIMEText(message, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email, password)
        text = msg.as_string()
        server.sendmail(email, email, text)
        print("Email sent")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server.quit()


### TRADE ###
# while True:
balance = cash
for asset in asset_list:
    if asset["holding"]:
        balance += (
            asset["quantity"] * asset["yfticker"].history(period="1d")["Close"].iloc[-1]
        )
instruction = trade(asset_list, start_date, cash)
# print(instruction)

send_email(email, password, instruction)
# time.sleep(get_pause())
