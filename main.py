from alpaca_trade import alpaca_trade, is_market_open
from alpaca_trade_api import REST
from flask import Flask
from threading import Thread
import time

app = Flask(__name__)


def run_bot():
    alpaca_trade()


# Create a background thread
def start_bot_thread():
    bot_thread = Thread(target=run_bot)
    bot_thread.start()


# Route to check service health
@app.route("/")
def health_check():
    return "Bot is running", 200


if __name__ == "__main__":
    # Start the bot in a separate thread
    start_bot_thread()
    # Run the HTTP server to satisfy Cloud Run's HTTP requirement
    app.run(host="0.0.0.0", port=8080)
