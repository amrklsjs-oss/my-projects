from __future__ import annotations

import json
import random
import time
from typing import Any

from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaConsumer, TopicPartition
from kafka.errors import TopicAlreadyExistsError


BOOTSTRAP_SERVERS = "localhost:9092"
USER_ACTIONS_TOPIC = "user-actions"
ORDERS_TOPIC = "orders"
AI_INSIGHTS_TOPIC = "ai-insights"

PRODUCTS = [
    {"id": "P-01", "name": "Smartphone", "category": "electronics", "price": 9000.0},
    {"id": "P-02", "name": "Laptop", "category": "electronics", "price": 18000.0},
    {"id": "P-03", "name": "Headphones", "category": "electronics", "price": 1200.0},
    {"id": "P-04", "name": "Smart Watch", "category": "electronics", "price": 3500.0},
    {"id": "P-05", "name": "T-Shirt", "category": "clothing", "price": 350.0},
    {"id": "P-06", "name": "Jacket", "category": "clothing", "price": 1500.0},
    {"id": "P-07", "name": "Sneakers", "category": "clothing", "price": 2200.0},
    {"id": "P-08", "name": "Backpack", "category": "clothing", "price": 900.0},
    {"id": "P-09", "name": "Clean Code", "category": "books", "price": 750.0},
    {"id": "P-10", "name": "Algorithms", "category": "books", "price": 850.0},
    {"id": "P-11", "name": "Data Science Book", "category": "books", "price": 950.0},
    {"id": "P-12", "name": "Kafka Guide", "category": "books", "price": 650.0},
    {"id": "P-13", "name": "Coffee Maker", "category": "home", "price": 2400.0},
    {"id": "P-14", "name": "Desk Lamp", "category": "home", "price": 600.0},
    {"id": "P-15", "name": "Office Chair", "category": "home", "price": 4200.0},
]

USERS = [f"U-{i}" for i in range(1, 21)]


def create_topics() -> None:
    admin = KafkaAdminClient(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        client_id="ecommerce-topic-admin",
    )
    try:
        existing_topics = set(admin.list_topics())
        topics = [
            NewTopic(USER_ACTIONS_TOPIC, num_partitions=1, replication_factor=1),
            NewTopic(ORDERS_TOPIC, num_partitions=1, replication_factor=1),
            NewTopic(AI_INSIGHTS_TOPIC, num_partitions=1, replication_factor=1),
        ]
        missing_topics = [topic for topic in topics if topic.name not in existing_topics]

        if missing_topics:
            try:
                admin.create_topics(new_topics=missing_topics, validate_only=False)
                print("Created missing Kafka topics.")
            except TopicAlreadyExistsError:
                pass
    finally:
        admin.close()


def wait_for_kafka(max_attempts: int = 30) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            create_topics()
            return
        except Exception as exc:
            if attempt == max_attempts:
                raise
            print(f"Kafka is not ready yet ({exc}). Retrying...")
            time.sleep(2)


def dumps(event: dict[str, Any]) -> bytes:
    return json.dumps(event, ensure_ascii=True).encode("utf-8")


def loads(value: bytes) -> dict[str, Any]:
    return json.loads(value.decode("utf-8"))


def build_replay_consumer(topic: str, client_id: str) -> KafkaConsumer:
    return build_manual_consumer(topic, client_id, start_at_beginning=True)


def build_live_consumer(topic: str, client_id: str) -> KafkaConsumer:
    return build_manual_consumer(topic, client_id, start_at_beginning=False)


def build_manual_consumer(topic: str, client_id: str, start_at_beginning: bool) -> KafkaConsumer:
    consumer = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        client_id=client_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=loads,
    )

    partitions = consumer.partitions_for_topic(topic)
    while partitions is None:
        time.sleep(1)
        partitions = consumer.partitions_for_topic(topic)

    topic_partitions = [TopicPartition(topic, partition) for partition in partitions]
    consumer.assign(topic_partitions)
    if start_at_beginning:
        consumer.seek_to_beginning(*topic_partitions)
    else:
        consumer.seek_to_end(*topic_partitions)
    return consumer


def poll_events(consumer: KafkaConsumer, timeout_ms: int = 1000):
    records = consumer.poll(timeout_ms=timeout_ms)
    for partition_records in records.values():
        for message in partition_records:
            yield message.value


def random_product_from_category(category: str, exclude_ids: set[str] | None = None) -> dict[str, Any]:
    exclude_ids = exclude_ids or set()
    candidates = [
        product
        for product in PRODUCTS
        if product["category"] == category and product["id"] not in exclude_ids
    ]
    if not candidates:
        candidates = [product for product in PRODUCTS if product["id"] not in exclude_ids]
    if not candidates:
        candidates = PRODUCTS
    return random.choice(candidates)
