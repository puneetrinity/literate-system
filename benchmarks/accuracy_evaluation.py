#\!/usr/bin/env python3
"""
Search Accuracy and Recall Evaluation for Ultra-Fast Search
"""

import json
import requests
import time
from typing import List, Dict, Tuple

class AccuracyEvaluator:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        
    def get_ground_truth_data(self) -> List[Dict]:
        """Get ground truth query-document pairs for evaluation"""
        # Based on the test documents we know exist
        return [
            {
                "query": "test document",
                "expected_docs": ["search_test.txt", "test_document.txt", "comprehensive_test.txt", "test.txt"],
                "relevance_threshold": 0.3
            },
            {
                "query": "search test",
                "expected_docs": ["search_test.txt"],
                "relevance_threshold": 0.5
            },
            {
                "query": "RAG system",
                "expected_docs": ["search_test.txt", "test_document.txt"],
                "relevance_threshold": 0.4
            },
            {
                "query": "document processing",
                "expected_docs": ["search_test.txt", "comprehensive_test.txt"],
                "relevance_threshold": 0.3
            },
            {
                "query": "upload functionality",
                "expected_docs": ["test_document.txt", "comprehensive_test.txt"],
                "relevance_threshold": 0.3
            }
        ]
    
    def search_rag_query(self, query: str, top_k: int = 10) -> Dict:
        """Execute RAG search query"""
        url = f"{self.base_url}/api/v2/rag/query"
        payload = {"query": query, "top_k": top_k}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"} 
        except Exception as e:
            return {"error": str(e)}
    
    def search_ultra_fast(self, query: str, num_results: int = 10) -> Dict:
        """Execute ultra-fast search query"""
        url = f"{self.base_url}/api/v2/search/ultra-fast"
        payload = {"query": query, "num_results": num_results}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_recall_at_k(self, retrieved_docs: List[str], relevant_docs: List[str], k: int = 10) -> float:
        """Calculate recall@k metric"""
        if not relevant_docs:
            return 0.0
        
        retrieved_set = set(retrieved_docs[:k])
        relevant_set = set(relevant_docs)
        
        intersection = retrieved_set & relevant_set
        return len(intersection) / len(relevant_set)
    
    def calculate_precision_at_k(self, retrieved_docs: List[str], relevant_docs: List[str], k: int = 10) -> float:
        """Calculate precision@k metric"""
        if not retrieved_docs:
            return 0.0
        
        retrieved_k = retrieved_docs[:k]
        relevant_set = set(relevant_docs)
        
        relevant_retrieved = [doc for doc in retrieved_k if doc in relevant_set]
        return len(relevant_retrieved) / len(retrieved_k)
    
    def evaluate_rag_accuracy(self) -> Dict:
        """Evaluate RAG search accuracy"""
        print("🎯 Evaluating RAG Search Accuracy...")
        
        ground_truth = self.get_ground_truth_data()
        results = []
        
        for test_case in ground_truth:
            query = test_case["query"]
            expected_docs = test_case["expected_docs"]
            threshold = test_case["relevance_threshold"]
            
            print(f"  Testing query: '{query}'")
            
            # Execute search
            search_result = self.search_rag_query(query)
            
            if "error" in search_result:
                results.append({
                    "query": query,
                    "error": search_result["error"],
                    "success": False
                })
                continue
            
            # Extract retrieved document filenames
            chunks = search_result.get("chunks", [])
            retrieved_docs = []
            
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                filename = metadata.get("source_filename", "")
                if filename and chunk.get("relevance_score", 0) >= threshold:
                    retrieved_docs.append(filename)
            
            # Remove duplicates while preserving order
            retrieved_docs = list(dict.fromkeys(retrieved_docs))
            
            # Calculate metrics
            recall_5 = self.calculate_recall_at_k(retrieved_docs, expected_docs, 5)
            recall_10 = self.calculate_recall_at_k(retrieved_docs, expected_docs, 10)
            precision_5 = self.calculate_precision_at_k(retrieved_docs, expected_docs, 5)
            precision_10 = self.calculate_precision_at_k(retrieved_docs, expected_docs, 10)
            
            results.append({
                "query": query,
                "expected_docs": expected_docs,
                "retrieved_docs": retrieved_docs,
                "total_chunks": len(chunks),
                "relevant_chunks": len([c for c in chunks if c.get("relevance_score", 0) >= threshold]),
                "recall@5": recall_5,
                "recall@10": recall_10,
                "precision@5": precision_5,
                "precision@10": precision_10,
                "processing_time_ms": search_result.get("processing_time", 0),
                "success": True
            })
            
            time.sleep(0.5)  # Small delay between queries
        
        # Calculate overall metrics
        successful_results = [r for r in results if r.get("success", False)]
        
        if successful_results:
            avg_recall_5 = sum(r["recall@5"] for r in successful_results) / len(successful_results)
            avg_recall_10 = sum(r["recall@10"] for r in successful_results) / len(successful_results)
            avg_precision_5 = sum(r["precision@5"] for r in successful_results) / len(successful_results)
            avg_precision_10 = sum(r["precision@10"] for r in successful_results) / len(successful_results)
            avg_processing_time = sum(r["processing_time_ms"] for r in successful_results) / len(successful_results)
            
            overall_metrics = {
                "avg_recall@5": round(avg_recall_5, 3),
                "avg_recall@10": round(avg_recall_10, 3),
                "avg_precision@5": round(avg_precision_5, 3),
                "avg_precision@10": round(avg_precision_10, 3),
                "avg_processing_time_ms": round(avg_processing_time, 2),
                "total_queries": len(ground_truth),
                "successful_queries": len(successful_results),
                "success_rate": len(successful_results) / len(ground_truth)
            }
        else:
            overall_metrics = {
                "error": "No successful queries",
                "total_queries": len(ground_truth),
                "successful_queries": 0,
                "success_rate": 0
            }
        
        return {
            "individual_results": results,
            "overall_metrics": overall_metrics
        }
    
    def evaluate_search_coverage(self) -> Dict:
        """Evaluate search coverage across different query types"""
        print("🔍 Evaluating Search Coverage...")
        
        query_types = {
            "exact_match": ["test", "document", "search"],
            "semantic": ["artificial intelligence", "machine learning", "data processing"],
            "compound": ["test document upload", "search functionality testing"],
            "domain_specific": ["RAG system implementation", "document processing pipeline"]
        }
        
        coverage_results = {}
        
        for query_type, queries in query_types.items():
            print(f"  Testing {query_type} queries...")
            type_results = []
            
            for query in queries:
                # Test both RAG and ultra-fast search
                rag_result = self.search_rag_query(query)
                ultra_fast_result = self.search_ultra_fast(query)
                
                rag_success = "error" not in rag_result and len(rag_result.get("chunks", [])) > 0
                ultra_fast_success = "error" not in ultra_fast_result and ultra_fast_result.get("total_found", 0) > 0
                
                type_results.append({
                    "query": query,
                    "rag_success": rag_success,
                    "ultra_fast_success": ultra_fast_success,
                    "rag_results_count": len(rag_result.get("chunks", [])),
                    "ultra_fast_results_count": ultra_fast_result.get("total_found", 0)
                })
                
                time.sleep(0.3)
            
            # Calculate coverage metrics for this type
            total_queries = len(type_results)
            rag_successful = sum(1 for r in type_results if r["rag_success"])
            ultra_fast_successful = sum(1 for r in type_results if r["ultra_fast_success"])
            
            coverage_results[query_type] = {
                "queries": type_results,
                "total_queries": total_queries,
                "rag_coverage": rag_successful / total_queries,
                "ultra_fast_coverage": ultra_fast_successful / total_queries,
                "avg_rag_results": sum(r["rag_results_count"] for r in type_results) / total_queries,
                "avg_ultra_fast_results": sum(r["ultra_fast_results_count"] for r in type_results) / total_queries
            }
        
        return coverage_results
    
    def run_comprehensive_accuracy_evaluation(self) -> Dict:
        """Run complete accuracy evaluation"""
        print("🎯 Starting Comprehensive Accuracy Evaluation")
        print("="*55)
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rag_accuracy": self.evaluate_rag_accuracy(),
            "search_coverage": self.evaluate_search_coverage()
        }
        
        return results

def main():
    evaluator = AccuracyEvaluator()
    results = evaluator.run_comprehensive_accuracy_evaluation()
    
    # Save results
    filename = f"accuracy_evaluation_{int(time.time())}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Print summary
    print("\n📊 ACCURACY SUMMARY:")
    print("="*30)
    
    rag_metrics = results["rag_accuracy"]["overall_metrics"]
    if "avg_recall@10" in rag_metrics:
        print(f"Average Recall@10: {rag_metrics['avg_recall@10']:.3f}")
        print(f"Average Precision@10: {rag_metrics['avg_precision@10']:.3f}")
        print(f"Success Rate: {rag_metrics['success_rate']*100:.1f}%")
        print(f"Avg Processing Time: {rag_metrics['avg_processing_time_ms']:.2f}ms")
    
    print("\n🔍 COVERAGE SUMMARY:")
    print("="*30)
    coverage = results["search_coverage"]
    for query_type, metrics in coverage.items():
        print(f"{query_type.title()}: RAG {metrics['rag_coverage']*100:.1f}%, Ultra-Fast {metrics['ultra_fast_coverage']*100:.1f}%")
    
    return results

if __name__ == "__main__":
    main()
