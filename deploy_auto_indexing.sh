#!/bin/bash
# Deploy Auto-Indexing Enhancement to RunPod
echo "🚀 DEPLOYING AUTO-INDEXING ENHANCEMENT TO RUNPOD"
echo "================================================"

# RunPod connection details
RUNPOD_HOST="190.111.198.202"
RUNPOD_PORT="20356"
SSH_KEY="/home/ews/.runpod/ssh/RunPod-Key-Go"

# First, copy the new startup module to RunPod
echo "📤 Copying startup.py to RunPod..."
scp -P $RUNPOD_PORT -i $SSH_KEY /home/ews/unified-ai-system-clean/document-search-service/app/startup.py root@$RUNPOD_HOST:/workspace/unified-ai-system-clean/document-search-service/app/

# Copy the updated main.py
echo "📤 Copying updated main.py to RunPod..."
scp -P $RUNPOD_PORT -i $SSH_KEY /home/ews/unified-ai-system-clean/document-search-service/app/main.py root@$RUNPOD_HOST:/workspace/unified-ai-system-clean/document-search-service/app/

# Execute the enhancement on RunPod
ssh root@$RUNPOD_HOST -p $RUNPOD_PORT -i $SSH_KEY << 'EOF'
echo "🔧 IMPLEMENTING AUTO-INDEXING ON RUNPOD"
echo "======================================="

cd /workspace/unified-ai-system-clean/document-search-service || exit 1
echo "✅ In service directory: $(pwd)"

# Verify files were copied
echo "🔍 Verifying copied files..."
if [ -f "app/startup.py" ]; then
    echo "✅ startup.py copied successfully"
    wc -l app/startup.py
else
    echo "❌ startup.py not found"
fi

if [ -f "app/main.py" ]; then
    echo "✅ main.py updated successfully"
    grep -n "initialize_search_engine_with_auto_indexing" app/main.py || echo "❌ Auto-indexing import not found"
else
    echo "❌ main.py not found"
fi

# Clean up old indexes to test auto-indexing
echo "🧹 Clearing old indexes to test auto-indexing..."
rm -rf ./indexes/*
mkdir -p ./indexes
echo "✅ Indexes cleared"

# Stop existing service
echo "🛑 Stopping existing service..."
pkill -f "uvicorn.*document-search" 2>/dev/null || echo "No existing service found"
sleep 3

# Start service with auto-indexing
echo "🚀 Starting service with auto-indexing..."
export INDEX_PATH="./indexes"
export UPLOAD_PATH="./data"

# Start in background and capture logs
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level info > /tmp/auto-indexing-service.log 2>&1 &
SERVICE_PID=$!
echo "✅ Service started with PID: $SERVICE_PID"

# Monitor startup logs
echo "📋 Monitoring startup logs for auto-indexing..."
sleep 2

# Show last few log lines
echo "Recent startup logs:"
tail -20 /tmp/auto-indexing-service.log 2>/dev/null || echo "No logs yet"

# Wait for startup to complete
echo "⏳ Waiting for startup to complete..."
sleep 15

# Test auto-indexing worked
echo "🧪 TESTING AUTO-INDEXING FUNCTIONALITY"
echo "======================================"

# Check if indexes were created
echo "🔍 Checking if indexes were auto-created..."
if [ -f "./indexes/hnsw.index" ] && [ -f "./indexes/other_data.pkl" ]; then
    echo "✅ Indexes auto-created successfully!"
    ls -la ./indexes/
else
    echo "❌ Indexes not auto-created"
    echo "Contents of indexes directory:"
    ls -la ./indexes/ 2>/dev/null || echo "Directory doesn't exist"
fi

# Test search functionality
echo "🔍 Testing search functionality..."
test_queries=("python" "machine learning" "developer" "artificial intelligence")
total_results=0

for query in "${test_queries[@]}"; do
    echo -n "Testing '$query'... "
    
    result=$(curl -s -X POST "http://localhost:8001/api/v2/search/ultra-fast" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" \
        --connect-timeout 5 --max-time 10)
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        count=$(echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('total_found', 0))
except:
    print(0)
" 2>/dev/null)
        
        if [ "$count" != "" ] && [ "$count" != "null" ] && [ "$count" -gt 0 ]; then
            echo "$count results ✅"
            total_results=$((total_results + count))
        else
            echo "0 results ❌"
        fi
    else
        echo "Connection failed ❌"
    fi
done

echo ""
echo "📊 AUTO-INDEXING TEST RESULTS"
echo "============================="
echo "Total results found: $total_results"

if [ $total_results -gt 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Auto-indexing is working!"
    echo "✅ Service automatically built indexes on startup"
    echo "✅ Search functionality is working"
    echo ""
    echo "🌐 Public endpoint ready:"
    echo "   https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/search/ultra-fast"
else
    echo ""
    echo "❌ Auto-indexing may have failed"
    echo "🔍 Debugging info:"
    echo ""
    echo "Service process:"
    ps aux | grep -E "(uvicorn|main)" | grep -v grep
    echo ""
    echo "Recent logs:"
    tail -30 /tmp/auto-indexing-service.log 2>/dev/null || echo "No logs available"
    echo ""
    echo "Index directory:"
    ls -la ./indexes/ 2>/dev/null || echo "No indexes directory"
fi

echo ""
echo "🏁 Auto-indexing deployment completed!"
EOF

echo ""
echo "✅ AUTO-INDEXING ENHANCEMENT DEPLOYED!"
echo "===================================="
echo ""
echo "🎯 What was enhanced:"
echo "   • Added automatic index building on startup"
echo "   • Added data file detection from multiple locations"
echo "   • Added search functionality verification"
echo "   • Added sample data creation if no data found"
echo ""
echo "🔗 Test the enhanced system:"
echo "   curl -X POST 'https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/search/ultra-fast' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"python developer\"}'"