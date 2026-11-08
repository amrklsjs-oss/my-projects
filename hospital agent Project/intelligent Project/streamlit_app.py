from __future__ import annotations

import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


st.set_page_config(page_title="Healthcare Agentic Dashboard", layout="wide")


def fetch_health(api_base_url: str) -> dict | None:
    try:
        response = requests.get(f"{api_base_url}/health", timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Health check failed: {exc}")
        return None


def submit_prediction(api_base_url: str, payload: dict) -> dict | None:
    try:
        response = requests.post(f"{api_base_url}/predict", json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Prediction request failed: {exc}")
        return None


def probability_chart(probabilities: dict[str, float]) -> go.Figure:
    frame = pd.DataFrame(
        {"Class": list(probabilities.keys()), "Probability": list(probabilities.values())}
    ).sort_values("Probability", ascending=False)
    figure = px.bar(
        frame,
        x="Class",
        y="Probability",
        color="Class",
        title="Class Probabilities",
        text_auto=".2f",
    )
    figure.update_layout(showlegend=False, yaxis_title="Probability")
    return figure


def risk_gauge(score: float) -> go.Figure:
    max_range = max(1.0, score * 1.25)
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"valueformat": ".3f"},
            title={"text": "Decision Score"},
            gauge={
                "axis": {"range": [0, max_range]},
                "bar": {"color": "#d62728"},
                "steps": [
                    {"range": [0, 0.10], "color": "#b7e4c7"},
                    {"range": [0.10, 0.35], "color": "#ffe08a"},
                    {"range": [0.35, max_range], "color": "#ffb4a2"},
                ],
            },
        )
    )
    return figure


def shap_importance_chart(shap_explanation: dict[str, float]) -> go.Figure:
    frame = pd.DataFrame(
        {"Feature": list(shap_explanation.keys()), "Contribution": list(shap_explanation.values())}
    ).sort_values("Contribution", key=lambda series: series.abs(), ascending=False)
    figure = px.bar(
        frame,
        x="Contribution",
        y="Feature",
        orientation="h",
        title="SHAP Feature Importance",
        color="Contribution",
        color_continuous_scale="RdBu",
    )
    figure.update_layout(yaxis={"categoryorder": "total ascending"})
    return figure


def shap_waterfall_chart(shap_explanation: dict[str, float]) -> go.Figure:
    frame = pd.DataFrame(
        {"Feature": list(shap_explanation.keys()), "Contribution": list(shap_explanation.values())}
    )
    figure = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative"] * len(frame),
            x=frame["Feature"],
            y=frame["Contribution"],
            connector={"line": {"color": "#6c757d"}},
        )
    )
    figure.update_layout(title="SHAP Waterfall View", showlegend=False)
    return figure


def forecast_chart(forecast_payload: dict) -> go.Figure:
    forecast_30 = pd.DataFrame(forecast_payload.get("forecast_30_days", []))
    if forecast_30.empty:
        return go.Figure()

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=forecast_30["date"],
            y=forecast_30["forecast"],
            mode="lines+markers",
            name="Forecast",
            line={"color": "#1f77b4"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_30["date"],
            y=forecast_30["upper"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_30["date"],
            y=forecast_30["lower"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.15)",
            line={"width": 0},
            name="Confidence Interval",
        )
    )
    figure.update_layout(
        title=f"30-Day SARIMA Forecast ({forecast_payload.get('trend_state', 'Unknown')})",
        xaxis_title="Date",
        yaxis_title="Forecasted Severity",
    )
    return figure


st.title("Healthcare Agentic System Dashboard")

with st.sidebar:
    api_base_url = st.text_input("FastAPI Base URL", value="http://127.0.0.1:8000")
    refresh_health = st.button("Refresh System Status")

health_data = fetch_health(api_base_url) if refresh_health or "health_data" not in st.session_state else st.session_state["health_data"]
if health_data is not None:
    st.session_state["health_data"] = health_data

prediction_result = st.session_state.get("prediction_result")

st.subheader("Patient Input Panel")
with st.form("patient_input_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        heart_rate = st.number_input("Heart Rate", min_value=20.0, max_value=220.0, value=110.0)
        systolic_bp = st.number_input("Systolic BP", min_value=50.0, max_value=250.0, value=145.0)
    with col2:
        diastolic_bp = st.number_input("Diastolic BP", min_value=30.0, max_value=180.0, value=90.0)
        oxygen_saturation = st.number_input("Oxygen Saturation", min_value=50.0, max_value=100.0, value=94.0)
    with col3:
        temperature = st.number_input("Temperature", min_value=30.0, max_value=45.0, value=37.5)
        wait_time = st.number_input("Wait Time", min_value=0.0, max_value=500.0, value=45.0)

    submit = st.form_submit_button("Submit to /predict")

if submit:
    payload = {
        "heart_rate": heart_rate,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "oxygen_saturation": oxygen_saturation,
        "temperature": temperature,
        "wait_time": wait_time,
    }
    prediction_result = submit_prediction(api_base_url, payload)
    if prediction_result is not None:
        st.session_state["prediction_result"] = prediction_result

if prediction_result:
    st.subheader("Prediction Result Panel")
    left, middle, right = st.columns(3)
    left.metric("Predicted Class", prediction_result["predicted_class"])
    middle.metric("Decision Score", f"{prediction_result['score']:.4f}")
    right.metric("Decision Case", f"{prediction_result['decision_case']} - {prediction_result['decision_label']}")

    st.write("Action:", prediction_result["action"])

    st.subheader("Risk Visualization")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.plotly_chart(probability_chart(prediction_result["all_probabilities"]), use_container_width=True)
    with chart_col2:
        st.plotly_chart(risk_gauge(prediction_result["score"]), use_container_width=True)

    st.subheader("SHAP Visualization")
    shap_col1, shap_col2 = st.columns(2)
    with shap_col1:
        st.plotly_chart(shap_importance_chart(prediction_result["shap_explanation"]), use_container_width=True)
    with shap_col2:
        st.plotly_chart(shap_waterfall_chart(prediction_result["shap_explanation"]), use_container_width=True)

    st.write("SHAP Explanation")
    st.json(prediction_result["shap_explanation"])

if health_data:
    st.subheader("Forecast Panel")
    st.plotly_chart(forecast_chart(health_data["forecast"]), use_container_width=True)
    st.caption(
        f"Trend: {health_data['forecast']['trend_state']} | "
        f"ARIMA Multiplier: {health_data['forecast']['ARIMA_mult']}"
    )

    st.subheader("System Status")
    status_left, status_right = st.columns(2)
    with status_left:
        st.write("Pipeline Sequence:", " → ".join(health_data["pipeline_sequence"]))
        st.write("Decision Log Entries:", health_data["decision_log_entries"])
        st.write("Drift Triggered:", health_data["drift"]["drift_triggered"])
    with status_right:
        st.json(health_data)
