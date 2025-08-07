#\!/usr/bin/env python3
"""
Comprehensive Ultra-Fast Search Benchmarking Suite
Comparing against traditional vector database performance metrics
"""

import asyncio
import json
import time
import statistics
import requests
import concurrent.futures
from typing import List, Dict, Any
import psutil
import numpy as np
from datetime import datetime

class UltraFastSearchBenchmark:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = {}
        
    def get_system_info(self) -> Dict:
        """Get current system information"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu,
            "memory_total_gb": memory.total / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "memory_used_percent": memory.percent,
            "disk_total_gb": disk.total / (1024**3),
            "disk_free_gb": disk.free / (1024**3),
            "disk_used_percent": (disk.used / disk.total) * 100
        }
    
    def benchmark_single_query(self, query: str, endpoint: str = "/api/v2/search/ultra-fast") -> Dict:
        """Benchmark a single query"""
        url = f"{self.base_url}{endpoint}"
        payload = {"query": query, "num_results": 10}
        
        start_time = time.perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=30)
            end_time = time.perf_counter()
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "latency_ms": (end_time - start_time) * 1000,
                    "response_time_ms": data.get("response_time_ms", 0),
                    "results_count": data.get("total_found", 0),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "latency_ms": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
        except Exception as e:
            end_time = time.perf_counter()
            return {
                "success": False,
                "latency_ms": (end_time - start_time) * 1000,
                "error": str(e)[:200]
            }
    
    def benchmark_throughput(self, queries: List[str], concurrent_requests: int = 10) -> Dict:
        """Benchmark throughput with concurrent requests"""
        print(f"🚀 Running throughput benchmark with {concurrent_requests} concurrent requests...")
        
        def run_query(query):
            return self.benchmark_single_query(query)
        
        all_queries = queries * (concurrent_requests // len(queries) + 1)
        all_queries = all_queries[:concurrent_requests]
        
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(run_query, query) for query in all_queries]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        successful_requests = [r for r in results if r.get("success", False)]
        failed_requests = [r for r in results if not r.get("success", False)]
        
        if successful_requests:
            latencies = [r["latency_ms"] for r in successful_requests]
            response_times = [r.get("response_time_ms", 0) for r in successful_requests]
            
            return {
                "total_requests": len(results),
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / len(results),
                "total_time_seconds": total_time,
                "queries_per_second": len(successful_requests) / total_time,
                "latency_stats": {
                    "mean_ms": statistics.mean(latencies),
                    "median_ms": statistics.median(latencies),
                    "p95_ms": np.percentile(latencies, 95),
                    "p99_ms": np.percentile(latencies, 99),
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
                },
                "response_time_stats": {
                    "mean_ms": statistics.mean(response_times) if response_times else 0,
                    "median_ms": statistics.median(response_times) if response_times else 0,
                    "p95_ms": np.percentile(response_times, 95) if response_times else 0,
                    "p99_ms": np.percentile(response_times, 99) if response_times else 0
                }
            }
        else:
            return {
                "total_requests": len(results),
                "successful_requests": 0,
                "failed_requests": len(failed_requests),
                "success_rate": 0,
                "error": "All requests failed"
            }
    
    def benchmark_scalability(self, base_queries: List[str]) -> Dict:
        """Test scalability with increasing load"""
        print("📈 Running scalability benchmark...")
        
        concurrency_levels = [1, 5, 10, 20, 50, 100]
        scalability_results = {}
        
        for concurrency in concurrency_levels:
            print(f"  Testing concurrency level: {concurrency}")
            result = self.benchmark_throughput(base_queries, concurrency)
            scalability_results[f"concurrency_{concurrency}"] = result
            
            # Brief pause between tests
            time.sleep(2)
        
        return scalability_results
    
    def benchmark_query_complexity(self) -> Dict:
        """Test different types of queries"""
        print("🔍 Running query complexity benchmark...")
        
        query_types = {
            "simple_keywords": [
                "test", "search", "document", "system", "data"
            ],
            "phrase_queries": [
                "machine learning", "artificial intelligence", "data science",
                "natural language processing", "computer vision"
            ],
            "long_queries": [
                "comprehensive analysis of machine learning algorithms for natural language processing",
                "advanced techniques in artificial intelligence and their applications in modern technology",
                "detailed explanation of neural networks and deep learning methodologies"
            ],
            "technical_queries": [
                "Python programming best practices", "database optimization techniques",
                "distributed systems architecture", "microservices design patterns"
            ]
        }
        
        complexity_results = {}
        
        for query_type, queries in query_types.items():
            print(f"  Testing {query_type}...")
            results = []
            
            for query in queries:
                result = self.benchmark_single_query(query)
                results.append(result)
                time.sleep(0.1)  # Small delay between queries
            
            successful_results = [r for r in results if r.get("success", False)]
            
            if successful_results:
                latencies = [r["latency_ms"] for r in successful_results]
                complexity_results[query_type] = {
                    "query_count": len(queries),
                    "successful_queries": len(successful_results),
                    "success_rate": len(successful_results) / len(queries),
                    "avg_latency_ms": statistics.mean(latencies),
                    "median_latency_ms": statistics.median(latencies),
                    "max_latency_ms": max(latencies),
                    "min_latency_ms": min(latencies)
                }
            else:
                complexity_results[query_type] = {
                    "query_count": len(queries),
                    "successful_queries": 0,
                    "success_rate": 0,
                    "error": "All queries failed"
                }
        
        return complexity_results
    
    def get_system_metrics(self) -> Dict:
        """Get current system performance metrics"""
        try:
            # Get metrics from the service
            metrics_response = requests.get(f"{self.base_url}/api/v2/metrics", timeout=10)
            health_response = requests.get(f"{self.base_url}/api/v2/health", timeout=10)
            
            metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}
            health_data = health_response.json() if health_response.status_code == 200 else {}
            
            return {
                "service_metrics": metrics_data,
                "service_health": health_data,
                "system_info": self.get_system_info()
            }
        except Exception as e:
            return {"error": str(e), "system_info": self.get_system_info()}
    
    def run_comprehensive_benchmark(self) -> Dict:
        """Run the complete benchmark suite"""
        print("🎯 Starting Comprehensive Ultra-Fast Search Benchmark")
        print("=" * 60)
        
        benchmark_start = datetime.now()
        
        # Base queries for testing
        base_queries = [
            "artificial intelligence",
            "machine learning algorithms",
            "data science techniques",
            "python programming",
            "database optimization",
            "search algorithms",
            "natural language processing",
            "computer vision"
        ]
        
        results = {
            "benchmark_info": {
                "start_time": benchmark_start.isoformat(),
                "base_url": self.base_url,
                "query_count": len(base_queries)
            },
            "system_info_start": self.get_system_info()
        }
        
        # 1. Single Query Performance
        print("\n1️⃣ Single Query Performance Test")
        single_query_results = []
        for query in base_queries[:3]:  # Test first 3 queries
            result = self.benchmark_single_query(query)
            single_query_results.append({"query": query, "result": result})
            print(f"   Query: '{query}' - {result.get('latency_ms', 0):.2f}ms")
            time.sleep(0.5)
        
        results["single_query_performance"] = single_query_results
        
        # 2. Throughput Benchmark
        print("\n2️⃣ Throughput Benchmark")
        throughput_result = self.benchmark_throughput(base_queries, concurrent_requests=20)
        results["throughput_benchmark"] = throughput_result
        
        if throughput_result.get("queries_per_second"):
            print(f"   QPS: {throughput_result['queries_per_second']:.2f}")
            print(f"   P99 Latency: {throughput_result['latency_stats']['p99_ms']:.2f}ms")
            print(f"   Success Rate: {throughput_result['success_rate']*100:.1f}%")
        
        # 3. Query Complexity Analysis
        print("\n3️⃣ Query Complexity Analysis")
        complexity_result = self.benchmark_query_complexity()
        results["query_complexity"] = complexity_result
        
        for query_type, stats in complexity_result.items():
            if stats.get("avg_latency_ms"):
                print(f"   {query_type}: {stats['avg_latency_ms']:.2f}ms avg")
        
        # 4. Scalability Test
        print("\n4️⃣ Scalability Test")
        scalability_result = self.benchmark_scalability(base_queries[:4])
        results["scalability_benchmark"] = scalability_result
        
        # 5. System Metrics
        print("\n5️⃣ System Metrics Collection")
        system_metrics = self.get_system_metrics()
        results["system_metrics"] = system_metrics
        
        # Final system state
        results["system_info_end"] = self.get_system_info()
        
        benchmark_end = datetime.now()
        results["benchmark_info"]["end_time"] = benchmark_end.isoformat()
        results["benchmark_info"]["total_duration_seconds"] = (benchmark_end - benchmark_start).total_seconds()
        
        print("\n✅ Benchmark Complete\!")
        print(f"Total Duration: {results['benchmark_info']['total_duration_seconds']:.2f} seconds")
        
        return results
    
    def generate_comparison_report(self, results: Dict) -> str:
        """Generate a comparison report against vector database benchmarks"""
        
        # Extract key metrics
        throughput = results.get("throughput_benchmark", {})
        qps = throughput.get("queries_per_second", 0)
        p99_latency = throughput.get("latency_stats", {}).get("p99_ms", 0)
        success_rate = throughput.get("success_rate", 0)
        
        # Vector DB comparison data (from research)
        comparison_data = {
            "Ultra Fast Search (Measured)": {
                "qps": qps,
                "p99_latency_ms": p99_latency,
                "success_rate": success_rate
            },
            "Redis Vector (Benchmark)": {
                "qps": 3000,
                "p99_latency_ms": 80,
                "success_rate": 0.98
            },
            "Milvus (Estimated)": {
                "qps": 910,
                "p99_latency_ms": 340,
                "success_rate": 0.90
            },
            "Qdrant (Estimated)": {
                "qps": 882,
                "p99_latency_ms": 320,
                "success_rate": 0.90
            },
            "Weaviate (Estimated)": {
                "qps": 1760,
                "p99_latency_ms": 140,
                "success_rate": 0.90
            }
        }
        
        report = "\n" + "="*80 + "\n"
        report += "📊 COMPREHENSIVE ULTRA-FAST SEARCH BENCHMARK REPORT\n"
        report += "="*80 + "\n\n"
        
        report += "🚀 PERFORMANCE SUMMARY\n"
        report += "-"*40 + "\n"
        report += f"Queries Per Second (QPS): {qps:.2f}\n"
        report += f"P99 Latency: {p99_latency:.2f}ms\n"
        report += f"Success Rate: {success_rate*100:.1f}%\n\n"
        
        report += "📈 COMPETITIVE COMPARISON\n"
        report += "-"*40 + "\n"
        report += f"{'System':<25} {'QPS':<10} {'P99 Latency':<15} {'Success Rate':<12}\n"
        report += "-"*62 + "\n"
        
        for system, metrics in comparison_data.items():
            report += f"{system:<25} {metrics['qps']:<10.0f} {metrics['p99_latency_ms']:<15.0f} {metrics['success_rate']*100:<12.1f}%\n"
        
        # Performance analysis
        report += "\n🎯 PERFORMANCE ANALYSIS\n"
        report += "-"*40 + "\n"
        
        if qps > 2000:
            report += "✅ EXCELLENT: QPS above 2000 - competing with top-tier systems\n"
        elif qps > 1000:
            report += "✅ GOOD: QPS above 1000 - competitive with major vector DBs\n"
        else:
            report += "⚠️  IMPROVEMENT NEEDED: QPS below 1000 - optimization required\n"
        
        if p99_latency < 100:
            report += "✅ EXCELLENT: P99 latency under 100ms - best-in-class performance\n"
        elif p99_latency < 200:
            report += "✅ GOOD: P99 latency under 200ms - competitive performance\n"
        else:
            report += "⚠️  IMPROVEMENT NEEDED: P99 latency high - optimization required\n"
        
        # System resource analysis
        system_info = results.get("system_info_end", {})
        report += f"\n💻 SYSTEM RESOURCES\n"
        report += "-"*40 + "\n"
        report += f"CPU Usage: {system_info.get('cpu_percent', 0):.1f}%\n"
        report += f"Memory Usage: {system_info.get('memory_used_percent', 0):.1f}%\n"
        report += f"Memory Available: {system_info.get('memory_available_gb', 0):.1f}GB\n"
        
        return report

def main():
    benchmark = UltraFastSearchBenchmark()
    
    # Run comprehensive benchmark
    results = benchmark.run_comprehensive_benchmark()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ultra_fast_search_benchmark_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Generate and print comparison report
    report = benchmark.generate_comparison_report(results)
    print(report)
    
    # Save report
    report_filename = f"ultra_fast_search_report_{timestamp}.txt"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    print(f"📄 Report saved to: {report_filename}")
    
    return results

if __name__ == "__main__":
    main()
