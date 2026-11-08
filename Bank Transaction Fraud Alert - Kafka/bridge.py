import threading
import time

from kafka_utils import FRAUD_TOPIC, TRANSACTION_TOPIC, ensure_topics, make_consumer, make_producer


HIGH_AMOUNT_LIMIT = 10000


def transaction_to_fraud_service():
    consumer = make_consumer("transaction-to-fraud-service", TRANSACTION_TOPIC)
    producer = make_producer()
    print("Fraud detection service is listening to transaction-events...")

    for message in consumer:
        event = message.value
        if event.get("eventType") != "TRANSACTION_CREATED":
            continue

        amount = float(event["amount"])
        if amount <= HIGH_AMOUNT_LIMIT:
            print(f"Transaction is normal, no alert created: {event['transactionId']}")
            continue

        alert = {
            "eventType": "FRAUD_ALERT_CREATED",
            "transactionId": event["transactionId"],
            "accountId": event["accountId"],
            "amount": amount,
            "reason": "High amount transaction",
            "riskLevel": "HIGH",
            "source": "transaction-to-fraud-service",
        }
        producer.send(FRAUD_TOPIC, key=event["transactionId"], value=alert)
        producer.flush()
        print(f"Read {TRANSACTION_TOPIC} and sent to {FRAUD_TOPIC}: {alert}")


def fraud_to_transaction_service():
    consumer = make_consumer("fraud-to-transaction-service", FRAUD_TOPIC)
    producer = make_producer()
    print("Transaction control service is listening to fraud-alert-events...")

    for message in consumer:
        event = message.value
        if event.get("eventType") != "FRAUD_ALERT_CREATED":
            continue

        time.sleep(2)
        blocked = {
            "eventType": "TRANSACTION_BLOCKED",
            "transactionId": event["transactionId"],
            "accountId": event["accountId"],
            "status": "BLOCKED",
            "reason": event["reason"],
            "source": "fraud-to-transaction-service",
        }
        producer.send(TRANSACTION_TOPIC, key=event["transactionId"], value=blocked)
        producer.flush()
        print(f"Read {FRAUD_TOPIC} and sent back to {TRANSACTION_TOPIC}: {blocked}")


def main():
    ensure_topics()
    threading.Thread(target=transaction_to_fraud_service, daemon=True).start()
    threading.Thread(target=fraud_to_transaction_service, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
