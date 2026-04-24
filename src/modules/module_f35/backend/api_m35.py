"""
Module M35: Therapy Effectiveness Dashboard - Backend API
Data Flow: Collection Layer (M1-M6, M25-M30) → M35 (Processing) → Decision Support Layer (M13-M24)

Storage: MongoDB Atlas (primary) with in-memory fallback when unavailable.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request

# ---- Env / path setup -------------------------------------------------------
# .env lives at Frontend/ root (4 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
_env_path = PROJECT_ROOT / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    pass

MONGO_URI = os.getenv("MONGO_URI", os.getenv("MONGO_DB_URI", "mongodb://localhost:27017"))
MONGO_DB  = os.getenv("MONGO_DB", "therapy_database")

# ---- MongoDB connection (with graceful fallback) -----------------------------
db = None
MONGO_AVAILABLE = False
try:
    from pymongo import MongoClient
    # tlsAllowInvalidCertificates handles SSL version mismatches with older Python SSL stacks
    _client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=4000,
        tlsAllowInvalidCertificates=True,
    )
    _client.admin.command("ping")
    db = _client[MONGO_DB]
    MONGO_AVAILABLE = True
    print(f"[M35] ✅ MongoDB connected → db: {MONGO_DB}")
except Exception as _e:
    print(f"[M35] ⚠️  MongoDB unavailable ({_e}), using in-memory fallback")

# ---- In-memory fallback store -----------------------------------------------
DATA_STORE: dict = {
    "therapies":    [],
    "responses":    [],
    "side_effects": [],
    "cost_analysis":[],
}

# ---- Mock seed data ---------------------------------------------------------
_MOCK_THERAPIES = [
    {"therapy_id": "T001", "name": "Chemo Regimen A",   "therapy_type": "Chemotherapy",  "start_date": "2026-01-10", "end_date": "2026-03-10", "cost_per_cycle": 12000, "source_module": "M1"},
    {"therapy_id": "T002", "name": "Immunotherapy B",   "therapy_type": "Immunotherapy", "start_date": "2026-02-01", "end_date": "2026-05-15", "cost_per_cycle": 18000, "source_module": "M1"},
    {"therapy_id": "T003", "name": "Targeted Therapy C","therapy_type": "Targeted",       "start_date": "2026-01-20", "end_date": "2026-04-20", "cost_per_cycle": 15000, "source_module": "M1"},
]
_MOCK_RESPONSES = [
    {"therapy_id": "T001", "patient_id": "P120", "clinical_improvement": 65, "symptom_relief": 58, "survival_days": 240, "response_grade": "PR",  "source_module": "M2"},
    {"therapy_id": "T002", "patient_id": "P145", "clinical_improvement": 74, "symptom_relief": 68, "survival_days": 310, "response_grade": "CR",  "source_module": "M2"},
    {"therapy_id": "T003", "patient_id": "P181", "clinical_improvement": 59, "symptom_relief": 52, "survival_days": 220, "response_grade": "SD",  "source_module": "M2"},
]
_MOCK_SIDE_EFFECTS = [
    {"therapy_id": "T001", "patient_id": "P120", "adverse_event": "Nausea",     "toxicity_grade": 2, "tolerability": "Moderate", "source_module": "M5"},
    {"therapy_id": "T002", "patient_id": "P145", "adverse_event": "Fatigue",    "toxicity_grade": 1, "tolerability": "High",     "source_module": "M5"},
    {"therapy_id": "T003", "patient_id": "P181", "adverse_event": "Neuropathy", "toxicity_grade": 3, "tolerability": "Low",      "source_module": "M5"},
]
_MOCK_COST = [
    {"therapy_id": "T001", "cycles": 4, "total_cost": 48000, "qalys": 1.2, "source_module": "M25"},
    {"therapy_id": "T002", "cycles": 4, "total_cost": 72000, "qalys": 1.8, "source_module": "M25"},
    {"therapy_id": "T003", "cycles": 4, "total_cost": 60000, "qalys": 1.1, "source_module": "M25"},
]


def _seed_if_empty():
    """Seed demo data when collections are empty so the dashboard always has something to show."""
    if MONGO_AVAILABLE:
        if db.therapies.count_documents({}) == 0:
            db.therapies.insert_many([dict(t, _id=t["therapy_id"]) for t in _MOCK_THERAPIES])
        if db.responses.count_documents({}) == 0:
            db.responses.insert_many([dict(r, _id=_new_id("R")) for r in _MOCK_RESPONSES])
        if db.side_effects.count_documents({}) == 0:
            db.side_effects.insert_many([dict(s, _id=_new_id("S")) for s in _MOCK_SIDE_EFFECTS])
        if db.cost_analysis.count_documents({}) == 0:
            db.cost_analysis.insert_many([dict(c, _id=_new_id("C")) for c in _MOCK_COST])
    else:
        if not DATA_STORE["therapies"]:
            DATA_STORE["therapies"]    = [dict(t, _id=t["therapy_id"]) for t in _MOCK_THERAPIES]
        if not DATA_STORE["responses"]:
            DATA_STORE["responses"]    = [dict(r, _id=_new_id("R")) for r in _MOCK_RESPONSES]
        if not DATA_STORE["side_effects"]:
            DATA_STORE["side_effects"] = [dict(s, _id=_new_id("S")) for s in _MOCK_SIDE_EFFECTS]
        if not DATA_STORE["cost_analysis"]:
            DATA_STORE["cost_analysis"]= [dict(c, _id=_new_id("C")) for c in _MOCK_COST]


# ---- Helpers -----------------------------------------------------------------
def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _prep(doc) -> dict:
    """Make a MongoDB document JSON-serialisable."""
    if doc is None:
        return {}
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    return d


def _all(collection: str) -> list:
    if MONGO_AVAILABLE:
        return [_prep(d) for d in db[collection].find({})]
    return list(DATA_STORE[collection])


def _filter(collection: str, **kw) -> list:
    """Filter documents by keyword equality."""
    docs = _all(collection)
    for k, v in kw.items():
        if v is not None:
            docs = [d for d in docs if d.get(k) == v]
    return docs


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


# ---- Flask app ---------------------------------------------------------------
app = Flask(__name__)


# ==================================================================================
# INGESTION ENDPOINTS  (Collection Layer → M35)
# ==================================================================================

@app.route("/api/m35/ingest/therapy", methods=["POST"])
def ingest_therapy():
    try:
        data = request.json or {}
        doc = {
            "_id":            _new_id("T"),
            "name":           data.get("name"),
            "therapy_type":   data.get("therapy_type"),
            "start_date":     data.get("start_date"),
            "end_date":       data.get("end_date"),
            "cost_per_cycle": data.get("cost_per_cycle"),
            "source_module":  data.get("source_module", "M1"),
            "created_at":     datetime.utcnow().isoformat(),
            "updated_at":     datetime.utcnow().isoformat(),
        }
        if MONGO_AVAILABLE:
            db.therapies.insert_one(doc)
        else:
            DATA_STORE["therapies"].append(doc)
        return jsonify({"status": "success", "therapy_id": doc["_id"], "message": "Therapy ingested successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/ingest/response", methods=["POST"])
def ingest_response():
    try:
        data = request.json or {}
        doc = {
            "_id":                 _new_id("R"),
            "therapy_id":          data.get("therapy_id"),
            "patient_id":          data.get("patient_id"),
            "clinical_improvement":data.get("clinical_improvement"),
            "symptom_relief":      data.get("symptom_relief"),
            "survival_days":       data.get("survival_days"),
            "response_grade":      data.get("response_grade"),
            "source_module":       data.get("source_module", "M2"),
            "recorded_at":         datetime.utcnow().isoformat(),
        }
        if MONGO_AVAILABLE:
            db.responses.insert_one(doc)
        else:
            DATA_STORE["responses"].append(doc)
        return jsonify({"status": "success", "response_id": doc["_id"], "message": "Response recorded successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/ingest/side-effect", methods=["POST"])
def ingest_side_effect():
    try:
        data = request.json or {}
        doc = {
            "_id":            _new_id("S"),
            "therapy_id":     data.get("therapy_id"),
            "patient_id":     data.get("patient_id"),
            "adverse_event":  data.get("adverse_event"),
            "toxicity_grade": data.get("toxicity_grade"),
            "tolerability":   data.get("tolerability"),
            "source_module":  data.get("source_module", "M5"),
            "noted_at":       datetime.utcnow().isoformat(),
        }
        if MONGO_AVAILABLE:
            db.side_effects.insert_one(doc)
        else:
            DATA_STORE["side_effects"].append(doc)
        return jsonify({"status": "success", "side_effect_id": doc["_id"], "message": "Side effect recorded successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/ingest/cost-analysis", methods=["POST"])
def ingest_cost_analysis():
    try:
        data = request.json or {}
        doc = {
            "_id":          _new_id("C"),
            "therapy_id":   data.get("therapy_id"),
            "cycles":       data.get("cycles"),
            "total_cost":   data.get("total_cost"),
            "qalys":        data.get("qalys"),
            "source_module":data.get("source_module", "M25"),
            "analyzed_at":  datetime.utcnow().isoformat(),
        }
        if MONGO_AVAILABLE:
            db.cost_analysis.insert_one(doc)
        else:
            DATA_STORE["cost_analysis"].append(doc)
        return jsonify({"status": "success", "cost_analysis_id": doc["_id"], "message": "Cost analysis recorded successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# RETRIEVAL ENDPOINTS  (M35 Processing Layer)
# ==================================================================================

@app.route("/api/m35/therapy", methods=["GET"])
def get_therapies():
    try:
        therapy_type = request.args.get("therapy_type")
        limit        = int(request.args.get("limit", 100))
        if MONGO_AVAILABLE:
            q = {"therapy_type": therapy_type} if therapy_type else {}
            docs = [_prep(d) for d in db.therapies.find(q).limit(limit)]
        else:
            docs = _filter("therapies", therapy_type=therapy_type)[:limit]
        return jsonify({"status": "success", "count": len(docs), "data": docs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/therapy/<therapy_id>", methods=["GET"])
def get_therapy(therapy_id):
    try:
        if MONGO_AVAILABLE:
            doc = _prep(db.therapies.find_one({"_id": therapy_id}))
        else:
            doc = next((d for d in DATA_STORE["therapies"] if d.get("_id") == therapy_id), None)
        if not doc:
            return jsonify({"status": "error", "message": "Therapy not found"}), 404
        return jsonify({"status": "success", "data": doc}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/response", methods=["GET"])
def get_responses():
    try:
        therapy_id = request.args.get("therapy_id")
        patient_id = request.args.get("patient_id")
        limit      = int(request.args.get("limit", 100))
        if MONGO_AVAILABLE:
            q = {}
            if therapy_id: q["therapy_id"] = therapy_id
            if patient_id: q["patient_id"] = patient_id
            docs = [_prep(d) for d in db.responses.find(q).limit(limit)]
        else:
            docs = _filter("responses", therapy_id=therapy_id, patient_id=patient_id)[:limit]
        return jsonify({"status": "success", "count": len(docs), "data": docs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/side-effect", methods=["GET"])
def get_side_effects():
    try:
        therapy_id = request.args.get("therapy_id")
        patient_id = request.args.get("patient_id")
        limit      = int(request.args.get("limit", 100))
        if MONGO_AVAILABLE:
            q = {}
            if therapy_id: q["therapy_id"] = therapy_id
            if patient_id: q["patient_id"] = patient_id
            docs = [_prep(d) for d in db.side_effects.find(q).limit(limit)]
        else:
            docs = _filter("side_effects", therapy_id=therapy_id, patient_id=patient_id)[:limit]
        return jsonify({"status": "success", "count": len(docs), "data": docs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/cost-analysis", methods=["GET"])
def get_cost_analysis():
    """GET all cost-analysis records (optionally filtered by therapy_id)."""
    try:
        therapy_id = request.args.get("therapy_id")
        limit      = int(request.args.get("limit", 100))
        if MONGO_AVAILABLE:
            q = {"therapy_id": therapy_id} if therapy_id else {}
            docs = [_prep(d) for d in db.cost_analysis.find(q).limit(limit)]
        else:
            docs = _filter("cost_analysis", therapy_id=therapy_id)[:limit]
        return jsonify({"status": "success", "count": len(docs), "data": docs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/metrics/<therapy_id>", methods=["GET"])
def get_therapy_metrics(therapy_id):
    """Benefit-Risk Analysis aggregated for one therapy."""
    try:
        if MONGO_AVAILABLE:
            responses     = [_prep(d) for d in db.responses.find({"therapy_id": therapy_id})]
            side_effects  = [_prep(d) for d in db.side_effects.find({"therapy_id": therapy_id})]
            cost_records  = [_prep(d) for d in db.cost_analysis.find({"therapy_id": therapy_id})]
        else:
            responses     = _filter("responses",    therapy_id=therapy_id)
            side_effects  = _filter("side_effects", therapy_id=therapy_id)
            cost_records  = _filter("cost_analysis",therapy_id=therapy_id)

        if not responses:
            return jsonify({"status": "error", "message": "No response data for this therapy"}), 404

        avg_improvement   = _mean([r.get("clinical_improvement", 0) for r in responses])
        avg_symptom_relief= _mean([r.get("symptom_relief", 0)      for r in responses])
        avg_survival_days = _mean([r.get("survival_days", 0)        for r in responses])
        avg_toxicity      = _mean([s.get("toxicity_grade", 0)       for s in side_effects])

        benefit_score     = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
        benefit_risk_index= benefit_score / (1 + avg_toxicity)

        cost_per_qaly = None
        if cost_records:
            tc   = _mean([c.get("total_cost", 0) for c in cost_records])
            qaly = _mean([c.get("qalys", 0)      for c in cost_records])
            if qaly:
                cost_per_qaly = tc / qaly

        return jsonify({"status": "success", "data": {
            "therapy_id":          therapy_id,
            "avg_improvement":     round(avg_improvement, 2),
            "avg_symptom_relief":  round(avg_symptom_relief, 2),
            "avg_survival_days":   round(avg_survival_days, 2),
            "avg_toxicity_grade":  round(avg_toxicity, 2),
            "adverse_events_count":len(side_effects),
            "benefit_risk_index":  round(benefit_risk_index, 2),
            "cost_per_qaly":       round(cost_per_qaly, 2) if cost_per_qaly else None,
            "response_count":      len(responses),
        }}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# DECISION SUPPORT LAYER  (M35 → M13-M24)
# ==================================================================================

@app.route("/api/m35/recommendation", methods=["GET"])
def get_recommendations():
    try:
        limit     = int(request.args.get("limit", 5))
        therapies = _all("therapies")
        recs      = []

        for therapy in therapies:
            tid = therapy.get("_id") or therapy.get("therapy_id")
            if MONGO_AVAILABLE:
                responses    = [_prep(d) for d in db.responses.find({"therapy_id": tid})]
                side_effects = [_prep(d) for d in db.side_effects.find({"therapy_id": tid})]
                cost_records = [_prep(d) for d in db.cost_analysis.find({"therapy_id": tid})]
            else:
                responses    = _filter("responses",    therapy_id=tid)
                side_effects = _filter("side_effects", therapy_id=tid)
                cost_records = _filter("cost_analysis",therapy_id=tid)

            if not responses:
                continue

            avg_impr   = _mean([r.get("clinical_improvement", 0) for r in responses])
            avg_relief = _mean([r.get("symptom_relief", 0)       for r in responses])
            avg_surv   = _mean([r.get("survival_days", 0)        for r in responses])
            avg_tox    = _mean([s.get("toxicity_grade", 0)       for s in side_effects])

            b_score = (avg_impr + avg_relief + (avg_surv / 365) * 100) / 3
            bri     = b_score / (1 + avg_tox)

            cpq = None
            if cost_records:
                tc = _mean([c.get("total_cost", 0) for c in cost_records])
                q  = _mean([c.get("qalys", 0)      for c in cost_records])
                if q:
                    cpq = tc / q

            rank = round(bri - (cpq / 100_000 if cpq else 0), 2)

            recs.append({
                "therapy_id":       str(tid),
                "name":             therapy.get("name"),
                "therapy_type":     therapy.get("therapy_type"),
                "benefit_risk_index":round(bri, 2),
                "cost_per_qaly":    round(cpq, 2) if cpq else None,
                "response_count":   len(responses),
                "adverse_events":   len(side_effects),
                "rank_score":       rank,
            })

        recs.sort(key=lambda x: x["rank_score"], reverse=True)
        return jsonify({
            "status":      "success",
            "count":       len(recs[:limit]),
            "destination": "Decision Support Layer (M13-M18)",
            "data":        recs[:limit],
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/m35/recommendation/send-to-dsl", methods=["POST"])
def send_recommendation_to_dsl():
    try:
        data = request.json or {}
        payload = {
            "source_module": "M35",
            "recommendation": data.get("recommendation_data"),
            "target_module":  data.get("target_dsl_module", "M13"),
            "patient_id":     data.get("patient_id"),
            "urgency":        data.get("urgency", "medium"),
            "timestamp":      datetime.utcnow().isoformat(),
            "status":         "dispatched_to_dsl",
        }
        return jsonify({
            "status":  "success",
            "message": f"Recommendation dispatched to {payload['target_module']} (Decision Support Layer)",
            "payload": payload,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# HEALTH CHECK
# ==================================================================================

@app.route("/api/m35/health", methods=["GET"])
def health_check():
    return jsonify({
        "status":            "healthy",
        "module":            "M35 - Therapy Effectiveness Dashboard",
        "storage":           "MongoDB Atlas" if MONGO_AVAILABLE else "in-memory (fallback)",
        "mongodb_connected": MONGO_AVAILABLE,
    }), 200


# ==================================================================================
# ENTRY POINT
# ==================================================================================

if __name__ == "__main__":
    _seed_if_empty()
    app.run(debug=True, port=5000)
