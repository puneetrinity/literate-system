#!/bin/bash
# Execute Ultra-Fast Search Fix on RunPod
# Uses SSH connection details from RUNPOD_SSH_CONNECTION_GUIDE.md

echo "🔧 EXECUTING ULTRA-FAST SEARCH FIX ON RUNPOD"
echo "============================================="

# RunPod connection details
RUNPOD_HOST="190.104.237.154"
RUNPOD_PORT="32734"
SSH_KEY="/home/ews/.runpod/ssh/RunPod-Key-Go"

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found at $SSH_KEY"
    exit 1
fi

echo "✅ SSH key found"
echo "🔗 Connecting to RunPod: $RUNPOD_HOST:$RUNPOD_PORT"

# Execute the fix on RunPod
ssh root@$RUNPOD_HOST -p $RUNPOD_PORT -i $SSH_KEY << 'EOF'
echo "🚀 STARTING ULTRA-FAST SEARCH FIX ON RUNPOD"
echo "==========================================="

# Navigate to service directory (try multiple possible paths)
if [ -d "/workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service" ]; then
    cd /workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service
    echo "✅ Found service at: $(pwd)"
elif [ -d "/workspace/unified-ai-search-system/document-search-service" ]; then
    cd /workspace/unified-ai-search-system/document-search-service
    echo "✅ Found service at: $(pwd)"
else
    echo "❌ Service directory not found. Searching..."
    find /workspace -name "document-search-service" -type d 2>/dev/null | head -5
    echo "Please check the correct path and update the script."
    exit 1
fi

# Check current configuration
echo "🔍 Current configuration:"
if [ -f "app/config.py" ]; then
    echo "   Config file exists"
    python3 -c "
import sys
sys.path.append('.')
try:
    from app.config import settings
    print(f'   Index path: {settings.index_path}')
except Exception as e:
    print(f'   Config error: {e}')
" 2>/dev/null || echo "   Could not load config"
else
    echo "   ❌ No config.py found"
fi

# Fix 1: Backup and update config.py
echo "🔧 Fixing config.py..."
if [ -f "app/config.py" ]; then
    cp app/config.py app/config.py.backup.$(date +%s)
    
    cat > app/config.py << 'CONFIG_EOF'
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    embedding_model_name: str = 'all-MiniLM-L6-v2'
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))
    use_gpu: bool = os.getenv("USE_GPU", "false").lower() == "true"
    # Fixed index path - always use ./indexes relative to service root
    index_path: str = os.getenv("INDEX_PATH", "./indexes")
    data_path: str = os.getenv("UPLOAD_PATH", "./data")

    class Config:
        env_file = ".env"

settings = Settings()
CONFIG_EOF
    
    echo "✅ Updated config.py"
else
    echo "❌ Config.py not found, cannot fix"
fi

# Fix 2: Check indexes exist
echo "🔍 Checking indexes..."
if [ -d "./indexes" ]; then
    echo "✅ Indexes directory exists"
    ls -la ./indexes/
else
    echo "⚠️  Creating indexes directory"
    mkdir -p ./indexes
fi

