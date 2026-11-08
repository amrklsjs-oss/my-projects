from __future__ import annotations

import argparse
import json
import threading
import time
from collections import Counter, defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse

from common import (
    AI_INSIGHTS_TOPIC,
    ORDERS_TOPIC,
    USER_ACTIONS_TOPIC,
    build_replay_consumer,
    poll_events,
    wait_for_kafka,
)


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Real-Time E-Commerce Analytics</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #687385;
      --line: #d9e0e7;
      --green: #0f766e;
      --blue: #2563eb;
      --red: #dc2626;
      --amber: #b45309;
      --violet: #6d28d9;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }
    header {
      padding: 18px 24px 12px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    .header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      max-width: 1440px;
      margin: 0 auto;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
    }
    .subtitle {
      margin-top: 5px;
      color: var(--muted);
      font-size: 13px;
    }
    .status {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--green);
      font-weight: 700;
      white-space: nowrap;
      font-size: 13px;
    }
    .dot {
      width: 10px;
      height: 10px;
      background: var(--green);
      border-radius: 50%;
      box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.16);
    }
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 20px 24px 28px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .metric {
      min-height: 104px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .metric-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 700;
    }
    .metric-value {
      font-size: 28px;
      font-weight: 800;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .metric-note {
      color: var(--muted);
      font-size: 12px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 14px;
      align-items: start;
    }
    .panel {
      padding: 16px;
      min-width: 0;
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 16px;
      line-height: 1.25;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(110px, 170px) 1fr 76px;
      gap: 10px;
      align-items: center;
      min-height: 31px;
      font-size: 13px;
    }
    .bar-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bar-track {
      height: 9px;
      border-radius: 999px;
      background: #edf1f5;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: var(--blue);
      border-radius: inherit;
      min-width: 2px;
    }
    .bar-value {
      text-align: right;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 14px;
    }
    .table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .table th, .table td {
      border-bottom: 1px solid var(--line);
      padding: 9px 7px;
      text-align: left;
      vertical-align: top;
    }
    .table th {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      min-width: 62px;
      justify-content: center;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .tag.view { background: #dbeafe; color: var(--blue); }
    .tag.add_to_cart { background: #fef3c7; color: var(--amber); }
    .tag.purchase, .tag.high { background: #fee2e2; color: var(--red); }
    .tag.medium { background: #fef3c7; color: var(--amber); }
    .tag.low { background: #dcfce7; color: var(--green); }
    .ai-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px;
      margin-bottom: 8px;
      background: #fbfcfd;
    }
    .ai-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 6px;
    }
    .ai-user {
      font-weight: 800;
      color: var(--violet);
    }
    .ai-body {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .empty {
      color: var(--muted);
      min-height: 80px;
      display: grid;
      place-items: center;
      border: 1px dashed var(--line);
      border-radius: 8px;
      font-size: 13px;
      text-align: center;
      padding: 12px;
    }
    @media (max-width: 980px) {
      .metrics, .grid, .two-col { grid-template-columns: 1fr; }
      .header-row { align-items: flex-start; flex-direction: column; }
    }
    @media (max-width: 560px) {
      header, main { padding-left: 14px; padding-right: 14px; }
      h1 { font-size: 20px; }
      .bar-row { grid-template-columns: 1fr; gap: 5px; }
      .bar-value { text-align: left; }
      .table { font-size: 12px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="header-row">
      <div>
        <h1>Real-Time E-Commerce Analytics</h1>
        <div class="subtitle">Kafka topics: user-actions, orders, ai-insights</div>
      </div>
      <div class="status"><span class="dot"></span><span id="status-text">Connecting</span></div>
    </div>
  </header>
  <main>
    <section class="metrics">
      <div class="metric">
        <div class="metric-label">Total Revenue</div>
        <div class="metric-value" id="total-revenue">$0.00</div>
        <div class="metric-note" id="orders-note">0 orders processed</div>
      </div>
      <div class="metric">
        <div class="metric-label">User Actions</div>
        <div class="metric-value" id="total-events">0</div>
        <div class="metric-note">views, carts, purchases</div>
      </div>
      <div class="metric">
        <div class="metric-label">Best Seller</div>
        <div class="metric-value" id="best-seller">-</div>
        <div class="metric-note" id="best-seller-note">waiting for orders</div>
      </div>
      <div class="metric">
        <div class="metric-label">High AI Intent</div>
        <div class="metric-value" id="high-intent">0</div>
        <div class="metric-note">users currently likely to buy</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Best-Selling Products</h2>
        <div id="best-selling-bars"></div>
      </div>
      <div class="panel">
        <h2>Revenue by Category</h2>
        <div id="category-bars"></div>
      </div>
    </section>

    <section class="two-col">
      <div class="panel">
        <h2>AI Model Insights</h2>
        <div id="ai-insights"></div>
      </div>
      <div class="panel">
        <h2>Live User Actions</h2>
        <table class="table">
          <thead><tr><th>Action</th><th>User</th><th>Product</th><th>Category</th></tr></thead>
          <tbody id="events-table"></tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[char]));
    }

    function setText(id, value) {
      document.getElementById(id).textContent = value;
    }

    function renderBars(id, rows, valueKey, suffix, color) {
      const root = document.getElementById(id);
      if (!rows.length) {
        root.innerHTML = `<div class="empty">Waiting for Kafka messages...</div>`;
        return;
      }
      const max = Math.max(...rows.map(row => row[valueKey]), 1);
      root.innerHTML = rows.map(row => {
        const width = Math.max(2, Math.round((row[valueKey] / max) * 100));
        return `
          <div class="bar-row">
            <div class="bar-label" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${color}"></div></div>
            <div class="bar-value">${escapeHtml(row[valueKey])}${suffix}</div>
          </div>
        `;
      }).join("");
    }

    function renderMoneyBars(id, rows) {
      const root = document.getElementById(id);
      if (!rows.length) {
        root.innerHTML = `<div class="empty">Waiting for orders...</div>`;
        return;
      }
      const max = Math.max(...rows.map(row => row.revenue), 1);
      root.innerHTML = rows.map(row => {
        const width = Math.max(2, Math.round((row.revenue / max) * 100));
        return `
          <div class="bar-row">
            <div class="bar-label" title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:#0f766e"></div></div>
            <div class="bar-value">${money.format(row.revenue)}</div>
          </div>
        `;
      }).join("");
    }

    function renderInsights(insights) {
      const root = document.getElementById("ai-insights");
      if (!insights.length) {
        root.innerHTML = `<div class="empty">Start ai_insights_consumer.py to generate model predictions.</div>`;
        return;
      }
      root.innerHTML = insights.map(item => `
        <div class="ai-card">
          <div class="ai-top">
            <span class="ai-user">${escapeHtml(item.user_id)}</span>
            <span class="tag ${escapeHtml(item.segment)}">${escapeHtml(item.segment)} ${Math.round(item.intent_score * 100)}%</span>
          </div>
          <div class="ai-body">
            ${escapeHtml(item.suggested_action)}<br>
            Suggest: <b>${escapeHtml(item.suggested_product)}</b> in ${escapeHtml(item.favorite_category)}<br>
            ${escapeHtml(item.reason)}
          </div>
        </div>
      `).join("");
    }

    function renderEvents(events) {
      const body = document.getElementById("events-table");
      if (!events.length) {
        body.innerHTML = `<tr><td colspan="4"><div class="empty">Waiting for user actions...</div></td></tr>`;
        return;
      }
      body.innerHTML = events.map(event => `
        <tr>
          <td><span class="tag ${escapeHtml(event.action)}">${escapeHtml(event.action)}</span></td>
          <td>${escapeHtml(event.user_id)}</td>
          <td>${escapeHtml(event.product_name)}</td>
          <td>${escapeHtml(event.category)}</td>
        </tr>
      `).join("");
    }

    async function refresh() {
      try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const state = await response.json();
        setText("status-text", "Live");
        setText("total-revenue", money.format(state.total_revenue));
        setText("orders-note", `${state.total_orders} orders processed`);
        setText("total-events", state.total_events);
        setText("high-intent", state.high_intent_users);
        setText("best-seller", state.best_seller?.name || "-");
        setText("best-seller-note", state.best_seller ? `${state.best_seller.orders} orders` : "waiting for orders");
        renderBars("best-selling-bars", state.best_selling_products, "orders", "", "#2563eb");
        renderMoneyBars("category-bars", state.revenue_by_category);
        renderInsights(state.ai_insights);
        renderEvents(state.recent_events);
      } catch (error) {
        setText("status-text", "Disconnected");
      }
    }

    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


class DashboardState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.recent_events = deque(maxlen=18)
        self.recent_orders = deque(maxlen=18)
        self.ai_insights = deque(maxlen=10)
        self.product_views = Counter()
        self.product_orders = Counter()
        self.category_revenue = defaultdict(float)
        self.latest_ai_by_user = {}
        self.total_revenue = 0.0
        self.total_events = 0
        self.total_orders = 0

    def apply_user_action(self, event: dict) -> None:
        with self.lock:
            self.total_events += 1
            self.recent_events.appendleft(event)
            if event.get("action") == "view":
                self.product_views[event["product_name"]] += 1

    def apply_order(self, order: dict) -> None:
        price = float(order.get("price", 0.0))
        with self.lock:
            self.total_orders += 1
            self.total_revenue += price
            self.recent_orders.appendleft(order)
            self.product_orders[order["product_name"]] += 1
            self.category_revenue[order["category"]] += price

    def apply_ai_insight(self, insight: dict) -> None:
        with self.lock:
            self.ai_insights.appendleft(insight)
            self.latest_ai_by_user[insight["user_id"]] = insight

    def snapshot(self) -> dict:
        with self.lock:
            best_selling = [
                {"name": name, "orders": count}
                for name, count in self.product_orders.most_common(7)
            ]
            revenue_by_category = [
                {"name": name, "revenue": round(amount, 2)}
                for name, amount in sorted(
                    self.category_revenue.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ]
            best_seller = best_selling[0] if best_selling else None
            high_intent_users = sum(
                1 for insight in self.latest_ai_by_user.values() if insight.get("segment") == "high"
            )
            return {
                "total_revenue": round(self.total_revenue, 2),
                "total_events": self.total_events,
                "total_orders": self.total_orders,
                "best_seller": best_seller,
                "best_selling_products": best_selling,
                "revenue_by_category": revenue_by_category,
                "high_intent_users": high_intent_users,
                "ai_insights": list(self.ai_insights),
                "recent_events": list(self.recent_events),
                "recent_orders": list(self.recent_orders),
            }


STATE = DashboardState()


def consume_topic(topic: str, client_id: str, handler: Callable[[dict], None]) -> None:
    while True:
        consumer = None
        try:
            consumer = build_replay_consumer(topic, client_id)
            while True:
                for event in poll_events(consumer, timeout_ms=500):
                    handler(event)
        except Exception as exc:
            print(f"Dashboard consumer for {topic} failed: {exc}. Retrying...")
            time.sleep(2)
        finally:
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    pass


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_text(HTML, "text/html; charset=utf-8")
            return
        if path == "/api/state":
            self._send_json(STATE.snapshot())
            return
        self.send_error(404)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_text(self, text: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_consumer_threads() -> None:
    threads = [
        (USER_ACTIONS_TOPIC, "dashboard-user-actions", STATE.apply_user_action),
        (ORDERS_TOPIC, "dashboard-orders", STATE.apply_order),
        (AI_INSIGHTS_TOPIC, "dashboard-ai-insights", STATE.apply_ai_insight),
    ]
    for topic, client_id, handler in threads:
        thread = threading.Thread(
            target=consume_topic,
            args=(topic, client_id, handler),
            daemon=True,
        )
        thread.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live dashboard for the Kafka e-commerce project.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print("Waiting for Kafka and creating topics if needed...")
    wait_for_kafka()
    start_consumer_threads()

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

