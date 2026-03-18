"""
Module M35: Therapy Effectiveness Dashboard - Backend API
Data Flow: Collection Layer (M1-M6, M25-M30) → M35 (Processing) → Decision Support Layer (M13-M24)
"""

from flask import Flask, request, jsonify
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)

DATA_STORE = {
    "therapies": [],
    "responses": [],
    "side_effects": [],
    "cost_analysis": [],
}


def _new_id(prefix):
    return f"{prefix}_{uuid4().hex[:8]}"


def _find_by_id(items, item_id):
    for item in items:
        if item.get("_id") == item_id:
            return item
    return None

# ==================================================================================
# DATA COLLECTION LAYER → M35 (Data Ingestion)
# Modules M1-M6 (Patient Clinical Data), M25-M30, M43-M48 provide source data
# ==================================================================================

@app.route('/api/m35/ingest/therapy', methods=['POST'])
def ingest_therapy():
    """
    Ingest therapy data from Data Collection Layer
    Source: M1 (Patient Demographics), M25+ (Lab/Clinical Data)
    
    Expected JSON:
    {
        "name": "Chemo Regimen A",
        "therapy_type": "Chemotherapy",
        "start_date": "2026-01-10",
        "end_date": "2026-03-10",
        "cost_per_cycle": 12000,
        "source_module": "M1"  # Which collection module provided this
    }
    """
    try:
        data = request.json
        therapy_doc = {
            "_id": _new_id("T"),
            "name": data.get("name"),
            "therapy_type": data.get("therapy_type"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "cost_per_cycle": data.get("cost_per_cycle"),
            "source_module": data.get("source_module", "M1"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        DATA_STORE["therapies"].append(therapy_doc)
        return jsonify({
            "status": "success",
            "therapy_id": therapy_doc["_id"],
            "message": "Therapy ingested successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/ingest/response', methods=['POST'])
def ingest_response():
    """
    Ingest patient therapy response data from Collection Layer
    Source: M2 (Chronic Disease Records), M25-M30 (Lab Results)
    
    Expected JSON:
    {
        "therapy_id": "ObjectId",
        "patient_id": "P120",
        "clinical_improvement": 65,
        "symptom_relief": 58,
        "survival_days": 240,
        "response_grade": "PR",
        "source_module": "M2"
    }
    """
    try:
        data = request.json
        response_doc = {
            "_id": _new_id("R"),
            "therapy_id": data.get("therapy_id"),
            "patient_id": data.get("patient_id"),
            "clinical_improvement": data.get("clinical_improvement"),
            "symptom_relief": data.get("symptom_relief"),
            "survival_days": data.get("survival_days"),
            "response_grade": data.get("response_grade"),
            "source_module": data.get("source_module", "M2"),
            "recorded_at": datetime.utcnow()
        }

        DATA_STORE["responses"].append(response_doc)
        return jsonify({
            "status": "success",
            "response_id": response_doc["_id"],
            "message": "Response recorded successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/ingest/side-effect', methods=['POST'])
def ingest_side_effect():
    """
    Ingest adverse events data from Collection Layer
    Source: M5 (Patient Allergy & Immunization), M25-M30
    
    Expected JSON:
    {
        "therapy_id": "ObjectId",
        "patient_id": "P120",
        "adverse_event": "Nausea",
        "toxicity_grade": 2,
        "tolerability": "Moderate",
        "source_module": "M5"
    }
    """
    try:
        data = request.json
        side_effect_doc = {
            "_id": _new_id("S"),
            "therapy_id": data.get("therapy_id"),
            "patient_id": data.get("patient_id"),
            "adverse_event": data.get("adverse_event"),
            "toxicity_grade": data.get("toxicity_grade"),
            "tolerability": data.get("tolerability"),
            "source_module": data.get("source_module", "M5"),
            "noted_at": datetime.utcnow()
        }

        DATA_STORE["side_effects"].append(side_effect_doc)
        return jsonify({
            "status": "success",
            "side_effect_id": side_effect_doc["_id"],
            "message": "Side effect recorded successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/ingest/cost-analysis', methods=['POST'])
def ingest_cost_analysis():
    """
    Ingest cost analysis data from Collection Layer
    Source: M25-M30 (Cost/Billing Data)
    
    Expected JSON:
    {
        "therapy_id": "ObjectId",
        "cycles": 4,
        "total_cost": 48000,
        "qalys": 0.65,
        "source_module": "M25"
    }
    """
    try:
        data = request.json
        cost_doc = {
            "_id": _new_id("C"),
            "therapy_id": data.get("therapy_id"),
            "cycles": data.get("cycles"),
            "total_cost": data.get("total_cost"),
            "qalys": data.get("qalys"),
            "source_module": data.get("source_module", "M25"),
            "analyzed_at": datetime.utcnow()
        }

        DATA_STORE["cost_analysis"].append(cost_doc)
        return jsonify({
            "status": "success",
            "cost_analysis_id": cost_doc["_id"],
            "message": "Cost analysis recorded successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# M35 PROCESSING LAYER - Analysis & Aggregation
# ==================================================================================

@app.route('/api/m35/therapy', methods=['GET'])
def get_therapies():
    """
    GET all therapies
    Query params: ?therapy_type=Chemotherapy&limit=10
    """
    try:
        therapy_type = request.args.get('therapy_type')
        limit = int(request.args.get('limit', 100))
        therapies = DATA_STORE["therapies"]
        if therapy_type:
            therapies = [t for t in therapies if t.get("therapy_type") == therapy_type]
        therapies = therapies[:limit]
        
        return jsonify({
            "status": "success",
            "count": len(therapies),
            "data": therapies
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/therapy/<therapy_id>', methods=['GET'])
def get_therapy(therapy_id):
    """GET specific therapy details"""
    try:
        therapy = _find_by_id(DATA_STORE["therapies"], therapy_id)
        
        if not therapy:
            return jsonify({"status": "error", "message": "Therapy not found"}), 404
        
        return jsonify({"status": "success", "data": therapy}), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/response', methods=['GET'])
def get_responses():
    """
    GET responses by therapy
    Query params: ?therapy_id=<id>&patient_id=P120&limit=10
    """
    try:
        therapy_id = request.args.get('therapy_id')
        patient_id = request.args.get('patient_id')
        limit = int(request.args.get('limit', 100))
        responses = DATA_STORE["responses"]
        if therapy_id:
            responses = [r for r in responses if r.get("therapy_id") == therapy_id]
        if patient_id:
            responses = [r for r in responses if r.get("patient_id") == patient_id]
        responses = responses[:limit]
        
        return jsonify({
            "status": "success",
            "count": len(responses),
            "data": responses
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/side-effect', methods=['GET'])
def get_side_effects():
    """
    GET side effects by therapy or patient
    Query params: ?therapy_id=<id>&patient_id=P120&limit=10
    """
    try:
        therapy_id = request.args.get('therapy_id')
        patient_id = request.args.get('patient_id')
        limit = int(request.args.get('limit', 100))
        side_effects = DATA_STORE["side_effects"]
        if therapy_id:
            side_effects = [s for s in side_effects if s.get("therapy_id") == therapy_id]
        if patient_id:
            side_effects = [s for s in side_effects if s.get("patient_id") == patient_id]
        side_effects = side_effects[:limit]
        
        return jsonify({
            "status": "success",
            "count": len(side_effects),
            "data": side_effects
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/metrics/<therapy_id>', methods=['GET'])
def get_therapy_metrics(therapy_id):
    """
    GET aggregated metrics for a therapy (Benefit-Risk Analysis)
    Returns: avg_improvement, avg_symptom_relief, avg_toxicity, benefit_risk_index, cost_per_qaly
    """
    try:
        # Fetch responses
        responses = [r for r in DATA_STORE["responses"] if r.get("therapy_id") == therapy_id]
        side_effects = [s for s in DATA_STORE["side_effects"] if s.get("therapy_id") == therapy_id]
        cost = next((c for c in DATA_STORE["cost_analysis"] if c.get("therapy_id") == therapy_id), None)
        
        if not responses:
            return jsonify({"status": "error", "message": "No data for this therapy"}), 404
        
        # Calculate averages
        def mean(values):
            return sum(values) / len(values) if values else 0
        
        avg_improvement = mean([r.get("clinical_improvement", 0) for r in responses])
        avg_symptom_relief = mean([r.get("symptom_relief", 0) for r in responses])
        avg_survival_days = mean([r.get("survival_days", 0) for r in responses])
        avg_toxicity = mean([s.get("toxicity_grade", 0) for s in side_effects])
        
        benefit_score = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
        benefit_risk_index = benefit_score / (1 + avg_toxicity)
        
        cost_per_qaly = None
        if cost and cost.get("qalys"):
            cost_per_qaly = cost["total_cost"] / cost["qalys"]
        
        metrics = {
            "therapy_id": therapy_id,
            "avg_improvement": round(avg_improvement, 2),
            "avg_symptom_relief": round(avg_symptom_relief, 2),
            "avg_survival_days": round(avg_survival_days, 2),
            "avg_toxicity_grade": round(avg_toxicity, 2),
            "adverse_events_count": len(side_effects),
            "benefit_risk_index": round(benefit_risk_index, 2),
            "cost_per_qaly": round(cost_per_qaly, 2) if cost_per_qaly else None,
            "response_count": len(responses)
        }
        
        return jsonify({
            "status": "success",
            "data": metrics
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# M35 → DECISION SUPPORT LAYER (M13-M24)
# Send processed recommendations to Decision Support Layer for clinical decision making
# ==================================================================================

@app.route('/api/m35/recommendation', methods=['GET'])
def get_recommendations():
    """
    GET therapy recommendations based on benefit-risk analysis
    Sends to Decision Support Layer (M13-M18)
    Query params: ?limit=5
    
    Returns: Top therapies ranked by benefit-risk index and cost-effectiveness
    """
    try:
        limit = int(request.args.get('limit', 5))
        therapies = DATA_STORE["therapies"]
        recommendations = []
        
        for therapy in therapies:
            therapy_id = therapy.get("_id")
            responses = [r for r in DATA_STORE["responses"] if r.get("therapy_id") == therapy_id]
            side_effects = [s for s in DATA_STORE["side_effects"] if s.get("therapy_id") == therapy_id]
            cost = next((c for c in DATA_STORE["cost_analysis"] if c.get("therapy_id") == therapy_id), None)
            
            if not responses:
                continue
            
            def mean(values):
                return sum(values) / len(values) if values else 0
            
            avg_improvement = mean([r.get("clinical_improvement", 0) for r in responses])
            avg_symptom_relief = mean([r.get("symptom_relief", 0) for r in responses])
            avg_survival_days = mean([r.get("survival_days", 0) for r in responses])
            avg_toxicity = mean([s.get("toxicity_grade", 0) for s in side_effects])
            
            benefit_score = (avg_improvement + avg_symptom_relief + (avg_survival_days / 365) * 100) / 3
            benefit_risk_index = benefit_score / (1 + avg_toxicity)
            
            cost_per_qaly = None
            if cost and cost.get("qalys"):
                cost_per_qaly = cost["total_cost"] / cost["qalys"]
            
            recommendations.append({
                "therapy_id": therapy_id,
                "name": therapy.get("name"),
                "therapy_type": therapy.get("therapy_type"),
                "benefit_risk_index": round(benefit_risk_index, 2),
                "cost_per_qaly": round(cost_per_qaly, 2) if cost_per_qaly else None,
                "response_count": len(responses),
                "adverse_events": len(side_effects),
                "rank_score": round(benefit_risk_index - (cost_per_qaly / 100000 if cost_per_qaly else 0), 2)
            })
        
        # Sort by rank_score descending
        recommendations.sort(key=lambda x: x['rank_score'], reverse=True)
        recommendations = recommendations[:limit]
        
        return jsonify({
            "status": "success",
            "count": len(recommendations),
            "destination": "Decision Support Layer (M13-M18)",
            "data": recommendations
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/m35/recommendation/send-to-dsl', methods=['POST'])
def send_recommendation_to_dsl():
    """
    Send M35 recommendation to Decision Support Layer endpoints (M13-M18)
    This integrates M35 with the DSL for clinical decision making
    
    Expected JSON:
    {
        "recommendation_data": {...},
        "target_dsl_module": "M13",  # M13-M18 are DSL modules
        "patient_id": "P120",
        "urgency": "high|medium|low"
    }
    """
    try:
        data = request.json
        
        # TODO: Implement actual DSL endpoint call
        # This would call the Decision Support Layer endpoints with the recommendation
        
        dsl_payload = {
            "source_module": "M35",
            "recommendation": data.get("recommendation_data"),
            "target_module": data.get("target_dsl_module", "M13"),
            "patient_id": data.get("patient_id"),
            "urgency": data.get("urgency", "medium"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "status": "success",
            "message": "Recommendation sent to Decision Support Layer",
            "payload": dsl_payload
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================================================================================
# HEALTH CHECK
# ==================================================================================

@app.route('/api/m35/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify M35 backend is running"""
    try:
        return jsonify({
            "status": "healthy",
            "module": "M35 - Therapy Effectiveness Dashboard",
            "storage": "in-memory"
        }), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
