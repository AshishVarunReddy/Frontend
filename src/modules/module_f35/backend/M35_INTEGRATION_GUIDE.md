# Module M35 - Data Flow Integration Guide

## Architecture Overview

Module M35 (Therapy Effectiveness Dashboard) operates in a four-tier healthcare data architecture:

```
┌─────────────────────────────────────┐
│ DATA COLLECTION LAYER (M1-M6, ... ) │  ← Collects patient therapy data
├─────────────────────────────────────┤
│  M35 PROCESSING & ANALYSIS LAYER    │  ← Aggregates & analyzes
├─────────────────────────────────────┤
│ DECISION SUPPORT LAYER (M13-M24)    │  ← Clinical decision making
├─────────────────────────────────────┤
│ SECURITY & DELIVERY LAYER(M37-M42)  │  ← Secure delivery
├─────────────────────────────────────┤
│ STORAGE LAYER                       │  ← In-memory store
└─────────────────────────────────────┘
```

## Setup Instructions

### 1. Start M35 Backend API

```bash
# Navigate to backend directory
cd C:\Users\prath\OneDrive\Desktop\DBMS_PROJECT\Frontend\src\modules\module_f35\backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (.env file)
# M35_API_BASE_URL=http://localhost:5000

# Run the Flask server
python api_m35.py
```

The API will be available at: `http://localhost:5000`

### 2. Verify Backend Health

```bash
curl http://localhost:5000/api/m35/health
```

Expected response:
```json
{
  "status": "healthy",
  "module": "M35 - Therapy Effectiveness Dashboard",
  "database": "connected"
}
```

## Data Flow: Collection Layer → M35 → DSL

### Step 1: Data Ingestion from Collection Layer

The Collection Layer modules (M1-M6, M25-M30, M43-M48) send raw clinical data to M35.

#### Example: Ingest Therapy Data (from M1 - Patient Demographics)

```python
import requests

api_url = "http://localhost:5000"

# POST therapy data
therapy_payload = {
    "name": "Chemo Regimen A",
    "therapy_type": "Chemotherapy",
    "start_date": "2026-01-10",
    "end_date": "2026-03-10",
    "cost_per_cycle": 12000,
    "source_module": "M1"  # Collection module source
}

response = requests.post(
    f"{api_url}/api/m35/ingest/therapy",
    json=therapy_payload
)

therapy_id = response.json()["therapy_id"]
print(f"Therapy created: {therapy_id}")
```

#### Example: Ingest Patient Response (from M2 - Chronic Disease Records)

```python
response_payload = {
    "therapy_id": therapy_id,
    "patient_id": "P120",
    "clinical_improvement": 65,      # % improvement (0-100)
    "symptom_relief": 58,             # % symptom relief (0-100)
    "survival_days": 240,             # days
    "response_grade": "PR",           # PR=Partial Response, CR=Complete, etc.
    "source_module": "M2"             # Source collection module
}

response = requests.post(
    f"{api_url}/api/m35/ingest/response",
    json=response_payload
)
```

#### Example: Ingest Adverse Events (from M5 - Allergy & Immunization)

```python
side_effect_payload = {
    "therapy_id": therapy_id,
    "patient_id": "P120",
    "adverse_event": "Nausea",
    "toxicity_grade": 2,              # 0-5 scale
    "tolerability": "Moderate",       # Low/Moderate/High
    "source_module": "M5"
}

response = requests.post(
    f"{api_url}/api/m35/ingest/side-effect",
    json=side_effect_payload
)
```

#### Example: Ingest Cost Analysis (from M25 - Cost/Billing)

```python
cost_payload = {
    "therapy_id": therapy_id,
    "cycles": 4,
    "total_cost": 48000,
    "qalys": 0.65,                    # Quality-adjusted life years
    "source_module": "M25"
}

response = requests.post(
    f"{api_url}/api/m35/ingest/cost-analysis",
    json=cost_payload
)
```

### Step 2: M35 Data Processing & Aggregation

M35 processes and aggregates the collected data:

#### GET All Therapies

```bash
curl "http://localhost:5000/api/m35/therapy?limit=10"
```

#### GET Therapy Metrics (Benefit-Risk Analysis)

```bash
curl "http://localhost:5000/api/m35/metrics/{therapy_id}"
```

Response includes:
- `avg_improvement`: Average clinical improvement percentage
- `avg_symptom_relief`: Average symptom relief
- `avg_toxicity_grade`: Average toxicity grade (safety metric)
- `benefit_risk_index`: Calculated as: benefit_score / (1 + toxicity)
- `cost_per_qaly`: Cost effectiveness metric

### Step 3: Send Recommendations to Decision Support Layer

M35 aggregates top therapies and sends recommendations to DSL (M13-M24):

#### GET Recommendations

```bash
curl "http://localhost:5000/api/m35/recommendation?limit=5"
```

Response: Top 5 therapies ranked by benefit-risk index and cost-effectiveness

#### POST Recommendation to DSL

```python
recommendation_payload = {
    "recommendation_data": {
        "therapy_id": therapy_id,
        "name": "Chemo Regimen A",
        "benefit_risk_index": 2.45,
        "cost_per_qaly": 18500.00
    },
    "target_dsl_module": "M13",       # Which DSL module receives this
    "patient_id": "P120",
    "urgency": "high"                 # high/medium/low
}

response = requests.post(
    "http://localhost:5000/api/m35/recommendation/send-to-dsl",
    json=recommendation_payload
)
```

