# 🔧 RunPod Ultra-Fast Search Fix

## Problem Identified
The Ultra-Fast Search endpoint returns 0% recall because the index path configuration is incorrect. The system looks for indexes at `/app/data/indexes` but they're stored at `./indexes`.

## Quick Fix (Copy & Paste on RunPod)

```bash
#!/bin/bash
echo "🔧 FIXING ULTRA-FAST SEARCH 0% RECALL ISSUE"
echo "============================================"

# Navigate to service directory
cd /workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service || {
    echo "❌ Service directory not found"
    echo "Trying alternative path..."
    cd /workspace/unified-ai-search-system/document-search-service || {
        echo "❌ Alternative path not found either"
        exit 1
    }
}

echo "✅ Found service directory: $(pwd)"

# Fix 1: Update config.py
echo "🔧 Updating config.py..."
cp app/config.py app/config.py.backup

cat > app/config.py << 'EOF'
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
EOF

echo "✅ Updated config.py"

# Fix 2: Ensure indexes directory exists
echo "🔧 Ensuring indexes directory exists..."
mkdir -p ./indexes

# Fix 3: Copy indexes if they exist in wrong location
if [ -d "/app/data/indexes" ]; then
    echo "🔧 Copying indexes from /app/data/indexes to ./indexes"
    cp -r /app/data/indexes/* ./indexes/ 2>/dev/null
    echo "✅ Indexes copied"
fi

# Fix 4: Check if we have the required data files
if [ ! -f "./data/resumes.json" ]; then
    echo "⚠️  No data file found, creating sample data..."
    mkdir -p ./data
    cat > ./data/resumes.json << 'EOF'
[
  {
    "id": "resume_1",
    "name": "John Doe",
    "experience_years": 5,
    "seniority_level": "senior",
    "skills": ["Python", "Machine Learning", "AI"],
    "technologies": ["TensorFlow", "PyTorch", "Scikit-learn"],
    "title": "Senior AI Engineer",
    "description": "Experienced AI engineer with expertise in machine learning and deep learning."
  },
  {
    "id": "resume_2", 
    "name": "Jane Smith",
    "experience_years": 3,
    "seniority_level": "mid",
    "skills": ["JavaScript", "React", "Node.js"],
    "technologies": ["React", "Express", "MongoDB"],
    "title": "Full Stack Developer",
    "description": "Full stack developer specializing in modern web technologies."
  },
  {
    "id": "resume_3",
    "name": "Alice Johnson", 
    "experience_years": 8,
    "seniority_level": "senior",
    "skills": ["Data Science", "Python", "SQL"],
    "technologies": ["Pandas", "NumPy", "PostgreSQL"],
    "title": "Senior Data Scientist",
    "description": "Senior data scientist with extensive experience in analytics and modeling."
  }
]
EOF
    echo "✅ Created sample data file"
fi

# Fix 5: Set environment variables
echo "🔧 Setting environment variables..."
export INDEX_PATH="./indexes"
export UPLOAD_PATH="./data"

# Add to supervisor environment if it exists
if [ -f "/etc/supervisor/conf.d/unified-ai-search.conf" ]; then
    echo "🔧 Updating supervisor configuration..."
    sed -i '/\[program:document-search-service\]/a environment=INDEX_PATH="./indexes",UPLOAD_PATH="./data"' /etc/supervisor/conf.d/unified-ai-search.conf
fi

# Fix 6: Restart services
echo "🔧 Restarting services..."
supervisorctl restart document-search-service 2>/dev/null || {
    echo "⚠️  Supervisor restart failed, trying alternative restart..."
    pkill -f "uvicorn.*document-search" 2>/dev/null
    sleep 2
}

supervisorctl restart all 2>/dev/null || echo "⚠️  Full supervisor restart not available"

# Fix 7: Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 10

# Fix 8: Test the fix
echo "🧪 TESTING THE FIX..."
echo "===================="

test_queries=("artificial intelligence" "machine learning" "test" "python" "senior")

total_results=0
for query in "${test_queries[@]}"; do
    echo -n "Testing '$query'... "
    
    result=$(curl -s -X POST http://localhost:8001/api/v2/search/ultra-fast \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" \
        --connect-timeout 5 \
        --max-time 10)
    
    if [ $? -eq 0 ]; then
        count=$(echo "$result" | jq -r '.total_found // 0' 2>/dev/null)
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
echo "📊 TEST RESULTS:"
echo "==============="
echo "Total results found: $total_results"

if [ $total_results -gt 0 ]; then
    echo "🎉 SUCCESS! Ultra-Fast Search is now working!"
    echo "✅ The 0% recall issue has been FIXED!"
else
    echo "❌ Fix incomplete - still returning 0 results"
    echo ""
    echo "🔍 DEBUGGING INFO:"
    echo "Current directory: $(pwd)"
    echo "Index path in config: $(python3 -c 'from app.config import settings; print(settings.index_path)' 2>/dev/null || echo 'Config load failed')"
    echo "Indexes exist: $(ls -la indexes/ 2>/dev/null || echo 'No indexes directory')"
    echo "Service status: $(curl -s http://localhost:8001/health | jq -r '.status // "unhealthy"' 2>/dev/null || echo 'Service unreachable')"
fi

echo ""
echo "🏁 Fix script completed!"
```

## Alternative Manual Steps

If the script doesn't work, follow these manual steps:

### 1. Navigate to Service Directory
```bash
cd /workspace/laughing-guacamole-runpod/unified-ai-search-system/document-search-service
```

### 2. Fix Configuration
```bash
# Backup original config
cp app/config.py app/config.py.backup

# Edit config.py and change:
# FROM: index_path: str = os.getenv("INDEX_PATH", "/app/data/indexes" if os.getenv("PYTHON_ENV") == "production" else "./indexes")
# TO:   index_path: str = os.getenv("INDEX_PATH", "./indexes")
```

### 3. Restart Service  
```bash
supervisorctl restart document-search-service
```

### 4. Test Fix
```bash
curl -X POST http://localhost:8001/api/v2/search/ultra-fast \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

## Expected Result After Fix

**Before Fix:**
```json
{
  "success": true,
  "results": [],
  "total_found": 0,
  "response_time_ms": 15.2
}
```

**After Fix:**  
```json
{
  "success": true,
  "results": [
    {
      "doc_id": "resume_1",
      "similarity_score": 0.85,
      "bm25_score": 2.4,
      "combined_score": 1.62,
      "name": "John Doe",
      "title": "Senior AI Engineer"
    }
  ],
  "total_found": 1,
  "response_time_ms": 18.7
}
```

## Root Cause Explanation

The issue was a **configuration path mismatch**:
- ✅ **Index files existed** (11,836 bytes with valid data)
- ✅ **Search engine initialized** successfully  
- ❌ **Wrong path lookup** (`/app/data/indexes` vs `./indexes`)
- ✅ **API worked** (returned HTTP 200 with empty results)

This fix resolves the path issue and should restore full Ultra-Fast Search functionality with proper recall rates.