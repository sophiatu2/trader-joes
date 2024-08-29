### trader-joes

## Overview

Simple trading bot running on SMA logic

## Installation

**Must have python and pip**
Run `pip install -r requirements.txt`
Set up a settings.py with the following information:

1. api_key: string
2. api_secret: string
3. base_url: string
4. asset_list: list of dictionaries (e.g., `[{"ticker": "ABC", "yfticker": yf.Ticker("ABC"), "holding": False)}]`)

## Real-time trading

Run `python trade.py` for a real-time trading simulation. Trades execute every minute based on data from the past day, though these parameters can all be changed.

## Back Testing

Run `python test.py` to test an algoritm against the SPY. Trades are executed daily based on data from the past year, though these parameters can all be changed.

Test on 8/29: Using slow interval of 10 mins and fast interval of 50 mins
Final Portfolio:
Initial Balance: $100000
Final Cash Balance: $81280.871925354
Final Portfolio Value: $131269.90103912354
Total Return: 31.27%
