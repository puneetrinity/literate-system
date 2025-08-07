#!/bin/bash
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
curl -X POST http://localhost:8001/api/v2/search/ultra-fast   -H "Content-Type: application/json"   -d '{"query": "test"}' | jq '.'

echo "✅ Fix applied! Ultra-Fast Search should now return results."
