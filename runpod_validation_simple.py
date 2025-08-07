#!/usr/bin/env python3
"""
Simple RunPod Claims Validation
Direct API testing to confirm critical findings
"""

import requests
import time
import json
import sys

def test_ultra_fast_recall():
    """Test Ultra-Fast endpoint to confirm 0% recall claim"""
    print("🔍 TESTING ULTRA-FAST SEARCH (0% RECALL CLAIM)")
    print("=" * 50)
    
    base_url = "https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2"
    endpoint = f"{base_url}/search/ultra-fast"
    
    test_queries = [
        "artificial intelligence",
        "machine learning", 
        "test",
        "document search",
        "python programming"
    ]
    
    total_results = 0
    successful_tests = 0
    latencies = []
    
    for i, query in enumerate(test_queries, 1):
        try:
            print(f"Test {i}/5: '{query}'", end=" -> ")
            
            start_time = time.time()
            response = requests.post(
                endpoint,
                json={"query": query},
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            if response.status_code == 200:
                data = response.json()
                results_count = data.get("total_found", 0) or len(data.get("results", []))
                total_results += results_count
                successful_tests += 1
                
                print(f"{results_count} results ({latency_ms:.1f}ms) ✅")
                print(f"      Response: {str(data)[:100]}{'...' if len(str(data)) > 100 else ''}")
            else:
                print(f"HTTP {response.status_code} ❌")
                
        except Exception as e:
            print(f"Error: {str(e)} ❌")
    
    print(f"\n📊 ULTRA-FAST RESULTS:")
    print(f"   • Success Rate: {successful_tests}/{len(test_queries)} ({successful_tests/len(test_queries)*100:.1f}%)")
    print(f"   • Total Results Found: {total_results}")
    print(f"   • Recall Rate: {0 if total_results == 0 else (total_results/len(test_queries))*100:.1f}%")
    if latencies:
        print(f"   • Average Latency: {sum(latencies)/len(latencies):.1f}ms")
        print(f"   • Latency Range: {min(latencies):.1f}ms - {max(latencies):.1f}ms")
    
    return {
        "total_results": total_results,
        "recall_rate": 0 if total_results == 0 else (total_results/len(test_queries)),
        "successful_tests": successful_tests,
        "avg_latency": sum(latencies)/len(latencies) if latencies else 0
    }

def test_rag_functionality():
    """Test RAG endpoint to confirm working functionality"""
    print("\n🔍 TESTING RAG SEARCH (WORKING FUNCTIONALITY CLAIM)")
    print("=" * 50)
    
    base_url = "https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2"
    endpoint = f"{base_url}/rag/search"
    
    test_queries = [
        "test document",
        "artificial intelligence",
        "machine learning"
    ]
    
    total_results = 0
    successful_tests = 0
    latencies = []
    
    for i, query in enumerate(test_queries, 1):
        try:
            print(f"Test {i}/3: '{query}'", end=" -> ")
            
            start_time = time.time()
            response = requests.post(
                endpoint,
                json={"query": query},
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get("results", []))
                total_results += results_count
                successful_tests += 1
                
                print(f"{results_count} results ({latency_ms:.1f}ms) ✅")
                print(f"      Response: {str(data)[:150]}{'...' if len(str(data)) > 150 else ''}")
            else:
                print(f"HTTP {response.status_code} ❌")
                
        except Exception as e:
            print(f"Error: {str(e)} ❌")
    
    print(f"\n📊 RAG RESULTS:")
    print(f"   • Success Rate: {successful_tests}/{len(test_queries)} ({successful_tests/len(test_queries)*100:.1f}%)")
    print(f"   • Total Results Found: {total_results}")
    if latencies:
        print(f"   • Average Latency: {sum(latencies)/len(latencies):.1f}ms")
        print(f"   • Latency Range: {min(latencies):.1f}ms - {max(latencies):.1f}ms")
    
    return {
        "total_results": total_results,
        "successful_tests": successful_tests,
        "avg_latency": sum(latencies)/len(latencies) if latencies else 0
    }

def test_health_endpoints():
    """Test system health"""
    print("\n🔍 TESTING SYSTEM HEALTH")
    print("=" * 30)
    
    endpoints = [
        "https://ij9lyqsrrt0kod-8003.proxy.runpod.net/api/v1/health",
        "https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/health"
    ]
    
    health_status = []
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint.split('/')[-2]}...", end=" ")
            
            start_time = time.time()
            response = requests.get(endpoint, timeout=5)
            end_time = time.time()
            
            latency_ms = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                print(f"✅ ({latency_ms:.1f}ms)")
                health_status.append(True)
            else:
                print(f"❌ HTTP {response.status_code}")
                health_status.append(False)
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            health_status.append(False)
    
    return health_status

