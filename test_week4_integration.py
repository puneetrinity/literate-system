#!/usr/bin/env python3
"""
Week 4: Integration Testing and Performance Benchmarking
Tests all three major system implementations:
- Week 1: 8→3 Router Consolidation 
- Week 2: Memory-Aware Contextual Bandits
- Week 3: Web Search Enterprise Controls
"""

import asyncio
import json
import time
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
import structlog

logger = structlog.get_logger()

class IntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: Dict[str, Any] = {
            "router_consolidation": {},
            "memory_system": {},
            "enterprise_controls": {},
            "performance_benchmarks": {}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_router_consolidation(self):
        """Test 8→3 Router Consolidation"""
        logger.info("Testing router consolidation (8→3 architecture)")
        
        test_cases = [
            {
                "name": "document_search_routing",
                "endpoint": "/api/v1/chat/complete",
                "payload": {
                    "message": "Find documents about machine learning algorithms",
                    "mode": "document_only"
                },
                "expected_router": "ContentTypeRouter"
            },
            {
                "name": "web_search_routing", 
                "endpoint": "/api/v1/chat/complete",
                "payload": {
                    "message": "What's happening in AI today?",
                    "mode": "web_search"
                },
                "expected_router": "WebSearchRouter"
            },
            {
                "name": "unified_intelligence_routing",
                "endpoint": "/api/v1/chat/complete", 
                "payload": {
                    "message": "Analyze recent AI developments and compare with historical trends",
                    "mode": "intelligent"
                },
                "expected_router": "UnifiedIntelligentRouter"
            }
        ]
        
        results = []
        for test_case in test_cases:
            start_time = time.time()
            try:
                async with self.session.post(
                    f"{self.base_url}{test_case['endpoint']}", 
                    json=test_case["payload"]
                ) as response:
                    response_data = await response.json()
                    duration = time.time() - start_time
                    
                    result = {
                        "test": test_case["name"],
                        "status": "success" if response.status == 200 else "failed",
                        "response_time": duration,
                        "router_used": response_data.get("router_info", {}).get("selected_router"),
                        "expected_router": test_case["expected_router"],
                        "router_match": response_data.get("router_info", {}).get("selected_router") == test_case["expected_router"]
                    }
                    results.append(result)
                    logger.info("Router test completed", **result)
                    
            except Exception as e:
                results.append({
                    "test": test_case["name"], 
                    "status": "error",
                    "error": str(e),
                    "response_time": time.time() - start_time
                })
        
        self.results["router_consolidation"] = {
            "tests": results,
            "success_rate": len([r for r in results if r.get("status") == "success"]) / len(results),
            "avg_response_time": statistics.mean([r["response_time"] for r in results])
        }

    async def test_memory_system(self):
        """Test Contextual Bandit Memory System"""
        logger.info("Testing contextual bandit memory system")
        
        # Test memory initialization
        try:
            async with self.session.get(f"{self.base_url}/api/v1/memory/status") as response:
                memory_status = await response.json()
                logger.info("Memory system status", status=memory_status)
        except Exception as e:
            logger.error("Memory status check failed", error=str(e))
        
        # Test memory-aware routing with multiple queries
        test_queries = [
            "What are the latest AI research papers?",
            "Explain quantum computing applications", 
            "Find documents about Python programming",
            "Current trends in machine learning",
            "Best practices for software architecture"
        ]
        
        routing_results = []
        for i, query in enumerate(test_queries):
            start_time = time.time()
            try:
                async with self.session.post(
                    f"{self.base_url}/api/v1/chat/complete",
                    json={
                        "message": query,
                        "mode": "intelligent",
                        "session_id": f"memory_test_session_{i}"
                    }
                ) as response:
                    response_data = await response.json()
                    duration = time.time() - start_time
                    
                    routing_results.append({
                        "query": query,
                        "response_time": duration,
                        "router_confidence": response_data.get("router_info", {}).get("confidence", 0),
                        "memory_context": response_data.get("memory_context", {}),
                        "bandit_arm_used": response_data.get("router_info", {}).get("bandit_arm")
                    })
                    
            except Exception as e:
                routing_results.append({
                    "query": query,
                    "error": str(e),
                    "response_time": time.time() - start_time
                })
        
