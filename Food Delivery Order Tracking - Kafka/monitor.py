from kafka_utils import DELIVERY_TOPIC, ORDER_TOPIC, ensure_topics, make_consumer


def main():
    ensure_topics()
    consumer = make_consumer("food-delivery-monitor", ORDER_TOPIC, DELIVERY_TOPIC)
    print("Monitoring both topics: order-events and delivery-events")

    for message in consumer:
        print(f"[{message.topic}] key={message.key} value={message.value}")


if __name__ == "__main__":
    main()