## Using the Frontend with APIs

The Streamlit frontend (`therapy_effectiveness_dashboard.py`) is pre-configured to use the APIs:

### Initialize API Client

```python
from src.modules.module_f35.api_client import get_api_client

# Get cached API client
api_client = get_api_client("http://localhost:5000")

# Check health
is_healthy = api_client.health_check()
```

### Fetch Data Through APIs

```python
# Get therapies
therapies = api_client.get_therapies(therapy_type="Chemotherapy", limit=10)

# Get responses for specific therapy
responses = api_client.get_responses(therapy_id=therapy_id)

# Get side effects
side_effects = api_client.get_side_effects(therapy_id=therapy_id)

# Get aggregated metrics
metrics = api_client.get_metrics(therapy_id)
```

### Get and Send Recommendations

```python
# Get recommendations for DSL
recommendations = api_client.get_recommendations(limit=5)

# Send to Decision Support Layer
response = api_client.send_recommendation_to_dsl(
    recommendation_data=recommendations[0],
    target_dsl_module="M13",
    patient_id="P120",
    urgency="high"
)
```

## API Endpoints Summary

### Ingestion Endpoints (Collection Layer → M35)

| Endpoint | Method | Purpose | Source Module |
|----------|--------|---------|---|
| `/api/m35/ingest/therapy` | POST | Ingest therapy data | M1 |
| `/api/m35/ingest/response` | POST | Ingest patient responses | M2 |
| `/api/m35/ingest/side-effect` | POST | Ingest adverse events | M5 |
| `/api/m35/ingest/cost-analysis` | POST | Ingest cost data | M25 |

### Retrieval Endpoints (M35 Processing)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/m35/therapy` | GET | List all therapies |
| `/api/m35/therapy/{id}` | GET | Get therapy details |
| `/api/m35/response` | GET | Get responses (with filters) |
| `/api/m35/side-effect` | GET | Get side effects (with filters) |
| `/api/m35/metrics/{id}` | GET | Get aggregated metrics (benefit-risk) |

### Decision Support Layer Endpoints (M35 → DSL)

| Endpoint | Method | Purpose | Target Layer |
|----------|--------|---------|---|
| `/api/m35/recommendation` | GET | Get recommendations | M13-M24 |
| `/api/m35/recommendation/send-to-dsl` | POST | Send to DSL | M13-M24 |

### Utility

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/m35/health` | GET | Health check |

## Data Model

### Therapy Document
```json
{
  "_id": "ObjectId",
  "name": "Chemo Regimen A",
  "therapy_type": "Chemotherapy",
  "start_date": "2026-01-10",
  "end_date": "2026-03-10",
  "cost_per_cycle": 12000,
  "source_module": "M1",
  "created_at": "2026-03-18T...",
  "updated_at": "2026-03-18T..."
}
```

### Response Document
```json
{
  "_id": "ObjectId",
  "therapy_id": "therapy_id_value",
  "patient_id": "P120",
  "clinical_improvement": 65,
  "symptom_relief": 58,
  "survival_days": 240,
  "response_grade": "PR",
  "source_module": "M2",
  "recorded_at": "2026-02-05T..."
}
```

### Side Effect Document
```json
{
  "_id": "ObjectId",
  "therapy_id": "therapy_id_value",
  "patient_id": "P120",
  "adverse_event": "Nausea",
  "toxicity_grade": 2,
  "tolerability": "Moderate",
  "source_module": "M5",
  "noted_at": "2026-02-06T..."
}
```

### Metrics Output (Benefit-Risk Analysis)
```json
{
  "therapy_id": "therapy_id_value",
  "avg_improvement": 65.0,
  "avg_symptom_relief": 58.0,
  "avg_survival_days": 240.0,
  "avg_toxicity_grade": 2.0,
  "adverse_events_count": 15,
  "benefit_risk_index": 2.45,
  "cost_per_qaly": 18500.00,
  "response_count": 25
}
```

## Troubleshooting

### Backend not responding

```bash
# Check if Flask server is running
netstat -ano | findstr :5000

# No database setup required (in-memory store)
```

### Database connection error

Check `.env` file:
```
M35_API_BASE_URL=http://localhost:5000
```

### No data showing in frontend

1. Verify backend health: `curl http://localhost:5000/api/m35/health`
2. Check ingestion endpoints are receiving data
3. Ensure data is ingested through the API endpoints

## Integration with Decision Support Layer

The `/api/m35/recommendation/send-to-dsl` endpoint integrates M35 with DSL modules (M13-M24):

- **M13**: Clinical Guidelines Analysis
- **M14-M18**: Specific decision support modules
- **Recommendation Data**: Includes therapy ID, benefit-risk index, cost-effectiveness
- **Urgency**: Informs DSL of clinical priority (high/medium/low)
- **Patient ID**: Links recommendation to specific patient context

## Next Steps

1. **Start Backend**: Ensure the Flask API is running on port 5000
2. **Run Backend**: Start `api_m35.py` on port 5000
3. **Run Frontend**: Open Streamlit dashboard, verify "📤 Send to DSL" tab
4. **Integration**: Connect with Decision Support Layer endpoints once available

---

**Module M35 Architecture**: Processing and Analysis Layer  
**Connected Layers**: Collection (upstream) → DSL (downstream)  
**Updated**: March 18, 2026
