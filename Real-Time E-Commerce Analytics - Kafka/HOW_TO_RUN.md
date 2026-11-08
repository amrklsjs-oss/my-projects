# Real-Time E-Commerce Analytics — How to Run

Big Data Analytics project • Kafka-based real-time streaming demo.

---

## What it is

A real-time e-commerce analytics pipeline built on **Apache Kafka**. One producer
streams synthetic user activity (product views, cart adds, purchases) into Kafka.
Three independent consumer services read the same live stream and each produce
their own analytics:

- **Trending products** — top 5 most-viewed products, updated in real time.
- **Personalized recommender** — suggests products to each user based on their
  recent activity.
- **Live revenue tracker** — running revenue total and per-category breakdown.

This demonstrates the classic Kafka pattern: one event source, many independent
consumers, no coupling between services.

The project maps to **Option 3 (Real-Time Recommendations)** from the assignment
requirements, adapted from movies → e-commerce products.

---

## Architecture

```
                       Kafka (KRaft, docker)
                              │
  user_activity_producer.py ──┤
   (clicks, views, cart,      │  topic: user-activity
    purchases — synthetic)    │
                              ├──▶ trending_consumer.py
                              │     (top 5 most-viewed)
                              │
                              └──▶ recommender_consumer.py
                                    (per-user suggestions)

                              ── topic: purchases ──▶ revenue_consumer.py
                                    (running revenue + categories)
```

**1 producer • 2 topics • 3 consumer groups • 1 Kafka broker (KRaft mode, no Zookeeper).**

---

## What each file does

| File | Role |
|---|---|
| `docker-compose.yml` | Boots a single-node Apache Kafka 3.7.2 container on `localhost:9092`. |
| `user_activity_producer.py` | Generates random e-commerce events every 0.5s (15 products, 20 users, view/cart/purchase weighted 70/20/10). Publishes to `user-activity` and `purchases` topics. |
| `trending_consumer.py` | Consumes `user-activity`. Counts product views. Prints top 5 every 10 events. |
| `recommender_consumer.py` | Consumes `user-activity`. Tracks each user's recent category preference. Suggests a product they haven't seen yet. |
| `revenue_consumer.py` | Consumes `purchases`. Maintains running total revenue and per-category totals. |
| `requirements.txt` | Python dependency: `confluent-kafka`. |

---

## Prerequisites

- **Docker Desktop** (Windows or Mac). Must be running before you start.
- **Python 3.10 or newer** (`python --version` to check).
- A terminal: PowerShell on Windows, Terminal on Mac/Linux.

That's it. No Java, no Zookeeper, no Spark.

---

## How to run (step by step)

### 1. Start Docker Desktop
Open it from your Start Menu / Applications. **Wait until the whale icon stops
animating** — that means the engine is ready.

### 2. Open a terminal in the project folder
```
cd path/to/kafka-project
```

### 3. Start Kafka
```
docker compose up -d
```
First time only: this downloads the Kafka image (~300 MB). After that it's instant.

Verify it's running:
```
docker ps
```
You should see a container named `kafka` with status `Up`.

### 4. Set up the Python environment (one-time)

**Windows (PowerShell):**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Mac / Linux:**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Run the four scripts (each in its own terminal)

Open **4 separate terminals**. In each one, activate the venv (same command as
above), then run **one** script per terminal:

| Terminal | Command |
|---|---|
| 1 | `python user_activity_producer.py` |
| 2 | `python trending_consumer.py` |
| 3 | `python recommender_consumer.py` |
| 4 | `python revenue_consumer.py` |

Order matters slightly: start the producer last so the consumers are ready to
catch the very first event. But honestly, since consumers use
`auto.offset.reset: earliest`, they'll replay everything regardless — so the
order doesn't really matter.

---

## What you should see

**Producer terminal:**
```
[view        ] U-5  -> Headphones     (electronics)
[add_to_cart ] U-19 -> Jacket         (clothing)
[purchase    ] U-8  -> Smartphone     (electronics)
```

**Trending consumer:**
```
[Trending Analytics] Top 5 Most-Viewed Products
--------------------------------------------------
  1. Headphones     -> 5 views
  2. Jacket         -> 3 views
  3. Algorithms     -> 2 views
```

**Recommender:**
```
[Recommender] U-20 liked 'electronics' -> suggest: Laptop
[Recommender] U-6  liked 'books'       -> suggest: Clean Code
```

**Revenue:**
```
[Revenue] Order #4 | U-7 bought Smartphone ($9000.00)
          Total revenue so far: $10,600.00
          By category: books=$900.00, clothing=$700.00, electronics=$9,000.00
```

---

## Troubleshooting

**Docker daemon not running**
Error: `unable to get image ... daemon is not running`.
→ Open Docker Desktop and wait for the whale icon to stop animating.

**Port 9092 already in use**
Error from `docker compose up`: `bind: address already in use`.
→ Something else is on that port. Run `docker ps -a` to find old containers,
`docker rm -f <name>` to remove them. Or change the port in `docker-compose.yml`
(`"9093:9092"` for example) — but then update each Python script's
`bootstrap.servers` to `localhost:9093`.

**`pip install confluent-kafka` fails on Mac**
Try the unpinned version:
```
pip install confluent-kafka
```
If still failing on Apple Silicon: `brew install librdkafka` first, then retry.

**Consumers say "no messages"**
The producer might not be running, or you may have hit Ctrl+C on it. Restart it.

---

## How to stop everything

1. **Ctrl+C** in each of the 4 Python terminals.
2. Stop Kafka:
   ```
   docker compose down
   ```
   This removes the container but keeps the image cached, so next startup is instant.

---

## Stack summary (for the discussion)

- **Apache Kafka 3.7.2** — KRaft mode, single broker, no Zookeeper.
- **Python 3.12** + `confluent-kafka` client library.
- **Docker Compose** — single-container orchestration.
- All consumers use unique `group.id`s + `auto.offset.reset: earliest`, so each
  one replays the full event history when started.

## Next iterations (if the doctor asks "what next?")

- **Apache Spark Structured Streaming** on top of `user-activity` for windowed
  aggregations (e.g. trending products per 1-minute window).
- **Redis** to cache personalized recommendations for fast lookup.
- **Real dataset** — Kaggle "E-commerce User Behavior" for honest evaluation.
- **Dashboard** — Streamlit or Grafana reading from a sink topic.
