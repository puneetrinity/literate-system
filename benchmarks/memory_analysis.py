#\!/usr/bin/env python3
"""
Memory and Index Efficiency Analysis for Ultra-Fast Search
"""

import os
import json
import requests
import psutil
from pathlib import Path

def analyze_index_sizes():
    """Analyze index file sizes and memory efficiency"""
    
    # Check index directory
    index_dir = Path("document-search-service/indexes")
    
    if not index_dir.exists():
        return {"error": "Index directory not found"}
    
    index_files = {}
    total_size = 0
    
    for file_path in index_dir.rglob("*"):
        if file_path.is_file():
            size_bytes = file_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            index_files[str(file_path)] = {
                "size_bytes": size_bytes,
                "size_mb": round(size_mb, 2)
            }
            total_size += size_bytes
    
    return {
        "total_index_size_mb": round(total_size / (1024 * 1024), 2),
        "total_index_size_gb": round(total_size / (1024 * 1024 * 1024), 3),
        "index_files": index_files,
        "file_count": len(index_files)
    }

def get_document_stats():
    """Get document statistics from the RAG system"""
    try:
        response = requests.get("http://localhost:8001/api/v2/rag/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Could not fetch document stats"}
    except Exception as e:
        return {"error": str(e)}

def analyze_memory_efficiency():
    """Analyze memory efficiency metrics"""
    
    # Get current process memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Get system memory
    system_memory = psutil.virtual_memory()
    
    # Get index sizes
    index_analysis = analyze_index_sizes()
    
    # Get document stats
    doc_stats = get_document_stats()
    
    # Calculate efficiency metrics
    index_size_mb = index_analysis.get("total_index_size_mb", 0)
    memory_used_mb = memory_info.rss / (1024 * 1024)
    
    analysis = {
        "memory_usage": {
            "process_rss_mb": round(memory_used_mb, 2),
            "process_vms_mb": round(memory_info.vms / (1024 * 1024), 2),
            "system_total_gb": round(system_memory.total / (1024**3), 2),
            "system_available_gb": round(system_memory.available / (1024**3), 2),
            "system_used_percent": system_memory.percent
        },
        "index_efficiency": index_analysis,
        "document_stats": doc_stats,
        "efficiency_metrics": {
            "memory_per_document_kb": 0,
            "index_size_per_document_kb": 0,
            "compression_ratio": 0
        }
    }
    
    # Calculate per-document metrics if we have document count
    if isinstance(doc_stats, dict) and "document_count" in doc_stats:
        doc_count = doc_stats["document_count"]
        if doc_count > 0:
            analysis["efficiency_metrics"]["memory_per_document_kb"] = round((memory_used_mb * 1024) / doc_count, 2)
            analysis["efficiency_metrics"]["index_size_per_document_kb"] = round((index_size_mb * 1024) / doc_count, 2)
    
    return analysis

def main():
    print("🧠 Memory and Index Efficiency Analysis")
    print("="*50)
    
    analysis = analyze_memory_efficiency()
    
    # Save results
    with open("memory_efficiency_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    print("\n📊 MEMORY USAGE:")
    memory = analysis["memory_usage"]
    print(f"Process Memory (RSS): {memory['process_rss_mb']}MB")
    print(f"Process Memory (VMS): {memory['process_vms_mb']}MB")
    print(f"System Memory Usage: {memory['system_used_percent']}%")
    
    print("\n💾 INDEX EFFICIENCY:")
    index_info = analysis["index_efficiency"]
    if "total_index_size_mb" in index_info:
        print(f"Total Index Size: {index_info['total_index_size_mb']}MB")
        print(f"Index Files: {index_info['file_count']}")
        
        for file_path, info in index_info["index_files"].items():
            print(f"  {os.path.basename(file_path)}: {info['size_mb']}MB")
    
    print("\n⚡ EFFICIENCY METRICS:")
    metrics = analysis["efficiency_metrics"]
    for metric, value in metrics.items():
        if value > 0:
            print(f"{metric.replace('_', ' ').title()}: {value}")
    
    print(f"\n💾 Results saved to: memory_efficiency_analysis.json")
    
    return analysis

if __name__ == "__main__":
    main()
