"""
M35 API Client for Frontend
Handles communication between Streamlit frontend and M35 backend API
"""

import requests
import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class M35APIClient:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.endpoints = {
            "ingest_therapy": f"{base_url}/api/m35/ingest/therapy",
            "ingest_response": f"{base_url}/api/m35/ingest/response",
            "ingest_side_effect": f"{base_url}/api/m35/ingest/side-effect",
            "ingest_cost_analysis": f"{base_url}/api/m35/ingest/cost-analysis",
            "get_therapies": f"{base_url}/api/m35/therapy",
            "get_therapy": f"{base_url}/api/m35/therapy",
            "get_responses": f"{base_url}/api/m35/response",
            "get_side_effects": f"{base_url}/api/m35/side-effect",
            "get_metrics": f"{base_url}/api/m35/metrics",
            "get_recommendations": f"{base_url}/api/m35/recommendation",
            "send_recommendation_dsl": f"{base_url}/api/m35/recommendation/send-to-dsl",
            "health": f"{base_url}/api/m35/health"
        }
    
    # ==================================================================================
    # DATA COLLECTION LAYER: INGESTION METHODS
    # ==================================================================================
    
    def ingest_therapy(self, name: str, therapy_type: str, start_date: str, 
                      end_date: str, cost_per_cycle: float, source_module: str = "M1") -> Dict:
        """
        Ingest therapy from Collection Layer (M1)
        
        Args:
            name: Therapy name (e.g., "Chemo Regimen A")
            therapy_type: Type (e.g., "Chemotherapy")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            cost_per_cycle: Cost per cycle
            source_module: Which collection module provided this (M1, M25, etc.)
        
        Returns:
            Dict with status and therapy_id
        """
        payload = {
            "name": name,
            "therapy_type": therapy_type,
            "start_date": start_date,
            "end_date": end_date,
            "cost_per_cycle": cost_per_cycle,
            "source_module": source_module
        }
        try:
            response = requests.post(self.endpoints["ingest_therapy"], json=payload, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Error ingesting therapy: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def ingest_response(self, therapy_id: str, patient_id: str, clinical_improvement: float,
                       symptom_relief: float, survival_days: int, response_grade: str,
                       source_module: str = "M2") -> Dict:
        """
        Ingest patient response from Collection Layer (M2 - Chronic Disease Records)
        
        Args:
            therapy_id: Therapy ID from ingest_therapy
            patient_id: Patient ID
            clinical_improvement: Percentage improvement (0-100)
            symptom_relief: Symptom relief percentage (0-100)
            survival_days: Survival days
            response_grade: Response grade (CR, PR, SD, PD)
            source_module: Collection module source (M2, M25, etc.)
        
        Returns:
            Dict with status and response_id
        """
        payload = {
            "therapy_id": therapy_id,
            "patient_id": patient_id,
            "clinical_improvement": clinical_improvement,
            "symptom_relief": symptom_relief,
            "survival_days": survival_days,
            "response_grade": response_grade,
            "source_module": source_module
        }
        try:
            response = requests.post(self.endpoints["ingest_response"], json=payload, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Error ingesting response: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def ingest_side_effect(self, therapy_id: str, patient_id: str, adverse_event: str,
                          toxicity_grade: int, tolerability: str, 
                          source_module: str = "M5") -> Dict:
        """
        Ingest side effect from Collection Layer (M5 - Allergy & Immunization)
        
        Args:
            therapy_id: Therapy ID
            patient_id: Patient ID
            adverse_event: Adverse event name
            toxicity_grade: Toxicity grade (0-5)
            tolerability: Tolerability level (Low, Moderate, High)
            source_module: Collection module source (M5, M25, etc.)
        
        Returns:
            Dict with status and side_effect_id
        """
        payload = {
            "therapy_id": therapy_id,
            "patient_id": patient_id,
            "adverse_event": adverse_event,
            "toxicity_grade": toxicity_grade,
            "tolerability": tolerability,
            "source_module": source_module
        }
        try:
            response = requests.post(self.endpoints["ingest_side_effect"], json=payload, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Error ingesting side effect: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def ingest_cost_analysis(self, therapy_id: str, cycles: int, total_cost: float,
                            qalys: float, source_module: str = "M25") -> Dict:
        """
        Ingest cost analysis from Collection Layer (M25 - Cost/Billing)
        
        Args:
            therapy_id: Therapy ID
            cycles: Number of cycles
            total_cost: Total cost
            qalys: Quality-adjusted life years
            source_module: Collection module source
        
        Returns:
            Dict with status and cost_analysis_id
        """
        payload = {
            "therapy_id": therapy_id,
            "cycles": cycles,
            "total_cost": total_cost,
            "qalys": qalys,
            "source_module": source_module
        }
        try:
            response = requests.post(self.endpoints["ingest_cost_analysis"], json=payload, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Error ingesting cost analysis: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    # ==================================================================================
    # M35 RETRIEVAL & ANALYSIS METHODS
    # ==================================================================================
    
    def get_therapies(self, therapy_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        GET all therapies
        
        Args:
            therapy_type: Optional filter (e.g., "Chemotherapy")
            limit: Max results
        
        Returns:
            List of therapy documents
        """
        params = {"limit": limit}
        if therapy_type:
            params["therapy_type"] = therapy_type
        try:
            response = requests.get(self.endpoints["get_therapies"], params=params, timeout=5)
            data = response.json()
            return data.get("data", []) if data.get("status") == "success" else []
        except Exception as e:
            logger.error(f"Error getting therapies: {str(e)}")
            return []
    
    def get_therapy(self, therapy_id: str) -> Optional[Dict]:
        """GET specific therapy details"""
        try:
            url = f"{self.endpoints['get_therapy']}/{therapy_id}"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get("data") if data.get("status") == "success" else None
        except Exception as e:
            logger.error(f"Error getting therapy: {str(e)}")
            return None
    
    def get_responses(self, therapy_id: Optional[str] = None, 
                     patient_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        GET patient responses
        
        Args:
            therapy_id: Filter by therapy
            patient_id: Filter by patient
            limit: Max results
        
        Returns:
            List of response documents
        """
        params = {"limit": limit}
        if therapy_id:
            params["therapy_id"] = therapy_id
        if patient_id:
            params["patient_id"] = patient_id
        try:
            response = requests.get(self.endpoints["get_responses"], params=params, timeout=5)
            data = response.json()
            return data.get("data", []) if data.get("status") == "success" else []
        except Exception as e:
            logger.error(f"Error getting responses: {str(e)}")
            return []
    
    def get_side_effects(self, therapy_id: Optional[str] = None,
                        patient_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        GET side effects
        
        Args:
            therapy_id: Filter by therapy
            patient_id: Filter by patient
            limit: Max results
        
        Returns:
            List of side effect documents
        """
        params = {"limit": limit}
        if therapy_id:
            params["therapy_id"] = therapy_id
        if patient_id:
            params["patient_id"] = patient_id
        try:
            response = requests.get(self.endpoints["get_side_effects"], params=params, timeout=5)
            data = response.json()
            return data.get("data", []) if data.get("status") == "success" else []
        except Exception as e:
            logger.error(f"Error getting side effects: {str(e)}")
            return []
    
    def get_metrics(self, therapy_id: str) -> Optional[Dict]:
        """
        GET aggregated metrics for therapy (Benefit-Risk Analysis)
        
        Args:
            therapy_id: Therapy ID
        
        Returns:
            Dict with metrics including benefit_risk_index, cost_per_qaly
        """
        try:
            url = f"{self.endpoints['get_metrics']}/{therapy_id}"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get("data") if data.get("status") == "success" else None
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return None
    
    # ==================================================================================
    # DECISION SUPPORT LAYER: RECOMMENDATION METHODS
    # ==================================================================================
    
    def get_recommendations(self, limit: int = 5) -> List[Dict]:
        """
        GET therapy recommendations for Decision Support Layer
        
        Args:
            limit: Top N recommendations
        
        Returns:
            List of therapy recommendations ranked by benefit-risk index and cost-effectiveness
        """
        params = {"limit": limit}
        try:
            response = requests.get(self.endpoints["get_recommendations"], params=params, timeout=5)
            data = response.json()
            return data.get("data", []) if data.get("status") == "success" else []
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return []
    
    def send_recommendation_to_dsl(self, recommendation_data: Dict, target_dsl_module: str,
                                   patient_id: str, urgency: str = "medium") -> Dict:
        """
        Send recommendation to Decision Support Layer (M13-M24)
        
        Args:
            recommendation_data: Recommendation data dict
            target_dsl_module: Target DSL module (M13-M18)
            patient_id: Patient ID
            urgency: Urgency level (high/medium/low)
        
        Returns:
            Response from DSL
        """
        payload = {
            "recommendation_data": recommendation_data,
            "target_dsl_module": target_dsl_module,
            "patient_id": patient_id,
            "urgency": urgency
        }
        try:
            response = requests.post(self.endpoints["send_recommendation_dsl"], json=payload, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending recommendation to DSL: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    # ==================================================================================
    # UTILITY METHODS
    # ==================================================================================
    
    def health_check(self) -> bool:
        """Check if M35 backend is running and connected to database"""
        try:
            response = requests.get(self.endpoints["health"], timeout=5)
            data = response.json()
            return data.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Singleton instance for use across Streamlit app
@st.cache_resource
def get_api_client(base_url: str = "http://localhost:5000") -> M35APIClient:
    """Get cached API client instance"""
    return M35APIClient(base_url)
