# Dataset Plan

Use public datasets for training and evaluation, then use CyberArena's own generated events for the live demo.

## Recommended Public Datasets

### 1. CICIDS2017

Use for intrusion detection, brute force, DoS/DDoS, web attacks, botnet, infiltration, and port scan.

Download source:
https://www.unb.ca/cic/datasets/ids-2017.html

Best file to start with:
`MachineLearningCSV.zip`

Why it fits:
- Labeled CSV files
- Common attack categories
- Good for Random Forest and Isolation Forest experiments

### 2. UNSW-NB15

Use for multi-class attack classification.

Download source:
https://research.unsw.edu.au/projects/unsw-nb15-dataset

Why it fits:
- Around 2.5M records
- Nine attack families
- Good for comparing classifiers

### 3. TON_IoT

Use for the advanced version of the project.

Download source:
https://research.unsw.edu.au/projects/toniot-datasets

Why it fits:
- Network, Windows, Linux, and IoT telemetry
- Good for threat hunting and AI-based cybersecurity research

### 4. LANL Cyber Security Dataset

Use for enterprise-style Blue Team detection and red-team ground truth.

Download source:
https://csr.lanl.gov/data/cyber1/

Why it fits:
- Authentication logs
- Process logs
- DNS
- Network flows
- Red-team compromise events

## What To Use In The First Version

Start with:

1. CyberArena `data/sample_cyber_events.csv`
2. CICIDS2017 MachineLearningCSV
3. UNSW-NB15 CSV files

## Dataset Folder Structure

```text
data/
  sample_cyber_events.csv
  sample_predictions.json
  raw/
    cicids2017/
    unsw-nb15/
    ton-iot/
    lanl/
  processed/
    train.csv
    test.csv
```

Do not commit very large public datasets to GitHub. Keep the download links and preprocessing scripts instead.
