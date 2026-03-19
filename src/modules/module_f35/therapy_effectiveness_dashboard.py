from pathlib import Path
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

try:
    from pymongo import MongoClient
except Exception:  # pragma: no cover - handled gracefully when package is absent
    MongoClient = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
MODULE_DIR = Path(__file__).resolve().parent
ER_DIAGRAM_IMAGE_PATH = MODULE_DIR / "assets" / "erdiagimp.jpg"
M35_MONGODB_URI = os.getenv("MONGO_DB_URI", os.getenv("M35_MONGODB_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017")))
M35_MONGODB_DB = os.getenv("M35_MONGODB_DB", os.getenv("MONGO_DB", "m35_therapy"))

MOCK_THERAPIES = [
    {
        "therapy_id": "T001",
        "name": "Chemo Regimen A",
        "therapy_type": "Chemotherapy",
        "start_date": "2026-01-10",
        "end_date": "2026-03-10",
        "cost_per_cycle": 12000,
        "source_module": "M1",
    },
    {
        "therapy_id": "T002",
        "name": "Immunotherapy B",
        "therapy_type": "Immunotherapy",
        "start_date": "2026-02-01",
        "end_date": "2026-05-15",
        "cost_per_cycle": 18000,
        "source_module": "M1",
    },
    {
        "therapy_id": "T003",
        "name": "Targeted Therapy C",
        "therapy_type": "Targeted",
        "start_date": "2026-01-20",
        "end_date": "2026-04-20",
        "cost_per_cycle": 15000,
        "source_module": "M1",
    },
]

MOCK_RESPONSES = [
    {
        "therapy_id": "T001",
        "patient_id": "P120",
        "clinical_improvement": 65,
        "symptom_relief": 58,
        "survival_days": 240,
        "response_grade": "PR",
        "source_module": "M2",
    },
    {
        "therapy_id": "T002",
        "patient_id": "P145",
        "clinical_improvement": 74,
        "symptom_relief": 68,
        "survival_days": 310,
        "response_grade": "CR",
        "source_module": "M2",
    },
    {
        "therapy_id": "T003",
        "patient_id": "P181",
        "clinical_improvement": 59,
        "symptom_relief": 52,
        "survival_days": 220,
        "response_grade": "SD",
        "source_module": "M2",
    },
]

MOCK_SIDE_EFFECTS = [
    {
        "therapy_id": "T001",
        "patient_id": "P120",
        "adverse_event": "Nausea",
        "toxicity_grade": 2,
        "tolerability": "Moderate",
        "source_module": "M5",
    },
    {
        "therapy_id": "T002",
        "patient_id": "P145",
        "adverse_event": "Fatigue",
        "toxicity_grade": 1,
        "tolerability": "High",
        "source_module": "M5",
    },
    {
        "therapy_id": "T003",
        "patient_id": "P181",
        "adverse_event": "Neuropathy",
        "toxicity_grade": 3,
        "tolerability": "Low",
        "source_module": "M5",
    },
]

MOCK_COST_ANALYSIS = [
    {"therapy_id": "T001", "cycles": 4, "total_cost": 48000, "qalys": 1.2, "source_module": "M25"},
    {"therapy_id": "T002", "cycles": 4, "total_cost": 72000, "qalys": 1.8, "source_module": "M25"},
    {"therapy_id": "T003", "cycles": 4, "total_cost": 60000, "qalys": 1.1, "source_module": "M25"},
]


def _mean(values):
    if not values:
        return 0
    return sum(values) / len(values)


def _seed_mock_data_if_empty(db):
    """Seed MongoDB collections once when empty so the dashboard always has demo data."""
    if db.therapies.count_documents({}) == 0:
        db.therapies.insert_many(MOCK_THERAPIES)
    if db.responses.count_documents({}) == 0:
        db.responses.insert_many(MOCK_RESPONSES)
    if db.side_effects.count_documents({}) == 0:
        db.side_effects.insert_many(MOCK_SIDE_EFFECTS)
    if db.cost_analysis.count_documents({}) == 0:
        db.cost_analysis.insert_many(MOCK_COST_ANALYSIS)


def _prepare_docs(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prepared = []
    for doc in documents:
        cleaned = dict(doc)
        if "_id" in cleaned:
            cleaned["_id"] = str(cleaned["_id"])
        prepared.append(cleaned)
    return prepared


def _fetch_mongodb_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Optional[str], str]:
    """Fetch M35 data from MongoDB and fall back to in-memory mock data if unavailable."""
    if MongoClient is None:
        return (
            list(MOCK_THERAPIES),
            list(MOCK_RESPONSES),
            list(MOCK_SIDE_EFFECTS),
            list(MOCK_COST_ANALYSIS),
            "pymongo is not installed. Showing local mock data.",
            "Mock Data",
        )

    try:
        client = MongoClient(M35_MONGODB_URI, serverSelectionTimeoutMS=1500)
        client.admin.command("ping")
        db = client[M35_MONGODB_DB]
        _seed_mock_data_if_empty(db)

        therapies = _prepare_docs(list(db.therapies.find({})))
        responses = _prepare_docs(list(db.responses.find({})))
        side_effects = _prepare_docs(list(db.side_effects.find({})))
        cost_analysis = _prepare_docs(list(db.cost_analysis.find({})))
        return therapies, responses, side_effects, cost_analysis, None, "MongoDB"
    except Exception as exc:
        return (
            list(MOCK_THERAPIES),
            list(MOCK_RESPONSES),
            list(MOCK_SIDE_EFFECTS),
            list(MOCK_COST_ANALYSIS),
            f"MongoDB unavailable ({str(exc)}). Showing local mock data.",
            "Mock Data",
        )


