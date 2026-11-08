# Task 2: Bank Transaction Fraud Alert with Kafka

## Idea

This project simulates a simple banking fraud detection system using two Kafka topics.

- `transaction-events`: receives bank transaction events.
- `fraud-alert-events`: receives fraud alert events.

The two topics communicate through Python services:

1. `producer.py` sends `TRANSACTION_CREATED` events to `transaction-events`.
2. `bridge.py` reads transactions from `transaction-events`.
3. If the amount is greater than 10000, `bridge.py` sends `FRAUD_ALERT_CREATED` to `fraud-alert-events`.
4. `bridge.py` reads the fraud alert from `fraud-alert-events`.
5. `bridge.py` sends `TRANSACTION_BLOCKED` back to `transaction-events`.

## Event Flow

```text
TRANSACTION_CREATED
    -> transaction-events
    -> Fraud Detection Service
    -> fraud-alert-events
    -> Transaction Control Service
    -> transaction-events
```

## Why this is a good simple Kafka task

It is simple but strong for discussion because it shows real-time analytics. Kafka receives a stream of transactions, a service analyzes the amount, and suspicious transactions create alerts that update the original transaction stream.

## Run Steps

Open a terminal inside this folder.

```powershell
docker compose up -d
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Open terminal 1:

```powershell
.\.venv\Scripts\activate
python bridge.py
```

Open terminal 2:

```powershell
.\.venv\Scripts\activate
python monitor.py
```

Open terminal 3:

```powershell
.\.venv\Scripts\activate
python producer.py
```

## Expected Output

Normal transactions only appear in `transaction-events`.

High amount transactions should create:

- `FRAUD_ALERT_CREATED` in `fraud-alert-events`
- `TRANSACTION_BLOCKED` back in `transaction-events`

## If the teacher gives another Docker file

Use the teacher Docker file to start Kafka, then run the Python scripts. If Kafka is not on `localhost:9092`, set:

```powershell
$env:KAFKA_BOOTSTRAP_SERVERS="host:port"
```
