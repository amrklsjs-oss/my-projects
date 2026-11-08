from __future__ import annotations

from collections import Counter

from common import ORDERS_TOPIC, build_replay_consumer, poll_events, wait_for_kafka


def print_best_sellers(order_counts: Counter[str]) -> None:
    print("\n[Best-Selling Products] Top 5 Products by Orders")
    print("-" * 50)

    if not order_counts:
        print("No orders yet.")
        return

    for rank, (product_name, count) in enumerate(order_counts.most_common(5), start=1):
        print(f"{rank:>2}. {product_name:<20} -> {count} orders")


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    consumer = build_replay_consumer(
        ORDERS_TOPIC,
        client_id="best-selling-products-consumer",
    )

    order_counts: Counter[str] = Counter()
    processed_orders = 0

    print("Best-sellers consumer started. Press Ctrl+C to stop.")

    try:
        while True:
            for order in poll_events(consumer):
                processed_orders += 1
                order_counts[order["product_name"]] += 1

                if processed_orders % 3 == 0:
                    print_best_sellers(order_counts)
    except KeyboardInterrupt:
        print("\nStopping best-sellers consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()

