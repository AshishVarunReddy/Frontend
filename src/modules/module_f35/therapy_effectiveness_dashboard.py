"""
Module F35 – Therapy Effectiveness Evaluation System
Category F – Case-Based Decision Support

Data flow:
  Collection Layer (M1 → therapies, M2 → responses, M5 → side effects, M25 → cost)
      ↓  direct PyMongo writes
  MongoDB Atlas  (therapy_database)
      ↓  direct PyMongo reads
  This Streamlit dashboard  →  Decision Support Layer (M13-M24)

No Flask backend required — all DB operations go through db_client.py.
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

MODULE_DIR            = Path(__file__).resolve().parent
ER_DIAGRAM_IMAGE_PATH = MODULE_DIR / "assets" / "erdiagimp.jpg"

# ---- Direct DB client (replaces Flask API) ----------------------------------
from src.modules.module_f35 import db_client

# Seed data on first import
db_client._seed_if_empty()


# ---- Fetch helpers -----------------------------------------------------------

def _fetch_all_data() -> Tuple[List, List, List, List, Optional[str], str]:
    """
    Fetch all four collections directly from MongoDB (or in-memory fallback).
    """
    try:
        therapies     = db_client.get_therapies(limit=500)
        responses     = db_client.get_responses(limit=500)
        side_effects  = db_client.get_side_effects(limit=500)
        cost_analysis = db_client.get_cost_analysis(limit=500)
        return therapies, responses, side_effects, cost_analysis, None, db_client.storage_label()
    except Exception as exc:
        return [], [], [], [], f"Error loading data: {exc}", "Error"


# ---- Metric computation -----------------------------------------------------

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

    # ---- Storage status banner -----------------------------------------------
    connected = db_client.is_connected()
    if connected:
        st.success(f"✅ Connected directly to MongoDB Atlas — `{db_client.MONGO_DB}`", icon="🟢")
    else:
        st.warning(
            "⚠️ MongoDB unavailable. Using in-memory fallback data. "
            "Set MONGO_URI in your .env or Streamlit secrets to connect.",
            icon="🔴",
        )

    # ---- Fetch data ----------------------------------------------------------
    therapies, responses, side_effects, cost_analysis, db_error, data_source = _fetch_all_data()
    if db_error:
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
Collection Layer  (direct MongoDB writes)
  ├─ M1  Patient Demographics    → therapies collection
  ├─ M2  Chronic Disease Records → responses collection
  ├─ M5  Allergy & Immunization  → side_effects collection
  └─ M25 Cost / Billing          → cost_analysis collection

M35 Processing Layer  (direct MongoDB reads)
  ├─ therapies     → benefit-risk analysis
  ├─ responses     → clinical improvement metrics
  ├─ side_effects  → safety / tolerability scoring
  └─ cost_analysis → cost-effectiveness (QALY)

Decision Support Layer  (M13-M24)
  └─ Ranked recommendations dispatched downstream
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
    # INGEST DATA  (direct writes from upstream modules)
    # =========================================================================
    elif tab == "📥 Ingest Data":
        st.markdown("### Ingest Data from Upstream Modules")
        st.info(
            "Use this tab to simulate upstream Collection Layer modules "
            "writing raw clinical data directly to the MongoDB collections.",
            icon="ℹ️",
        )

        source = st.selectbox(
            "Select source module",
            ["M1 – Patient Demographics (Therapy)", "M2 – Chronic Disease Records (Response)",
             "M5 – Allergy & Immunization (Side Effect)", "M25 – Cost / Billing (Cost Analysis)"],
        )

        # ---- Therapy (M1) ---------------------------------------------------
        if source.startswith("M1"):
            st.markdown("#### Insert Therapy Data → `therapies` collection")
            with st.form("form_therapy"):
                col1, col2 = st.columns(2)
                name          = col1.text_input("Therapy Name", "Chemo Regimen X")
                therapy_type  = col2.selectbox("Therapy Type",
                                               ["Chemotherapy", "Immunotherapy", "Targeted", "Radiation", "Hormonal"])
                start_date    = col1.text_input("Start Date (YYYY-MM-DD)", "2026-01-01")
                end_date      = col2.text_input("End Date   (YYYY-MM-DD)", "2026-04-01")
                cost_per_cycle= st.number_input("Cost per Cycle ($)", min_value=0.0, value=10000.0, step=500.0)
                submitted     = st.form_submit_button("📤 Insert Therapy (from M1)")

            if submitted:
                with st.spinner("Writing to database…"):
                    result = db_client.ingest_therapy(name, therapy_type, start_date, end_date, cost_per_cycle, "M1")
                if result.get("status") == "success":
                    st.success(f"✅ Therapy created — ID: `{result.get('therapy_id')}`")
                    st.json(result)
                else:
                    st.error(f"❌ Error: {result.get('message')}")

        # ---- Response (M2) --------------------------------------------------
        elif source.startswith("M2"):
            st.markdown("#### Insert Patient Response → `responses` collection")
            therapy_list = db_client.get_therapies(limit=100)
            therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

            with st.form("form_response"):
                selected_therapy   = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                col1, col2         = st.columns(2)
                patient_id         = col1.text_input("Patient ID", "P200")
                response_grade     = col2.selectbox("Response Grade", ["CR", "PR", "SD", "PD"])
                clinical_improvement = col1.slider("Clinical Improvement (%)", 0, 100, 60)
                symptom_relief       = col2.slider("Symptom Relief (%)",       0, 100, 55)
                survival_days        = st.number_input("Survival Days", min_value=0, value=300, step=10)
                submitted            = st.form_submit_button("📤 Insert Response (from M2)")

            if submitted:
                tid = therapy_opts[selected_therapy]
                with st.spinner("Writing to database…"):
                    result = db_client.ingest_response(tid, patient_id, clinical_improvement,
                                                       symptom_relief, int(survival_days), response_grade, "M2")
                if result.get("status") == "success":
                    st.success(f"✅ Response recorded — ID: `{result.get('response_id')}`")
                    st.json(result)
                else:
                    st.error(f"❌ Error: {result.get('message')}")

        # ---- Side Effect (M5) -----------------------------------------------
        elif source.startswith("M5"):
            st.markdown("#### Insert Side Effect → `side_effects` collection")
            therapy_list = db_client.get_therapies(limit=100)
            therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

            with st.form("form_side_effect"):
                selected_therapy = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                col1, col2       = st.columns(2)
                patient_id       = col1.text_input("Patient ID", "P200")
                adverse_event    = col2.text_input("Adverse Event", "Nausea")
                toxicity_grade   = col1.slider("Toxicity Grade (0–5)", 0, 5, 2)
                tolerability     = col2.selectbox("Tolerability", ["High", "Moderate", "Low"])
                submitted        = st.form_submit_button("📤 Insert Side Effect (from M5)")

            if submitted:
                tid = therapy_opts[selected_therapy]
                with st.spinner("Writing to database…"):
                    result = db_client.ingest_side_effect(tid, patient_id, adverse_event,
                                                          toxicity_grade, tolerability, "M5")
                if result.get("status") == "success":
                    st.success(f"✅ Side effect recorded — ID: `{result.get('side_effect_id')}`")
                    st.json(result)
                else:
                    st.error(f"❌ Error: {result.get('message')}")

        # ---- Cost Analysis (M25) --------------------------------------------
        elif source.startswith("M25"):
            st.markdown("#### Insert Cost Analysis → `cost_analysis` collection")
            therapy_list = db_client.get_therapies(limit=100)
            therapy_opts = {t.get("name", t.get("_id")): t.get("_id") or t.get("therapy_id") for t in therapy_list}

            with st.form("form_cost"):
                selected_therapy = st.selectbox("Select Therapy", list(therapy_opts.keys()))
                col1, col2       = st.columns(2)
                cycles           = col1.number_input("Cycles Completed", min_value=1, value=4)
                total_cost       = col2.number_input("Total Cost ($)", min_value=0.0, value=50000.0, step=1000.0)
                qalys            = st.number_input("QALYs (Quality-Adjusted Life Years)", min_value=0.0, value=1.2, step=0.1)
                submitted        = st.form_submit_button("📤 Insert Cost Analysis (from M25)")

            if submitted:
                tid = therapy_opts[selected_therapy]
                with st.spinner("Writing to database…"):
                    result = db_client.ingest_cost_analysis(tid, int(cycles), total_cost, qalys, "M25")
                if result.get("status") == "success":
                    st.success(f"✅ Cost analysis recorded — ID: `{result.get('cost_analysis_id')}`")
                    st.json(result)
                else:
                    st.error(f"❌ Error: {result.get('message')}")

    # =========================================================================
    # TABLES  (all collections)
    # =========================================================================
    elif tab == "📋 Tables":
        st.markdown("### Data from MongoDB Collections")

        st.markdown("#### Therapies — `therapies` collection")
        st.caption(f"{len(therapies)} record(s)")
        st.dataframe(therapies, use_container_width=True)

        st.markdown("#### Patient Responses — `responses` collection")
        st.caption(f"{len(responses)} record(s)")
        st.dataframe(responses, use_container_width=True)

        st.markdown("#### Side Effects — `side_effects` collection")
        st.caption(f"{len(side_effects)} record(s)")
        st.dataframe(side_effects, use_container_width=True)

        st.markdown("#### Cost Analysis — `cost_analysis` collection")
        st.caption(f"{len(cost_analysis)} record(s)")
        st.dataframe(cost_analysis, use_container_width=True)

    # =========================================================================
    # BACKEND LOGIC
    # =========================================================================
    elif tab == "⚙️ Backend Logic":
        st.markdown("### Backend Logic — M35 Processing Layer")
        st.code("""
