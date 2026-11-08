from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from kafka import KafkaProducer

from ai_model import PurchaseIntentModel, new_user_profile
from common import (
    AI_INSIGHTS_TOPIC,
    BOOTSTRAP_SERVERS,
    USER_ACTIONS_TOPIC,
    build_live_consumer,
    dumps,
    poll_events,
    random_product_from_category,
    wait_for_kafka,
)


def segment_for(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def action_for(segment: str) -> str:
    if segment == "high":
        return "Send discount and prioritize checkout reminder"
    if segment == "medium":
        return "Show personalized product recommendation"
    return "Keep user in discovery feed"


def calibrate_score(score: float, event: dict) -> float:
    if event["action"] == "purchase":
        return max(score, 0.78)
    if event["action"] == "add_to_cart":
        return max(score, 0.54)
    return score


def update_profile(profile: dict, event: dict) -> None:
    action = event["action"]
    if action == "view":
        profile["views"] += 1
    elif action == "add_to_cart":
        profile["add_to_cart"] += 1
    elif action == "purchase":
        profile["purchases"] += 1

    profile["categories"][event["category"]] += 1
    profile["seen_products"].append(event["product_id"])
    profile["recent_actions"].append(action)
    profile["total_price"] += float(event["price"])


def favorite_category(profile: dict, fallback: str) -> str:
    if not profile["categories"]:
        return fallback
    return profile["categories"].most_common(1)[0][0]


def main() -> None:
    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()

    model = PurchaseIntentModel()
    profiles = defaultdict(new_user_profile)

    consumer = build_live_consumer(
        USER_ACTIONS_TOPIC,
        client_id="ai-purchase-intent-consumer",
    )
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        client_id="ai-insights-producer",
        acks="all",
        retries=5,
    )

    print("AI insights consumer started. Press Ctrl+C to stop.")

    try:
        while True:
            for event in poll_events(consumer):
                user_id = event["user_id"]
                profile = profiles[user_id]
                update_profile(profile, event)

                score = calibrate_score(model.predict(profile), event)
                segment = segment_for(score)
                category = favorite_category(profile, event["category"])
                suggestion = random_product_from_category(
                    category,
                    exclude_ids=set(profile["seen_products"]),
                )

                insight = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_event_id": event["event_id"],
                    "user_id": user_id,
                    "intent_score": round(score, 3),
                    "segment": segment,
                    "favorite_category": category,
                    "suggested_product": suggestion["name"],
                    "suggested_action": action_for(segment),
                    "reason": (
                        f"views={profile['views']}, carts={profile['add_to_cart']}, "
                        f"purchases={profile['purchases']}"
                    ),
                }

                producer.send(
                    AI_INSIGHTS_TOPIC,
                    key=user_id.encode("utf-8"),
                    value=dumps(insight),
                )
                print(
                    f"[AI] {user_id:<4} intent={score:.2f} segment={segment:<6} "
                    f"-> {insight['suggested_action']}"
                )
    except KeyboardInterrupt:
        print("\nStopping AI insights consumer...")
    finally:
        producer.flush(10)
        producer.close()
        consumer.close()


if __name__ == "__main__":
    main()
