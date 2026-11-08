# Model Architecture

CyberArena AI should use a hybrid AI architecture. This is stronger than using one model only.

```text
Red Team Agent
  -> generates attack events
  -> Blue Team Detection Model
  -> Risk Scoring Model
  -> AI Explanation and Incident Report
```

## 1. Red Team Decision Model

Purpose:
Choose the attacker's next action.

Recommended first version:
Rule-based scoring.

Formula:

```text
attack_score = vulnerability_score + asset_value + access_level - defense_strength
```

Future upgrade:
Reinforcement-learning-style policy selection.

## 2. Blue Team Detection Model

Purpose:
Detect suspicious events and classify attack type.

Recommended models:

- Isolation Forest for anomaly detection
- Random Forest for attack classification
- Rule-based model as explainable baseline

Current file:
`ml_models.py`

## 3. Risk Scoring Model

Purpose:
Calculate enterprise risk.

Formula:

```text
risk = base_risk
     + attack_pressure
     - containment_strength
     - defense_bonus
```

Current file:
`models.py`

## 4. AI Explanation / Report Generator

Purpose:
Explain alerts, summarize the cyber battle, and recommend actions.

Current file:
`models.py`

Future upgrade:
Connect to an LLM API or local LLM for richer explanations.
