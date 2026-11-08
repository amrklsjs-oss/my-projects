from __future__ import annotations

import math
import random
from collections import Counter, deque
from typing import Any


class PurchaseIntentModel:
    """Small package-free logistic-regression model for the project demo."""

    def __init__(self) -> None:
        self.weights = [0.0] * 7
        self._train()

    def predict(self, profile: dict[str, Any]) -> float:
        features = self.features(profile)
        return self._sigmoid(sum(weight * value for weight, value in zip(self.weights, features)))

    @staticmethod
    def features(profile: dict[str, Any]) -> list[float]:
        views = float(profile.get("views", 0))
        carts = float(profile.get("add_to_cart", 0))
        purchases = float(profile.get("purchases", 0))
        recent_events = float(len(profile.get("recent_actions", [])))
        categories = profile.get("categories", Counter())
        unique_categories = float(len(categories))
        avg_price = float(profile.get("total_price", 0.0)) / max(1.0, views + carts + purchases)

        return [
            1.0,
            min(views, 12.0) / 12.0,
            min(carts, 5.0) / 5.0,
            min(purchases, 3.0) / 3.0,
            min(recent_events, 20.0) / 20.0,
            min(unique_categories, 4.0) / 4.0,
            min(avg_price, 18000.0) / 18000.0,
        ]

    def _train(self) -> None:
        rng = random.Random(42)
        training_rows = []

        for _ in range(600):
            profile = {
                "views": rng.randint(0, 14),
                "add_to_cart": rng.randint(0, 6),
                "purchases": rng.randint(0, 3),
                "recent_actions": deque(maxlen=20),
                "categories": Counter({f"cat-{i}": 1 for i in range(rng.randint(1, 4))}),
                "total_price": rng.uniform(300.0, 18000.0),
            }
            for _event in range(rng.randint(0, 20)):
                profile["recent_actions"].append("event")

            intent_signal = (
                -2.4
                + 0.20 * profile["views"]
                + 1.25 * profile["add_to_cart"]
                + 1.60 * profile["purchases"]
                + 0.05 * len(profile["recent_actions"])
                + rng.uniform(-0.8, 0.8)
            )
            label = 1.0 if intent_signal >= 0 else 0.0
            training_rows.append((self.features(profile), label))

        learning_rate = 0.28
        for _epoch in range(450):
            for features, label in training_rows:
                prediction = self._sigmoid(
                    sum(weight * value for weight, value in zip(self.weights, features))
                )
                error = prediction - label
                for index, value in enumerate(features):
                    self.weights[index] -= learning_rate * error * value

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value < -60:
            return 0.0
        if value > 60:
            return 1.0
        return 1.0 / (1.0 + math.exp(-value))


def new_user_profile() -> dict[str, Any]:
    return {
        "views": 0,
        "add_to_cart": 0,
        "purchases": 0,
        "categories": Counter(),
        "seen_products": deque(maxlen=20),
        "recent_actions": deque(maxlen=20),
        "total_price": 0.0,
    }

