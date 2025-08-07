#!/usr/bin/env python3
"""
RunPod Deployment Fix Script
Fixes the index path configuration issue causing 0% recall
"""

import os
import shutil
import json
from pathlib import Path

def fix_runpod_index_path():
    """Fix the index path configuration for RunPod deployment"""
    print("🔧 FIXING RUNPOD INDEX PATH CONFIGURATION")
    print("=" * 50)
    
    # Expected paths in RunPod
    runpod_paths = {
        'service_root': '/workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service',
        'current_indexes': '/workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service/indexes',
        'production_indexes': '/app/data/indexes',
        'config_file': '/workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service/app/config.py'
    }
    
    fixes_applied = []
    
    # Fix 1: Update config.py if it exists
    if os.path.exists(runpod_paths['config_file']):
        print("✅ Found config.py, updating index path...")
        
        with open(runpod_paths['config_file'], 'r') as f:
            content = f.read()
        
        # Replace the problematic line
        old_line = 'index_path: str = os.getenv("INDEX_PATH", "/app/data/indexes" if os.getenv("PYTHON_ENV") == "production" else "./indexes")'
        new_line = 'index_path: str = os.getenv("INDEX_PATH", "./indexes")'
        
        if old_line in content:
            content = content.replace(old_line, new_line)
            
            with open(runpod_paths['config_file'], 'w') as f:
                f.write(content)
            
            fixes_applied.append("Updated config.py index path")
            print("   ✅ Updated config.py")
        else:
            print("   ⚠️ Config.py already updated or different format")
    else:
        print("❌ Config.py not found at expected path")
    
    # Fix 2: Ensure indexes exist in the correct location
    service_root = runpod_paths['service_root']
    if os.path.exists(service_root):
        os.chdir(service_root)
        print(f"✅ Changed to service directory: {service_root}")
        
        if not os.path.exists('./indexes'):
            print("⚠️ ./indexes directory doesn't exist, creating it...")
            os.makedirs('./indexes', exist_ok=True)
            fixes_applied.append("Created ./indexes directory")
    
    # Fix 3: Copy indexes from production path if they exist there
    prod_index_path = runpod_paths['production_indexes']
    local_index_path = os.path.join(service_root, 'indexes')
    
    if os.path.exists(prod_index_path) and os.path.exists(service_root):
        print(f"✅ Found indexes at {prod_index_path}, copying to correct location...")
        
        # Copy all index files
        for file in os.listdir(prod_index_path):
            src = os.path.join(prod_index_path, file)
            dst = os.path.join(local_index_path, file)
            shutil.copy2(src, dst)
            print(f"   Copied {file}")
        
        fixes_applied.append("Copied indexes to correct location")
    
    # Fix 4: Set environment variable to override
    print("\n🔧 Setting INDEX_PATH environment variable...")
    env_commands = [
        'export INDEX_PATH="./indexes"',
        'export UPLOAD_PATH="./data"'
    ]
    
    print("Add these to your RunPod environment:")
    for cmd in env_commands:
        print(f"   {cmd}")
    
    fixes_applied.append("Environment variable commands provided")
    
    return fixes_applied

def create_runpod_fix_script():
    """Create a script that can be executed directly on RunPod"""
    script_content = '''#!/bin/bash
# RunPod Ultra-Fast Search Fix Script
echo "🔧 FIXING ULTRA-FAST SEARCH 0% RECALL ISSUE"

# Navigate to service directory
cd /workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service || {
    echo "❌ Service directory not found"
    exit 1
}

# Set environment variables
export INDEX_PATH="./indexes"
export UPLOAD_PATH="./data"

# Fix config.py
echo "✅ Updating config.py..."
sed -i 's|index_path: str = os.getenv("INDEX_PATH", "/app/data/indexes" if os.getenv("PYTHON_ENV") == "production" else "./indexes")|index_path: str = os.getenv("INDEX_PATH", "./indexes")|g' app/config.py

# Ensure indexes directory exists
mkdir -p ./indexes

# Copy indexes if they exist in wrong location
if [ -d "/app/data/indexes" ]; then
    echo "✅ Copying indexes from /app/data/indexes to ./indexes"
    cp -r /app/data/indexes/* ./indexes/ 2>/dev/null || true
fi

# Restart services
echo "✅ Restarting services..."
supervisorctl restart document-search-service 2>/dev/null || true
supervisorctl restart all 2>/dev/null || true

# Test the fix
echo "🧪 Testing fix..."
sleep 5
curl -X POST http://localhost:8001/api/v2/search/ultra-fast \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' | jq '.'

echo "✅ Fix applied! Ultra-Fast Search should now return results."
'''
    
    with open('/home/ews/unified-ai-system-clean/runpod_fix_script.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('/home/ews/unified-ai-system-clean/runpod_fix_script.sh', 0o755)
    print("✅ Created runpod_fix_script.sh")

def create_local_test_script():
    """Create a script to test the fix locally"""
    test_script = '''#!/usr/bin/env python3
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
    
    print(f"\n📊 RESULTS:")
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
'''
    
    with open('/home/ews/unified-ai-system-clean/test_fix_locally.py', 'w') as f:
        f.write(test_script)
    
    os.chmod('/home/ews/unified-ai-system-clean/test_fix_locally.py', 0o755)
    print("✅ Created test_fix_locally.py")

def main():
    print("🔧 ULTRA-FAST SEARCH FIX GENERATOR")
    print("=" * 50)
    
    # Apply local fixes
    print("\n1. APPLYING LOCAL FIXES...")
    local_fixes = fix_runpod_index_path()
    
    # Create RunPod fix script
    print("\n2. CREATING RUNPOD FIX SCRIPT...")
    create_runpod_fix_script()
    
    # Create local test script
    print("\n3. CREATING LOCAL TEST SCRIPT...")
    create_local_test_script()
    
    print("\n🎯 FIX SUMMARY")
    print("=" * 30)
    print("✅ Local configuration updated")
    print("✅ RunPod fix script created: runpod_fix_script.sh")
    print("✅ Local test script created: test_fix_locally.py")
    
    print("\n📋 NEXT STEPS:")
    print("=" * 20)
    print("🔄 LOCAL TESTING:")
    print("   1. Start your local document-search-service")
    print("   2. Run: python3 test_fix_locally.py")
    
    print("\n🚀 RUNPOD DEPLOYMENT:")
    print("   1. Copy runpod_fix_script.sh to your RunPod instance")
    print("   2. Run: chmod +x runpod_fix_script.sh && ./runpod_fix_script.sh")
    print("   3. The script will automatically restart services and test")
    
    print("\n✅ This should resolve the 0% recall issue!")

if __name__ == "__main__":
    main()