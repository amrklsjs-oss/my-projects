from __future__ import annotations

from collections import Counter

from common import USER_ACTIONS_TOPIC, build_replay_consumer, poll_events, wait_for_kafka


def print_top_products(view_counts: Counter[str]) -> None:
    print("\n[Trending Analytics] Top 5 Most-Viewed Products")
    print("-" * 50)

    if not view_counts:
        print("No product views yet.")
        return

    for rank, (product_name, count) in enumerate(view_counts.most_common(5), start=1):
        print(f"{rank:>2}. {product_name:<20} -> {count} views")


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    consumer = build_replay_consumer(
        USER_ACTIONS_TOPIC,
        client_id="trending-products-consumer",
    )

    view_counts: Counter[str] = Counter()
    processed_events = 0

    print("Trending consumer started. Press Ctrl+C to stop.")

    try:
        while True:
            for event in poll_events(consumer):
                processed_events += 1

                if event["action"] == "view":
                    view_counts[event["product_name"]] += 1

                if processed_events % 10 == 0:
                    print_top_products(view_counts)
    except KeyboardInterrupt:
        print("\nStopping trending consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