Startup
  1. Connect to MongoDB Atlas (MONGO_URI from .env / Streamlit secrets)
  2. Seed mock records when collections are empty
  3. All DB operations happen directly via PyMongo (no Flask)

Data ingestion (direct writes)
  Collection module → db_client.ingest_*()
  Validates, assigns _id, stores in MongoDB collection

Retrieval (direct reads)
  Dashboard → db_client.get_*()
  Queries MongoDB, returns Python dicts

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
            "storage":     db_client.storage_label(),
        })

    # =========================================================================
    # OUTPUT  (metrics)
    # =========================================================================
    elif tab == "📊 Output":
        st.markdown("### Benefit-Risk Summary")
        st.caption("Metrics computed directly from MongoDB collection data.")

        metrics = _aggregate_metrics(therapies, responses, side_effects, cost_analysis)

        c1, c2, c3 = st.columns(3)
        c1.metric("Therapies",     len(therapies))
        c2.metric("Responses",     len(responses))
        c3.metric("Adverse Events",len(side_effects))

        st.divider()
        if metrics:
            st.dataframe(metrics, use_container_width=True)

            # Individual therapy metrics
            if therapies:
                st.markdown("### Per-Therapy Metrics")
                sel_name = st.selectbox("Select therapy", [t.get("name", t.get("_id")) for t in therapies])
                sel_therapy = next(
                    (t for t in therapies if t.get("name") == sel_name or t.get("_id") == sel_name), None
                )
                if sel_therapy:
                    tid = sel_therapy.get("_id") or sel_therapy.get("therapy_id")
                    with st.spinner("Computing metrics…"):
                        m = db_client.get_metrics(str(tid))
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
    # SEND TO DSL  (dispatch recommendations)
    # =========================================================================
    elif tab == "📤 Send to DSL":
        st.markdown("### Therapy Recommendations → Decision Support Layer (M13-M24)")
        st.caption("Recommendations computed directly from MongoDB data and dispatched to DSL modules.")

        # Fetch recommendations
        with st.spinner("Computing recommendations…"):
            recommendations = db_client.get_recommendations(limit=10)

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
                        result = db_client.send_recommendation_to_dsl(
                            recommendation_data=rec,
                            target_dsl_module=module_code,
                            patient_id=pid,
                            urgency=urgency,
                        )
                        if result.get("status") == "success":
                            sent += 1
                        else:
                            failed += 1

                if failed == 0:
                    st.success(f"✅ {sent}/{top_n} recommendation(s) dispatched to {module_code}.")
                else:
                    st.warning(f"Sent {sent}, failed {failed}.")

                st.markdown("#### Last dispatched payload")
                last_rec = recommendations[0]
                st.json({
                    "source_module":    "M35",
                    "target_module":    module_code,
                    "urgency":          urgency,
                    "patient_id":       pid,
                    "recommendation":   last_rec,
                })

            st.divider()
            st.markdown("#### Data Flow")
            st.code("""
Collection Layer (M1, M2, M5, M25)
  ↓  direct MongoDB writes
M35 Processing & Analysis
  ├─ benefit_risk_index = benefit_score / (1 + avg_toxicity)
  ├─ cost_per_qaly      = total_cost / qalys
  └─ rank_score         = bri - cost_per_qaly/100,000
  ↓  direct MongoDB reads → compute recommendations
Decision Support Layer (M13 – M18)
            """, language="text")


# ---- Standalone run ---------------------------------------------------------
if __name__ == "__main__":
    render_module_f35()
