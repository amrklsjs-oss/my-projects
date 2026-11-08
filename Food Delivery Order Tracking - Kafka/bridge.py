import random
import threading
import time

from kafka_utils import DELIVERY_TOPIC, ORDER_TOPIC, ensure_topics, make_consumer, make_producer


DRIVERS = ["Ahmed", "Youssef", "Karim", "Mona"]


def order_to_delivery_service():
    consumer = make_consumer("order-to-delivery-service", ORDER_TOPIC)
    producer = make_producer()
    print("Order service is listening to order-events...")

    for message in consumer:
        event = message.value
        if event.get("eventType") != "ORDER_CREATED":
            continue

        delivery_event = {
            "eventType": "DELIVERY_ASSIGNED",
            "orderId": event["orderId"],
            "driver": random.choice(DRIVERS),
            "status": "ON_THE_WAY",
            "source": "order-to-delivery-service",
        }
        producer.send(DELIVERY_TOPIC, key=event["orderId"], value=delivery_event)
        producer.flush()
        print(f"Read {ORDER_TOPIC} and sent to {DELIVERY_TOPIC}: {delivery_event}")


def delivery_to_order_service():
    consumer = make_consumer("delivery-to-order-service", DELIVERY_TOPIC)
    producer = make_producer()
    print("Delivery service is listening to delivery-events...")

    for message in consumer:
        event = message.value
        if event.get("eventType") != "DELIVERY_ASSIGNED":
            continue

        time.sleep(3)
        order_update = {
            "eventType": "ORDER_DELIVERED",
            "orderId": event["orderId"],
            "driver": event["driver"],
            "status": "COMPLETED",
            "source": "delivery-to-order-service",
        }
        producer.send(ORDER_TOPIC, key=event["orderId"], value=order_update)
        producer.flush()
        print(f"Read {DELIVERY_TOPIC} and sent back to {ORDER_TOPIC}: {order_update}")


def main():
    ensure_topics()
    threading.Thread(target=order_to_delivery_service, daemon=True).start()
    threading.Thread(target=delivery_to_order_service, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
