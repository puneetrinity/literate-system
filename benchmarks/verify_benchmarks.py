#!/usr/bin/env python3
"""
Verification script for Ultra-Fast Search benchmark results
"""

import json
import os
from pathlib import Path

def verify_benchmark_files():
    """Verify all benchmark files are present and valid"""
    
    expected_files = {
        'ultra_fast_search_benchmark_20250729_064007.json': 'Performance benchmark results',
        'accuracy_evaluation_1753771414.json': 'Accuracy evaluation results', 
        'memory_efficiency_analysis.json': 'Memory analysis results',
        'ultra_fast_search_comprehensive_report_20250729_064520.md': 'Comprehensive report',
        'comprehensive_ultra_fast_benchmark.py': 'Main benchmark script',
        'accuracy_evaluation.py': 'Accuracy evaluation script',
        'memory_analysis.py': 'Memory analysis script',
        'comprehensive_benchmark_report.py': 'Report generator script',
        'README.md': 'Documentation'
    }
    
    print("🔍 Verifying Ultra-Fast Search Benchmark Files")
    print("=" * 50)
    
    all_valid = True
    total_size = 0
    
    for filename, description in expected_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            total_size += size
            size_kb = size / 1024
            
            # Validate JSON files
            if filename.endswith('.json'):
                try:
                    with open(filename, 'r') as f:
                        data = json.load(f)
                    print(f"✅ {filename:<45} ({size_kb:.1f}KB) - Valid JSON")
                except json.JSONDecodeError:
                    print(f"❌ {filename:<45} ({size_kb:.1f}KB) - Invalid JSON")
                    all_valid = False
            else:
                print(f"✅ {filename:<45} ({size_kb:.1f}KB) - Present")
        else:
            print(f"❌ {filename:<45} - Missing")
            all_valid = False
    
    print(f"\n📊 Summary:")
    print(f"Total files: {len([f for f in expected_files.keys() if os.path.exists(f)])}/{len(expected_files)}")
    print(f"Total size: {total_size/1024:.1f}KB")
    print(f"Status: {'✅ All files valid' if all_valid else '❌ Some files missing/invalid'}")
    
    return all_valid

def extract_key_metrics():
    """Extract and display key metrics from benchmark results"""
    
    print(f"\n🎯 Key Performance Metrics")
    print("=" * 30)
    
    # Performance metrics
    try:
        with open('ultra_fast_search_benchmark_20250729_064007.json', 'r') as f:
            perf_data = json.load(f)
        
        scalability = perf_data.get('scalability_benchmark', {})
        max_qps = 0
        best_latency = float('inf')
        
        for level, result in scalability.items():
            qps = result.get('queries_per_second', 0)
            p99 = result.get('latency_stats', {}).get('p99_ms', float('inf'))
            if qps > max_qps:
                max_qps = qps
            if p99 < best_latency:
                best_latency = p99
        
        print(f"Peak QPS: {max_qps:.0f}")
        print(f"Best P99 Latency: {best_latency:.1f}ms")
        
    except Exception as e:
        print(f"❌ Could not extract performance metrics: {e}")
    
    # Accuracy metrics
    try:
        with open('accuracy_evaluation_1753771414.json', 'r') as f:
            acc_data = json.load(f)
        
        rag_metrics = acc_data.get('rag_accuracy', {}).get('overall_metrics', {})
        recall = rag_metrics.get('avg_recall@10', 0) * 100
        precision = rag_metrics.get('avg_precision@10', 0) * 100
        success_rate = rag_metrics.get('success_rate', 0) * 100
        
        print(f"Recall@10: {recall:.1f}%")
        print(f"Precision@10: {precision:.1f}%") 
        print(f"Success Rate: {success_rate:.1f}%")
        
    except Exception as e:
        print(f"❌ Could not extract accuracy metrics: {e}")

def main():
    """Main verification function"""
    
    # Change to benchmarks directory
    benchmark_dir = Path(__file__).parent
    os.chdir(benchmark_dir)
    
    # Verify files
    files_valid = verify_benchmark_files()
    
    if files_valid:
        # Extract metrics
        extract_key_metrics()
        
        print(f"\n🎉 Benchmark verification complete!")
        print(f"📁 All files saved in: {benchmark_dir.absolute()}")
        print(f"📖 Read README.md for detailed information")
    else:
        print(f"\n⚠️  Some benchmark files are missing or invalid")
        print(f"📁 Check directory: {benchmark_dir.absolute()}")

if __name__ == "__main__":
    main()