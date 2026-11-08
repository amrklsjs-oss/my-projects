from confluent_kafka import Consumer
from collections import Counter
import json
import uuid

group_id = f"trending-analytics-{uuid.uuid4()}"

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group_id,
    "auto.offset.reset": "earliest",
})

consumer.subscribe(["user-activity"])

view_counts = Counter()
processed = 0

print("Trending Products Consumer started...")
print("Counts product views in real time. Prints top 5 every 10 events.\n")

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Error:", msg.error())
        continue

    event = json.loads(msg.value().decode())

    # Only views count for "trending".
    if event["event_type"] == "view":
        view_counts[event["product"]] += 1

    processed += 1

    if processed % 10 == 0:
        top = view_counts.most_common(5)
        print("\n[Trending Analytics] Top 5 Most-Viewed Products")
        print("-" * 50)
        for rank, (product, count) in enumerate(top, start=1):
            print(f"  {rank}. {product:15} -> {count} views")
        print("-" * 50)
