#!/usr/bin/env python3
"""Test Ultra-Fast Search Fix Locally"""

import requests
import json
import time

def test_ultra_fast_search():
    print("🧪 TESTING ULTRA-FAST SEARCH FIX")
    print("=" * 40)
    
    base_url = "http://localhost:8001"
    
    # Test queries
    test_queries = [
        "artificial intelligence",
        "machine learning", 
        "test",
        "python",
        "senior developer"
    ]
    
    print("Testing Ultra-Fast Search endpoint...")
    total_results = 0
    
    for i, query in enumerate(test_queries, 1):
        try:
            response = requests.post(
                f"{base_url}/api/v2/search/ultra-fast",
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results_count = data.get("total_found", 0)
                total_results += results_count
                
                print(f"  {i}. '{query}' -> {results_count} results ✅")
            else:
                print(f"  {i}. '{query}' -> HTTP {response.status_code} ❌")
                
        except Exception as e:
            print(f"  {i}. '{query}' -> Error: {e} ❌")
    
    print(f"
📊 RESULTS:")
    print(f"   Total results found: {total_results}")
    
    if total_results > 0:
        print(f"   ✅ FIX SUCCESSFUL! Ultra-Fast Search is working.")
    else:
        print(f"   ❌ Fix failed - still returning 0 results.")
        print(f"   Check that:")
        print(f"   - Document search service is running")
        print(f"   - Indexes are in the correct location")
        print(f"   - Configuration has been updated")
    
    return total_results > 0

if __name__ == "__main__":
    test_ultra_fast_search()