def _aggregate_metrics(therapies, responses, side_effects, cost_analysis):
    """
    Aggregate metrics from MongoDB data
    Sends aggregated insights to Decision Support Layer (M13-M24)
    """
    metrics = []

    for therapy in therapies:
        therapy_id = therapy.get("_id") or therapy.get("therapy_id")
        
        # Filter responses and side effects for this therapy
        therapy_responses = [r for r in responses if r.get("therapy_id") == therapy_id]
        therapy_side_effects = [s for s in side_effects if s.get("therapy_id") == therapy_id]

        avg_improvement = _mean([r.get("clinical_improvement", 0) for r in therapy_responses])
        avg_symptom_relief = _mean([r.get("symptom_relief", 0) for r in therapy_responses])
        avg_survival_days = _mean([r.get("survival_days", 0) for r in therapy_responses])
        avg_toxicity = _mean([s.get("toxicity_grade", 0) for s in therapy_side_effects])

        benefit_score = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
        benefit_risk_index = benefit_score / (1 + avg_toxicity)

        # Compute cost_per_qaly directly from MongoDB cost_analysis collection data.
        cost_per_qaly = None
        cost_records = [c for c in cost_analysis if c.get("therapy_id") == therapy_id]
        if cost_records:
            total_cost = _mean([c.get("total_cost", 0) for c in cost_records])
            qalys = _mean([c.get("qalys", 0) for c in cost_records])
            if qalys:
                cost_per_qaly = total_cost / qalys

        metrics.append(
            {
                "therapy_id": str(therapy_id),
                "name": therapy.get("name", "Unknown"),
                "avg_improvement": round(avg_improvement, 1),
                "avg_symptom_relief": round(avg_symptom_relief, 1),
                "avg_survival_days": round(avg_survival_days, 1),
                "avg_toxicity_grade": round(avg_toxicity, 1),
                "adverse_events": len(therapy_side_effects),
                "benefit_risk_index": round(benefit_risk_index, 2),
                "cost_per_qaly": round(cost_per_qaly, 2) if cost_per_qaly else None,
            }
        )

    return metrics


def _render_er_diagram_image():
    """Render ER diagram from module-local asset file."""
    if not ER_DIAGRAM_IMAGE_PATH.exists():
        st.error(f"ER diagram asset not found: {ER_DIAGRAM_IMAGE_PATH}")
        return

    st.image(str(ER_DIAGRAM_IMAGE_PATH), use_container_width=True)


