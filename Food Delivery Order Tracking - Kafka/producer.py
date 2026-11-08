import time
from uuid import uuid4

from kafka_utils import ORDER_TOPIC, ensure_topics, make_producer


def main():
    ensure_topics()
    producer = make_producer()

    orders = [
        {"customer": "Amr", "restaurant": "Pizza House", "total": 250},
        {"customer": "Omar", "restaurant": "Burger Station", "total": 180},
        {"customer": "Laila", "restaurant": "Sushi Corner", "total": 420},
    ]

    for order in orders:
        order_id = "ORD-" + str(uuid4())[:8].upper()
        event = {
            "eventType": "ORDER_CREATED",
            "orderId": order_id,
            "customer": order["customer"],
            "restaurant": order["restaurant"],
            "total": order["total"],
            "source": "order-producer",
        }
        producer.send(ORDER_TOPIC, key=order_id, value=event)
        producer.flush()
        print(f"Sent to {ORDER_TOPIC}: {event}")
        time.sleep(2)

    producer.close()


if __name__ == "__main__":
    main()
