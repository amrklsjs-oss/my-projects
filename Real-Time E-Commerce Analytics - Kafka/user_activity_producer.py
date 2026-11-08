from confluent_kafka import Producer
import json
import uuid
import time
import random

producer = Producer({"bootstrap.servers": "localhost:9092"})

# Small e-commerce catalog: 15 products across 3 categories.
CATALOG = [
    {"product_id": "P-101", "name": "Laptop",       "category": "electronics", "price": 15000},
    {"product_id": "P-102", "name": "Headphones",   "category": "electronics", "price": 800},
    {"product_id": "P-103", "name": "Smartphone",   "category": "electronics", "price": 9000},
    {"product_id": "P-104", "name": "Mouse",        "category": "electronics", "price": 350},
    {"product_id": "P-105", "name": "Keyboard",     "category": "electronics", "price": 1200},

    {"product_id": "P-201", "name": "T-Shirt",      "category": "clothing",    "price": 250},
    {"product_id": "P-202", "name": "Jeans",        "category": "clothing",    "price": 700},
    {"product_id": "P-203", "name": "Sneakers",     "category": "clothing",    "price": 1500},
    {"product_id": "P-204", "name": "Jacket",       "category": "clothing",    "price": 1800},
    {"product_id": "P-205", "name": "Cap",          "category": "clothing",    "price": 200},

    {"product_id": "P-301", "name": "Python Book",  "category": "books",       "price": 400},
    {"product_id": "P-302", "name": "Data Science", "category": "books",       "price": 550},
    {"product_id": "P-303", "name": "Algorithms",   "category": "books",       "price": 600},
    {"product_id": "P-304", "name": "Clean Code",   "category": "books",       "price": 450},
    {"product_id": "P-305", "name": "Deep Work",    "category": "books",       "price": 300},
]

USERS = [f"U-{i}" for i in range(1, 21)]  # 20 users

EVENT_TYPES = ["view", "view", "view", "view", "view", "view", "view",  # 70% view
               "add_to_cart", "add_to_cart",                              # 20% cart
               "purchase"]                                                # 10% purchase

print("E-commerce User Activity Producer started...")
print(f"Catalog: {len(CATALOG)} products | Users: {len(USERS)}")
print("Streaming events every 0.5s. Ctrl+C to stop.\n")

try:
    while True:
        product = random.choice(CATALOG)
        event = {
            "event_id":   str(uuid.uuid4()),
            "user_id":    random.choice(USERS),
            "product_id": product["product_id"],
            "product":    product["name"],
            "category":   product["category"],
            "price":      product["price"],
            "event_type": random.choice(EVENT_TYPES),
            "timestamp":  time.time(),
        }

        # Always publish to user-activity (full event stream).
        producer.produce(
            "user-activity",
            key=event["user_id"],
            value=json.dumps(event).encode("utf-8"),
        )

        # Purchases go to a dedicated topic for the revenue consumer.
        if event["event_type"] == "purchase":
            producer.produce(
                "purchases",
                key=event["user_id"],
                value=json.dumps(event).encode("utf-8"),
            )

        producer.poll(0)
        print(f"[{event['event_type']:12}] {event['user_id']} -> {event['product']:13} ({event['category']})")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nFlushing and shutting down producer...")
    producer.flush()
    print("Done.")
