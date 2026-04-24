"""
Module F35 – Therapy Effectiveness Evaluation System
Category F – Case-Based Decision Support

Data flow:
  Collection Layer (M1 → therapies, M2 → responses, M5 → side effects, M25 → cost)
      ↓  POST  (ingestion endpoints)
  M35 Flask Backend  (http://localhost:5000)
      ↓  GET   (retrieval / analysis endpoints)
  This Streamlit dashboard  →  Decision Support Layer (M13-M24)
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

# ---- Path & env setup -------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

MODULE_DIR           = Path(__file__).resolve().parent
ER_DIAGRAM_IMAGE_PATH= MODULE_DIR / "assets" / "erdiagimp.jpg"
M35_API_BASE_URL     = os.getenv("M35_API_BASE_URL", "http://localhost:5000")

# ---- Local mock fallback (shown when Flask API is offline) ------------------
MOCK_THERAPIES = [
    {"_id": "T001", "therapy_id": "T001", "name": "Chemo Regimen A",    "therapy_type": "Chemotherapy",  "start_date": "2026-01-10", "end_date": "2026-03-10", "cost_per_cycle": 12000, "source_module": "M1"},
    {"_id": "T002", "therapy_id": "T002", "name": "Immunotherapy B",    "therapy_type": "Immunotherapy", "start_date": "2026-02-01", "end_date": "2026-05-15", "cost_per_cycle": 18000, "source_module": "M1"},
    {"_id": "T003", "therapy_id": "T003", "name": "Targeted Therapy C", "therapy_type": "Targeted",       "start_date": "2026-01-20", "end_date": "2026-04-20", "cost_per_cycle": 15000, "source_module": "M1"},
]
MOCK_RESPONSES = [
    {"therapy_id": "T001", "patient_id": "P120", "clinical_improvement": 65, "symptom_relief": 58, "survival_days": 240, "response_grade": "PR",  "source_module": "M2"},
    {"therapy_id": "T002", "patient_id": "P145", "clinical_improvement": 74, "symptom_relief": 68, "survival_days": 310, "response_grade": "CR",  "source_module": "M2"},
    {"therapy_id": "T003", "patient_id": "P181", "clinical_improvement": 59, "symptom_relief": 52, "survival_days": 220, "response_grade": "SD",  "source_module": "M2"},
]
MOCK_SIDE_EFFECTS = [
    {"therapy_id": "T001", "patient_id": "P120", "adverse_event": "Nausea",     "toxicity_grade": 2, "tolerability": "Moderate", "source_module": "M5"},
    {"therapy_id": "T002", "patient_id": "P145", "adverse_event": "Fatigue",    "toxicity_grade": 1, "tolerability": "High",     "source_module": "M5"},
    {"therapy_id": "T003", "patient_id": "P181", "adverse_event": "Neuropathy", "toxicity_grade": 3, "tolerability": "Low",      "source_module": "M5"},
]
MOCK_COST_ANALYSIS = [
    {"therapy_id": "T001", "cycles": 4, "total_cost": 48000, "qalys": 1.2, "source_module": "M25"},
    {"therapy_id": "T002", "cycles": 4, "total_cost": 72000, "qalys": 1.8, "source_module": "M25"},
    {"therapy_id": "T003", "cycles": 4, "total_cost": 60000, "qalys": 1.1, "source_module": "M25"},
]


# ---- API client helpers -------------------------------------------------------

def _client():
    """Return cached M35APIClient."""
    from src.modules.module_f35.api_client import get_api_client
    return get_api_client(M35_API_BASE_URL)


def _api_online() -> bool:
    try:
        return _client().health_check()
    except Exception:
        return False


def _fetch_all_data() -> Tuple[List, List, List, List, Optional[str], str]:
    """
    Fetch all four collections via GET API calls.
    Falls back to local mock data if the backend is offline.
    """
    try:
        c = _client()
        if not c.health_check():
            raise ConnectionError("Backend health check failed")

        therapies    = c.get_therapies(limit=500)
        responses    = c.get_responses(limit=500)
        side_effects = c.get_side_effects(limit=500)
        cost_analysis= c.get_cost_analysis(limit=500)
        return therapies, responses, side_effects, cost_analysis, None, "API ✅"
    except Exception as exc:
        return (
            list(MOCK_THERAPIES), list(MOCK_RESPONSES),
            list(MOCK_SIDE_EFFECTS), list(MOCK_COST_ANALYSIS),
            f"Backend offline ({exc}). Showing local mock data.",
            "Mock (offline)",
        )


# ---- Metric computation (used when API metrics endpoint isn't available) ----

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate_metrics(therapies, responses, side_effects, cost_analysis) -> List[Dict]:
    metrics = []
    for therapy in therapies:
        tid = therapy.get("_id") or therapy.get("therapy_id")

        tr  = [r for r in responses    if r.get("therapy_id") == tid]
        ts  = [s for s in side_effects if s.get("therapy_id") == tid]
        tc  = [c for c in cost_analysis if c.get("therapy_id") == tid]

        avg_impr   = _mean([r.get("clinical_improvement", 0) for r in tr])
        avg_relief = _mean([r.get("symptom_relief", 0)       for r in tr])
        avg_surv   = _mean([r.get("survival_days", 0)        for r in tr])
        avg_tox    = _mean([s.get("toxicity_grade", 0)       for s in ts])

        b_score = (avg_impr + avg_relief + (avg_surv / 365) * 100) / 3
        bri     = b_score / (1 + avg_tox)

        cpq = None
        if tc:
            total_cost = _mean([c.get("total_cost", 0) for c in tc])
            qalys      = _mean([c.get("qalys", 0)      for c in tc])
            if qalys:
                cpq = total_cost / qalys

        metrics.append({
            "therapy_id":         str(tid),
            "name":               therapy.get("name", "Unknown"),
            "avg_improvement":    round(avg_impr, 1),
            "avg_symptom_relief": round(avg_relief, 1),
            "avg_survival_days":  round(avg_surv, 1),
            "avg_toxicity_grade": round(avg_tox, 1),
            "adverse_events":     len(ts),
            "benefit_risk_index": round(bri, 2),
            "cost_per_qaly":      round(cpq, 2) if cpq else None,
        })
    return metrics


# ---- ER diagram helper -------------------------------------------------------

def _render_er_diagram():
    if not ER_DIAGRAM_IMAGE_PATH.exists():
        st.error(f"ER diagram asset not found: {ER_DIAGRAM_IMAGE_PATH}")
        return
    st.image(str(ER_DIAGRAM_IMAGE_PATH), use_container_width=True)


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_module_f35():
    st.markdown("## 🧬 Module F35: Therapy Effectiveness Evaluation System")
    st.caption("Category F – Case-Based Clinical Decision Support")

    # ---- Backend status banner ----------------------------------------------
    online = _api_online()
    if online:
        st.success(f"✅ Backend API online — `{M35_API_BASE_URL}`", icon="🟢")
    else:
        st.warning(
            f"⚠️ Backend API offline (`{M35_API_BASE_URL}`). "
            "Showing local mock data.  Run `python src/modules/module_f35/backend/api_m35.py` to start it.",
            icon="🔴",
        )

    # ---- Fetch data (once per tab render, cached in session state) ----------
    therapies, responses, side_effects, cost_analysis, db_error, data_source = _fetch_all_data()
    if db_error and online:          # only show DB-level error if API was thought to be online
        st.warning(db_error)
    st.caption(f"Data source: **{data_source}**")

    # ---- Tabs ---------------------------------------------------------------
    tab = st.radio(
        "",
        ["🏠 Home", "🗂 ER Diagram", "📥 Ingest Data", "📋 Tables",
         "⚙️ Backend Logic", "📊 Output", "📤 Send to DSL"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    # =========================================================================
    # HOME
    # =========================================================================
    if tab == "🏠 Home":
        st.markdown("### Objectives")
        st.write(
            "Design a therapy response measurement system with benefit and risk tracking. "
            "Aggregate multi-source clinical data to rank therapies by effectiveness and cost-efficiency."
        )

        st.markdown("### Data Flow Architecture")
        st.code("""
