import json
import os
import time

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
ORDER_TOPIC = "order-events"
DELIVERY_TOPIC = "delivery-events"


def wait_for_kafka():
    for _ in range(30):
        try:
            admin = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)
            admin.close()
            return
        except NoBrokersAvailable:
            time.sleep(1)
    raise RuntimeError("Kafka is not reachable. Start Docker Compose first.")


def ensure_topics():
    wait_for_kafka()
    admin = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS, client_id="food-delivery-admin")
    topics = [
        NewTopic(name=ORDER_TOPIC, num_partitions=1, replication_factor=1),
        NewTopic(name=DELIVERY_TOPIC, num_partitions=1, replication_factor=1),
    ]
    try:
        admin.create_topics(new_topics=topics, validate_only=False)
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()


def make_producer():
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if value else None,
    )


def make_consumer(group_id, *topics):
    return KafkaConsumer(
        *topics,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
    )