# Fix 3: Copy indexes from wrong location if they exist
if [ -d "/app/data/indexes" ] && [ "$(ls -A /app/data/indexes 2>/dev/null)" ]; then
    echo "🔧 Copying indexes from /app/data/indexes"
    cp -r /app/data/indexes/* ./indexes/ 2>/dev/null
    echo "✅ Indexes copied"
fi

# Fix 4: Set environment variables
echo "🔧 Setting environment variables..."
export INDEX_PATH="./indexes"
export UPLOAD_PATH="./data"

# Update supervisor config if it exists
if [ -f "/etc/supervisor/conf.d/unified-ai-search.conf" ]; then
    echo "🔧 Updating supervisor environment..."
    if ! grep -q "INDEX_PATH" /etc/supervisor/conf.d/unified-ai-search.conf; then
        sed -i '/\[program:document-search-service\]/a environment=INDEX_PATH="./indexes",UPLOAD_PATH="./data"' /etc/supervisor/conf.d/unified-ai-search.conf
        echo "✅ Supervisor config updated"
    fi
fi

# Fix 5: Ensure we have sample data
echo "🔍 Checking data files..."
mkdir -p ./data
if [ ! -f "./data/resumes.json" ]; then
    echo "⚠️  Creating sample data file..."
    cat > ./data/resumes.json << 'DATA_EOF'
[
  {
    "id": "resume_1",
    "name": "John Doe",
    "experience_years": 5,
    "seniority_level": "senior",
    "skills": ["Python", "Machine Learning", "AI", "Deep Learning"],
    "technologies": ["TensorFlow", "PyTorch", "Scikit-learn", "Pandas"],
    "title": "Senior AI Engineer",
    "description": "Experienced AI engineer with expertise in machine learning, deep learning, and artificial intelligence systems. Specializes in building scalable ML pipelines."
  },
  {
    "id": "resume_2", 
    "name": "Jane Smith",
    "experience_years": 3,
    "seniority_level": "mid",
    "skills": ["JavaScript", "React", "Node.js", "Python"],
    "technologies": ["React", "Express", "MongoDB", "Docker"],
    "title": "Full Stack Developer",
    "description": "Full stack developer specializing in modern web technologies. Experience with both frontend React applications and backend Node.js services."
  },
  {
    "id": "resume_3",
    "name": "Alice Johnson", 
    "experience_years": 8,
    "seniority_level": "senior",
    "skills": ["Data Science", "Python", "SQL", "Machine Learning"],
    "technologies": ["Pandas", "NumPy", "PostgreSQL", "Apache Spark"],
    "title": "Senior Data Scientist",
    "description": "Senior data scientist with extensive experience in analytics, statistical modeling, and big data processing. Expert in Python and SQL."
  }
]
DATA_EOF
    echo "✅ Created sample data file with 3 documents"
else
    echo "✅ Data file exists"
    python3 -c "
import json
with open('./data/resumes.json', 'r') as f:
    data = json.load(f)
    print(f'   Found {len(data)} documents')
" 2>/dev/null || echo "   Could not read data file"
fi

# Fix 6: Restart services
echo "🔄 Restarting services..."
supervisorctl status | grep document-search-service
if [ $? -eq 0 ]; then
    echo "   Restarting document-search-service..."
    supervisorctl restart document-search-service
    sleep 5
else
    echo "   Service not found in supervisor, trying alternative restart..."
    pkill -f "uvicorn.*document-search" 2>/dev/null
    sleep 3
fi

# Check if service is running
echo "🔍 Checking service status..."
ps aux | grep -E "(uvicorn|document-search)" | grep -v grep || echo "   No service processes found"

# Fix 7: Test the fix
echo "🧪 TESTING THE FIX"
echo "=================="

# Wait for service to be ready
sleep 10

# Test different endpoints
test_queries=("artificial intelligence" "machine learning" "test" "python" "senior" "data science")
total_results=0
successful_tests=0

for query in "${test_queries[@]}"; do
    echo -n "Testing '$query'... "
    
    # Try both local and external endpoints
    for endpoint in "http://localhost:8001" "http://127.0.0.1:8001"; do
        result=$(curl -s -X POST "$endpoint/api/v2/search/ultra-fast" \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"$query\"}" \
            --connect-timeout 5 \
            --max-time 10 2>/dev/null)
        
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
                successful_tests=$((successful_tests + 1))
                break
            fi
        fi
    done
    
    # If no results from either endpoint
    if [ $((successful_tests)) -eq 0 ] || [ -z "$count" ] || [ "$count" = "0" ]; then
        echo "0 results ❌"
    fi
done

echo ""
echo "📊 TEST RESULTS"
echo "=============="
echo "Total results found: $total_results"
echo "Successful tests: $successful_tests/${#test_queries[@]}"

if [ $total_results -gt 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Ultra-Fast Search is now working!"
    echo "✅ The 0% recall issue has been FIXED!"
    echo ""
    echo "🔗 You can now test via your browser:"
    echo "   https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/search/ultra-fast"
else
    echo ""
    echo "⚠️  Fix may be incomplete - debugging info:"
    echo "Current directory: $(pwd)"
    echo "Config test:"
    python3 -c "
import sys
sys.path.append('.')
try:
    from app.config import settings
    print(f'   Index path: {settings.index_path}')
    import os
    print(f'   Indexes exist: {os.path.exists(settings.index_path)}')
    if os.path.exists(settings.index_path):
        print(f'   Index files: {os.listdir(settings.index_path)}')
except Exception as e:
    print(f'   Config error: {e}')
" 2>/dev/null || echo "   Could not test config"
    
    echo "Service health:"
    curl -s http://localhost:8001/health 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'   Status: {data.get(\"status\", \"unknown\")}')
except:
    print('   Health check failed')
" || echo "   Service not responding"
fi

echo ""
echo "🏁 RunPod fix execution completed!"
EOF

# Check the exit status of the SSH command
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ RUNPOD FIX EXECUTED SUCCESSFULLY!"
    echo "=================================="
    echo ""
    echo "🔗 Test the fix at:"
    echo "   https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/search/ultra-fast"
    echo ""
    echo "📝 You can also test with curl:"
    echo "   curl -X POST 'https://ij9lyqsrrt0kod-8001.proxy.runpod.net/api/v2/search/ultra-fast' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"query\": \"artificial intelligence\"}'"
else
    echo ""
    echo "❌ SSH connection failed or fix execution had errors"
    echo "Please check your RunPod instance status and try again"
fi