Collection Layer  (POST endpoints → M35)
  ├─ M1  Patient Demographics    → POST /api/m35/ingest/therapy
  ├─ M2  Chronic Disease Records → POST /api/m35/ingest/response
  ├─ M5  Allergy & Immunization  → POST /api/m35/ingest/side-effect
  └─ M25 Cost / Billing          → POST /api/m35/ingest/cost-analysis

M35 Processing Layer  (GET endpoints)
  ├─ GET /api/m35/therapy
  ├─ GET /api/m35/response
  ├─ GET /api/m35/side-effect
  ├─ GET /api/m35/cost-analysis
  └─ GET /api/m35/metrics/{therapy_id}

Decision Support Layer  (M13-M24)
  ├─ GET  /api/m35/recommendation
  └─ POST /api/m35/recommendation/send-to-dsl
        """, language="text")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Input Entities")
            for e in ["Therapy (M1)", "PatientResponse (M2)", "SideEffect (M5)", "CostAnalysis (M25)"]:
                st.success(e)
        with col2:
            st.markdown("#### Output Entities")
            for e in ["Benefit-Risk Summary", "Cost-Effectiveness Report", "Ranked Therapy Recommendations"]:
                st.success(e)

        st.markdown("### Effectiveness Measures")
        st.write("Clinical improvement %, symptom relief %, survival days, benefit-risk index.")
        st.markdown("### Safety Metrics")
        st.write("Adverse events, toxicity grades (0-5), tolerability (Low / Moderate / High).")

    # =========================================================================
    # ER DIAGRAM
    # =========================================================================
    elif tab == "🗂 ER Diagram":
        st.markdown("### Entity Relationship Diagram")
        _render_er_diagram()

    # =========================================================================
    # INGEST DATA  (POST from upstream modules)
    # =========================================================================
    elif tab == "📥 Ingest Data":
        st.markdown("### Ingest Data from Upstream Modules")
        st.info(
            "Use this tab to simulate upstream Collection Layer modules "
            "**POST**-ing raw clinical data to M35 via the REST API.",
            icon="ℹ️",
        )

        if not online:
            st.error("Backend must be running to ingest data. Start the Flask API first.")
        else:
            source = st.selectbox(
                "Select source module",
                ["M1 – Patient Demographics (Therapy)", "M2 – Chronic Disease Records (Response)",
                 "M5 – Allergy & Immunization (Side Effect)", "M25 – Cost / Billing (Cost Analysis)"],
            )

            c = _client()

            # ---- Therapy (M1) -----------------------------------------------
            if source.startswith("M1"):
                st.markdown("#### POST Therapy Data → `/api/m35/ingest/therapy`")
                with st.form("form_therapy"):
                    col1, col2 = st.columns(2)
                    name          = col1.text_input("Therapy Name", "Chemo Regimen X")
                    therapy_type  = col2.selectbox("Therapy Type",
                                                   ["Chemotherapy", "Immunotherapy", "Targeted", "Radiation", "Hormonal"])
                    start_date    = col1.text_input("Start Date (YYYY-MM-DD)", "2026-01-01")
                    end_date      = col2.text_input("End Date   (YYYY-MM-DD)", "2026-04-01")
                    cost_per_cycle= st.number_input("Cost per Cycle ($)", min_value=0.0, value=10000.0, step=500.0)
                    submitted     = st.form_submit_button("📤 POST Therapy (from M1)")

                if submitted:
                    with st.spinner("Sending POST request…"):
                        result = c.ingest_therapy(name, therapy_type, start_date, end_date, cost_per_cycle, "M1")
                    if result.get("status") == "success":
                        st.success(f"✅ Therapy created — ID: `{result.get('therapy_id')}`")
                        st.json(result)
                    else:
                        st.error(f"❌ Error: {result.get('message')}")

            # ---- Response (M2) ----------------------------------------------
            elif source.startswith("M2"):
                st.markdown("#### POST Patient Response → `/api/m35/ingest/response`")
                therapy_list = _client().get_therapies(limit=100)
                therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

                with st.form("form_response"):
                    selected_therapy   = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                    col1, col2         = st.columns(2)
                    patient_id         = col1.text_input("Patient ID", "P200")
                    response_grade     = col2.selectbox("Response Grade", ["CR", "PR", "SD", "PD"])
                    clinical_improvement = col1.slider("Clinical Improvement (%)", 0, 100, 60)
                    symptom_relief       = col2.slider("Symptom Relief (%)",       0, 100, 55)
                    survival_days        = st.number_input("Survival Days", min_value=0, value=300, step=10)
                    submitted            = st.form_submit_button("📤 POST Response (from M2)")

                if submitted:
                    tid = therapy_opts[selected_therapy]
                    with st.spinner("Sending POST request…"):
                        result = c.ingest_response(tid, patient_id, clinical_improvement,
                                                   symptom_relief, int(survival_days), response_grade, "M2")
                    if result.get("status") == "success":
                        st.success(f"✅ Response recorded — ID: `{result.get('response_id')}`")
                        st.json(result)
                    else:
                        st.error(f"❌ Error: {result.get('message')}")

            # ---- Side Effect (M5) -------------------------------------------
            elif source.startswith("M5"):
                st.markdown("#### POST Side Effect → `/api/m35/ingest/side-effect`")
                therapy_list = _client().get_therapies(limit=100)
                therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

                with st.form("form_side_effect"):
                    selected_therapy = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                    col1, col2       = st.columns(2)
                    patient_id       = col1.text_input("Patient ID", "P200")
                    adverse_event    = col2.text_input("Adverse Event", "Nausea")
                    toxicity_grade   = col1.slider("Toxicity Grade (0–5)", 0, 5, 2)
                    tolerability     = col2.selectbox("Tolerability", ["High", "Moderate", "Low"])
                    submitted        = st.form_submit_button("📤 POST Side Effect (from M5)")

                if submitted:
                    tid = therapy_opts[selected_therapy]
                    with st.spinner("Sending POST request…"):
                        result = c.ingest_side_effect(tid, patient_id, adverse_event,
                                                      toxicity_grade, tolerability, "M5")
                    if result.get("status") == "success":
                        st.success(f"✅ Side effect recorded — ID: `{result.get('side_effect_id')}`")
                        st.json(result)
                    else:
                        st.error(f"❌ Error: {result.get('message')}")

            # ---- Cost Analysis (M25) ----------------------------------------
            elif source.startswith("M25"):
                st.markdown("#### POST Cost Analysis → `/api/m35/ingest/cost-analysis`")
                therapy_list = _client().get_therapies(limit=100)
                therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

                with st.form("form_cost"):
                    selected_therapy = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                    col1, col2       = st.columns(2)
                    cycles           = col1.number_input("Cycles Completed", min_value=1, value=4)
                    total_cost       = col2.number_input("Total Cost ($)", min_value=0.0, value=50000.0, step=1000.0)
                    qalys            = st.number_input("QALYs (Quality-Adjusted Life Years)", min_value=0.0, value=1.2, step=0.1)
                    submitted        = st.form_submit_button("📤 POST Cost Analysis (from M25)")

                if submitted:
                    tid = therapy_opts[selected_therapy]
                    with st.spinner("Sending POST request…"):
                        result = c.ingest_cost_analysis(tid, int(cycles), total_cost, qalys, "M25")
                    if result.get("status") == "success":
                        st.success(f"✅ Cost analysis recorded — ID: `{result.get('cost_analysis_id')}`")
                        st.json(result)
                    else:
                        st.error(f"❌ Error: {result.get('message')}")

    # =========================================================================
    # TABLES  (GET all collections)
    # =========================================================================
    elif tab == "📋 Tables":
        st.markdown("### Data retrieved via GET APIs")

        st.markdown(f"#### Therapies — `GET {M35_API_BASE_URL}/api/m35/therapy`")
        st.caption(f"{len(therapies)} record(s)")
        st.dataframe(therapies, use_container_width=True)

        st.markdown(f"#### Patient Responses — `GET {M35_API_BASE_URL}/api/m35/response`")
        st.caption(f"{len(responses)} record(s)")
        st.dataframe(responses, use_container_width=True)

        st.markdown(f"#### Side Effects — `GET {M35_API_BASE_URL}/api/m35/side-effect`")
        st.caption(f"{len(side_effects)} record(s)")
        st.dataframe(side_effects, use_container_width=True)

        st.markdown(f"#### Cost Analysis — `GET {M35_API_BASE_URL}/api/m35/cost-analysis`")
        st.caption(f"{len(cost_analysis)} record(s)")
        st.dataframe(cost_analysis, use_container_width=True)

    # =========================================================================
    # BACKEND LOGIC
    # =========================================================================
    elif tab == "⚙️ Backend Logic":
        st.markdown("### Backend Logic — M35 Processing Layer")
        st.code("""
