from pathlib import Path
import os
import sys

import streamlit as st
from pymongo import MongoClient
from pymongo.errors import PyMongoError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from components.tabs import module_tabs


MONGODB_SCHEMA = """
Collections:
1) therapies
   { _id: "T001", name, therapy_type, start_date, end_date, cost_per_cycle }

2) responses
   { _id: "R1001", therapy_id: "T001", patient_id, clinical_improvement, symptom_relief, survival_days,
     response_grade, recorded_at }

3) side_effects
   { _id: "S501", therapy_id: "T001", patient_id, adverse_event, toxicity_grade, tolerability, noted_at }

4) cost_analysis
   { _id: "C001", therapy_id: "T001", cycles, total_cost, qalys, analyzed_at }

Indexes:
- responses: { therapy_id: 1 }
- side_effects: { therapy_id: 1 }
- cost_analysis: { therapy_id: 1 }
""".strip()


MONGODB_EXAMPLES = """
therapies
{ _id: "T001", name: "Chemo Regimen A", therapy_type: "Chemotherapy",
  start_date: "2026-01-10", end_date: "2026-03-10", cost_per_cycle: 12000 }

responses
{ _id: "R1001", therapy_id: "T001", patient_id: "P120", clinical_improvement: 65,
  symptom_relief: 58, survival_days: 240, response_grade: "PR", recorded_at: ISODate("2026-02-05") }

side_effects
{ _id: "S501", therapy_id: "T001", patient_id: "P120", adverse_event: "Nausea",
  toxicity_grade: 2, tolerability: "Moderate", noted_at: ISODate("2026-02-06") }

cost_analysis
{ _id: "C001", therapy_id: "T001", cycles: 4, total_cost: 48000, qalys: 0.65,
  analyzed_at: ISODate("2026-03-01") }
""".strip()


API_CONTRACT = {
    "GET /api/therapy": "List therapies",
    "GET /api/therapy/{therapy_id}": "Therapy details",
    "GET /api/response?therapy_id=": "Responses by therapy",
    "GET /api/side-effect?therapy_id=": "Side effects by therapy",
    "GET /api/cost-analysis?therapy_id=": "Cost analysis by therapy",
    "POST /api/response": "Add response record",
    "POST /api/side-effect": "Add side effect record",
}


def _mean(values):
    if not values:
        return 0
    return sum(values) / len(values)


@st.cache_resource
def _get_mongo_client():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/therapy_f35")
    return MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)


def _get_database():
    db_name = os.getenv("MONGO_DB", "therapy_database")
    client = _get_mongo_client()
    return client[db_name]


def _ensure_collections(db):
    db.therapies.create_index("_id", unique=True)
    db.responses.create_index("therapy_id")
    db.side_effects.create_index("therapy_id")
    db.cost_analysis.create_index("therapy_id")


def _fetch_backend_data():
    try:
        db = _get_database()
        _ensure_collections(db)
        therapies = list(db.therapies.find({}, {"_id": 1, "name": 1, "therapy_type": 1, "start_date": 1, "end_date": 1, "cost_per_cycle": 1}))
        responses = list(db.responses.find({}, {"_id": 1, "therapy_id": 1, "patient_id": 1, "clinical_improvement": 1, "symptom_relief": 1, "survival_days": 1, "response_grade": 1}))
        side_effects = list(db.side_effects.find({}, {"_id": 1, "therapy_id": 1, "patient_id": 1, "adverse_event": 1, "toxicity_grade": 1, "tolerability": 1}))
        cost_analysis = list(db.cost_analysis.find({}, {"_id": 1, "therapy_id": 1, "cycles": 1, "total_cost": 1, "qalys": 1}))
        return therapies, responses, side_effects, cost_analysis, None
    except PyMongoError as exc:
        return [], [], [], [], str(exc)


