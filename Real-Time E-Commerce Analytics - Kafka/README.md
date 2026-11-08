# Real-Time E-Commerce Analytics (Kafka)

Streams synthetic user activity (views, cart adds, purchases) through Apache Kafka
and runs three independent real-time analytics services on top of it.

Built on Option 3 (Real-Time Recommendations) from the project requirements,
adapted from movies → products.

## Architecture

```
                       Kafka (KRaft, docker)
                              │
  user_activity_producer.py ──┤
   (clicks, views, cart,      │  topic: user-activity
    purchases — synthetic)    │
                              ├──▶ trending_consumer.py
                              │     (rolling count of views per
                              │      product → "top 5 trending")
                              │
                              └──▶ recommender_consumer.py
                                    (per-user recent views → suggests
                                     same-category products)

                              ── topic: purchases ──▶ revenue_consumer.py
                                    (running revenue + per-category totals)
```

- **1 producer**, **2 topics** (`user-activity`, `purchases`), **3 consumer groups**.
- All three consumers read independently — classic Kafka pub-sub pattern.
- KRaft mode single-node Kafka (no Zookeeper). Auto-create topics enabled.

## How to run

```bash
# 1. Start Kafka
docker compose up -d

# 2. (one time) Set up Python env
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. Open 4 terminals (in venv each) and run, in this order:
python user_activity_producer.py
python trending_consumer.py
python recommender_consumer.py
python revenue_consumer.py
```

Each consumer uses a unique `group.id` so they all replay events from the
beginning (`auto.offset.reset: earliest`).

## Stack

- Apache Kafka 3.7.2 (KRaft mode, single broker)
- Python 3.12 + `confluent-kafka`
- Docker Compose

## Next iterations

- Spark Structured Streaming on `user-activity` for windowed aggregations.
- Redis for caching personalized recommendations.
- Real dataset (e.g. Kaggle "E-commerce User Behavior").
- Dashboard (Streamlit / Grafana) reading from a sink topic.
