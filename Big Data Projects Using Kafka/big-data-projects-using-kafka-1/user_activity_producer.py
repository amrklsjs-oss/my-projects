from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer

from common import (
    BOOTSTRAP_SERVERS,
    ORDERS_TOPIC,
    PRODUCTS,
    USER_ACTIONS_TOPIC,
    USERS,
    dumps,
    wait_for_kafka,
)


def build_event(sequence: int) -> dict:
    product = random.choice(PRODUCTS)
    action = random.choices(
        ["view", "add_to_cart", "purchase"],
        weights=[70, 20, 10],
        k=1,
    )[0]

    return {
        "event_id": str(uuid.uuid4()),
        "sequence": sequence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": random.choice(USERS),
        "product_id": product["id"],
        "product_name": product["name"],
        "category": product["category"],
        "price": product["price"],
        "action": action,
    }


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        client_id="ecommerce-user-activity-producer",
        acks="all",
        retries=5,
    )

    print("Producer started. Press Ctrl+C to stop.")
    sequence = 1

    try:
        while True:
            event = build_event(sequence)

            producer.send(
                USER_ACTIONS_TOPIC,
                key=event["user_id"].encode("utf-8"),
                value=dumps(event),
            )

            if event["action"] == "purchase":
                order = {
                    **event,
                    "order_id": f"ORD-{sequence:06d}",
                }
                producer.send(
                    ORDERS_TOPIC,
                    key=event["user_id"].encode("utf-8"),
                    value=dumps(order),
                )

            print(
                f"[{event['action']:<11}] {event['user_id']:<4} -> "
                f"{event['product_name']:<18} ({event['category']})"
            )

            sequence += 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.flush(10)
        producer.close()


if __name__ == "__main__":
    main()