def _aggregate_metrics(therapies, responses, side_effects, cost_analysis):
    cost_map = {item["therapy_id"]: item for item in cost_analysis}
    metrics = []

    for therapy in therapies:
        therapy_id = therapy["therapy_id"]
        therapy_responses = [r for r in responses if r["therapy_id"] == therapy_id]
        therapy_side_effects = [s for s in side_effects if s["therapy_id"] == therapy_id]

        avg_improvement = _mean([r["clinical_improvement"] for r in therapy_responses])
        avg_symptom_relief = _mean([r["symptom_relief"] for r in therapy_responses])
        avg_survival_days = _mean([r["survival_days"] for r in therapy_responses])
        avg_toxicity = _mean([s["toxicity_grade"] for s in therapy_side_effects])

        benefit_score = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
        benefit_risk_index = benefit_score / (1 + avg_toxicity)

        cost_entry = cost_map.get(therapy_id)
        cost_per_qaly = None
        if cost_entry and cost_entry["qalys"]:
            cost_per_qaly = cost_entry["total_cost"] / cost_entry["qalys"]

        metrics.append(
            {
                "therapy_id": therapy_id,
                "name": therapy["name"],
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


def render_module_f35():
    st.markdown("## Module 35: Therapy Effectiveness Evaluation System")
    st.caption("Category F - Case-Based Decision Support")

    therapies, responses, side_effects, cost_analysis, db_error = _fetch_backend_data()

    tab = st.radio(
        "",
        ["Home", "ER Diagram", "Tables", "MongoDB Queries", "Backend Logic", "Output"],
        horizontal=True,
    )
    st.divider()

    if db_error:
        st.error(f"MongoDB connection error: {db_error}")

    if tab == "Home":
        st.markdown("### Objectives")
        st.write("Design a therapy response measurement system with benefit and risk tracking.")

        st.markdown("### Backend Scope")
        st.write("Defines schema and API contract for therapy effectiveness data.")

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
        st.code(
                        """
Therapy (therapy_id PK)
    1 |--< N Response (response_id PK, therapy_id FK, patient_id, clinical_improvement, symptom_relief, survival_days)
    1 |--< N SideEffect (side_effect_id PK, therapy_id FK, patient_id, adverse_event, toxicity_grade, tolerability)
    1 |--< N CostAnalysis (analysis_id PK, therapy_id FK, cycles, total_cost, qalys)

TherapySummary (therapy_id PK)
    1 |-- 1 TherapySummary (avg_improvement, avg_symptom_relief, avg_toxicity, benefit_risk_index, cost_per_qaly)
""".strip(),
                        language="text",
                )

    elif tab == "Tables":
        if not therapies and not responses and not side_effects and not cost_analysis:
            st.info("No data found in MongoDB collections yet.")
        st.markdown("### Therapy")
        st.table(therapies)

        st.markdown("### Response")
        st.table(responses)

        st.markdown("### SideEffect")
        st.table(side_effects)

        st.markdown("### CostAnalysis")
        st.table(cost_analysis)

    elif tab == "MongoDB Queries":
        st.markdown("### MongoDB Schema")
        st.code(MONGODB_SCHEMA, language="text")

        st.markdown("### Example Documents")
        st.code(MONGODB_EXAMPLES, language="javascript")

        st.markdown("### API Contract")
        st.json(API_CONTRACT)

        st.markdown("### Sample MongoDB Aggregations")
        st.code(
                        """
// Benefit calculation per therapy
db.responses.aggregate([
    {
        $group: {
            _id: "$therapy_id",
            avg_improvement: { $avg: "$clinical_improvement" },
            avg_symptom_relief: { $avg: "$symptom_relief" },
            avg_survival_days: { $avg: "$survival_days" }
        }
    }
]);

// Cost per QALY
db.cost_analysis.aggregate([
    {
        $project: {
            therapy_id: 1,
            cost_per_qaly: {
                $cond: [
                    { $gt: ["$qalys", 0] },
                    { $divide: ["$total_cost", "$qalys"] },
                    null
                ]
            }
        }
    }
]);

// Comparative effectiveness with toxicity
db.therapies.aggregate([
    {
        $lookup: {
            from: "responses",
            localField: "_id",
            foreignField: "therapy_id",
            as: "responses"
        }
    },
    {
        $lookup: {
            from: "side_effects",
            localField: "_id",
            foreignField: "therapy_id",
            as: "side_effects"
        }
    },
    {
        $project: {
            therapy_id: "$_id",
            name: 1,
            avg_improvement: { $avg: "$responses.clinical_improvement" },
            avg_toxicity: { $avg: "$side_effects.toxicity_grade" }
        }
    }
]);
""".strip(),
                        language="javascript",
                )

    elif tab == "Backend Logic":
                st.markdown("### Backend Logic (MongoDB)")
                st.code(
                        """
// Change stream listener to refresh summary collection
// Pseudocode: watch responses and side_effects inserts
db.responses.watch([ { $match: { operationType: "insert" } } ])
    .on("change", (event) => {
        // recompute summary for event.fullDocument.therapy_id
    });

// Materialized summary via aggregation pipeline
db.responses.aggregate([
    {
        $group: {
            _id: "$therapy_id",
            avg_improvement: { $avg: "$clinical_improvement" },
            avg_symptom_relief: { $avg: "$symptom_relief" }
        }
    },
    { $merge: { into: "therapy_summary", on: "_id", whenMatched: "replace" } }
]);
""".strip(),
                        language="javascript",
                )

    elif tab == "Output":
        st.markdown("### Benefit and Risk Summary")
        if not therapies:
            st.info("Summary metrics will appear after backend data is available.")
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


if __name__ == "__main__":
    render_module_f35()
