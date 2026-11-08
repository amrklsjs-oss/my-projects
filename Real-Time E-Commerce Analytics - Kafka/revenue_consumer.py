from confluent_kafka import Consumer
import json
import uuid

group_id = f"revenue-{uuid.uuid4()}"

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group_id,
    "auto.offset.reset": "earliest",
})

consumer.subscribe(["purchases"])

total_revenue = 0.0
order_count   = 0
by_category   = {}

print("Revenue Consumer started...")
print("Listens on 'purchases' topic. Tracks running revenue + per-category totals.\n")

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Error:", msg.error())
        continue

    purchase = json.loads(msg.value().decode())

    price    = float(purchase["price"])
    category = purchase["category"]

    order_count   += 1
    total_revenue += price
    by_category[category] = by_category.get(category, 0.0) + price

    print(f"\n[Revenue] Order #{order_count} | {purchase['user_id']} bought "
          f"{purchase['product']} (${price:.2f})")
    print(f"          Total revenue so far: ${total_revenue:,.2f}")
    print(f"          By category: " +
          ", ".join(f"{c}=${v:,.2f}" for c, v in by_category.items()))
