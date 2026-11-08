from __future__ import annotations

from collections import defaultdict

from common import ORDERS_TOPIC, build_replay_consumer, poll_events, wait_for_kafka


def format_money(value: float) -> str:
    return f"${value:,.2f}"


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    consumer = build_replay_consumer(
        ORDERS_TOPIC,
        client_id="live-revenue-consumer",
    )

    total_revenue = 0.0
    category_revenue: dict[str, float] = defaultdict(float)

    print("Revenue consumer started. Press Ctrl+C to stop.")

    try:
        while True:
            for order in poll_events(consumer):
                price = float(order["price"])
                category = order["category"]

                total_revenue += price
                category_revenue[category] += price

                categories = ", ".join(
                    f"{name}={format_money(amount)}"
                    for name, amount in sorted(category_revenue.items())
                )

                print(
                    f"\n[Revenue] {order['order_id']} | {order['user_id']} bought "
                    f"{order['product_name']} ({format_money(price)})"
                )
                print(f"          Total revenue so far: {format_money(total_revenue)}")
                print(f"          By category: {categories}")
    except KeyboardInterrupt:
        print("\nStopping revenue consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
