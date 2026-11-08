import time
from uuid import uuid4

from kafka_utils import TRANSACTION_TOPIC, ensure_topics, make_producer


def main():
    ensure_topics()
    producer = make_producer()

    transactions = [
        {"accountId": "ACC-101", "amount": 900, "merchant": "Coffee Shop"},
        {"accountId": "ACC-202", "amount": 18500, "merchant": "Electronics Store"},
        {"accountId": "ACC-303", "amount": 650, "merchant": "Book Store"},
        {"accountId": "ACC-404", "amount": 25000, "merchant": "International Transfer"},
    ]

    for tx in transactions:
        transaction_id = "TX-" + str(uuid4())[:8].upper()
        event = {
            "eventType": "TRANSACTION_CREATED",
            "transactionId": transaction_id,
            "accountId": tx["accountId"],
            "amount": tx["amount"],
            "merchant": tx["merchant"],
            "source": "transaction-producer",
        }
        producer.send(TRANSACTION_TOPIC, key=transaction_id, value=event)
        producer.flush()
        print(f"Sent to {TRANSACTION_TOPIC}: {event}")
        time.sleep(2)

    producer.close()


if __name__ == "__main__":
    main()
