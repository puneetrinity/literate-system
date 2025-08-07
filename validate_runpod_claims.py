#!/usr/bin/env python3
"""
RunPod Claims Validation Script
Tests all critical claims from the strategic analysis document
"""

import requests
import time
import json
from typing import Dict, List, Any

class RunPodValidator:
    def __init__(self, use_local=False):
        if use_local:
            self.chat_base = "http://localhost:8003/api/v1"
            self.doc_base = "http://localhost:8001/api/v2"
        else:
            self.chat_base = "https://ij9lyqsrrt0kod-8003.proxy.runpod.net/api/v1"
            self.doc_base = "https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2"
        self.results = {}
        
    def test_ultra_fast_endpoint(self) -> Dict[str, Any]:
        """Test Ultra-Fast Search endpoint - expecting 0% recall"""
        print("🔍 Testing Ultra-Fast Search Endpoint...")
        
        test_queries = [
            "artificial intelligence",
            "machine learning",
            "test",
            "document search",
            "python programming"
        ]
        
        results = {
            "endpoint": f"{self.doc_base}/search/ultra-fast",
            "total_queries": len(test_queries),
            "successful_queries": 0,
            "total_results_found": 0,
            "average_latency_ms": 0,
            "query_results": []
        }
        
        latencies = []
        
        for query in test_queries:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.doc_base}/search/ultra-fast",
                    json={"query": query},
                    timeout=10
                )
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                if response.status_code == 200:
                    data = response.json()
                    results["successful_queries"] += 1
                    results_count = data.get("total_found", 0) or len(data.get("results", []))
                    results["total_results_found"] += results_count
                    
                    results["query_results"].append({
                        "query": query,
                        "status_code": response.status_code,
                        "latency_ms": round(latency_ms, 2),
                        "results_found": results_count,
                        "success": data.get("success", False),
                        "response_preview": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                    })
                    
                    print(f"  ✅ Query: '{query}' -> {results_count} results in {latency_ms:.1f}ms")
                else:
                    print(f"  ❌ Query: '{query}' -> HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Query: '{query}' -> Error: {str(e)}")
                
        if latencies:
            results["average_latency_ms"] = round(sum(latencies) / len(latencies), 2)
            results["min_latency_ms"] = round(min(latencies), 2)
            results["max_latency_ms"] = round(max(latencies), 2)
            
        # Calculate recall rate
        results["recall_rate"] = 0.0 if results["total_results_found"] == 0 else (results["total_results_found"] / results["total_queries"])
        results["recall_percentage"] = round(results["recall_rate"] * 100, 1)
        
        return results
    
    def test_rag_endpoint(self) -> Dict[str, Any]:
        """Test RAG endpoint - expecting working functionality"""
        print("🔍 Testing RAG Search Endpoint...")
        
        test_queries = [
            "test document",
            "artificial intelligence",
            "machine learning algorithms"
        ]
        
        results = {
            "endpoint": f"{self.doc_base}/rag/search",
            "total_queries": len(test_queries),
            "successful_queries": 0,
            "total_results_found": 0,
            "average_latency_ms": 0,
            "query_results": []
        }
        
        latencies = []
        
        for query in test_queries:
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.doc_base}/rag/search",
                    json={"query": query},
                    timeout=15
                )
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                if response.status_code == 200:
                    data = response.json()
                    results["successful_queries"] += 1
                    results_count = len(data.get("results", []))
                    results["total_results_found"] += results_count
                    
                    results["query_results"].append({
                        "query": query,
                        "status_code": response.status_code,
                        "latency_ms": round(latency_ms, 2),
                        "results_found": results_count,
                        "response_preview": str(data)[:300] + "..." if len(str(data)) > 300 else str(data)
                    })
                    
                    print(f"  ✅ Query: '{query}' -> {results_count} results in {latency_ms:.1f}ms")
                else:
                    print(f"  ❌ Query: '{query}' -> HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Query: '{query}' -> Error: {str(e)}")
                
        if latencies:
            results["average_latency_ms"] = round(sum(latencies) / len(latencies), 2)
            results["min_latency_ms"] = round(min(latencies), 2)
            results["max_latency_ms"] = round(max(latencies), 2)
            
        return results
    
    def test_health_endpoints(self) -> Dict[str, Any]:
        """Test system health endpoints"""
        print("🔍 Testing Health Endpoints...")
        
        endpoints = [
            f"{self.chat_base}/health",
            f"{self.doc_base}/health"
        ]
        
        results = {
            "health_checks": []
        }
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=5)
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                health_result = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                    "healthy": response.status_code == 200
                }
                
                if response.status_code == 200:
                    print(f"  ✅ {endpoint} -> Healthy ({latency_ms:.1f}ms)")
                else:
                    print(f"  ❌ {endpoint} -> HTTP {response.status_code}")
                    
                results["health_checks"].append(health_result)
                
            except Exception as e:
                print(f"  ❌ {endpoint} -> Error: {str(e)}")
                results["health_checks"].append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "healthy": False
                })
                
        return results
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        print("🚨 RUNPOD CLAIMS VALIDATION STARTING...")
        print("=" * 60)
        
        # Test all endpoints
        ultra_fast_results = self.test_ultra_fast_endpoint()
        rag_results = self.test_rag_endpoint()
        health_results = self.test_health_endpoints()
        
        # Compile final report
        validation_report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "runpod_endpoints": {
                "chat_service": self.chat_base,
                "document_service": self.doc_base
            },
            "ultra_fast_search": ultra_fast_results,
            "rag_search": rag_results,
            "health_checks": health_results,
            "critical_findings": self.analyze_critical_findings(ultra_fast_results, rag_results)
        }
        
        return validation_report
    
    def analyze_critical_findings(self, ultra_fast: Dict, rag: Dict) -> Dict[str, Any]:
        """Analyze critical findings against claimed benchmarks"""
        findings = {}
        
        # Ultra-Fast Search Analysis
        findings["ultra_fast_recall_claim"] = {
            "claimed": "0% recall rate",
            "actual": f"{ultra_fast.get('recall_percentage', 'N/A')}% recall rate",
            "verified": ultra_fast.get('recall_percentage', 0) == 0.0,
            "total_results_across_queries": ultra_fast.get('total_results_found', 0)
        }
        
        # Performance Analysis
        findings["performance_analysis"] = {
            "ultra_fast_latency": {
                "claimed_range": "6-64ms (from benchmarks)",
                "actual_avg": f"{ultra_fast.get('average_latency_ms', 'N/A')}ms",
                "actual_range": f"{ultra_fast.get('min_latency_ms', 'N/A')}-{ultra_fast.get('max_latency_ms', 'N/A')}ms"
            },
            "rag_latency": {
                "claimed_range": "~28ms average (from benchmarks)",
                "actual_avg": f"{rag.get('average_latency_ms', 'N/A')}ms",
                "actual_range": f"{rag.get('min_latency_ms', 'N/A')}-{rag.get('max_latency_ms', 'N/A')}ms"
            }
        }
        
        # System Status
        findings["system_status"] = {
            "ultra_fast_success_rate": f"{(ultra_fast.get('successful_queries', 0) / ultra_fast.get('total_queries', 1)) * 100:.1f}%",
            "rag_success_rate": f"{(rag.get('successful_queries', 0) / rag.get('total_queries', 1)) * 100:.1f}%",
            "infrastructure_reliability": "100%" if all(h.get('healthy', False) for h in findings.get('health_checks', [])) else "Degraded"
        }
        
        return findings

