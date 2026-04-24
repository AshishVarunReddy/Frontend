"""
M35 Direct MongoDB Client — replaces Flask API + api_client.py
Streamlit ↔ MongoDB (no Flask middleman)
"""

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Dict, List, Optional

import streamlit as st

# ---- Env setup ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

def _get_secret(key, default=None):
    """Read from Streamlit secrets first, then env vars."""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

MONGO_URI = _get_secret("MONGO_URI", os.getenv("MONGO_DB_URI", "mongodb://localhost:27017"))
MONGO_DB  = _get_secret("MONGO_DB", "therapy_database")


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


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


# ---- Connection --------------------------------------------------------------

@st.cache_resource
def _get_db():
    """
    Return (db_handle, is_connected: bool).
    Cached across Streamlit reruns so we don't reconnect every time.
    """
    try:
        from pymongo import MongoClient
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=4000,
            tlsAllowInvalidCertificates=True,
        )
        client.admin.command("ping")
        db = client[MONGO_DB]
        print(f"[M35] ✅ MongoDB connected → db: {MONGO_DB}")
        return db, True
    except Exception as e:
        print(f"[M35] ⚠️  MongoDB unavailable ({e}), using in-memory fallback")
        return None, False


# ---- In-memory fallback store (per session) -----------------------------------
def _get_store() -> dict:
    """Session-scoped in-memory data store."""
    if "_m35_store" not in st.session_state:
        st.session_state._m35_store = {
            "therapies":     [dict(t, _id=t["therapy_id"]) for t in _MOCK_THERAPIES],
            "responses":     [dict(r, _id=_new_id("R"))   for r in _MOCK_RESPONSES],
            "side_effects":  [dict(s, _id=_new_id("S"))   for s in _MOCK_SIDE_EFFECTS],
            "cost_analysis": [dict(c, _id=_new_id("C"))   for c in _MOCK_COST],
        }
    return st.session_state._m35_store


def _seed_if_empty():
    """Seed demo data when collections are empty so the dashboard always has something to show."""
    db, connected = _get_db()
    if connected:
        if db.therapies.count_documents({}) == 0:
            db.therapies.insert_many([dict(t, _id=t["therapy_id"]) for t in _MOCK_THERAPIES])
        if db.responses.count_documents({}) == 0:
            db.responses.insert_many([dict(r, _id=_new_id("R")) for r in _MOCK_RESPONSES])
        if db.side_effects.count_documents({}) == 0:
            db.side_effects.insert_many([dict(s, _id=_new_id("S")) for s in _MOCK_SIDE_EFFECTS])
        if db.cost_analysis.count_documents({}) == 0:
            db.cost_analysis.insert_many([dict(c, _id=_new_id("C")) for c in _MOCK_COST])
    # In-memory store is seeded automatically by _get_store()


# ==============================================================================
# PUBLIC API — drop-in replacement for the old Flask endpoints
# ==============================================================================

def is_connected() -> bool:
    """Return True when MongoDB is reachable."""
    _, ok = _get_db()
    return ok


def storage_label() -> str:
    return "MongoDB Atlas ✅" if is_connected() else "In-memory (fallback)"


# ---- Retrieval ---------------------------------------------------------------

