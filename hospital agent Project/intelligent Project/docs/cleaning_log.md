# Cleaning Log

## Missing Before
TIMESTAMP               0
HOSPITAL_ID             0
PATIENT_ID              0
age                     0
gender                  0
admission_type          0
medical_condition       0
heart_rate              0
systolic_bp             0
diastolic_bp            0
temperature             0
oxygen_saturation       0
wait_time               0
length_of_stay_hours    0
billing_amount          0

## Missing After
TIMESTAMP                 0
HOSPITAL_ID               0
PATIENT_ID                0
age                       0
gender                    0
admission_type            0
medical_condition         0
heart_rate                0
systolic_bp               0
diastolic_bp              0
temperature               0
oxygen_saturation         0
wait_time                 0
length_of_stay_hours      0
billing_amount            0
hour                      0
day                       0
week                      0
hour_sin                  0
hour_cos                  0
day_sin                   0
day_cos                   0
severity_score            0
heart_rate_lag1           0
oxygen_saturation_lag1    0
systolic_bp_lag1          0
gender_encoded            0
admission_type_encoded    0

## Steps
- Interpolation is applied per patient on numerical columns.
- Categorical values are forward/back filled per patient, then mode-imputed.
- Time-based, lag, and severity features are created once in preprocessing.
- No scaling is applied in preprocessing to prevent leakage into Person 2.
