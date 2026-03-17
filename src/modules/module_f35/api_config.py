"""
Configuration for M35 Backend API Endpoints
Maps the data flow architecture: Collection Layer → M35 → Decision Support Layer
"""

import os
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

# Backend API Base URL
M35_API_BASE_URL = os.getenv("M35_API_BASE_URL", "http://localhost:5000")

# ==================================================================================
# DATA COLLECTION LAYER INGESTION ENDPOINTS
# These receive data from Collection Layer modules (M1-M6, M25-M30, M43-M48)
# ==================================================================================

COLLECTION_ENDPOINTS = {
    "ingest_therapy": f"{M35_API_BASE_URL}/api/m35/ingest/therapy",
    "ingest_response": f"{M35_API_BASE_URL}/api/m35/ingest/response",
    "ingest_side_effect": f"{M35_API_BASE_URL}/api/m35/ingest/side-effect",
    "ingest_cost_analysis": f"{M35_API_BASE_URL}/api/m35/ingest/cost-analysis",
}

# ==================================================================================
# M35 PROCESSING & RETRIEVAL ENDPOINTS
# ==================================================================================

RETRIEVAL_ENDPOINTS = {
    "get_therapies": f"{M35_API_BASE_URL}/api/m35/therapy",
    "get_therapy_detail": f"{M35_API_BASE_URL}/api/m35/therapy",  # + /{therapy_id}
    "get_responses": f"{M35_API_BASE_URL}/api/m35/response",
    "get_side_effects": f"{M35_API_BASE_URL}/api/m35/side-effect",
    "get_metrics": f"{M35_API_BASE_URL}/api/m35/metrics",  # + /{therapy_id}
}

# ==================================================================================
# DECISION SUPPORT LAYER OUTPUT ENDPOINTS
# These send recommendations to DSL modules (M13-M24)
# ==================================================================================

DSL_ENDPOINTS = {
    "get_recommendations": f"{M35_API_BASE_URL}/api/m35/recommendation",
    "send_to_dsl": f"{M35_API_BASE_URL}/api/m35/recommendation/send-to-dsl",
}

# Health check
HEALTH_CHECK = f"{M35_API_BASE_URL}/api/m35/health"

# ==================================================================================
# DATA FLOW MAPPING
# ==================================================================================

DATA_FLOW_SCHEMA = """
DATA COLLECTION LAYER (M1-M6, M25-M30, M43-M48)
        ↓
        ├─ M1: Patient Demographics → ingest_therapy
        ├─ M2: Chronic Disease Records → ingest_response
        ├─ M5: Allergy & Immunization → ingest_side_effect
        ├─ M25-M30: Lab Results, Cost Data → ingest_cost_analysis
        └─ M43-M48: Other Clinical Data
        
        ↓
M35 PROCESSING & ANALYSIS LAYER
        ├─ Extract therapy data
        ├─ Aggregate patient responses
        ├─ Calculate benefits (clinical_improvement, symptom_relief, survival)
        ├─ Assess risks (adverse_events, toxicity_grade)
        ├─ Compute benefit_risk_index = benefit_score / (1 + toxicity)
        └─ Calculate cost_per_qaly for cost-effectiveness
        
        ↓
DECISION SUPPORT LAYER (M13-M24)
        ├─ M13-M18: Clinical Decision Support
        ├─ Receive ranked recommendations from M35
        ├─ Apply clinical guidelines
        └─ Generate personalized therapy recommendations

OUTPUT: Treatment effectiveness dashboard with actionable insights
"""
