from kafka_utils import FRAUD_TOPIC, TRANSACTION_TOPIC, ensure_topics, make_consumer


def main():
    ensure_topics()
    consumer = make_consumer("bank-fraud-monitor", TRANSACTION_TOPIC, FRAUD_TOPIC)
    print("Monitoring both topics: transaction-events and fraud-alert-events")

    for message in consumer:
        print(f"[{message.topic}] key={message.key} value={message.value}")


if __name__ == "__main__":
    main()