def render_module_f35():
    st.markdown("## Module 35: Therapy Effectiveness Evaluation System")
    st.caption("Category F - Case-Based Decision Support")

    therapies, responses, side_effects, cost_analysis, db_error, data_source = _fetch_mongodb_data()

    tab = st.radio(
        "",
        ["Home", "ER Diagram", "Tables", "MongoDB", "Backend Logic", "Output", "📤 Send to DSL"],
        horizontal=True,
    )
    st.divider()

    if db_error:
        st.warning(db_error)

    st.caption(f"Data Source: {data_source}")

    if tab == "Home":
        st.markdown("### Objectives")
        st.write("Design a therapy response measurement system with benefit and risk tracking.")

        st.markdown("### Backend Scope")
        st.write("Defines MongoDB collections and analytics logic for therapy effectiveness data.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Input Entities")
            st.success("Therapy")
            st.success("Response")
            st.success("SideEffect")
            st.success("CostAnalysis")

        with col2:
            st.markdown("#### Output Entities")
            st.success("Benefit and risk summary")
            st.success("Cost effectiveness report")
            st.success("Personalized therapy recommendations")

        st.markdown("### Effectiveness Measures")
        st.write("Clinical improvement, symptom relief, and survival outcomes.")
        st.markdown("### Safety Metrics")
        st.write("Adverse events, toxicity grades, and tolerability.")

    elif tab == "ER Diagram":
        st.markdown("### Entity Relationship Diagram")
        _render_er_diagram_image()

    elif tab == "Tables":
        if not therapies and not responses and not side_effects and not cost_analysis:
            st.info("No data available from MongoDB yet.")
        st.markdown("### Therapy")
        st.table(therapies)

        st.markdown("### Response")
        st.table(responses)

        st.markdown("### SideEffect")
        st.table(side_effects)

        st.markdown("### CostAnalysis")
        st.table(cost_analysis)

    elif tab == "MongoDB":
        st.markdown("### MongoDB Configuration")
        st.json({
            "database": M35_MONGODB_DB,
            "collections": ["therapies", "responses", "side_effects", "cost_analysis"],
        })
        st.markdown("### Notes")
        st.write("This dashboard now reads directly from MongoDB. If MongoDB is offline, local mock data is shown so development can continue.")
        st.write("Later, this can be switched back to API mode by replacing _fetch_mongodb_data with API client calls.")

    elif tab == "Backend Logic":
        st.markdown("### Backend Logic (MongoDB)")
        st.code(
            """
MongoDB collections:
    therapies
    responses
    side_effects
    cost_analysis

Startup flow:
    1) Connect to MongoDB
    2) Seed mock records when collections are empty
    3) Read collection documents
    4) Aggregate benefit-risk and cost metrics in dashboard
    5) Rank recommendations for decision support modules
""".strip(),
            language="text",
        )

    elif tab == "Output":
        st.markdown("### Benefit and Risk Summary")
        if not therapies:
            st.info("Summary metrics will appear after MongoDB data is available.")
        metrics = _aggregate_metrics(therapies, responses, side_effects, cost_analysis)

        top_col1, top_col2, top_col3 = st.columns(3)
        with top_col1:
            st.metric("Therapies", len(therapies))
        with top_col2:
            st.metric("Responses", len(responses))
        with top_col3:
            st.metric("Adverse Events", len(side_effects))

        st.table(metrics)

        st.markdown("### Backend Response Example")
        st.json(
            {
                "therapy_id": "T000",
                "responses": [],
                "side_effects": [],
                "cost_analysis": [],
            }
        )

        st.markdown("### Recommendation Logic")
        st.write("Select therapies with high benefit-risk index and lower cost per QALY.")

    elif tab == "📤 Send to DSL":
        st.markdown("### Therapy Recommendations → Decision Support Layer (M13-M24)")
        st.info("This tab currently simulates sending recommendations from MongoDB-derived metrics. API integration can be re-enabled later.")
        metrics = _aggregate_metrics(therapies, responses, side_effects, cost_analysis)
        recommendations = sorted(metrics, key=lambda m: m.get("benefit_risk_index", 0), reverse=True)[:10]
        
        if not recommendations:
            st.warning("No recommendations available. Ensure MongoDB has data.")
        else:
            st.markdown("#### Top Therapy Recommendations")
            
            rec_data = []
            for rec in recommendations:
                rec_data.append({
                    "Therapy": rec.get("name", "Unknown"),
                    "Benefit-Risk Index": rec.get("benefit_risk_index", 0),
                    "Cost/QALY": f"${rec.get('cost_per_qaly', 0):.2f}" if rec.get('cost_per_qaly') else "N/A",
                    "Responses": rec.get("adverse_events", 0),
                })
            
            st.dataframe(rec_data, use_container_width=True)
            
            st.markdown("#### Send to Decision Support Layer")
            col1, col2 = st.columns(2)
            
            with col1:
                target_module = st.selectbox(
                    "Target DSL Module:",
                    ["M13", "M14", "M15", "M16", "M17", "M18"],
                    help="Select which Decision Support module to send recommendations to"
                )
            
            with col2:
                urgency = st.selectbox(
                    "Urgency Level:",
                    ["low", "medium", "high"],
                    help="Set urgency for clinical decision making"
                )
            
            patient_id = st.text_input("Patient ID (if applicable):", "")
            
            if st.button("🚀 Send Recommendations to Decision Support Layer", use_container_width=True):
                if recommendations:
                    payload = {
                        "status": "simulated",
                        "target_module": target_module,
                        "urgency": urgency,
                        "patient_id": patient_id or "GENERAL",
                        "recommendation_count": min(3, len(recommendations)),
                        "top_recommendations": recommendations[:3],
                    }
                    st.success(
                        f"Prepared {payload['recommendation_count']} recommendations for {target_module}. "
                        "API handoff is disabled in mock mode."
                    )
                    st.json(payload)
            
            st.markdown("---")
            st.markdown("#### Data Flow Architecture")
            st.code("""
DATA COLLECTION LAYER (M1-M6, M25-M30, M43-M48)
    ↓ (Raw clinical data)
    M35 PROCESSING LAYER
    ├─ Clinical Improvement: avg of all response scores
    ├─ Symptom Relief: avg symptom relief percentages
    ├─ Survival Analysis: avg survival days
    ├─ Safety Profile: toxicity grades and adverse events
    └─ Cost-Effectiveness: cost per QALY
    ↓ (Aggregated insights)
DECISION SUPPORT LAYER (M13-M24)
    ├─ M13: Clinical Guidelines
    ├─ M14-M18: Decision Support Modules
    └─ Clinical Decision Making
            """, language="text")


if __name__ == "__main__":
    render_module_f35()