def main():
    validator = RunPodValidator()
    report = validator.run_validation()
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    
    ultra_fast = report["ultra_fast_search"]
    rag = report["rag_search"]
    findings = report["critical_findings"]
    
    print(f"📊 Ultra-Fast Search Results:")
    print(f"   • Recall Rate: {ultra_fast.get('recall_percentage', 'N/A')}%")
    print(f"   • Average Latency: {ultra_fast.get('average_latency_ms', 'N/A')}ms")
    print(f"   • Success Rate: {findings['system_status']['ultra_fast_success_rate']}")
    print(f"   • Total Results Found: {ultra_fast.get('total_results_found', 0)}")
    
    print(f"\n📊 RAG Search Results:")
    print(f"   • Average Latency: {rag.get('average_latency_ms', 'N/A')}ms")
    print(f"   • Success Rate: {findings['system_status']['rag_success_rate']}")
    print(f"   • Total Results Found: {rag.get('total_results_found', 0)}")
    
    print(f"\n🔍 Critical Claims Validation:")
    ultra_claim = findings["ultra_fast_recall_claim"]
    print(f"   • 0% Recall Claim: {'✅ VERIFIED' if ultra_claim['verified'] else '❌ REJECTED'}")
    print(f"   • Claimed: {ultra_claim['claimed']}")
    print(f"   • Actual: {ultra_claim['actual']}")
    
    # Save detailed report
    with open("runpod_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📝 Detailed report saved to: runpod_validation_report.json")
    print("=" * 60)
    
    return report

if __name__ == "__main__":
    main()