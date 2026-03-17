from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from components.tabs import module_tabs


SCHEMA_SQL = """
CREATE TABLE Therapy (
    therapy_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    therapy_type VARCHAR(40) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    cost_per_cycle DECIMAL(12, 2)
);

CREATE TABLE Response (
    response_id VARCHAR(20) PRIMARY KEY,
    therapy_id VARCHAR(20) NOT NULL,
    patient_id VARCHAR(20) NOT NULL,
    clinical_improvement INT CHECK (clinical_improvement BETWEEN 0 AND 100),
    symptom_relief INT CHECK (symptom_relief BETWEEN 0 AND 100),
    survival_days INT,
    response_grade VARCHAR(10),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (therapy_id) REFERENCES Therapy(therapy_id)
);

CREATE TABLE SideEffect (
    side_effect_id VARCHAR(20) PRIMARY KEY,
    therapy_id VARCHAR(20) NOT NULL,
    patient_id VARCHAR(20) NOT NULL,
    adverse_event VARCHAR(120) NOT NULL,
    toxicity_grade INT CHECK (toxicity_grade BETWEEN 0 AND 5),
    tolerability VARCHAR(20),
    noted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (therapy_id) REFERENCES Therapy(therapy_id)
);

CREATE TABLE CostAnalysis (
    analysis_id VARCHAR(20) PRIMARY KEY,
    therapy_id VARCHAR(20) NOT NULL,
    cycles INT NOT NULL,
    total_cost DECIMAL(14, 2) NOT NULL,
    qalys DECIMAL(6, 2),
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (therapy_id) REFERENCES Therapy(therapy_id)
);
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

    therapies = []
    responses = []
    side_effects = []
    cost_analysis = []

    tab = module_tabs()
    st.divider()

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
  |--< Response (response_id PK, therapy_id FK, patient_id, clinical_improvement, symptom_relief, survival_days)
  |--< SideEffect (side_effect_id PK, therapy_id FK, patient_id, adverse_event, toxicity_grade, tolerability)
  |--< CostAnalysis (analysis_id PK, therapy_id FK, cycles, total_cost, qalys)
""".strip(),
            language="text",
        )

    elif tab == "Tables":
        st.info("Tables are shown once backend data is connected.")
        st.markdown("### Therapy")
        st.table(therapies)

        st.markdown("### Response")
        st.table(responses)

        st.markdown("### SideEffect")
        st.table(side_effects)

        st.markdown("### CostAnalysis")
        st.table(cost_analysis)

    elif tab == "SQL Query":
        st.markdown("### Schema (DDL)")
        st.code(SCHEMA_SQL, language="sql")

        st.markdown("### API Contract")
        st.json(API_CONTRACT)

        st.markdown("### Sample SQL Queries")
        st.code(
            """
-- Benefit calculation per therapy
SELECT
    r.therapy_id,
    AVG(r.clinical_improvement) AS avg_improvement,
    AVG(r.symptom_relief) AS avg_symptom_relief,
    AVG(r.survival_days) AS avg_survival_days
FROM Response r
GROUP BY r.therapy_id;

-- Cost per QALY
SELECT
    c.therapy_id,
    c.total_cost / NULLIF(c.qalys, 0) AS cost_per_qaly
FROM CostAnalysis c;

-- Comparative effectiveness with toxicity
SELECT
    t.therapy_id,
    t.name,
    AVG(r.clinical_improvement) AS avg_improvement,
    AVG(s.toxicity_grade) AS avg_toxicity
FROM Therapy t
JOIN Response r ON t.therapy_id = r.therapy_id
LEFT JOIN SideEffect s ON t.therapy_id = s.therapy_id
GROUP BY t.therapy_id, t.name;
""".strip(),
            language="sql",
        )

    elif tab == "Triggers":
        st.markdown("### Triggers and Procedures")
        st.code(
            """
-- Trigger to update therapy summary after response insert
CREATE TRIGGER trg_update_therapy_summary
AFTER INSERT ON Response
FOR EACH ROW
BEGIN
    UPDATE TherapySummary
    SET avg_improvement = (
        SELECT AVG(clinical_improvement)
        FROM Response
        WHERE therapy_id = NEW.therapy_id
    ),
    avg_symptom_relief = (
        SELECT AVG(symptom_relief)
        FROM Response
        WHERE therapy_id = NEW.therapy_id
    )
    WHERE therapy_id = NEW.therapy_id;
END;

-- Procedure to compute benefit-risk index
CREATE PROCEDURE sp_compute_benefit_risk()
BEGIN
    UPDATE TherapySummary
    SET benefit_risk_index = (avg_improvement + avg_symptom_relief) / (1 + avg_toxicity_grade);
END;
""".strip(),
            language="sql",
        )

    elif tab == "Output":
        st.markdown("### Benefit and Risk Summary")
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
