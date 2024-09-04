### trader-joes

## Overview

Simple trading bot running on SMA logic

## Installation

**Must have python and pip**
Run `pip install -r requirements.txt` in a venv
Set up a settings.py with the following information:

1. api_key: string
2. api_secret: string
3. base_url: string
4. asset_list: list of dictionaries (e.g., `[{"ticker": "ABC", "yfticker": yf.Ticker("ABC"), "holding": False), "quantity": 0}]`)
5. email: string (optional if you want trading instructions to be emailed to you)
6. password: string (optional app specific password for gmail if you want trading instructions to be emailed to you)

## Trading

Run `python trade.py` and uncomment the while loop for a real-time trading simulation. Parameters can be changed to execute trades at different intervals based on different periods of historical data. Uncomment the send_email function if you do not want the trades to be emailed to you.

## Back Testing

Run `python test.py` to test an algoritm against the SPY. Trades are executed daily based on data from the past year, though these parameters can all be changed.

Test on 8/29: Using fast interval of 10 days and slow interval of 50 days

Initial Balance: $100000

Final Cash Balance: $60297.517475128174

Final Portfolio Value: $182044.0571784973

Total Return: 82.04%
