#!/usr/bin/env python3
"""
Test Script for M35 API Endpoints
Tests data flow: Collection Layer → M35 → Decision Support Layer
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_health_check():
    """Test health check endpoint"""
    print_section("Testing Health Check")
    response = requests.get(f"{BASE_URL}/api/m35/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_ingest_therapy():
    """Test ingesting therapy from Collection Layer"""
    print_section("Testing Therapy Ingestion (from M1)")
    
    payload = {
        "name": "TEST - Chemo Regimen A",
        "therapy_type": "Chemotherapy",
        "start_date": "2026-01-10",
        "end_date": "2026-03-10",
        "cost_per_cycle": 12000,
        "source_module": "M1"
    }
    
    response = requests.post(f"{BASE_URL}/api/m35/ingest/therapy", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    
    return data.get("therapy_id") if response.status_code == 201 else None

def test_ingest_response(therapy_id):
    """Test ingesting response from Collection Layer"""
    print_section("Testing Response Ingestion (from M2)")
    
    payload = {
        "therapy_id": therapy_id,
        "patient_id": "P120",
        "clinical_improvement": 65,
        "symptom_relief": 58,
        "survival_days": 240,
        "response_grade": "PR",
        "source_module": "M2"
    }
    
    response = requests.post(f"{BASE_URL}/api/m35/ingest/response", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.status_code == 201

def test_ingest_side_effect(therapy_id):
    """Test ingesting side effect from Collection Layer"""
    print_section("Testing Side Effect Ingestion (from M5)")
    
    payload = {
        "therapy_id": therapy_id,
        "patient_id": "P120",
        "adverse_event": "Nausea",
        "toxicity_grade": 2,
        "tolerability": "Moderate",
        "source_module": "M5"
    }
    
    response = requests.post(f"{BASE_URL}/api/m35/ingest/side-effect", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.status_code == 201

def test_ingest_cost_analysis(therapy_id):
    """Test ingesting cost analysis from Collection Layer"""
    print_section("Testing Cost Analysis Ingestion (from M25)")
    
    payload = {
        "therapy_id": therapy_id,
        "cycles": 4,
        "total_cost": 48000,
        "qalys": 0.65,
        "source_module": "M25"
    }
    
    response = requests.post(f"{BASE_URL}/api/m35/ingest/cost-analysis", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.status_code == 201

def test_get_therapies():
    """Test getting therapies"""
    print_section("Testing GET Therapies (M35 Retrieval)")
    
    response = requests.get(f"{BASE_URL}/api/m35/therapy?limit=10")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data.get('count', 0)} therapies")
    if data.get("data"):
        print("\nFirst therapy:")
        print(json.dumps(data["data"][0], indent=2, default=str))

def test_get_metrics(therapy_id):
    """Test getting aggregated metrics"""
    print_section("Testing GET Metrics (Benefit-Risk Analysis)")
    
    response = requests.get(f"{BASE_URL}/api/m35/metrics/{therapy_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json().get("data", {}), indent=2))
    else:
        print(json.dumps(response.json(), indent=2))

def test_get_recommendations():
    """Test getting recommendations for Decision Support Layer"""
    print_section("Testing GET Recommendations (M35 → DSL)")
    
    response = requests.get(f"{BASE_URL}/api/m35/recommendation?limit=5")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Destination: {data.get('destination', 'N/A')}")
    print(f"Found {data.get('count', 0)} recommendations\n")
    
    if data.get("data"):
        for i, rec in enumerate(data["data"][:3], 1):
            print(f"Recommendation {i}:")
            print(f"  Therapy: {rec.get('name')}")
            print(f"  Type: {rec.get('therapy_type')}")
            print(f"  Benefit-Risk Index: {rec.get('benefit_risk_index')}")
            print(f"  Cost/QALY: ${rec.get('cost_per_qaly', 'N/A')}")
            print(f"  Rank Score: {rec.get('rank_score')}\n")

def test_send_to_dsl(therapy_id):
    """Test sending recommendation to Decision Support Layer"""
    print_section("Testing POST to Decision Support Layer (M13-M24)")
    
    payload = {
        "recommendation_data": {
            "therapy_id": therapy_id,
            "name": "TEST - Chemo Regimen A",
            "benefit_risk_index": 2.45,
            "cost_per_qaly": 18500.00
        },
        "target_dsl_module": "M13",
        "patient_id": "P120",
        "urgency": "high"
    }
    
    response = requests.post(f"{BASE_URL}/api/m35/recommendation/send-to-dsl", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.status_code == 200

def run_full_test():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("  M35 API Integration Test Suite")
    print("  Data Flow: Collection Layer → M35 → Decision Support Layer")
    print("="*70)
    
    # Health check
    if not test_health_check():
        print("\n❌ Backend is not responding. Ensure M35 backend is running on port 5000")
        print("   Start with: python src/modules/module_f35/backend/api_m35.py")
        return
    
    print("✅ Backend is healthy")
    
    # Test data ingestion from Collection Layer
    therapy_id = test_ingest_therapy()
    if not therapy_id:
        print("❌ Failed to create therapy")
        return
    
    print(f"✅ Therapy created: {therapy_id}")
    
    # Ingest related data
    if test_ingest_response(therapy_id):
        print("✅ Response ingested")
    
    if test_ingest_side_effect(therapy_id):
        print("✅ Side effect ingested")
    
    if test_ingest_cost_analysis(therapy_id):
        print("✅ Cost analysis ingested")
    
    # Test M35 retrieval
    test_get_therapies()
    
    # Test metrics (benefit-risk analysis)
    import time
    time.sleep(1)  # Give backend time to process
    test_get_metrics(therapy_id)
    
    # Test recommendations for DSL
    test_get_recommendations()
    
    # Test sending to DSL
    test_send_to_dsl(therapy_id)
    
    print("\n" + "="*70)
    print("  ✅ Test Suite Completed")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        run_full_test()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to M35 backend at http://localhost:5000")
        print("\nTo start the backend:")
        print("  1. Open PowerShell")
        print("  2. Navigate to: C:\\Users\\prath\\OneDrive\\Desktop\\DBMS_PROJECT\\Frontend\\src\\modules\\module_f35\\backend")
        print("  3. Run: python api_m35.py")
        print("\nThen run this test script again.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