Startup
  1. Connect to MongoDB Atlas (MONGO_URI from .env)
  2. Seed mock records when collections are empty
  3. Start Flask API on port 5000

Data ingestion (POST)
  Collection module → POST /api/m35/ingest/{type}
  Backend validates, assigns _id, stores in MongoDB

Retrieval (GET)
  Dashboard → GET /api/m35/{collection}
  Backend queries MongoDB, returns JSON

Benefit-Risk Calculation
  benefit_score     = (avg_improvement + avg_symptom_relief + avg_survival_days/365*100) / 3
  benefit_risk_index= benefit_score / (1 + avg_toxicity_grade)
  cost_per_qaly     = total_cost / qalys

Recommendation Ranking
  rank_score = benefit_risk_index - (cost_per_qaly / 100_000)
  Top-N sorted descending → sent to DSL (M13-M18)
        """, language="text")

        st.markdown("### MongoDB Collections")
        st.json({
            "database":    os.getenv("MONGO_DB", "therapy_database"),
            "collections": ["therapies", "responses", "side_effects", "cost_analysis"],
            "api_base":    M35_API_BASE_URL,
        })

    # =========================================================================
    # OUTPUT  (metrics via API)
    # =========================================================================
    elif tab == "📊 Output":
        st.markdown("### Benefit-Risk Summary")
        st.caption("Metrics fetched via `GET /api/m35/metrics/{therapy_id}` or computed locally from collection data.")

        metrics = _aggregate_metrics(therapies, responses, side_effects, cost_analysis)

        c1, c2, c3 = st.columns(3)
        c1.metric("Therapies",     len(therapies))
        c2.metric("Responses",     len(responses))
        c3.metric("Adverse Events",len(side_effects))

        st.divider()
        if metrics:
            st.dataframe(metrics, use_container_width=True)

            # Individual therapy metrics via API
            if online and therapies:
                st.markdown("### Per-Therapy Metrics (via `GET /api/m35/metrics/{id}`)")
                sel_name = st.selectbox("Select therapy", [t.get("name", t.get("_id")) for t in therapies])
                sel_therapy = next(
                    (t for t in therapies if t.get("name") == sel_name or t.get("_id") == sel_name), None
                )
                if sel_therapy:
                    tid = sel_therapy.get("_id") or sel_therapy.get("therapy_id")
                    with st.spinner("Fetching metrics…"):
                        m = _client().get_metrics(str(tid))
                    if m:
                        mc1, mc2, mc3, mc4 = st.columns(4)
                        mc1.metric("Benefit-Risk Index", m.get("benefit_risk_index", "—"))
                        mc2.metric("Avg Improvement",    f"{m.get('avg_improvement', 0)}%")
                        mc3.metric("Avg Toxicity",       m.get("avg_toxicity_grade", "—"))
                        mc4.metric("Cost/QALY",
                                   f"${m.get('cost_per_qaly', 0):,.0f}" if m.get("cost_per_qaly") else "N/A")
                        st.json(m)
                    else:
                        st.warning("No metric data yet for this therapy — add responses first.")
        else:
            st.info("No data available. Ingest data using the 📥 Ingest Data tab.")

        st.markdown("### Recommendation Logic")
        st.write("Therapies ranked by `rank_score = benefit_risk_index − cost_per_qaly/100,000`. Higher = better.")

    # =========================================================================
    # SEND TO DSL  (real POST)
    # =========================================================================
    elif tab == "📤 Send to DSL":
        st.markdown("### Therapy Recommendations → Decision Support Layer (M13-M24)")
        st.caption(
            f"Recommendations fetched via `GET {M35_API_BASE_URL}/api/m35/recommendation`  "
            f"then dispatched via `POST {M35_API_BASE_URL}/api/m35/recommendation/send-to-dsl`"
        )

        if not online:
            st.error("Backend must be running to send real recommendations. Start the Flask API first.")
            st.info("When offline, the simulated payload below shows what would be sent.")

        # Fetch (or compute) recommendations
        if online:
            with st.spinner("Fetching recommendations from API…"):
                recommendations = _client().get_recommendations(limit=10)
        else:
            metrics = _aggregate_metrics(therapies, responses, side_effects, cost_analysis)
            recommendations = sorted(metrics, key=lambda m: m.get("benefit_risk_index", 0), reverse=True)[:10]

        if not recommendations:
            st.warning("No recommendations available — ingest therapy and response data first.")
        else:
            st.markdown("#### Top Therapy Recommendations")
            display = []
            for rec in recommendations:
                cpq = rec.get("cost_per_qaly")
                display.append({
                    "Therapy":             rec.get("name", "Unknown"),
                    "Type":                rec.get("therapy_type", "—"),
                    "Benefit-Risk Index":  rec.get("benefit_risk_index", 0),
                    "Cost / QALY":         f"${cpq:,.0f}" if cpq else "N/A",
                    "Rank Score":          rec.get("rank_score", rec.get("benefit_risk_index", 0)),
                })
            st.dataframe(display, use_container_width=True)

            st.markdown("#### Dispatch to Decision Support Layer")
            col1, col2 = st.columns(2)
            target_module = col1.selectbox(
                "Target DSL Module",
                ["M13 – Clinical Guidelines", "M14 – Treatment Planning",
                 "M15 – Drug Interactions",   "M16 – Allergy Alerts",
                 "M17 – Dosage Optimisation",  "M18 – Patient Monitoring"],
            )
            urgency       = col2.selectbox("Urgency", ["low", "medium", "high"])
            patient_id    = st.text_input("Patient ID (optional)", "")
            top_n         = st.slider("Number of recommendations to dispatch", 1, min(5, len(recommendations)), 3)

            if st.button("🚀 Send Recommendations to Decision Support Layer", use_container_width=True):
                module_code = target_module.split(" ")[0]
                pid         = patient_id.strip() or "GENERAL"
                sent, failed= 0, 0

                with st.spinner(f"Dispatching {top_n} recommendation(s) to {module_code}…"):
                    for rec in recommendations[:top_n]:
                        if online:
                            result = _client().send_recommendation_to_dsl(
                                recommendation_data=rec,
                                target_dsl_module=module_code,
                                patient_id=pid,
                                urgency=urgency,
                            )
                            if result.get("status") == "success":
                                sent += 1
                            else:
                                failed += 1
                        else:
                            sent += 1  # simulated

                if online:
                    if failed == 0:
                        st.success(f"✅ {sent}/{top_n} recommendation(s) dispatched to {module_code}.")
                    else:
                        st.warning(f"Sent {sent}, failed {failed}.")
                else:
                    st.info(f"[Simulated] {sent} recommendation(s) prepared for {module_code}.")

                st.markdown("#### Last dispatched payload")
                last_rec = recommendations[0]
                st.json({
                    "source_module":    "M35",
                    "target_module":    module_code,
                    "urgency":          urgency,
                    "patient_id":       pid,
                    "recommendation":   last_rec,
                    "mode":             "live" if online else "simulated",
                })

            st.divider()
            st.markdown("#### Data Flow")
            st.code("""
Collection Layer (M1, M2, M5, M25)
  ↓  POST /api/m35/ingest/*
M35 Processing & Analysis
  ├─ benefit_risk_index = benefit_score / (1 + avg_toxicity)
  ├─ cost_per_qaly      = total_cost / qalys
  └─ rank_score         = bri - cost_per_qaly/100,000
  ↓  GET /api/m35/recommendation
  ↓  POST /api/m35/recommendation/send-to-dsl
Decision Support Layer (M13 – M18)
            """, language="text")


# ---- Standalone run ---------------------------------------------------------
if __name__ == "__main__":
    render_module_f35()
