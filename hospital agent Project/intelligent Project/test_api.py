import requests

url = "http://127.0.0.1:8000/predict"

data = {
    "heart_rate": 110,
    "systolic_bp": 145,
    "diastolic_bp": 90,
    "oxygen_saturation": 92,
    "temperature": 38.2,
    "wait_time": 30
}

response = requests.post(url, json=data)

print(response.json())