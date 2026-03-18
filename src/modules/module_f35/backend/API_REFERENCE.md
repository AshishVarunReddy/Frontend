# M35 API Reference - Quick Guide

## Base URL
```
http://localhost:5000
```

## Endpoints Summary

### ⚡ Health Check
```
GET /api/m35/health
```
Check if backend is running.

---

## 📥 DATA COLLECTION LAYER ENDPOINTS (Ingestion)

Receive data from Collection Layer modules (M1-M6, M25-M30, M43-M48)

### 1. Ingest Therapy Data (from M1)
```
POST /api/m35/ingest/therapy

{
  "name": "Chemo Regimen A",
  "therapy_type": "Chemotherapy",
  "start_date": "2026-01-10",
  "end_date": "2026-03-10",
  "cost_per_cycle": 12000,
  "source_module": "M1"
}

Response:
{
  "status": "success",
  "therapy_id": "...",
  "message": "Therapy ingested successfully"
}
```

### 2. Ingest Patient Response (from M2)
```
POST /api/m35/ingest/response

{
  "therapy_id": "{therapy_id}",
  "patient_id": "P120",
  "clinical_improvement": 65,
  "symptom_relief": 58,
  "survival_days": 240,
  "response_grade": "PR",
  "source_module": "M2"
}

Response:
{
  "status": "success",
  "response_id": "...",
  "message": "Response recorded successfully"
}
```

### 3. Ingest Adverse Events (from M5)
```
POST /api/m35/ingest/side-effect

{
  "therapy_id": "{therapy_id}",
  "patient_id": "P120",
  "adverse_event": "Nausea",
  "toxicity_grade": 2,
  "tolerability": "Moderate",
  "source_module": "M5"
}

Response:
{
  "status": "success",
  "side_effect_id": "...",
  "message": "Side effect recorded successfully"
}
```

### 4. Ingest Cost Analysis (from M25)
```
POST /api/m35/ingest/cost-analysis

{
  "therapy_id": "{therapy_id}",
  "cycles": 4,
  "total_cost": 48000,
  "qalys": 0.65,
  "source_module": "M25"
}

Response:
{
  "status": "success",
  "cost_analysis_id": "...",
  "message": "Cost analysis recorded successfully"
}
```

---

## 📊 M35 PROCESSING ENDPOINTS (Retrieval & Analysis)

### 1. Get All Therapies
```
GET /api/m35/therapy?therapy_type=Chemotherapy&limit=10

Query Parameters:
  - therapy_type: (optional) Filter by type
  - limit: (optional) Max results, default 100

Response:
{
  "status": "success",
  "count": 5,
  "data": [
    {
      "_id": "...",
      "name": "Chemo Regimen A",
      "therapy_type": "Chemotherapy",
      ...
    }
  ]
}
```

### 2. Get Therapy Details
```
GET /api/m35/therapy/{therapy_id}

Response:
{
  "status": "success",
  "data": {
    "_id": "...",
    "name": "Chemo Regimen A",
    "therapy_type": "Chemotherapy",
    "start_date": "2026-01-10",
    "end_date": "2026-03-10",
    "cost_per_cycle": 12000
  }
}
```

### 3. Get Patient Responses
```
GET /api/m35/response?therapy_id=...&patient_id=P120&limit=10

Query Parameters:
  - therapy_id: (optional) Filter by therapy
  - patient_id: (optional) Filter by patient
  - limit: Max results, default 100

Response:
{
  "status": "success",
  "count": 25,
  "data": [
    {
      "_id": "...",
      "therapy_id": "...",
      "patient_id": "P120",
      "clinical_improvement": 65,
      "symptom_relief": 58,
      "survival_days": 240,
      "response_grade": "PR"
    }
  ]
}
```

### 4. Get Side Effects
```
GET /api/m35/side-effect?therapy_id=...&patient_id=P120&limit=10

Query Parameters:
  - therapy_id: (optional) Filter by therapy
  - patient_id: (optional) Filter by patient
  - limit: Max results, default 100

Response:
{
  "status": "success",
  "count": 15,
  "data": [
    {
      "_id": "...",
      "therapy_id": "...",
      "patient_id": "P120",
      "adverse_event": "Nausea",
      "toxicity_grade": 2,
      "tolerability": "Moderate"
    }
  ]
}
```

### 5. Get Therapy Metrics (Benefit-Risk Analysis)
```
GET /api/m35/metrics/{therapy_id}

Response:
{
  "status": "success",
  "data": {
    "therapy_id": "...",
    "avg_improvement": 65.0,
    "avg_symptom_relief": 58.0,
    "avg_survival_days": 240.0,
    "avg_toxicity_grade": 2.0,
    "adverse_events_count": 15,
    "benefit_risk_index": 2.45,
    "cost_per_qaly": 18500.00,
    "response_count": 25
  }
}
```

**Key Metrics Explained:**
- `benefit_risk_index` = benefit_score / (1 + toxicity)
  - Higher is better (more benefit, less risk)
  - Used for therapy ranking
