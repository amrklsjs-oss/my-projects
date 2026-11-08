from confluent_kafka import Consumer
from collections import defaultdict, deque, Counter
import json
import uuid
import random

group_id = f"recommender-{uuid.uuid4()}"

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group_id,
    "auto.offset.reset": "earliest",
})

consumer.subscribe(["user-activity"])

# Catalog grouped by category (for picking a recommendation).
CATALOG_BY_CATEGORY = {
    "electronics": ["Laptop", "Headphones", "Smartphone", "Mouse", "Keyboard"],
    "clothing":    ["T-Shirt", "Jeans", "Sneakers", "Jacket", "Cap"],
    "books":       ["Python Book", "Data Science", "Algorithms", "Clean Code", "Deep Work"],
}

# Per-user state: recent categories viewed + products already seen.
recent_categories = defaultdict(lambda: deque(maxlen=5))
seen_products     = defaultdict(set)

print("Recommender Consumer started...")
print("Tracks each user's recent activity and suggests a product they haven't seen.\n")

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Error:", msg.error())
        continue

    event = json.loads(msg.value().decode())
    user     = event["user_id"]
    product  = event["product"]
    category = event["category"]

    recent_categories[user].append(category)
    seen_products[user].add(product)

    # Pick the user's most-frequent recent category.
    top_category = Counter(recent_categories[user]).most_common(1)[0][0]

    # Recommend something from that category they haven't seen.
    candidates = [p for p in CATALOG_BY_CATEGORY[top_category]
                  if p not in seen_products[user]]

    if candidates:
        suggestion = random.choice(candidates)
        print(f"[Recommender] {user} liked '{top_category}' "
              f"-> suggest: {suggestion}")
    else:
        print(f"[Recommender] {user} already saw everything in '{top_category}'")