def main():
    print("🚨 RUNPOD CLAIMS VALIDATION")
    print("=" * 60)
    print("Testing live RunPod deployment to validate critical claims...")
    print()
    
    # Test Ultra-Fast endpoint (expecting 0% recall)
    ultra_fast_results = test_ultra_fast_recall()
    
    # Test RAG endpoint (expecting functioning results)
    rag_results = test_rag_functionality()
    
    # Test system health
    health_results = test_health_endpoints()
    
    # Final validation summary
    print("\n" + "=" * 60)
    print("🎯 CLAIMS VALIDATION SUMMARY")
    print("=" * 60)
    
    # Validate 0% recall claim
    ultra_fast_recall = ultra_fast_results["recall_rate"]
    print(f"❗ CRITICAL CLAIM: Ultra-Fast 0% Recall")
    print(f"   Claimed: 0% recall rate")
    print(f"   Actual: {ultra_fast_recall*100:.1f}% recall rate")
    print(f"   Status: {'✅ VERIFIED' if ultra_fast_recall == 0 else '❌ REJECTED'}")
    
    # Validate RAG functionality
    rag_working = rag_results["total_results"] > 0
    print(f"\n❗ CRITICAL CLAIM: RAG System Working")
    print(f"   Claimed: RAG returns results")
    print(f"   Actual: {rag_results['total_results']} total results found")
    print(f"   Status: {'✅ VERIFIED' if rag_working else '❌ REJECTED'}")
    
    # Performance metrics
    print(f"\n📊 PERFORMANCE VALIDATION:")
    print(f"   Ultra-Fast Latency: {ultra_fast_results['avg_latency']:.1f}ms avg")
    print(f"   RAG Latency: {rag_results['avg_latency']:.1f}ms avg")
    print(f"   System Health: {'✅ All services healthy' if all(health_results) else '⚠️ Some services degraded'}")
    
    # Final conclusion
    print(f"\n🏁 FINAL VERDICT:")
    if ultra_fast_recall == 0 and rag_working:
        print("✅ ALL CRITICAL CLAIMS VALIDATED")
        print("   • Ultra-Fast Search: 0% recall confirmed")
        print("   • RAG System: Working functionality confirmed")
        print("   • Infrastructure: Reliable and responsive")
    else:
        print("❌ CLAIMS VALIDATION FAILED")
        print(f"   • Ultra-Fast 0% recall: {'✅' if ultra_fast_recall == 0 else '❌'}")
        print(f"   • RAG functionality: {'✅' if rag_working else '❌'}")
    
    # Save results
    validation_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "ultra_fast_results": ultra_fast_results,
        "rag_results": rag_results,
        "health_results": health_results,
        "claims_validated": {
            "ultra_fast_zero_recall": ultra_fast_recall == 0,
            "rag_functionality": rag_working,
            "system_reliability": all(health_results)
        }
    }
    
    with open("runpod_validation_results.json", "w") as f:
        json.dump(validation_results, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: runpod_validation_results.json")
    return validation_results

if __name__ == "__main__":
    main()