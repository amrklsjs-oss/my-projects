# Real-Time E-Commerce Analytics باستخدام Kafka

المشروع ده مطابق لفكرة رقم 14:

- Stream orders and user activity
- Kafka topics: `orders` و `user-actions`
- Track revenue
- Identify best-selling products
- AI model لتوقع نية الشراء
- Live dashboard في المتصفح

## الفكرة

المشروع بيحاكي منصة تجارة إلكترونية. فيه producer بيولد أحداث users زي:

- `view`
- `add_to_cart`
- `purchase`

الأحداث بتروح إلى Kafka، وبعدها أجزاء مختلفة من المشروع تقرأ نفس البيانات وتطلع تحليلات مباشرة.

## المعمارية

```text
user_activity_producer.py
        |
        +--> Kafka topic: user-actions
        |          |
        |          +--> ai_insights_consumer.py
        |          |          |
        |          |          +--> Kafka topic: ai-insights
        |          |
        |          +--> dashboard_server.py
        |
        +--> Kafka topic: orders
                   |
                   +--> revenue_consumer.py
                   +--> best_sellers_consumer.py
                   +--> dashboard_server.py
```

## الملفات المهمة

- `docker-compose.yml`: يشغل Kafka.
- `user_activity_producer.py`: يولد user actions و orders.
- `ai_model.py`: موديل Logistic Regression بسيط بدون مكتبات خارجية.
- `ai_insights_consumer.py`: يستخدم الموديل ويتوقع purchase intent.
- `dashboard_server.py`: dashboard live على المتصفح.
- `revenue_consumer.py`: يحسب الإيرادات.
- `best_sellers_consumer.py`: يحدد المنتجات الأكثر مبيعًا.
- `trending_consumer.py`: يحدد المنتجات الأكثر مشاهدة.
- `dataset_orders_producer.py`: تشغيل dataset من Kaggle لو موجودة كملف CSV.

## البرامج المطلوبة

1. Docker Desktop
2. Python 3.10 أو أحدث
3. VS Code اختياري

## التشغيل خطوة بخطوة

### 1. شغل Docker Desktop

افتح Docker Desktop واستنى لحد ما يبقى شغال بالكامل.

### 2. افتح PowerShell داخل فولدر المشروع

```powershell
cd "C:\Users\Ahmed\Documents\Codex\2026-05-12\big-data-projects-using-kafka-1"
```

### 3. شغل Kafka

```powershell
docker compose up -d
```

اتأكد إنه شغال:

```powershell
docker ps
```

لازم تشوف container اسمه `kafka` وحالته `Up`.

### 4. جهز Python environment

لو البيئة موجودة ومكتبة `kafka-python-ng` اتثبتت قبل كده، مش لازم تعيد الخطوة دي.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

لو PowerShell رفض تشغيل `Activate.ps1`:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

وبعدها:

```powershell
.\.venv\Scripts\Activate.ps1
```

## تشغيل النظام الكامل

افتح 4 terminals.

في كل terminal:

```powershell
cd "C:\Users\Ahmed\Documents\Codex\2026-05-12\big-data-projects-using-kafka-1"
.\.venv\Scripts\Activate.ps1
```

Terminal 1:

```powershell
python ai_insights_consumer.py
```

Terminal 2:

```powershell
python dashboard_server.py
```

افتح المتصفح على:

```text
http://127.0.0.1:8000
```

Terminal 3:

```powershell
python user_activity_producer.py
```

Terminal 4 اختياري للشرح:

```powershell
python revenue_consumer.py
```

## Consumers اختيارية

لو عايز تعرض أجزاء التحليل في terminals إضافية:

```powershell
python best_sellers_consumer.py
```

```powershell
python trending_consumer.py
```

```powershell
python recommender_consumer.py
```

## تشغيل Dataset حقيقي من Kaggle

المشروع شغال ببيانات synthetic عشان الديمو يبقى سهل وسريع.

لو نزلت Dataset من Kaggle، حط ملف CSV داخل فولدر المشروع باسم:

```text
data.csv
```

وبدل `user_activity_producer.py` شغل:

```powershell
python dataset_orders_producer.py
```

## إيقاف المشروع

اقفل سكربتات Python بـ `Ctrl+C`.

ثم أوقف Kafka:

```powershell
docker compose down
```

