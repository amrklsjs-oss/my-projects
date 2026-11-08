import json
from agent import run_agentic_system

test_samples = [
    {
        "heart_rate": 120,
        "systolic_bp": 180,
        "diastolic_bp": 110,
        "oxygen_saturation": 85,
        "temperature": 39.5,
        "wait_time": 50
    },
    {
        "heart_rate": 85,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "oxygen_saturation": 97,
        "temperature": 36.8,
        "wait_time": 10
    },
    {
        "heart_rate": 60,
        "systolic_bp": 110,
        "diastolic_bp": 70,
        "oxygen_saturation": 99,
        "temperature": 36.5,
        "wait_time": 5
    },

    # 🔴 HIGH EMERGENCY (clear critical cases)
    {
        "heart_rate": 135,
        "systolic_bp": 190,
        "diastolic_bp": 120,
        "oxygen_saturation": 82,
        "temperature": 40.0,
        "wait_time": 60
    },
    {
        "heart_rate": 125,
        "systolic_bp": 175,
        "diastolic_bp": 115,
        "oxygen_saturation": 85,
        "temperature": 39.2,
        "wait_time": 45
    },

    # 🟠 HIGH BUT LESS EXTREME
    {
        "heart_rate": 110,
        "systolic_bp": 160,
        "diastolic_bp": 100,
        "oxygen_saturation": 90,
        "temperature": 38.5,
        "wait_time": 30
    },

    # 🟡 BORDERLINE (should trigger RAG / REACT mix)
    {
        "heart_rate": 95,
        "systolic_bp": 140,
        "diastolic_bp": 90,
        "oxygen_saturation": 94,
        "temperature": 37.5,
        "wait_time": 25
    },
    {
        "heart_rate": 88,
        "systolic_bp": 135,
        "diastolic_bp": 85,
        "oxygen_saturation": 95,
        "temperature": 37.0,
        "wait_time": 20
    },

    # 🟢 NORMAL CASES
    {
        "heart_rate": 75,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "oxygen_saturation": 98,
        "temperature": 36.7,
        "wait_time": 10
    },
    {
        "heart_rate": 70,
        "systolic_bp": 115,
        "diastolic_bp": 75,
        "oxygen_saturation": 99,
        "temperature": 36.5,
        "wait_time": 5
    },

    # 🔵 VERY LOW RISK (should always be monitor)
    {
        "heart_rate": 60,
        "systolic_bp": 110,
        "diastolic_bp": 70,
        "oxygen_saturation": 99,
        "temperature": 36.3,
        "wait_time": 2
    },

    # ⚠️ EDGE NOISE CASES (to test stability)
    {
        "heart_rate": 200,
        "systolic_bp": 90,
        "diastolic_bp": 60,
        "oxygen_saturation": 88,
        "temperature": 37.0,
        "wait_time": 15
    },
    {
        "heart_rate": 50,
        "systolic_bp": 200,
        "diastolic_bp": 130,
        "oxygen_saturation": 97,
        "temperature": 36.8,
        "wait_time": 80
    },

    # 🧠 MIXED REALISTIC HOSPITAL CASES
    {
        "heart_rate": 100,
        "systolic_bp": 150,
        "diastolic_bp": 95,
        "oxygen_saturation": 92,
        "temperature": 38.0,
        "wait_time": 40
    },
    {
        "heart_rate": 85,
        "systolic_bp": 130,
        "diastolic_bp": 85,
        "oxygen_saturation": 96,
        "temperature": 37.2,
        "wait_time": 35
    }

]

for i, sample in enumerate(test_samples):
    print(f"\n=== SAMPLE {i+1} ===")
    result = run_agentic_system(sample)

    print("Predicted class:", result["predicted_class"])
    print("Score:", result["score"])
    print("Case:", result["decision_case"])
    print("Label:", result["decision_label"])
    print("Action:", result["action"])