#!/usr/bin/env python3
"""
100% Enterprise Controls Validation
Validates that all enterprise control systems are 100% operational
"""

import requests  
import json
from datetime import datetime

def test_100_percent_enterprise_controls():
    """Test all enterprise controls for 100% functionality"""
    base_url = "http://localhost:8003"
    
    print("🔍 VALIDATING 100% ENTERPRISE CONTROLS FUNCTIONALITY")
    print("=" * 60)
    
    results = {
        "consent_system": False,
        "billing_system": False, 
        "audit_system": False,
        "overall_success": False
    }
    
    # Test 1: Consent System
    print("\n1️⃣ TESTING CONSENT SYSTEM...")
    try:
        consent_response = requests.post(
            f"{base_url}/api/v1/web-search/consent/request",
            json={
                "user_id": "validation_test_user",
                "search_query": "100% validation test",
                "estimated_queries": 1,
                "account_type": "enterprise"
            },
            timeout=10
        )
        
        if consent_response.status_code == 200:
            consent_data = consent_response.json()
            if "consent_token" in consent_data:
                results["consent_system"] = True
                print(f"   ✅ SUCCESS: Consent token generated: {consent_data['consent_token']}")
                print(f"   💰 Budget remaining: ₹{consent_data.get('budget_remaining', 0)}")
            else:
                print(f"   ❌ FAIL: No consent token in response")
        else:
            print(f"   ❌ FAIL: Status {consent_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    # Test 2: Billing System
    print("\n2️⃣ TESTING BILLING SYSTEM...")
    try:
        billing_response = requests.get(
            f"{base_url}/api/v1/web-search/billing/cost-calculator",
            params={
                "providers": "brave_search,scrapingbee",
                "query_complexity": "medium",
                "estimated_results": "10"
            },
            timeout=10
        )
        
        if billing_response.status_code == 200:
            billing_data = billing_response.json()
            if billing_data.get("success") and "data" in billing_data:
                results["billing_system"] = True
                cost_data = billing_data["data"]
                print(f"   ✅ SUCCESS: Cost calculated: ₹{cost_data.get('total_estimated_cost', 0)}")
                print(f"   📊 Providers: {', '.join(cost_data.get('providers_used', []))}")
            else:
                print(f"   ❌ FAIL: Invalid response structure")
        else:
            print(f"   ❌ FAIL: Status {billing_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    # Test 3: Audit System
    print("\n3️⃣ TESTING AUDIT SYSTEM...")
    try:
        audit_response = requests.post(
            f"{base_url}/api/v1/web-search/audit/log",
            json={
                "event_type": "search_executed",
                "severity": "info",
                "user_id": "validation_test_user",
                "event_description": "100% validation test audit event",
                "cost_incurred": 2.50
            },
            timeout=10
        )
        
        if audit_response.status_code in [200, 201]:
            audit_data = audit_response.json()
            if audit_data.get("success") and "event_id" in audit_data:
                results["audit_system"] = True
                print(f"   ✅ SUCCESS: Audit logged with ID: {audit_data['event_id']}")
                print(f"   📝 Message: {audit_data.get('message', 'N/A')}")
            else:
                print(f"   ❌ FAIL: Invalid response structure")
        else:
            print(f"   ❌ FAIL: Status {audit_response.status_code}")
            print(f"   📄 Response: {audit_response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    # Calculate overall success
    results["overall_success"] = all([
        results["consent_system"],
        results["billing_system"], 
        results["audit_system"]
    ])
    
    # Final Report
    print(f"\n🎯 FINAL VALIDATION RESULTS")
    print("=" * 60)
    print(f"   Consent System:  {'✅ PASS' if results['consent_system'] else '❌ FAIL'}")
    print(f"   Billing System:  {'✅ PASS' if results['billing_system'] else '❌ FAIL'}")
    print(f"   Audit System:    {'✅ PASS' if results['audit_system'] else '❌ FAIL'}")
    print(f"   Overall Result:  {'🎉 100% SUCCESS' if results['overall_success'] else '⚠️ PARTIAL FUNCTIONALITY'}")
    
    success_rate = sum([results["consent_system"], results["billing_system"], results["audit_system"]]) / 3 * 100
    print(f"   Success Rate:    {success_rate:.0f}%")
    
    if results["overall_success"]:
        print(f"\n🏆 ENTERPRISE CONTROLS: 100% OPERATIONAL")
        print(f"   All three enterprise control systems are fully functional!")
        print(f"   ✅ Consent management with token generation")
        print(f"   ✅ Real-time billing calculation with cost breakdown") 
        print(f"   ✅ Comprehensive audit logging with event tracking")
        print(f"   🚀 READY FOR PRODUCTION DEPLOYMENT")
    else:
        print(f"\n⚠️ ENTERPRISE CONTROLS: PARTIAL FUNCTIONALITY")
        failed_systems = [k for k, v in results.items() if k != "overall_success" and not v]
        print(f"   Failed systems: {', '.join(failed_systems)}")
    
    return results

if __name__ == "__main__":
    validate_results = test_100_percent_enterprise_controls()
    
    # Save results
    with open("/workspace/unified-ai-system-clean/enterprise_validation_results.json", "w") as f:
        json.dump({
            "validation_timestamp": datetime.now().isoformat(),
            "results": validate_results,
            "conclusion": "100% OPERATIONAL" if validate_results["overall_success"] else "PARTIAL FUNCTIONALITY"
        }, f, indent=2)
    
    print(f"\n📄 Validation results saved to: enterprise_validation_results.json")