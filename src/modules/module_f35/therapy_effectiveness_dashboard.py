from pathlib import Path
import os
import sys

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
MODULE_DIR = Path(__file__).resolve().parent
ER_DIAGRAM_SVG_PATH = MODULE_DIR / "assets" / "m35_er_diagram.svg"

from components.tabs import module_tabs
from src.modules.module_f35.api_client import get_api_client


API_EXAMPLES = """
POST /api/m35/ingest/therapy
{
  "name": "Chemo Regimen A",
  "therapy_type": "Chemotherapy",
  "start_date": "2026-01-10",
  "end_date": "2026-03-10",
  "cost_per_cycle": 12000,
  "source_module": "M1"
}

POST /api/m35/ingest/response
{
  "therapy_id": "<therapy_id>",
  "patient_id": "P120",
  "clinical_improvement": 65,
  "symptom_relief": 58,
  "survival_days": 240,
  "response_grade": "PR",
  "source_module": "M2"
}

GET /api/m35/therapy?limit=10
GET /api/m35/metrics/<therapy_id>
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


def _fetch_backend_data():
    """
    Fetch data from M35 API Backend instead of direct database access
    Data flows from: Collection Layer → M35 Backend → Frontend
    """
    try:
        api_client = get_api_client(os.getenv("M35_API_BASE_URL", "http://localhost:5000"))
        
        # Check if backend is healthy
        if not api_client.health_check():
            return [], [], [], [], "Backend API not responding. Ensure M35 backend is running on port 5000"
        
        # Fetch data from M35 API endpoints
        therapies = api_client.get_therapies(limit=1000)
        responses = api_client.get_responses(limit=5000)
        side_effects = api_client.get_side_effects(limit=5000)
        
        # Note: cost_analysis comes from responses if available
        cost_analysis = []
        
        return therapies, responses, side_effects, cost_analysis, None
    except Exception as exc:
        return [], [], [], [], f"Failed to fetch data from M35 Backend: {str(exc)}"


def _aggregate_metrics(therapies, responses, side_effects, cost_analysis):
    """
    Aggregate metrics from API data
    Sends aggregated insights to Decision Support Layer (M13-M24)
    """
    metrics = []
    api_client = get_api_client(os.getenv("M35_API_BASE_URL", "http://localhost:5000"))

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

        # Try to get cost_per_qaly from API metrics endpoint
        cost_per_qaly = None
        try:
            metrics_data = api_client.get_metrics(str(therapy_id))
            if metrics_data:
                cost_per_qaly = metrics_data.get("cost_per_qaly")
        except:
            pass

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
        if not ER_DIAGRAM_SVG_PATH.exists():
                st.error(f"ER diagram asset not found: {ER_DIAGRAM_SVG_PATH}")
                return

        er_svg = ER_DIAGRAM_SVG_PATH.read_text(encoding="utf-8")
        components.html(er_svg, height=720, scrolling=True)


def render_module_f35():
    st.markdown("## Module 35: Therapy Effectiveness Evaluation System")
    st.caption("Category F - Case-Based Decision Support")

    therapies, responses, side_effects, cost_analysis, db_error = _fetch_backend_data()

    tab = st.radio(
        "",
        ["Home", "ER Diagram", "Tables", "API Requests", "Backend Logic", "Output", "📤 Send to DSL"],
        horizontal=True,
    )
    st.divider()

    if db_error:
        st.error(db_error)

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
        _render_er_diagram_image()

    elif tab == "Tables":
        if not therapies and not responses and not side_effects and not cost_analysis:
            st.info("No data returned from the API yet.")
        st.markdown("### Therapy")
        st.table(therapies)

        st.markdown("### Response")
        st.table(responses)

        st.markdown("### SideEffect")
        st.table(side_effects)

        st.markdown("### CostAnalysis")
        st.table(cost_analysis)

    elif tab == "API Requests":
        st.markdown("### API Contract")
        st.json(API_CONTRACT)

        st.markdown("### Example API Requests")
        st.code(
            API_EXAMPLES,
            language="json",
        )

    elif tab == "Backend Logic":
        st.markdown("### Backend Logic (REST API)")
        st.code(
            """
POST /api/m35/ingest/therapy     -> store therapy metadata
POST /api/m35/ingest/response    -> store outcomes and symptoms
POST /api/m35/ingest/side-effect -> store adverse events
POST /api/m35/ingest/cost-analysis -> store costs + QALY

GET /api/m35/metrics/<therapy_id>
    -> aggregates benefit, risk, and cost per QALY

GET /api/m35/recommendation
    -> ranks therapies for decision support modules
""".strip(),
            language="text",
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

    elif tab == "📤 Send to DSL":
        st.markdown("### Therapy Recommendations → Decision Support Layer (M13-M24)")
        st.info("This tab sends M35 recommendations to the Decision Support Layer for clinical decision making")
        
        api_client = get_api_client(os.getenv("M35_API_BASE_URL", "http://localhost:5000"))
        recommendations = api_client.get_recommendations(limit=10)
        
        if not recommendations:
            st.warning("No recommendations available. Ensure M35 backend is running and has data.")
        else:
            st.markdown("#### Top Therapy Recommendations")
            
            # Display as table
            rec_data = []
            for rec in recommendations:
                rec_data.append({
                    "Therapy": rec.get("name", "Unknown"),
                    "Type": rec.get("therapy_type", "N/A"),
                    "Benefit-Risk Index": rec.get("benefit_risk_index", 0),
                    "Cost/QALY": f"${rec.get('cost_per_qaly', 0):.2f}" if rec.get('cost_per_qaly') else "N/A",
                    "Rank Score": rec.get("rank_score", 0),
                    "Responses": rec.get("response_count", 0)
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
                    # Send each recommendation to DSL
                    success_count = 0
                    for rec in recommendations[:3]:  # Send top 3 recommendations
                        response = api_client.send_recommendation_to_dsl(
                            recommendation_data=rec,
                            target_dsl_module=target_module,
                            patient_id=patient_id or "GENERAL",
                            urgency=urgency
                        )
                        if response.get("status") == "success":
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"✅ Sent {success_count} recommendations to Decision Support Layer ({target_module})")
                        st.json({"status": "success", "count": success_count, "target": target_module})
                    else:
                        st.error("Failed to send recommendations. Ensure M35 backend is running.")
            
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
