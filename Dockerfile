FROM python:3.10-slim

# Install dependencies
WORKDIR /app
COPY main.py .
COPY alpaca_trade.py .
COPY settings.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

# Run  script
CMD ["python", "main.py"]
