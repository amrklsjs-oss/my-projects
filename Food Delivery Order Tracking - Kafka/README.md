# Task 1: Food Delivery Order Tracking with Kafka

## Idea

This project simulates a food delivery system using two Kafka topics.

- `order-events`: receives order events.
- `delivery-events`: receives delivery events.

The two topics communicate through Python services:

1. `producer.py` sends `ORDER_CREATED` events to `order-events`.
2. `bridge.py` reads `ORDER_CREATED` from `order-events`.
3. `bridge.py` sends `DELIVERY_ASSIGNED` to `delivery-events`.
4. `bridge.py` reads `DELIVERY_ASSIGNED` from `delivery-events`.
5. `bridge.py` sends `ORDER_DELIVERED` back to `order-events`.

## Event Flow

```text
ORDER_CREATED
    -> order-events
    -> Order Service
    -> delivery-events
    -> Delivery Service
    -> order-events
```

## Why this is a good simple Kafka task

It is easy to explain because every order creates a delivery event, and every delivery event updates the order status. This proves that the two topics are connected through Kafka producers and consumers.

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

You should see:

- `ORDER_CREATED` in `order-events`
- `DELIVERY_ASSIGNED` in `delivery-events`
- `ORDER_DELIVERED` back in `order-events`

## If the teacher gives another Docker file

Use the teacher Docker file to start Kafka, then run the Python scripts. If Kafka is not on `localhost:9092`, set:

```powershell
$env:KAFKA_BOOTSTRAP_SERVERS="host:port"
```
