from __future__ import annotations

from collections import Counter, defaultdict, deque

from common import USER_ACTIONS_TOPIC, build_replay_consumer, poll_events, random_product_from_category, wait_for_kafka


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    consumer = build_replay_consumer(
        USER_ACTIONS_TOPIC,
        client_id="personalized-recommender-consumer",
    )

    category_preferences: dict[str, Counter[str]] = defaultdict(Counter)
    seen_products: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=10))

    print("Recommender consumer started. Press Ctrl+C to stop.")

    try:
        while True:
            for event in poll_events(consumer):
                user_id = event["user_id"]
                category = event["category"]

                category_preferences[user_id][category] += 1
                seen_products[user_id].append(event["product_id"])

                favorite_category = category_preferences[user_id].most_common(1)[0][0]
                suggestion = random_product_from_category(
                    favorite_category,
                    exclude_ids=set(seen_products[user_id]),
                )

                print(
                    f"[Recommender] {user_id:<4} liked '{favorite_category:<11}' "
                    f"-> suggest: {suggestion['name']}"
                )
    except KeyboardInterrupt:
        print("\nStopping recommender consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
