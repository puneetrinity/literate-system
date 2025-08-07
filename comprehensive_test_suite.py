#!/usr/bin/env python3
"""
Comprehensive Test Suite for Ultra-Fast Search System
Tests auto-indexing, performance, accuracy, and reliability
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

@dataclass
class TestResult:
    query: str
    response_time_ms: float
    results_count: int
    success: bool
    error: str = None
    status_code: int = 200

class ComprehensiveTestSuite:
    def __init__(self, base_url: str = "https://ij9lyqsrrt0kod-8001.proxy.runpod.net"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v2/search/ultra-fast"
        self.health_endpoint = f"{base_url}/health"
        self.results = {}
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("🧪 COMPREHENSIVE ULTRA-FAST SEARCH TEST SUITE")
        print("=" * 60)
        print(f"Testing endpoint: {self.endpoint}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        # Test categories
        tests = [
            ("🏥 Health Check", self.test_health_check),
            ("⚡ Basic Functionality", self.test_basic_functionality),
            ("🎯 Search Accuracy", self.test_search_accuracy),
            ("📊 Performance Benchmarks", self.test_performance_benchmarks),
            ("🔄 Concurrency Tests", self.test_concurrency),
            ("🌐 Edge Cases", self.test_edge_cases),
            ("📈 Scalability Tests", self.test_scalability),
        ]
        
        all_results = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "endpoint": self.endpoint,
                "test_categories": len(tests)
            }
        }
        
        for test_name, test_func in tests:
            print(f"\n{test_name}")
            print("-" * len(test_name))
            
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                result["test_duration_seconds"] = round(duration, 2)
                all_results[test_name.split()[1].lower().replace(" ", "_")] = result
                
                # Print summary
                if result.get('success', False):
                    print(f"✅ {test_name} completed successfully in {duration:.2f}s")
                else:
                    print(f"❌ {test_name} failed in {duration:.2f}s")
                    
            except Exception as e:
                print(f"💥 {test_name} crashed: {str(e)}")
                all_results[test_name.split()[1].lower().replace(" ", "_")] = {
                    "success": False,
                    "error": str(e),
                    "test_duration_seconds": 0
                }
        
        # Generate final report
        all_results["final_summary"] = self.generate_final_summary(all_results)
        
        return all_results
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test system health endpoints"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                start_time = time.time()
                async with session.get(self.health_endpoint) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Health check passed ({response_time:.1f}ms)")
                        print(f"   Status: {data.get('status', 'unknown')}")
                        
                        return {
                            "success": True,
                            "response_time_ms": response_time,
                            "status": data.get('status'),
                            "details": data
                        }
                    else:
                        print(f"   ❌ Health check failed: HTTP {response.status}")
                        return {"success": False, "status_code": response.status}
                        
        except Exception as e:
            print(f"   💥 Health check error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_basic_functionality(self) -> Dict[str, Any]:
        """Test basic search functionality"""
        test_queries = [
            "python",
            "machine learning", 
            "developer",
            "artificial intelligence",
            "senior engineer"
        ]
        
        results = []
        total_results = 0
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            for query in test_queries:
                try:
                    start_time = time.time()
                    
                    async with session.post(
                        self.endpoint,
                        json={"query": query},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            data = await response.json()
                            results_count = data.get('total_found', 0)
                            total_results += results_count
                            
                            result = TestResult(
                                query=query,
                                response_time_ms=response_time,
                                results_count=results_count,
                                success=True
                            )
                            
                            print(f"   ✅ '{query}': {results_count} results ({response_time:.1f}ms)")
                            
                        else:
                            result = TestResult(
                                query=query,
                                response_time_ms=response_time,
                                results_count=0,
                                success=False,
                                status_code=response.status
                            )
                            print(f"   ❌ '{query}': HTTP {response.status}")
                        
                        results.append(result)
                        
                except Exception as e:
                    result = TestResult(
                        query=query,
                        response_time_ms=0,
                        results_count=0,
                        success=False,
                        error=str(e)
                    )
                    results.append(result)
                    print(f"   💥 '{query}': {e}")
        
        # Calculate metrics
        successful_queries = [r for r in results if r.success]
        avg_response_time = statistics.mean([r.response_time_ms for r in successful_queries]) if successful_queries else 0
        
        summary = {
            "success": len(successful_queries) == len(test_queries),
            "total_queries": len(test_queries),
            "successful_queries": len(successful_queries),
            "total_results_found": total_results,
            "average_response_time_ms": round(avg_response_time, 2),
            "success_rate_percent": round((len(successful_queries) / len(test_queries)) * 100, 1)
        }
        
        print(f"   📊 Summary: {summary['successful_queries']}/{summary['total_queries']} queries successful")
        print(f"   📊 Average response time: {summary['average_response_time_ms']}ms")
        
        return summary
    
    async def test_search_accuracy(self) -> Dict[str, Any]:
        """Test search accuracy and relevance"""
        accuracy_tests = [
            {
                "query": "python developer",
                "expected_keywords": ["python", "developer", "programming"],
                "min_results": 1
            },
            {
                "query": "machine learning engineer", 
                "expected_keywords": ["machine learning", "ai", "ml", "data"],
                "min_results": 1
            },
            {
                "query": "senior software engineer",
                "expected_keywords": ["senior", "software", "engineer", "development"],
                "min_results": 1
            }
        ]
        
        accuracy_results = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            for test in accuracy_tests:
                try:
                    async with session.post(
                        self.endpoint,
                        json={"query": test["query"]},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            results = data.get('results', [])
                            
                            # Analyze relevance
                            relevance_score = self.calculate_relevance_score(
                                results, test["expected_keywords"]
                            )
                            
                            meets_minimum = len(results) >= test["min_results"]
                            
                            accuracy_results.append({
                                "query": test["query"],
                                "results_count": len(results),
                                "meets_minimum": meets_minimum,
                                "relevance_score": relevance_score,
                                "success": meets_minimum and relevance_score > 0.3
                            })
                            
                            print(f"   ✅ '{test['query']}': {len(results)} results, relevance: {relevance_score:.2f}")
                            
                        else:
                            accuracy_results.append({
                                "query": test["query"],
                                "success": False,
                                "error": f"HTTP {response.status}"
                            })
                            print(f"   ❌ '{test['query']}': HTTP {response.status}")
                            
                except Exception as e:
                    accuracy_results.append({
                        "query": test["query"],
                        "success": False,
                        "error": str(e)
                    })
                    print(f"   💥 '{test['query']}': {e}")
        
        successful_tests = [r for r in accuracy_results if r.get('success', False)]
        avg_relevance = statistics.mean([r['relevance_score'] for r in successful_tests if 'relevance_score' in r]) if successful_tests else 0
        
        return {
            "success": len(successful_tests) == len(accuracy_tests),
            "total_accuracy_tests": len(accuracy_tests),
            "successful_tests": len(successful_tests),
            "average_relevance_score": round(avg_relevance, 3),
            "accuracy_rate_percent": round((len(successful_tests) / len(accuracy_tests)) * 100, 1),
            "detailed_results": accuracy_results
        }
    
    def calculate_relevance_score(self, results: List[Dict], expected_keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matching"""
        if not results:
            return 0.0
        
        total_score = 0
        for result in results:
            # Check all text fields for keyword matches
            text_fields = [
                result.get('name', ''),
                result.get('title', ''),
                result.get('description', ''),
                ' '.join(result.get('skills', [])),
                ' '.join(result.get('technologies', []))
            ]
            
            full_text = ' '.join(text_fields).lower()
            
            # Count keyword matches
            matches = sum(1 for keyword in expected_keywords if keyword.lower() in full_text)
            total_score += matches / len(expected_keywords)
        
        return total_score / len(results)
    
    async def test_performance_benchmarks(self) -> Dict[str, Any]:
        """Comprehensive performance testing"""
        print("   🏃 Running performance benchmarks...")
        
        # Different load levels
        load_tests = [
            {"concurrent_requests": 1, "iterations": 10},
            {"concurrent_requests": 5, "iterations": 20},
            {"concurrent_requests": 10, "iterations": 30},
            {"concurrent_requests": 20, "iterations": 40},
        ]
        
        benchmark_results = []
        
        for load_test in load_tests:
            print(f"   📊 Testing {load_test['concurrent_requests']} concurrent requests...")
            
            result = await self.run_load_test(
                concurrent_requests=load_test['concurrent_requests'],
                total_iterations=load_test['iterations']
            )
            
            benchmark_results.append({
                "concurrency_level": load_test['concurrent_requests'],
                "total_requests": load_test['iterations'],
                **result
            })
            
            print(f"      ⏱️  Avg: {result['avg_response_time_ms']:.1f}ms, "
                  f"P95: {result['p95_response_time_ms']:.1f}ms, "
                  f"QPS: {result['queries_per_second']:.1f}")
        
        return {
            "success": True,
            "benchmark_results": benchmark_results,
            "peak_performance": max(benchmark_results, key=lambda x: x['queries_per_second'])
        }
    
    async def run_load_test(self, concurrent_requests: int, total_iterations: int) -> Dict[str, Any]:
        """Run load test with specified concurrency"""
        query = "python developer"  # Standard test query
        
        async def single_request(session):
            try:
                start_time = time.time()
                async with session.post(
                    self.endpoint,
                    json={"query": query},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "response_time_ms": response_time,
                            "results_count": data.get('total_found', 0)
                        }
                    else:
                        return {
                            "success": False,
                            "response_time_ms": response_time,
                            "status_code": response.status
                        }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "response_time_ms": 0
                }
        
        # Run concurrent requests
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = []
            for _ in range(total_iterations):
                # Create semaphore to limit concurrency
                if len(tasks) >= concurrent_requests:
                    # Wait for some tasks to complete
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    tasks = list(pending)
                
                task = asyncio.create_task(single_request(session))
                tasks.append(task)
            
            # Wait for all remaining tasks
            if tasks:
                await asyncio.wait(tasks)
        
        total_time = time.time() - start_time
        
        # Collect all results
        all_results = []
        for task in tasks:
            try:
                result = await task
                all_results.append(result)
            except Exception:
                pass
        
        # Calculate metrics
        successful_requests = [r for r in all_results if r.get('success', False)]
        response_times = [r['response_time_ms'] for r in successful_requests]
        
        if response_times:
            return {
                "total_requests": len(all_results),
                "successful_requests": len(successful_requests),
                "success_rate_percent": round((len(successful_requests) / len(all_results)) * 100, 1),
                "avg_response_time_ms": round(statistics.mean(response_times), 2),
                "median_response_time_ms": round(statistics.median(response_times), 2),
                "p95_response_time_ms": round(statistics.quantiles(response_times, n=20)[18], 2),
                "p99_response_time_ms": round(statistics.quantiles(response_times, n=100)[98], 2),
                "min_response_time_ms": round(min(response_times), 2),
                "max_response_time_ms": round(max(response_times), 2),
                "queries_per_second": round(len(successful_requests) / total_time, 2),
                "total_duration_seconds": round(total_time, 2)
            }
        else:
            return {
                "success": False,
                "error": "No successful requests"
            }
    
    async def test_concurrency(self) -> Dict[str, Any]:
        """Test system behavior under concurrent load"""
        print("   🔄 Testing concurrent request handling...")
        
        # Test concurrent requests with different queries
        queries = [
            "python developer",
            "machine learning engineer", 
            "data scientist",
            "frontend developer",
            "devops engineer"
        ]
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = []
            
            # Create 25 concurrent requests (5 queries × 5 repetitions)
            for _ in range(5):
                for query in queries:
                    task = asyncio.create_task(self.single_search_request(session, query))
                    tasks.append(task)
            
            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        
        return {
            "success": len(successful_results) > 0,
            "total_concurrent_requests": len(tasks),
            "successful_requests": len(successful_results),
            "concurrency_success_rate": round((len(successful_results) / len(tasks)) * 100, 1),
            "total_concurrent_duration": round(total_time, 2),
            "concurrent_qps": round(len(successful_results) / total_time, 2)
        }
    
    async def single_search_request(self, session, query: str) -> Dict[str, Any]:
        """Single search request for concurrency testing"""
        try:
            start_time = time.time()
            async with session.post(
                self.endpoint,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "query": query,
                        "response_time_ms": response_time,
                        "results_count": data.get('total_found', 0)
                    }
                else:
                    return {
                        "success": False,
                        "query": query,
                        "status_code": response.status
                    }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
    
    async def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases and error handling"""
        edge_cases = [
            {"query": "", "description": "Empty query"},
            {"query": "   ", "description": "Whitespace only"},
            {"query": "a", "description": "Single character"},
            {"query": "x" * 1000, "description": "Very long query"},
            {"query": "🤖🔍💻", "description": "Emoji query"},
            {"query": "SELECT * FROM users", "description": "SQL injection attempt"},
            {"query": "../../etc/passwd", "description": "Path traversal attempt"},
        ]
        
        edge_case_results = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            for case in edge_cases:
                try:
                    async with session.post(
                        self.endpoint,
                        json={"query": case["query"]},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        
                        # Any response (even 400) is acceptable for edge cases
                        result = {
                            "description": case["description"],
                            "query": case["query"][:50] + "..." if len(case["query"]) > 50 else case["query"],
                            "status_code": response.status,
                            "handled_gracefully": response.status in [200, 400, 422]
                        }
                        
                        if response.status == 200:
                            data = await response.json()
                            result["results_count"] = data.get('total_found', 0)
                            print(f"   ✅ {case['description']}: {response.status} ({result.get('results_count', 0)} results)")
                        else:
                            print(f"   ⚠️  {case['description']}: HTTP {response.status}")
                        
                        edge_case_results.append(result)
                        
                except Exception as e:
                    edge_case_results.append({
                        "description": case["description"],
                        "query": case["query"][:50],
                        "error": str(e),
                        "handled_gracefully": False
                    })
                    print(f"   💥 {case['description']}: {e}")
        
        handled_gracefully = [r for r in edge_case_results if r.get('handled_gracefully', False)]
        
        return {
            "success": len(handled_gracefully) >= len(edge_cases) * 0.8,  # 80% should be handled gracefully
            "total_edge_cases": len(edge_cases),
            "handled_gracefully": len(handled_gracefully),
            "graceful_handling_rate": round((len(handled_gracefully) / len(edge_cases)) * 100, 1),
            "detailed_results": edge_case_results
        }
    
    async def test_scalability(self) -> Dict[str, Any]:
        """Test system scalability with increasing load"""
        print("   📈 Testing scalability limits...")
        
        # Progressive load increase
        scalability_levels = [
            {"requests": 10, "description": "Light load"},
            {"requests": 25, "description": "Medium load"},
            {"requests": 50, "description": "Heavy load"},
            {"requests": 100, "description": "Stress test"},
        ]
        
        scalability_results = []
        
        for level in scalability_levels:
            print(f"      📊 {level['description']}: {level['requests']} requests")
            
            result = await self.run_scalability_test(level['requests'])
            result["description"] = level["description"]
            result["request_count"] = level["requests"]
            
            scalability_results.append(result)
            
            # Check if system is degrading significantly
            if result.get('success_rate_percent', 0) < 80:
                print(f"      ⚠️  Success rate dropped to {result['success_rate_percent']}%, stopping scalability test")
                break
        
        return {
            "success": len(scalability_results) > 0,
            "scalability_results": scalability_results,
            "max_successful_load": max([r['request_count'] for r in scalability_results if r.get('success_rate_percent', 0) >= 90], default=0)
        }
    
    async def run_scalability_test(self, request_count: int) -> Dict[str, Any]:
        """Run single scalability test"""
        query = "python developer"
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            # Create all requests
            tasks = [
                asyncio.create_task(self.single_search_request(session, query))
                for _ in range(request_count)
            ]
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        
        if successful_results:
            response_times = [r['response_time_ms'] for r in successful_results]
            
            return {
                "success": len(successful_results) > 0,
                "total_requests": request_count,
                "successful_requests": len(successful_results),
                "success_rate_percent": round((len(successful_results) / request_count) * 100, 1),
                "avg_response_time_ms": round(statistics.mean(response_times), 2),
                "p95_response_time_ms": round(statistics.quantiles(response_times, n=20)[18], 2) if len(response_times) >= 20 else round(max(response_times), 2),
                "queries_per_second": round(len(successful_results) / total_time, 2),
                "total_duration_seconds": round(total_time, 2)
            }
        else:
            return {
                "success": False,
                "error": "No successful requests",
                "total_requests": request_count
            }
    
    def generate_final_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final test summary"""
        test_categories = [k for k in all_results.keys() if k not in ['test_metadata', 'final_summary']]
        
        successful_categories = [
            category for category in test_categories 
            if all_results.get(category, {}).get('success', False)
        ]
        
        # Extract key metrics
        basic_func = all_results.get('functionality', {})
        performance = all_results.get('benchmarks', {})
        accuracy = all_results.get('accuracy', {})
        
        return {
            "overall_success": len(successful_categories) >= len(test_categories) * 0.8,
            "total_test_categories": len(test_categories),
            "successful_categories": len(successful_categories),
            "success_rate_percent": round((len(successful_categories) / len(test_categories)) * 100, 1),
            "key_metrics": {
                "avg_response_time_ms": basic_func.get('average_response_time_ms', 0),
                "search_success_rate": basic_func.get('success_rate_percent', 0),
                "accuracy_rate": accuracy.get('accuracy_rate_percent', 0),
                "peak_qps": max([
                    r.get('queries_per_second', 0) 
                    for r in performance.get('benchmark_results', [])
                ], default=0)
            },
            "test_status_by_category": {
                category: "✅ PASSED" if all_results.get(category, {}).get('success', False) else "❌ FAILED"
                for category in test_categories
            }
        }

async def main():
    """Run comprehensive test suite"""
    test_suite = ComprehensiveTestSuite()
    
    # Run all tests
    results = await test_suite.run_all_tests()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comprehensive_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🎯 FINAL TEST SUMMARY")
    print("=" * 60)
    
    summary = results['final_summary']
    
    print(f"Overall Success: {'✅ PASSED' if summary['overall_success'] else '❌ FAILED'}")
    print(f"Test Categories: {summary['successful_categories']}/{summary['total_test_categories']} passed ({summary['success_rate_percent']}%)")
    print()
    
    print("📊 Key Performance Metrics:")
    metrics = summary['key_metrics']
    print(f"   • Average Response Time: {metrics['avg_response_time_ms']}ms")
    print(f"   • Search Success Rate: {metrics['search_success_rate']}%")
    print(f"   • Accuracy Rate: {metrics['accuracy_rate']}%")
    print(f"   • Peak QPS: {metrics['peak_qps']}")
    print()
    
    print("📋 Test Status by Category:")
    for category, status in summary['test_status_by_category'].items():
        print(f"   • {category.replace('_', ' ').title()}: {status}")
    
    print(f"\n📄 Detailed results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())