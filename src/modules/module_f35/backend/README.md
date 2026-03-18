# M35 Backend API - README

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start M35 Backend API
```bash
python api_m35.py
```

Backend runs on: **http://localhost:5000**

### 3. Test the API
```bash
# In another terminal
python test_api.py
```

---

## API Structure

### Ingestion Layer (Collection Layer → M35)
- `POST /api/m35/ingest/therapy` - Add therapy
- `POST /api/m35/ingest/response` - Add patient response
- `POST /api/m35/ingest/side-effect` - Add adverse event
- `POST /api/m35/ingest/cost-analysis` - Add cost data

### Processing Layer (M35)
- `GET /api/m35/therapy` - List therapies
- `GET /api/m35/response` - List responses
- `GET /api/m35/side-effect` - List side effects
- `GET /api/m35/metrics/{id}` - Get benefit-risk metrics

### Decision Support Layer (M35 → DSL)
- `GET /api/m35/recommendation` - Get recommendations
- `POST /api/m35/recommendation/send-to-dsl` - Send to DSL

---

## Data Flow Example

```bash
# 1. Ingest therapy (M1)
curl -X POST http://localhost:5000/api/m35/ingest/therapy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chemo A",
    "therapy_type": "Chemotherapy",
    "start_date": "2026-01-10",
    "end_date": "2026-03-10",
    "cost_per_cycle": 12000,
    "source_module": "M1"
  }'

# Save therapy_id from response

# 2. Ingest response (M2)
curl -X POST http://localhost:5000/api/m35/ingest/response \
  -H "Content-Type: application/json" \
  -d '{
    "therapy_id": "{THERAPY_ID}",
    "patient_id": "P120",
    "clinical_improvement": 65,
    "symptom_relief": 58,
    "survival_days": 240,
    "response_grade": "PR",
    "source_module": "M2"
  }'

# 3. Get metrics (M35 analysis)
curl http://localhost:5000/api/m35/metrics/{THERAPY_ID}

# 4. Get recommendations (DSL output)
curl http://localhost:5000/api/m35/recommendation?limit=5

# 5. Send to DSL (M13-M24)
curl -X POST http://localhost:5000/api/m35/recommendation/send-to-dsl \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_data": {...},
    "target_dsl_module": "M13",
    "patient_id": "P120",
    "urgency": "high"
  }'
```

---

## Files

| File | Purpose |
|------|---------|
| `api_m35.py` | Main Flask API with all endpoints |
| `requirements.txt` | Python dependencies |
| `test_api.py` | Comprehensive API test suite |
| `API_REFERENCE.md` | Quick API endpoint reference |
| `M35_INTEGRATION_GUIDE.md` | Detailed integration guide |
| `ARCHITECTURE_SUMMARY.md` | Complete architecture documentation |

---

## Architecture

```
Data Collection Layer (M1-M6, M25-M30)
            ↓ (POST endpoints)
        M35 API Backend
            ↓ (Processing)
     Benefit-Risk Analysis
            ↓ (GET endpoints)
Decision Support Layer (M13-M24)
```

---

## Key Metrics

- **Benefit-Risk Index**: `benefit_score / (1 + toxicity)`
  - Higher = Better clinical outcome with lower risk
  
- **Cost per QALY**: `total_cost / quality_adjusted_life_years`
  - Lower = More cost-effective
  
- **Rank Score**: Combines both metrics
  - Used to rank therapies for recommendation

---

## Troubleshooting

### Backend not starting
- Verify port 5000 is available: `netstat -ano | findstr :5000`
- Check Python version: `python --version` (needs 3.8+)

### API returning errors
- Check request JSON format
- Verify all required fields are present
- Review response error message
- Check API logs in terminal

---

## Development

### Add New Endpoint
1. Add route in `api_m35.py`
2. Update `api_client.py` with client method
3. Update `API_REFERENCE.md`
4. Add test in `test_api.py`

### Modify Metrics Calculation
- Edit `_aggregate_metrics()` in `api_m35.py`
- Update documentation in `ARCHITECTURE_SUMMARY.md`

---

## Performance

- Requests timeout at 5 seconds
- Caching disabled for real-time data
- Limit results with `limit` query parameter

---

## Healthcare Compliance

- HIPAA-ready data structure (can add HIPAA compliance layer)
- Audit trail tracked via `source_module` and timestamps
- Data validation on all inputs

---

## Support

For issues or questions:
1. Check `API_REFERENCE.md` for endpoint details
2. Review `M35_INTEGRATION_GUIDE.md` for integration help
3. Run `test_api.py` to verify setup
4. Check logs in terminal for errors

---

**Last Updated**: March 18, 2026  
**Status**: ✅ Production Ready