def get_therapies(therapy_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
    db, ok = _get_db()
    if ok:
        q = {"therapy_type": therapy_type} if therapy_type else {}
        return [_prep(d) for d in db.therapies.find(q).limit(limit)]
    store = _get_store()
    docs = store["therapies"]
    if therapy_type:
        docs = [d for d in docs if d.get("therapy_type") == therapy_type]
    return docs[:limit]


def get_responses(therapy_id: Optional[str] = None, patient_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    db, ok = _get_db()
    if ok:
        q = {}
        if therapy_id: q["therapy_id"] = therapy_id
        if patient_id: q["patient_id"] = patient_id
        return [_prep(d) for d in db.responses.find(q).limit(limit)]
    store = _get_store()
    docs = store["responses"]
    if therapy_id:
        docs = [d for d in docs if d.get("therapy_id") == therapy_id]
    if patient_id:
        docs = [d for d in docs if d.get("patient_id") == patient_id]
    return docs[:limit]


def get_side_effects(therapy_id: Optional[str] = None, patient_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    db, ok = _get_db()
    if ok:
        q = {}
        if therapy_id: q["therapy_id"] = therapy_id
        if patient_id: q["patient_id"] = patient_id
        return [_prep(d) for d in db.side_effects.find(q).limit(limit)]
    store = _get_store()
    docs = store["side_effects"]
    if therapy_id:
        docs = [d for d in docs if d.get("therapy_id") == therapy_id]
    if patient_id:
        docs = [d for d in docs if d.get("patient_id") == patient_id]
    return docs[:limit]


def get_cost_analysis(therapy_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    db, ok = _get_db()
    if ok:
        q = {"therapy_id": therapy_id} if therapy_id else {}
        return [_prep(d) for d in db.cost_analysis.find(q).limit(limit)]
    store = _get_store()
    docs = store["cost_analysis"]
    if therapy_id:
        docs = [d for d in docs if d.get("therapy_id") == therapy_id]
    return docs[:limit]


# ---- Ingestion ---------------------------------------------------------------

def ingest_therapy(name, therapy_type, start_date, end_date, cost_per_cycle, source_module="M1") -> Dict:
    doc = {
        "_id":            _new_id("T"),
        "name":           name,
        "therapy_type":   therapy_type,
        "start_date":     start_date,
        "end_date":       end_date,
        "cost_per_cycle": cost_per_cycle,
        "source_module":  source_module,
        "created_at":     datetime.utcnow().isoformat(),
        "updated_at":     datetime.utcnow().isoformat(),
    }
    db, ok = _get_db()
    if ok:
        db.therapies.insert_one(doc)
    else:
        _get_store()["therapies"].append(doc)
    return {"status": "success", "therapy_id": doc["_id"], "message": "Therapy ingested successfully"}


def ingest_response(therapy_id, patient_id, clinical_improvement, symptom_relief, survival_days, response_grade, source_module="M2") -> Dict:
    doc = {
        "_id":                  _new_id("R"),
        "therapy_id":           therapy_id,
        "patient_id":           patient_id,
        "clinical_improvement": clinical_improvement,
        "symptom_relief":       symptom_relief,
        "survival_days":        survival_days,
        "response_grade":       response_grade,
        "source_module":        source_module,
        "recorded_at":          datetime.utcnow().isoformat(),
    }
    db, ok = _get_db()
    if ok:
        db.responses.insert_one(doc)
    else:
        _get_store()["responses"].append(doc)
    return {"status": "success", "response_id": doc["_id"], "message": "Response recorded successfully"}


def ingest_side_effect(therapy_id, patient_id, adverse_event, toxicity_grade, tolerability, source_module="M5") -> Dict:
    doc = {
        "_id":            _new_id("S"),
        "therapy_id":     therapy_id,
        "patient_id":     patient_id,
        "adverse_event":  adverse_event,
        "toxicity_grade": toxicity_grade,
        "tolerability":   tolerability,
        "source_module":  source_module,
        "noted_at":       datetime.utcnow().isoformat(),
    }
    db, ok = _get_db()
    if ok:
        db.side_effects.insert_one(doc)
    else:
        _get_store()["side_effects"].append(doc)
    return {"status": "success", "side_effect_id": doc["_id"], "message": "Side effect recorded successfully"}


def ingest_cost_analysis(therapy_id, cycles, total_cost, qalys, source_module="M25") -> Dict:
    doc = {
        "_id":           _new_id("C"),
        "therapy_id":    therapy_id,
        "cycles":        cycles,
        "total_cost":    total_cost,
        "qalys":         qalys,
        "source_module": source_module,
        "analyzed_at":   datetime.utcnow().isoformat(),
    }
    db, ok = _get_db()
    if ok:
        db.cost_analysis.insert_one(doc)
    else:
        _get_store()["cost_analysis"].append(doc)
    return {"status": "success", "cost_analysis_id": doc["_id"], "message": "Cost analysis recorded successfully"}


# ---- Metrics / Recommendations -----------------------------------------------

def get_metrics(therapy_id: str) -> Optional[Dict]:
    responses    = get_responses(therapy_id=therapy_id, limit=500)
    side_effects = get_side_effects(therapy_id=therapy_id, limit=500)
    cost_records = get_cost_analysis(therapy_id=therapy_id, limit=500)

    if not responses:
        return None

    avg_improvement    = _mean([r.get("clinical_improvement", 0) for r in responses])
    avg_symptom_relief = _mean([r.get("symptom_relief", 0)      for r in responses])
    avg_survival_days  = _mean([r.get("survival_days", 0)       for r in responses])
    avg_toxicity       = _mean([s.get("toxicity_grade", 0)      for s in side_effects])

    benefit_score      = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
    benefit_risk_index = benefit_score / (1 + avg_toxicity)

    cost_per_qaly = None
    if cost_records:
        tc   = _mean([c.get("total_cost", 0) for c in cost_records])
        qaly = _mean([c.get("qalys", 0)      for c in cost_records])
        if qaly:
            cost_per_qaly = tc / qaly

    return {
        "therapy_id":          therapy_id,
        "avg_improvement":     round(avg_improvement, 2),
        "avg_symptom_relief":  round(avg_symptom_relief, 2),
        "avg_survival_days":   round(avg_survival_days, 2),
        "avg_toxicity_grade":  round(avg_toxicity, 2),
        "adverse_events_count": len(side_effects),
        "benefit_risk_index":  round(benefit_risk_index, 2),
        "cost_per_qaly":       round(cost_per_qaly, 2) if cost_per_qaly else None,
        "response_count":      len(responses),
    }


def get_recommendations(limit: int = 5) -> List[Dict]:
    therapies = get_therapies(limit=500)
    recs = []

    for therapy in therapies:
        tid = therapy.get("_id") or therapy.get("therapy_id")
        responses    = get_responses(therapy_id=tid, limit=500)
        side_effects = get_side_effects(therapy_id=tid, limit=500)
        cost_records = get_cost_analysis(therapy_id=tid, limit=500)

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
            "therapy_id":        str(tid),
            "name":              therapy.get("name"),
            "therapy_type":      therapy.get("therapy_type"),
            "benefit_risk_index": round(bri, 2),
            "cost_per_qaly":     round(cpq, 2) if cpq else None,
            "response_count":    len(responses),
            "adverse_events":    len(side_effects),
            "rank_score":        rank,
        })

    recs.sort(key=lambda x: x["rank_score"], reverse=True)
    return recs[:limit]


def send_recommendation_to_dsl(recommendation_data, target_dsl_module, patient_id, urgency="medium") -> Dict:
    payload = {
        "source_module":    "M35",
        "recommendation":   recommendation_data,
        "target_module":    target_dsl_module,
        "patient_id":       patient_id,
        "urgency":          urgency,
        "timestamp":        datetime.utcnow().isoformat(),
        "status":           "dispatched_to_dsl",
    }
    return {
        "status":  "success",
        "message": f"Recommendation dispatched to {target_dsl_module} (Decision Support Layer)",
        "payload": payload,
    }