        self.results["memory_system"] = {
            "routing_tests": routing_results,
            "avg_response_time": statistics.mean([r["response_time"] for r in routing_results if "error" not in r]),
            "memory_learning_observed": len([r for r in routing_results if r.get("memory_context")]) > 0
        }

    async def test_enterprise_controls(self):
        """Test Web Search Enterprise Controls End-to-End"""
        logger.info("Testing web search enterprise controls")
        
        # Test consent workflow
        consent_results = []
        
        # 1. Request consent
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/web-search/consent/request",
                json={
                    "user_id": "test_user_integration",
                    "query": "Latest technology news",
                    "estimated_queries": 3,
                    "account_type": "enterprise"
                }
            ) as response:
                consent_data = await response.json()
                consent_token = consent_data.get("consent_token")
                consent_results.append({"step": "consent_request", "success": True, "token": consent_token})
                
                # 2. Confirm consent  
                async with self.session.post(
                    f"{self.base_url}/api/v1/web-search/consent/confirm",
                    json={
                        "consent_token": consent_token,
                        "user_confirmation": True,
                        "cost_acknowledged": True
                    }
                ) as confirm_response:
                    confirm_data = await confirm_response.json()
                    consent_results.append({"step": "consent_confirm", "success": True, "data": confirm_data})
                    
        except Exception as e:
            consent_results.append({"step": "consent_workflow", "success": False, "error": str(e)})
        
        # Test billing system
        billing_results = []
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/web-search/billing/cost-calculator",
                params={
                    "provider": "comprehensive",
                    "query_complexity": "medium",
                    "estimated_results": 10
                }
            ) as response:
                billing_data = await response.json()
                billing_results.append({"test": "cost_calculation", "success": True, "data": billing_data})
                
        except Exception as e:
            billing_results.append({"test": "cost_calculation", "success": False, "error": str(e)})
        
        # Test audit logging
        audit_results = []
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/web-search/audit/log",
                json={
                    "event_type": "web_search_executed",
                    "severity": "info",
                    "user_id": "test_user_integration",
                    "query": "Integration test query",
                    "cost_incurred": 2.50,
                    "provider_used": "brave_search"
                }
            ) as response:
                audit_data = await response.json()
                audit_results.append({"test": "audit_logging", "success": response.status == 200, "data": audit_data})
                
        except Exception as e:
            audit_results.append({"test": "audit_logging", "success": False, "error": str(e)})
        
        self.results["enterprise_controls"] = {
            "consent_workflow": consent_results,
            "billing_system": billing_results, 
            "audit_logging": audit_results,
            "overall_success": all([
                any(r.get("success") for r in consent_results),
                any(r.get("success") for r in billing_results),
                any(r.get("success") for r in audit_results)
            ])
        }

    async def performance_benchmarking(self):
        """Comprehensive Performance Benchmarking"""
        logger.info("Starting performance benchmarking")
        
        # Benchmark different routing scenarios
        benchmark_scenarios = [
            {
                "name": "document_search_performance",
                "endpoint": "/api/v1/chat/complete",
                "payload": {"message": "Find research papers on neural networks", "mode": "document_only"},
                "iterations": 10
            },
            {
                "name": "web_search_performance", 
                "endpoint": "/api/v1/chat/complete",
                "payload": {"message": "Current AI news", "mode": "web_search"},
                "iterations": 5  # Fewer due to cost
            },
            {
                "name": "intelligent_routing_performance",
                "endpoint": "/api/v1/chat/complete", 
                "payload": {"message": "Analyze AI trends and provide recommendations", "mode": "intelligent"},
                "iterations": 8
            }
        ]
        
        benchmark_results = {}
        
        for scenario in benchmark_scenarios:
            logger.info(f"Benchmarking {scenario['name']}")
            response_times = []
            errors = 0
            
            for i in range(scenario["iterations"]):
                start_time = time.time()
                try:
                    async with self.session.post(
                        f"{self.base_url}{scenario['endpoint']}",
                        json=scenario["payload"]
                    ) as response:
                        await response.json()  # Consume response
                        response_times.append(time.time() - start_time)
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Benchmark error in {scenario['name']}", error=str(e))
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            if response_times:
                benchmark_results[scenario["name"]] = {
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": statistics.median(response_times),
                    "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                    "success_rate": (scenario["iterations"] - errors) / scenario["iterations"],
                    "total_requests": scenario["iterations"],
                    "errors": errors
                }
        
        self.results["performance_benchmarks"] = benchmark_results

    async def run_comprehensive_test(self):
        """Run all integration tests and benchmarks"""
        logger.info("Starting comprehensive integration testing")
        
        # Test router consolidation
        await self.test_router_consolidation()
        
        # Test memory system
        await self.test_memory_system()
        
        # Test enterprise controls
        await self.test_enterprise_controls()
        
        # Performance benchmarking
        await self.performance_benchmarking()
        
        # Generate summary report
        self.generate_summary_report()
        
        return self.results

    def generate_summary_report(self):
        """Generate comprehensive test summary"""
        summary = {
            "test_timestamp": datetime.now().isoformat(),
            "overall_status": "PASS",
            "component_status": {},
            "performance_summary": {},
            "recommendations": []
        }
        
        # Router consolidation status
        router_success_rate = self.results["router_consolidation"].get("success_rate", 0)
        summary["component_status"]["router_consolidation"] = {
            "status": "PASS" if router_success_rate >= 0.8 else "FAIL",
            "success_rate": router_success_rate,
            "avg_response_time": self.results["router_consolidation"].get("avg_response_time")
        }
        
        # Memory system status  
        memory_learning = self.results["memory_system"].get("memory_learning_observed", False)
        summary["component_status"]["memory_system"] = {
            "status": "PASS" if memory_learning else "PARTIAL",
            "learning_observed": memory_learning,
            "avg_response_time": self.results["memory_system"].get("avg_response_time")
        }
        
        # Enterprise controls status
        enterprise_success = self.results["enterprise_controls"].get("overall_success", False)
        summary["component_status"]["enterprise_controls"] = {
            "status": "PASS" if enterprise_success else "FAIL", 
            "consent_system": any(r.get("success") for r in self.results["enterprise_controls"].get("consent_workflow", [])),
            "billing_system": any(r.get("success") for r in self.results["enterprise_controls"].get("billing_system", [])),
            "audit_system": any(r.get("success") for r in self.results["enterprise_controls"].get("audit_logging", []))
        }
        
        # Performance summary
        benchmarks = self.results["performance_benchmarks"]
        if benchmarks:
            summary["performance_summary"] = {
                "document_search_avg": benchmarks.get("document_search_performance", {}).get("avg_response_time"),
                "web_search_avg": benchmarks.get("web_search_performance", {}).get("avg_response_time"), 
                "intelligent_routing_avg": benchmarks.get("intelligent_routing_performance", {}).get("avg_response_time")
            }
        
        # Generate recommendations
        if router_success_rate < 0.9:
            summary["recommendations"].append("Router consolidation needs optimization")
        if not memory_learning:
            summary["recommendations"].append("Memory system learning mechanism needs verification")
        if not enterprise_success:
            summary["recommendations"].append("Enterprise controls require attention")
            
        # Overall status
        if (router_success_rate >= 0.8 and memory_learning and enterprise_success):
            summary["overall_status"] = "PASS"
        else:
            summary["overall_status"] = "NEEDS_ATTENTION"
        
        self.results["summary"] = summary
        
        # Print summary
        print("\n" + "="*80)
        print("WEEK 4: INTEGRATION TESTING & PERFORMANCE BENCHMARK RESULTS")
        print("="*80)
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Test Timestamp: {summary['test_timestamp']}")
        print("\nComponent Status:")
        for component, status in summary["component_status"].items():
            print(f"  {component}: {status['status']}")
        
        if summary["performance_summary"]:
            print("\nPerformance Summary:")
            for metric, value in summary["performance_summary"].items():
                if value:
                    print(f"  {metric}: {value:.2f}s")
        
        if summary["recommendations"]:
            print("\nRecommendations:")
            for rec in summary["recommendations"]:
                print(f"  - {rec}")
        print("="*80)

async def main():
    """Main integration testing function"""
    async with IntegrationTester() as tester:
        results = await tester.run_comprehensive_test()
        
        # Save detailed results
        with open("/workspace/unified-ai-system-clean/integration_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: integration_test_results.json")
        
        return results

if __name__ == "__main__":
    asyncio.run(main())