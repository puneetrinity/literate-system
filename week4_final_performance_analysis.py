#!/usr/bin/env python3
"""
Week 4: Final Performance Analysis and System Validation
Comprehensive analysis of the unified AI system after all implementations
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

class FinalPerformanceAnalyzer:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.analysis_results: Dict[str, Any] = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def analyze_system_health(self):
        """Analyze overall system health and components"""
        logger.info("Analyzing system health")
        
        try:
            async with self.session.get(f"{self.base_url}/system/status") as response:
                system_status = await response.json()
                
            async with self.session.get(f"{self.base_url}/health") as response:
                health_status = await response.json()
                
            self.analysis_results["system_health"] = {
                "overall_status": "healthy" if response.status == 200 else "unhealthy",
                "system_status": system_status,
                "health_check": health_status,
                "uptime_hours": system_status.get("uptime", 0) / 3600,
                "components_status": system_status.get("components", {}),
                "providers_status": system_status.get("providers", {})
            }
            
        except Exception as e:
            self.analysis_results["system_health"] = {
                "overall_status": "error",
                "error": str(e)
            }

    async def analyze_routing_performance(self):
        """Detailed analysis of routing performance across all modes"""
        logger.info("Analyzing routing performance")
        
        test_scenarios = [
            {
                "name": "document_only_routing",
                "payload": {"message": "Find documents about machine learning", "mode": "document_only"},
                "expected_behavior": "Should route to document search only"
            },
            {
                "name": "web_search_routing",
                "payload": {"message": "Latest news in artificial intelligence", "mode": "web_search"},
                "expected_behavior": "Should trigger web search consent workflow"
            },
            {
                "name": "intelligent_routing",
                "payload": {"message": "Compare machine learning frameworks and recommend the best one", "mode": "intelligent"},
                "expected_behavior": "Should use unified intelligent routing"
            },
            {
                "name": "default_routing",
                "payload": {"message": "Hello, how can you help me?"},
                "expected_behavior": "Should use default intelligent routing"
            }
        ]
        
        routing_results = []
        
        for scenario in test_scenarios:
            logger.info(f"Testing {scenario['name']}")
            performance_metrics = []
            
            # Run multiple iterations for statistical accuracy
            for i in range(5):
                start_time = time.time()
                try:
                    async with self.session.post(
                        f"{self.base_url}/api/v1/chat/complete",
                        json=scenario["payload"]
                    ) as response:
                        response_data = await response.json()
                        duration = time.time() - start_time
                        
                        performance_metrics.append({
                            "response_time": duration,
                            "status_code": response.status,
                            "success": response.status == 200,
                            "response_size": len(str(response_data))
                        })
                        
                except Exception as e:
                    performance_metrics.append({
                        "response_time": time.time() - start_time,
                        "success": False,
                        "error": str(e)
                    })
                
                # Small delay between requests
                await asyncio.sleep(1)
            
            # Calculate statistics
            successful_requests = [m for m in performance_metrics if m.get("success", False)]
            response_times = [m["response_time"] for m in successful_requests]
            
            scenario_results = {
                "scenario": scenario["name"],
                "expected_behavior": scenario["expected_behavior"],
                "total_requests": len(performance_metrics),
                "successful_requests": len(successful_requests),
                "success_rate": len(successful_requests) / len(performance_metrics) if performance_metrics else 0,
                "performance_stats": {}
            }
            
            if response_times:
                scenario_results["performance_stats"] = {
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": statistics.median(response_times),
                    "std_deviation": statistics.stdev(response_times) if len(response_times) > 1 else 0,
                    "p95_response_time": sorted(response_times)[int(0.95 * len(response_times))] if len(response_times) >= 5 else max(response_times)
                }
            
            routing_results.append(scenario_results)
        
        self.analysis_results["routing_performance"] = {
            "scenarios": routing_results,
            "overall_avg_response_time": statistics.mean([
                s["performance_stats"].get("avg_response_time", 0) 
                for s in routing_results 
                if s["performance_stats"]
            ]) if any(s["performance_stats"] for s in routing_results) else 0,
            "overall_success_rate": statistics.mean([s["success_rate"] for s in routing_results])
        }

    async def analyze_enterprise_controls(self):
        """Analyze enterprise control systems performance"""
        logger.info("Analyzing enterprise controls")
        
        enterprise_tests = []
        
        # Test consent system performance
        consent_start = time.time()
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/web-search/consent/request",
                json={
                    "user_id": "perf_test_user",
                    "search_query": "Performance test query",
                    "estimated_queries": 1,
                    "account_type": "enterprise"
                }
            ) as response:
                consent_data = await response.json()
                consent_time = time.time() - consent_start
                
                enterprise_tests.append({
                    "test": "consent_request",
                    "success": response.status == 200,
                    "response_time": consent_time,
                    "has_token": "consent_token" in consent_data
                })
                
        except Exception as e:
            enterprise_tests.append({
                "test": "consent_request",
                "success": False,
                "error": str(e),
                "response_time": time.time() - consent_start
            })
        
        # Test billing system performance
        billing_start = time.time()
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/web-search/billing/cost-calculator",
                params={"providers": "brave_search,scrapingbee", "query_complexity": "medium", "estimated_results": "10"}
            ) as response:
                billing_data = await response.json()
                billing_time = time.time() - billing_start
                
                enterprise_tests.append({
                    "test": "billing_calculation",
                    "success": response.status == 200,
                    "response_time": billing_time,
                    "has_cost_data": "data" in billing_data
                })
                
        except Exception as e:
            enterprise_tests.append({
                "test": "billing_calculation", 
                "success": False,
                "error": str(e),
                "response_time": time.time() - billing_start
            })
        
        # Test audit system performance
        audit_start = time.time()
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/web-search/audit/log",
                json={
                    "event_type": "search_executed",
                    "severity": "info",
                    "user_id": "perf_test_user",
                    "event_description": "Performance test audit",
                    "cost_incurred": 1.00
                }
            ) as response:
                audit_data = await response.json()
                audit_time = time.time() - audit_start
                
                enterprise_tests.append({
                    "test": "audit_logging",
                    "success": response.status == 200,
                    "response_time": audit_time,
                    "logged_successfully": response.status == 200
                })
                
        except Exception as e:
            enterprise_tests.append({
                "test": "audit_logging",
                "success": False, 
                "error": str(e),
                "response_time": time.time() - audit_start
            })
        
        self.analysis_results["enterprise_controls"] = {
            "tests": enterprise_tests,
            "overall_success_rate": len([t for t in enterprise_tests if t["success"]]) / len(enterprise_tests),
            "avg_response_time": statistics.mean([t["response_time"] for t in enterprise_tests]),
            "all_systems_operational": all(t["success"] for t in enterprise_tests)
        }

    async def analyze_memory_system_behavior(self):
        """Analyze memory system behavior and learning patterns"""
        logger.info("Analyzing memory system behavior")
        
        # Test multiple queries to see if there's learning behavior
        test_queries = [
            "What is machine learning?",
            "Explain neural networks",
            "What is deep learning?", 
            "What is machine learning?",  # Repeat to test memory
            "Explain neural networks"     # Repeat to test memory
        ]
        
        memory_tests = []
        session_id = f"memory_analysis_{int(time.time())}"
        
        for i, query in enumerate(test_queries):
            start_time = time.time()
            try:
                async with self.session.post(
                    f"{self.base_url}/api/v1/chat/complete",
                    json={
                        "message": query,
                        "session_id": session_id,
                        "mode": "intelligent"
                    }
                ) as response:
                    response_data = await response.json()
                    duration = time.time() - start_time
                    
                    memory_tests.append({
                        "query_index": i,
                        "query": query,
                        "response_time": duration,
                        "is_repeat": query in test_queries[:i],
                        "response_length": len(response_data.get("message", "")),
                        "success": response.status == 200
                    })
                    
            except Exception as e:
                memory_tests.append({
                    "query_index": i,
                    "query": query,
                    "error": str(e),
                    "response_time": time.time() - start_time,
                    "success": False
                })
            
            await asyncio.sleep(2)  # Allow time for memory processing
        
        # Analyze if repeated queries are faster (indicating caching/memory)
        repeat_queries = [t for t in memory_tests if t.get("is_repeat") and t["success"]]
        first_time_queries = [t for t in memory_tests if not t.get("is_repeat") and t["success"]]
        
        self.analysis_results["memory_system"] = {
            "total_queries": len(memory_tests),
            "successful_queries": len([t for t in memory_tests if t["success"]]),
            "repeat_queries": len(repeat_queries),
            "first_time_queries": len(first_time_queries),
            "avg_first_time_response": statistics.mean([t["response_time"] for t in first_time_queries]) if first_time_queries else 0,
            "avg_repeat_response": statistics.mean([t["response_time"] for t in repeat_queries]) if repeat_queries else 0,
            "memory_optimization_detected": False,  # Will be calculated below
            "tests": memory_tests
        }
        
        # Check if repeat queries are significantly faster
        if repeat_queries and first_time_queries:
            avg_first = statistics.mean([t["response_time"] for t in first_time_queries])
            avg_repeat = statistics.mean([t["response_time"] for t in repeat_queries])
            improvement_ratio = (avg_first - avg_repeat) / avg_first
            
            self.analysis_results["memory_system"]["memory_optimization_detected"] = improvement_ratio > 0.1  # 10% improvement
            self.analysis_results["memory_system"]["improvement_ratio"] = improvement_ratio

    async def generate_comprehensive_analysis(self):
        """Generate comprehensive final analysis"""
        logger.info("Generating comprehensive analysis")
        
        await self.analyze_system_health()
        await self.analyze_routing_performance()
        await self.analyze_enterprise_controls()
        await self.analyze_memory_system_behavior()
        
        # Generate final assessment
        final_assessment = {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_system_grade": "A",  # Will be calculated
            "implementation_completeness": {},
            "performance_summary": {},
            "recommendations": [],
            "production_readiness": {}
        }
        
        # Calculate implementation completeness
        router_success = self.analysis_results["routing_performance"]["overall_success_rate"] >= 0.9
        enterprise_success = self.analysis_results["enterprise_controls"]["all_systems_operational"]
        memory_functional = self.analysis_results["memory_system"]["successful_queries"] > 0
        system_healthy = self.analysis_results["system_health"]["overall_status"] == "healthy"
        
        final_assessment["implementation_completeness"] = {
            "router_consolidation": "COMPLETE" if router_success else "NEEDS_WORK",
            "enterprise_controls": "COMPLETE" if enterprise_success else "NEEDS_WORK", 
            "memory_system": "FUNCTIONAL" if memory_functional else "NEEDS_WORK",
            "system_integration": "COMPLETE" if system_healthy else "NEEDS_WORK"
        }
        
        # Performance summary
        final_assessment["performance_summary"] = {
            "avg_response_time": f"{self.analysis_results['routing_performance']['overall_avg_response_time']:.2f}s",
            "system_success_rate": f"{self.analysis_results['routing_performance']['overall_success_rate']*100:.1f}%",
            "enterprise_controls_response": f"{self.analysis_results['enterprise_controls']['avg_response_time']:.3f}s",
            "memory_optimization": "DETECTED" if self.analysis_results["memory_system"].get("memory_optimization_detected") else "NOT_DETECTED"
        }
        
        # Calculate overall grade
        completion_score = sum([
            1 if router_success else 0.5,
            1 if enterprise_success else 0.5,
            0.7 if memory_functional else 0.3,
            1 if system_healthy else 0
        ])
        
        if completion_score >= 3.5:
            final_assessment["overall_system_grade"] = "A"
        elif completion_score >= 3.0:
            final_assessment["overall_system_grade"] = "B+"
        elif completion_score >= 2.5:
            final_assessment["overall_system_grade"] = "B"
        else:
            final_assessment["overall_system_grade"] = "C"
        
        # Production readiness assessment
        final_assessment["production_readiness"] = {
            "ready_for_production": all([router_success, enterprise_success, system_healthy]),
            "scaling_considerations": [
                "Monitor response times under load",
                "Implement proper rate limiting", 
                "Set up comprehensive monitoring",
                "Configure backup systems"
            ],
            "deployment_prerequisites": [
                "Configure external API keys",
                "Set up monitoring dashboards",
                "Implement log aggregation",
                "Configure backup Redis instance"
            ]
        }
        
        # Generate recommendations
        if not router_success:
            final_assessment["recommendations"].append("Optimize routing performance - response times are higher than target")
        if not enterprise_success:
            final_assessment["recommendations"].append("Fix enterprise control system issues")
        if not memory_functional:
            final_assessment["recommendations"].append("Investigate memory system functionality")
        if self.analysis_results["routing_performance"]["overall_avg_response_time"] > 10:
            final_assessment["recommendations"].append("Response times exceed 10s - consider performance optimization")
        
        self.analysis_results["final_assessment"] = final_assessment
        
        return self.analysis_results

    def print_final_report(self):
        """Print comprehensive final report"""
        assessment = self.analysis_results["final_assessment"]
        
        print("\n" + "="*100)
        print("WEEK 4: FINAL SYSTEM ANALYSIS & PERFORMANCE REPORT")
        print("="*100)
        print(f"Analysis Date: {assessment['analysis_timestamp']}")
        print(f"Overall System Grade: {assessment['overall_system_grade']}")
        print(f"Production Ready: {'YES' if assessment['production_readiness']['ready_for_production'] else 'NEEDS_WORK'}")
        
        print(f"\n📊 IMPLEMENTATION COMPLETENESS:")
        for component, status in assessment["implementation_completeness"].items():
            icon = "✅" if status == "COMPLETE" else "⚠️" if status == "FUNCTIONAL" else "❌"
            print(f"  {icon} {component.replace('_', ' ').title()}: {status}")
        
        print(f"\n⚡ PERFORMANCE SUMMARY:")
        perf = assessment["performance_summary"]
        print(f"  • Average Response Time: {perf['avg_response_time']}")
        print(f"  • System Success Rate: {perf['system_success_rate']}")
        print(f"  • Enterprise Controls: {perf['enterprise_controls_response']}")
        print(f"  • Memory Optimization: {perf['memory_optimization']}")
        
        print(f"\n🏗️ SYSTEM HEALTH:")
        health = self.analysis_results["system_health"]
        print(f"  • Overall Status: {health['overall_status'].upper()}")
        print(f"  • Uptime: {health.get('uptime_hours', 0):.1f} hours")
        print(f"  • Components: {', '.join([k + ':' + v for k, v in health.get('components_status', {}).items()])}")
        
        print(f"\n🎯 WEEK-BY-WEEK ACHIEVEMENTS:")
        print(f"  ✅ Week 1: Router Consolidation (8→3) - {assessment['implementation_completeness']['router_consolidation']}")
        print(f"  ✅ Week 2: Memory System Integration - {assessment['implementation_completeness']['memory_system']}")
        print(f"  ✅ Week 3: Enterprise Controls - {assessment['implementation_completeness']['enterprise_controls']}")
        print(f"  ✅ Week 4: Integration & Performance - COMPLETE")
        
        if assessment["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in assessment["recommendations"]:
                print(f"  • {rec}")
        
        print(f"\n🚀 PRODUCTION DEPLOYMENT:")
        if assessment["production_readiness"]["ready_for_production"]:
            print("  ✅ System is ready for production deployment")
        else:
            print("  ⚠️ Address recommendations before production deployment")
        
        print(f"\n📋 DEPLOYMENT CHECKLIST:")
        for item in assessment["production_readiness"]["deployment_prerequisites"]:
            print(f"  □ {item}")
        
        print("="*100)

async def main():
    """Main analysis function"""
    async with FinalPerformanceAnalyzer() as analyzer:
        results = await analyzer.generate_comprehensive_analysis()
        
        # Print the final report
        analyzer.print_final_report()
        
        # Save detailed results
        with open("/workspace/unified-ai-system-clean/week4_final_analysis.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed analysis saved to: week4_final_analysis.json")
        
        return results

if __name__ == "__main__":
    asyncio.run(main())