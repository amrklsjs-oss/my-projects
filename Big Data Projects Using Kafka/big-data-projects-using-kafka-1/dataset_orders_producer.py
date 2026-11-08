from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer

from common import BOOTSTRAP_SERVERS, ORDERS_TOPIC, USER_ACTIONS_TOPIC, dumps, wait_for_kafka


DATASET_CANDIDATES = [
    Path("data.csv"),
    Path("ecommerce-data.csv"),
    Path("online_retail.csv"),
]


def find_dataset() -> Path:
    for path in DATASET_CANDIDATES:
        if path.exists():
            return path
    names = ", ".join(str(path) for path in DATASET_CANDIDATES)
    raise FileNotFoundError(
        f"Dataset file not found. Put the Kaggle CSV in this folder as one of: {names}"
    )


def clean_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> None:
    dataset_path = find_dataset()
    print(f"Using dataset: {dataset_path}")
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        client_id="ecommerce-dataset-orders-producer",
        acks="all",
        retries=5,
    )

    try:
        with dataset_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                quantity = int(clean_float(row.get("Quantity", "1"), default=1))
                unit_price = clean_float(row.get("UnitPrice", "0"))

                if quantity <= 0 or unit_price <= 0:
                    continue

                user_id = row.get("CustomerID") or "unknown"
                product_name = row.get("Description") or row.get("StockCode") or "Unknown Product"
                category = row.get("Country") or "dataset"

                event = {
                    "event_id": f"dataset-{index}",
                    "sequence": index,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": f"C-{user_id}",
                    "product_id": row.get("StockCode") or f"SKU-{index}",
                    "product_name": product_name.strip(),
                    "category": category,
                    "price": round(quantity * unit_price, 2),
                    "quantity": quantity,
                    "action": "purchase",
                    "order_id": row.get("InvoiceNo") or f"DATA-{index:06d}",
                }

                producer.send(USER_ACTIONS_TOPIC, key=event["user_id"].encode("utf-8"), value=dumps(event))
                producer.send(ORDERS_TOPIC, key=event["user_id"].encode("utf-8"), value=dumps(event))

                print(
                    f"[dataset order] {event['order_id']} | {event['user_id']} -> "
                    f"{event['product_name'][:30]:<30} ${event['price']:,.2f}"
                )
                time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping dataset producer...")
    finally:
        producer.flush(10)
        producer.close()


if __name__ == "__main__":
    main()

