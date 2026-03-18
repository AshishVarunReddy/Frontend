# Module M35 - Quick Start Checklist ✅

## Pre-Setup
- [ ] Python 3.8+ installed
- [ ] Git repository ready

## Environment Setup

### Step 1: Install Backend Dependencies
```bash
cd C:\Users\prath\OneDrive\Desktop\DBMS_PROJECT\Frontend\src\modules\module_f35\backend
pip install -r requirements.txt
```
**Expected output**: All packages installed successfully

### Step 2: Start M35 Backend API
```bash
cd C:\Users\prath\OneDrive\Desktop\DBMS_PROJECT\Frontend\src\modules\module_f35\backend
python api_m35.py
```
**Expected output**:
```
 * Serving Flask app ...
 * Running on http://127.0.0.1:5000
```

### Step 3: Test Backend (New Terminal)
```bash
cd C:\Users\prath\OneDrive\Desktop\DBMS_PROJECT\Frontend\src\modules\module_f35\backend
python test_api.py
```
**Expected output**: Test suite runs and shows ✅ completion

## Usage

### In Streamlit Dashboard

1. Open the therapy_effectiveness_dashboard in doctor dashboard:
   - **Dashboard** → **I - Analytics & Reporting** → **I5: Therapy Effectiveness Dashboard**

2. Navigate to **📤 Send to DSL** tab to:
   - See recommendations
   - Target DSL module (M13-M18)
   - Set urgency level
   - Send to Decision Support Layer

### Using Python API Client

```python
from src.modules.module_f35.api_client import get_api_client

api = get_api_client("http://localhost:5000")

# Check health
if api.health_check():
    print("✅ Backend is running")

# Get therapies
therapies = api.get_therapies(limit=10)

# Get metrics
metrics = api.get_metrics(therapy_id)

# Get recommendations
recommendations = api.get_recommendations(limit=5)
```

### Using cURL

```bash
# Health check
curl http://localhost:5000/api/m35/health

# Get therapies
curl http://localhost:5000/api/m35/therapy?limit=10

# Get recommendations
curl http://localhost:5000/api/m35/recommendation?limit=5
```

## Data Entry Flow

### Method 1: Ingest via API
```python
import requests

# Step 1: Create therapy
therapy_response = requests.post(
    "http://localhost:5000/api/m35/ingest/therapy",
    json={
        "name": "Chemo A",
        "therapy_type": "Chemotherapy",
        "start_date": "2026-01-10",
        "end_date": "2026-03-10",
        "cost_per_cycle": 12000,
        "source_module": "M1"
    }
)
therapy_id = therapy_response.json()["therapy_id"]

# Step 2: Add patient response
requests.post(
    "http://localhost:5000/api/m35/ingest/response",
    json={
        "therapy_id": therapy_id,
        "patient_id": "P120",
        "clinical_improvement": 65,
        "symptom_relief": 58,
        "survival_days": 240,
        "response_grade": "PR",
        "source_module": "M2"
    }
)

# Step 3: Add adverse events
requests.post(
    "http://localhost:5000/api/m35/ingest/side-effect",
    json={
        "therapy_id": therapy_id,
        "patient_id": "P120",
        "adverse_event": "Nausea",
        "toxicity_grade": 2,
        "tolerability": "Moderate",
        "source_module": "M5"
    }
)

# Step 4: Add cost analysis
requests.post(
    "http://localhost:5000/api/m35/ingest/cost-analysis",
    json={
        "therapy_id": therapy_id,
        "cycles": 4,
        "total_cost": 48000,
        "qalys": 0.65,
        "source_module": "M25"
    }
)
```

## Verification Checklist

- [ ] Backend running on port 5000
- [ ] Health check endpoint returns 200
- [ ] Test API suite passes
- [ ] Streamlit dashboard loads M35 module
- [ ] "📤 Send to DSL" tab visible
- [ ] Sample data ingested successfully
- [ ] Metrics calculated and displayed
- [ ] Recommendations generated

## Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **ARCHITECTURE_SUMMARY.md** | Complete system design | `/src/modules/module_f35/backend/` |
| **M35_INTEGRATION_GUIDE.md** | Integration instructions | `/src/modules/module_f35/backend/` |
| **API_REFERENCE.md** | Endpoint quick reference | `/src/modules/module_f35/backend/` |
| **README.md** | Quick start guide | `/src/modules/module_f35/backend/` |

## API Endpoints (Quick Reference)

### Ingestion (Collection Layer → M35)
```
POST /api/m35/ingest/therapy
POST /api/m35/ingest/response
POST /api/m35/ingest/side-effect
POST /api/m35/ingest/cost-analysis
```

### Processing (M35)
```
GET /api/m35/therapy
GET /api/m35/response
GET /api/m35/side-effect
GET /api/m35/metrics/{id}
```

### Decision Support (M35 → DSL)
```
GET /api/m35/recommendation
POST /api/m35/recommendation/send-to-dsl
```

### Health
```
GET /api/m35/health
```

## Architecture at a Glance

```
Collection Layer (M1-M6, M25-M30, M43-M48)
        ↓
       POST (ingest data)
        ↓
   M35 Backend API
        ↓ (processes & analyzes)
   Benefit-Risk Analysis
        ↓
       GET (retrieve metrics)
        ↓
Streamlit Dashboard
        ↓
   Recommendations
        ↓
       POST to DSL
        ↓
Decision Support Layer (M13-M24)
        ↓
   Clinical Decisions
```

## Common Tasks

### View All Data
```bash
curl http://localhost:5000/api/m35/therapy?limit=100
curl http://localhost:5000/api/m35/response?limit=100
```

### Get Recommendations
```bash
curl http://localhost:5000/api/m35/recommendation?limit=5
```

### Send to DSL Module
```bash
curl -X POST http://localhost:5000/api/m35/recommendation/send-to-dsl \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_data": {...},
    "target_dsl_module": "M13",
    "patient_id": "P120",
    "urgency": "high"
  }'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Ensure the backend is running on port 5000 |
| "Port 5000 in use" | Kill process on 5000 or start on a different port |
| "Health check fails" | Check backend logs for errors |
| "No data in dashboard" | Use test_api.py to ingest sample data |
| "Metrics not showing" | Wait 1-2 seconds after ingestion, refresh page |

## Next Steps

1. **✅ Complete Setup**: Follow environment setup steps above
2. **✅ Verify**: Run test suite successfully
3. **✅ Ingest Data**: Use test_api.py or manual POST requests
4. **✅ View Dashboard**: Open M35 in Streamlit
5. **✅ Send to DSL**: Test "📤 Send to DSL" tab
6. **✅ Integrate**: Connect with DSL modules when ready

---

**Status**: Ready for Production  
**Last Updated**: March 18, 2026  
**Module**: M35 - Therapy Effectiveness Dashboard  
**Architecture**: Processing & Analysis Layer