- `cost_per_qaly` = total_cost / quality_adjusted_life_years
  - Lower is better (more cost-effective)
  - Used for economic analysis

---

## 📤 DECISION SUPPORT LAYER ENDPOINTS (M13-M24)

### 1. Get Therapy Recommendations
```
GET /api/m35/recommendation?limit=5

Query Parameters:
  - limit: Number of top recommendations, default 5

Response:
{
  "status": "success",
  "count": 5,
  "destination": "Decision Support Layer (M13-M18)",
  "data": [
    {
      "therapy_id": "...",
      "name": "Chemo Regimen A",
      "therapy_type": "Chemotherapy",
      "benefit_risk_index": 2.45,
      "cost_per_qaly": 18500.00,
      "response_count": 25,
      "adverse_events": 15,
      "rank_score": 2.33
    }
  ]
}
```

**Therapies ranked by:**
1. Benefit-Risk Index (higher is better)
2. Cost per QALY (lower is better)
3. Combined Rank Score for final ranking

### 2. Send Recommendation to Decision Support Layer
```
POST /api/m35/recommendation/send-to-dsl

{
  "recommendation_data": {
    "therapy_id": "...",
    "name": "Chemo Regimen A",
    "benefit_risk_index": 2.45,
    "cost_per_qaly": 18500.00
  },
  "target_dsl_module": "M13",
  "patient_id": "P120",
  "urgency": "high"
}

Query Parameters (for target module):
  - M13: Clinical Guidelines Analysis
  - M14: Treatment Planning
  - M15: Drug Interaction Detection
  - M16: Allergy Alerts
  - M17: Dosage Optimization
  - M18: Patient Monitoring

Urgency Levels:
  - "high": Critical/immediate decision needed
  - "medium": Standard decision
  - "low": Informational only

Response:
{
  "status": "success",
  "message": "Recommendation sent to Decision Support Layer",
  "payload": {
    "source_module": "M35",
    "recommendation": {...},
    "target_module": "M13",
    "patient_id": "P120",
    "urgency": "high",
    "timestamp": "2026-03-18T..."
  }
}
```

---

## 🧪 Example Usage with Python

### Using M35APIClient
```python
from src.modules.module_f35.api_client import get_api_client

# Initialize
api = get_api_client("http://localhost:5000")

# Check health
if api.health_check():
    print("Backend is running!")

# Ingest therapy from Collection Layer
result = api.ingest_therapy(
    name="Chemo A",
    therapy_type="Chemotherapy",
    start_date="2026-01-10",
    end_date="2026-03-10",
    cost_per_cycle=12000,
    source_module="M1"
)
therapy_id = result["therapy_id"]

# Get metrics
metrics = api.get_metrics(therapy_id)
print(f"Benefit-Risk Index: {metrics['benefit_risk_index']}")

# Get recommendations for DSL
recommendations = api.get_recommendations(limit=5)
for rec in recommendations:
    api.send_recommendation_to_dsl(
        recommendation_data=rec,
        target_dsl_module="M13",
        patient_id="P120",
        urgency="high"
    )
```

---

## 🔄 Complete Data Flow

```
┌─ M1: Patient Demographics
│  ├─ POST /api/m35/ingest/therapy
│
├─ M2: Chronic Disease Records
│  ├─ POST /api/m35/ingest/response
│
├─ M5: Allergy & Immunization
│  ├─ POST /api/m35/ingest/side-effect
│
└─ M25: Cost/Billing
   └─ POST /api/m35/ingest/cost-analysis

        ↓ (Aggregation)

    M35 PROCESSING

        ↓ (Analysis)

GET /api/m35/therapy            ← List therapies
GET /api/m35/response           ← List responses
GET /api/m35/side-effect        ← List adverse events
GET /api/m35/metrics/{id}       ← Benefit-Risk Analysis

        ↓ (Recommendations)

┌─ M13: Clinical Guidelines
├─ M14: Treatment Planning
├─ M15: Drug Interactions
├─ M16: Allergy Alerts
├─ M17: Dosage Optimization
└─ M18: Patient Monitoring

GET /api/m35/recommendation     ← Top therapies ranked
POST /api/m35/recommendation/send-to-dsl  ← Send to DSL
```

---

## 🛠️ Error Codes

| Status | Meaning | Solution |
|--------|---------|----------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid payload or query parameters |
| 404 | Not Found | Resource not found |
| 500 | Server Error | Backend error - check logs |

---

## 📝 Notes

- All timestamps are in ISO 8601 format with UTC timezone
- Response/Side Effect/Cost data requires valid `therapy_id`
- Metrics become available after data ingestion
- Recommendations are ordered by Rank Score (benefit-risk balance)
- DSL integration requires target module to be available

---

**Last Updated**: March 18, 2026  
**Module**: M35 - Therapy Effectiveness Dashboard  
**Architecture**: Processing & Analysis Layer
