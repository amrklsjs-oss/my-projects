# CyberArena AI

CyberArena AI is a safe, browser-based graduation project prototype for an autonomous Red Team vs Blue Team cyber range.

## What It Shows

- A simulated company network and attack graph
- Red Team AI action planning
- Blue Team AI detection and containment
- Live SOC timeline
- Active alert queue
- Enterprise risk scoring
- What-if defenses
- Auto-generated incident report

## Files

- `index.html`, `styles.css`, `app.js`: polished browser demo
- `streamlit_app.py`: Streamlit dashboard version
- `models.py`: Red Team / Blue Team simulation logic and risk model
- `ml_models.py`: Blue Team detection baseline model
- `train_models.py`: sample model evaluation script
- `data/sample_cyber_events.csv`: starter synthetic event dataset
- `docs/`: dataset plan, model architecture, and team roles
- `requirements.txt`: Python dependencies
- `server.js`: optional local static server for the browser demo

## How To Run

Option 1: open `index.html` in a browser.

Option 2: run the local server:

```bash
node server.js
```

Then open:

```text
http://127.0.0.1:8765
```

Option 3: run the Streamlit version:

```bash
streamlit run streamlit_app.py
```

Option 4: run the sample model evaluation:

```bash
python train_models.py
```

The browser demo needs no installation or internet connection. The Streamlit version requires Streamlit installed in your Python environment.

## Safety

This prototype does not run real attacks. It models attack and defense behavior for education, presentation, and defensive security planning.
