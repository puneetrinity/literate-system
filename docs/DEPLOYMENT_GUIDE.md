# 🚀 Unified AI System - Deployment Guide

## 📖 Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Local Development Setup](#local-development-setup)
4. [Docker Deployment](#docker-deployment)
5. [RunPod Cloud Deployment](#runpod-cloud-deployment)
6. [Production Deployment](#production-deployment)
7. [Environment Configuration](#environment-configuration)
8. [Service Monitoring](#service-monitoring)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Unified AI System consists of multiple interconnected services:

- **AI Chat Service** (Port 8003): LangGraph orchestration and multi-agent workflows
- **Document Search Service** (Port 8001): Ultra-fast document search with RAG
- **Redis Cache** (Port 6379): Distributed caching and session storage
- **Ollama** (Port 11434): Local AI model serving
- **Nginx** (Port 8000): Reverse proxy and load balancing

## 🖥️ System Requirements

### Minimum Requirements (Development)
```yaml
CPU: 4 cores (Intel i5 or AMD Ryzen 5)
RAM: 8GB
Storage: 20GB available space
Network: Broadband internet connection
OS: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10+
```

### Recommended Requirements (Production)
```yaml
CPU: 8+ cores (Intel i7/Xeon or AMD Ryzen 7/EPYC)
RAM: 16GB+ (32GB recommended)
Storage: 100GB+ SSD
Network: High-speed internet with low latency
OS: Linux (Ubuntu 22.04 LTS recommended)
```

### RunPod Requirements (Cloud GPU)
```yaml
GPU: RTX 4090, A100, or similar (24GB+ VRAM)
CPU: 8+ cores
RAM: 32GB+
Storage: 100GB+ NVMe SSD
Network: High-speed cloud networking
```

## 🛠️ Local Development Setup

### Prerequisites Installation

#### 1. Install Docker and Docker Compose

**Ubuntu/Debian:**
```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or use Homebrew
brew install --cask docker
```

**Windows:**
```powershell
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or use Chocolatey
choco install docker-desktop
```

#### 2. Install Python 3.10+

**Ubuntu/Debian:**
```bash
sudo apt install python3.10 python3.10-pip python3.10-venv
```

**macOS:**
```bash
brew install python@3.10
```

**Windows:**
```powershell
# Download from python.org or use Chocolatey
choco install python310
```

#### 3. Install Git and Clone Repository

```bash
# Install Git
sudo apt install git  # Ubuntu/Debian
brew install git       # macOS
choco install git      # Windows

# Clone repository
git clone https://github.com/your-org/unified-ai-system-clean.git
cd unified-ai-system-clean
```

### Environment Configuration

#### 1. Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your preferred editor
nano .env
```

#### 2. Basic Environment Variables

```bash
# .env file
# ===============================
# ENVIRONMENT CONFIGURATION
# ===============================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# ===============================
# SERVICE PORTS
# ===============================
AI_CHAT_PORT=8003
DOCUMENT_SEARCH_PORT=8001
REDIS_PORT=6379
OLLAMA_PORT=11434
NGINX_PORT=8000

# ===============================
# DATABASE & CACHE
# ===============================
REDIS_URL=redis://localhost:6379
REDIS_MAX_CONNECTIONS=20
REDIS_TIMEOUT=5

# ===============================
# AI MODEL CONFIGURATION
# ===============================
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=phi3:mini
FALLBACK_MODEL=llama3.2:latest
MODEL_TIMEOUT=60
MAX_CONCURRENT_MODELS=3

# ===============================
# API KEYS (Optional but Recommended)
# ===============================
BRAVE_API_KEY=your_brave_search_api_key_here
SCRAPINGBEE_API_KEY=your_scrapingbee_api_key_here

# ===============================
# COST & PERFORMANCE
# ===============================
DEFAULT_MONTHLY_BUDGET=50.0
COST_TRACKING_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
TARGET_RESPONSE_TIME=2.5

# ===============================
# SECURITY
# ===============================
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
ENABLE_RATE_LIMITING=false
ENABLE_AUTHENTICATION=false

# ===============================
# ADVANCED FEATURES
# ===============================
ENABLE_MEMORY_SYSTEM=false
ENABLE_CLICKHOUSE=false
ENABLE_ROUTER_MIGRATION=true
USE_GPU=false
```

### Quick Start Commands

#### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Clean restart
docker-compose down -v && docker-compose up --build
```

#### Option 2: Manual Development Setup

**Terminal 1 - Redis:**
```bash
# Install and start Redis
sudo apt install redis-server
redis-server --port 6379
```

**Terminal 2 - Ollama:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Download models (new terminal)
ollama pull phi3:mini
ollama pull llama3.2:latest
```

**Terminal 3 - Document Search Service:**
```bash
cd document-search-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 4 - AI Chat Service:**
```bash
cd ai-chat-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Verification

```bash
# Check service health
curl http://localhost:8003/health  # AI Chat Service
curl http://localhost:8001/health  # Document Search Service

# Test basic functionality
curl -X POST "http://localhost:8003/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, test the system"}'

curl -X POST "http://localhost:8001/api/v2/search/ultra-fast" \
  -H "Content-Type: application/json" \
  -d '{"query": "test document search"}'
```

## 🐳 Docker Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: unified-redis-prod
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - unified-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  ollama:
    image: ollama/ollama:latest
    container_name: unified-ollama-prod
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - unified-network
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_KEEP_ALIVE=24h
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  document-search:
    build:
      context: ./document-search-service
      dockerfile: Dockerfile.optimized
      args:
        - BUILDKIT_INLINE_CACHE=1
    container_name: unified-document-search-prod
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - OLLAMA_HOST=http://ollama:11434
      - ENVIRONMENT=production
      - DEBUG=false
      - USE_GPU=${USE_GPU:-false}
      - EMBEDDING_DIM=384
    volumes:
      - ./document-search-service/data:/app/data
      - ./document-search-service/indexes:/app/indexes
      - document_logs:/app/logs
    networks:
      - unified-network
    depends_on:
      redis:
        condition: service_healthy
      ollama:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  ai-chat:
    build:
      context: ./ai-chat-service
      dockerfile: Dockerfile.optimized
      args:
        - BUILDKIT_INLINE_CACHE=1
    container_name: unified-ai-chat-prod
    ports:
      - "8003:8003"
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - OLLAMA_HOST=http://ollama:11434
      - DOCUMENT_SEARCH_URL=http://document-search:8001
      - ENVIRONMENT=production
      - DEBUG=false
      - BRAVE_API_KEY=${BRAVE_API_KEY}
      - SCRAPINGBEE_API_KEY=${SCRAPINGBEE_API_KEY}
      - DEFAULT_MONTHLY_BUDGET=${DEFAULT_MONTHLY_BUDGET:-100.0}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-200}
      - TARGET_RESPONSE_TIME=${TARGET_RESPONSE_TIME:-2.0}
      - ENABLE_RATE_LIMITING=true
      - ENABLE_AUTHENTICATION=${ENABLE_AUTHENTICATION:-false}
    volumes:
      - ./ai-chat-service/data:/app/data
      - chat_logs:/app/logs
    networks:
      - unified-network
    depends_on:
      redis:
        condition: service_healthy
      ollama:
        condition: service_healthy
      document-search:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 15s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 3G

  nginx:
    image: nginx:alpine
    container_name: unified-nginx-prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./config/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    networks:
      - unified-network
    depends_on:
      - ai-chat
      - document-search
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
  ollama_data:
  document_logs:
  chat_logs:
  nginx_logs:

networks:
  unified-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Production Environment File

Create `.env.prod`:

```bash
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Security
REDIS_PASSWORD=your_secure_redis_password_here
ENABLE_RATE_LIMITING=true
ENABLE_AUTHENTICATION=true
JWT_SECRET_KEY=your_jwt_secret_key_here

# API Keys (Required for production)
BRAVE_API_KEY=your_brave_api_key
SCRAPINGBEE_API_KEY=your_scrapingbee_api_key

# Performance
DEFAULT_MONTHLY_BUDGET=500.0
RATE_LIMIT_PER_MINUTE=200
TARGET_RESPONSE_TIME=1.5
USE_GPU=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# SSL (if using HTTPS)
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

### Deploy to Production

```bash
# Deploy with production config
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale ai-chat=3

# Update services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Backup data
docker run --rm -v unified-ai-system-clean_redis_data:/data \
  -v $(pwd)/backup:/backup alpine \
  tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## ☁️ RunPod Cloud Deployment

### RunPod Template Configuration

Create `runpod-template.json`:

```json
{
  "name": "Unified AI System",
  "image": "ubuntu:22.04",
  "containerDiskInGb": 100,
  "volumeInGb": 200,
  "volumeMountPath": "/workspace",
  "ports": "8000/http,8001/http,8003/http,6379/tcp,11434/http",
  "env": [
    {
      "key": "ENVIRONMENT",
      "value": "production"
    },
    {
      "key": "USE_GPU", 
      "value": "true"
    },
    {
      "key": "CUDA_VISIBLE_DEVICES",
      "value": "0"
    }
  ],
  "dockerArgs": "--shm-size=2g --ulimit memlock=-1 --ulimit stack=67108864",
  "startScript": "#!/bin/bash\ncd /workspace && ./scripts/runpod-startup.sh"
}
```

### RunPod Startup Script

Create `scripts/runpod-startup.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Unified AI System on RunPod..."

# Update system
apt-get update && apt-get install -y \
    curl \
    git \
    python3.10 \
    python3.10-pip \
    python3.10-venv \
    docker.io \
    docker-compose \
    nginx \
    redis-server \
    supervisor

# Install Ollama with GPU support
curl -fsSL https://ollama.ai/install.sh | sh

# Create application directory
cd /workspace
if [ ! -d "unified-ai-system-clean" ]; then
    git clone https://github.com/your-org/unified-ai-system-clean.git
fi
cd unified-ai-system-clean

# Create RunPod environment file
cat > .env.runpod << EOF
ENVIRONMENT=production
DEBUG=false
USE_GPU=true
CUDA_VISIBLE_DEVICES=0

# Services
REDIS_URL=redis://localhost:6379
OLLAMA_HOST=http://localhost:11434
AI_CHAT_PORT=8003
DOCUMENT_SEARCH_PORT=8001

# API Keys
BRAVE_API_KEY=${BRAVE_API_KEY:-}
SCRAPINGBEE_API_KEY=${SCRAPINGBEE_API_KEY:-}

# Performance
DEFAULT_MONTHLY_BUDGET=1000.0
RATE_LIMIT_PER_MINUTE=500
TARGET_RESPONSE_TIME=1.0
EMBEDDING_DIM=384

# GPU Configuration
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=4
OLLAMA_FLASH_ATTENTION=1
EOF

# Create supervisor configuration
cat > /etc/supervisor/conf.d/unified-ai.conf << 'EOF'
[program:redis]
command=redis-server --port 6379 --daemonize no
autostart=true
autorestart=true
user=root
priority=100
stdout_logfile=/var/log/redis.log
stderr_logfile=/var/log/redis.log

[program:ollama]
command=ollama serve
environment=OLLAMA_HOST=0.0.0.0,CUDA_VISIBLE_DEVICES=0
autostart=true
autorestart=true
user=root
priority=200
stdout_logfile=/var/log/ollama.log
stderr_logfile=/var/log/ollama.log

[program:document-search]
command=/workspace/unified-ai-system-clean/scripts/start-document-search.sh
directory=/workspace/unified-ai-system-clean/document-search-service
autostart=true
autorestart=true
user=root
priority=300
stdout_logfile=/var/log/document-search.log
stderr_logfile=/var/log/document-search.log

[program:ai-chat]
command=/workspace/unified-ai-system-clean/scripts/start-ai-chat.sh
directory=/workspace/unified-ai-system-clean/ai-chat-service
autostart=true
autorestart=true
user=root
priority=400
stdout_logfile=/var/log/ai-chat.log
stderr_logfile=/var/log/ai-chat.log
EOF

# Create service startup scripts
mkdir -p scripts

cat > scripts/start-document-search.sh << 'EOF'
#!/bin/bash
cd /workspace/unified-ai-system-clean/document-search-service
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
EOF

cat > scripts/start-ai-chat.sh << 'EOF'
#!/bin/bash
cd /workspace/unified-ai-system-clean/ai-chat-service
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8003
EOF

chmod +x scripts/*.sh

# Install Python dependencies
cd document-search-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

cd ../ai-chat-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

cd ..

# Wait for Ollama to start and download models
echo "📥 Downloading AI models..."
sleep 10
ollama pull phi3:mini
ollama pull llama3.2:latest

# Start all services
supervisord -c /etc/supervisor/supervisord.conf

echo "✅ Unified AI System started successfully!"
echo "🔗 Access points:"
echo "   - AI Chat Service: https://${RUNPOD_POD_ID}-8003.proxy.runpod.net"
echo "   - Document Search: https://${RUNPOD_POD_ID}-8001.proxy.runpod.net"
echo "   - Health Check: https://${RUNPOD_POD_ID}-8003.proxy.runpod.net/health"

# Keep container running
tail -f /var/log/supervisor/supervisord.log
```

### RunPod Deployment Commands

```bash
# Deploy using RunPod API
curl -X POST "https://api.runpod.ai/v2/pods" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @runpod-template.json

# Or use RunPod CLI
runpod create pod \
  --name "unified-ai-system" \
  --image-name "ubuntu:22.04" \
  --gpu-type "RTX4090" \
  --container-disk-in-gb 100 \
  --volume-in-gb 200 \
  --ports "8000/http,8001/http,8003/http"
```

### RunPod Monitoring

```bash
# Check pod status
runpod get pod POD_ID

# Connect via SSH
runpod connect POD_ID

# View logs
runpod logs POD_ID

# Stop pod
runpod stop POD_ID
```

## 🏭 Production Deployment

### Load Balancing with Nginx

Create `config/nginx.prod.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream ai_chat_backend {
        least_conn;
        server ai-chat-1:8003 max_fails=3 fail_timeout=30s;
        server ai-chat-2:8003 max_fails=3 fail_timeout=30s;
        server ai-chat-3:8003 max_fails=3 fail_timeout=30s;
    }

    upstream document_search_backend {
        least_conn;
        server document-search-1:8001 max_fails=3 fail_timeout=30s;
        server document-search-2:8001 max_fails=3 fail_timeout=30s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=chat:10m rate=5r/s;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # AI Chat Service
        location /api/v1/chat/ {
            limit_req zone=chat burst=10 nodelay;
            proxy_pass http://ai_chat_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        # AI Research & Search
        location /api/v1/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://ai_chat_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Document Search Service
        location /api/v2/ {
            limit_req zone=api burst=30 nodelay;
            proxy_pass http://document_search_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support for streaming
        location /ws {
            proxy_pass http://ai_chat_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public";
        }

        # API Documentation
        location /docs {
            proxy_pass http://ai_chat_backend;
            proxy_set_header Host $host;
        }
    }
}
```

### Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unified-ai-system
  labels:
    app: unified-ai-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: unified-ai-system
  template:
    metadata:
      labels:
        app: unified-ai-system
    spec:
      containers:
      - name: ai-chat
        image: your-registry/unified-ai-chat:latest
        ports:
        - containerPort: 8003
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8003
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8003
          initialDelaySeconds: 30
          periodSeconds: 10

      - name: document-search
        image: your-registry/unified-document-search:latest
        ports:
        - containerPort: 8001
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: USE_GPU
          value: "true"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
            nvidia.com/gpu: 1
          limits:
            memory: "3Gi"
            cpu: "1500m"
            nvidia.com/gpu: 1
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 15
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: unified-ai-service
spec:
  selector:
    app: unified-ai-system
  ports:
  - name: ai-chat
    port: 8003
    targetPort: 8003
  - name: document-search
    port: 8001
    targetPort: 8001
  type: LoadBalancer
```

## ⚙️ Environment Configuration

### Complete Environment Variables Reference

```bash
# ===============================
# CORE SYSTEM CONFIGURATION
# ===============================
ENVIRONMENT=development                    # development, staging, production
DEBUG=true                                # Enable debug logging
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR, CRITICAL
APP_NAME="Unified AI System"             # Application name

# ===============================
# SERVICE NETWORK CONFIGURATION
# ===============================
AI_CHAT_HOST=0.0.0.0                    # AI Chat service host
AI_CHAT_PORT=8003                       # AI Chat service port
DOCUMENT_SEARCH_HOST=0.0.0.0            # Document search host
DOCUMENT_SEARCH_PORT=8001               # Document search port
NGINX_PORT=8000                         # Nginx reverse proxy port

# ===============================
# DATABASE AND CACHE
# ===============================
REDIS_URL=redis://localhost:6379        # Redis connection URL
REDIS_PASSWORD=                         # Redis password (optional)
REDIS_MAX_CONNECTIONS=20                # Max Redis connections
REDIS_TIMEOUT=5                         # Redis timeout in seconds
REDIS_DB=0                              # Redis database number

# Cache TTL Settings (seconds)
CACHE_TTL_DEFAULT=3600                  # Default cache TTL (1 hour)
CACHE_TTL_ROUTING=300                   # Routing cache TTL (5 minutes)
CACHE_TTL_RESPONSES=1800                # Response cache TTL (30 minutes)

# ===============================
# AI MODEL CONFIGURATION
# ===============================
OLLAMA_HOST=http://localhost:11434      # Ollama service URL
OLLAMA_TIMEOUT=60                       # Ollama request timeout
OLLAMA_MAX_RETRIES=3                    # Max retry attempts
OLLAMA_KEEP_ALIVE=5m                    # Model keep-alive duration

# Model Selection
DEFAULT_MODEL=phi3:mini                 # Default AI model
FALLBACK_MODEL=llama3.2:latest          # Fallback AI model
MAX_CONCURRENT_MODELS=3                 # Max models in memory
MODEL_MEMORY_THRESHOLD=0.8              # Memory usage threshold

# Model Performance
OLLAMA_NUM_PARALLEL=2                   # Parallel requests
OLLAMA_MAX_LOADED_MODELS=4              # Max loaded models
OLLAMA_FLASH_ATTENTION=1                # Enable flash attention (GPU)

# ===============================
# API KEYS AND EXTERNAL SERVICES
# ===============================
BRAVE_API_KEY=                          # Brave Search API key
SCRAPINGBEE_API_KEY=                    # ScrapingBee API key
OPENAI_API_KEY=                         # OpenAI API key (optional)
ANTHROPIC_API_KEY=                      # Anthropic API key (optional)

# ===============================
# COST MANAGEMENT
# ===============================
COST_TRACKING_ENABLED=true              # Enable cost tracking
DEFAULT_MONTHLY_BUDGET=50.0             # Default monthly budget (INR)
COST_PER_API_CALL=0.008                # Cost per API call (INR)
BUDGET_WARNING_THRESHOLD=0.8            # Budget warning threshold
BUDGET_HARD_LIMIT=true                  # Enforce hard budget limits

# ===============================
# RATE LIMITING AND THROTTLING
# ===============================
ENABLE_RATE_LIMITING=false              # Enable rate limiting
RATE_LIMIT_PER_MINUTE=60               # Requests per minute
RATE_LIMIT_BURST=10                    # Burst capacity
RATE_LIMIT_STORAGE=redis                # Rate limit storage backend

# Quality-based rate limits
RATE_LIMIT_MINIMAL=120                  # Minimal quality requests/min
RATE_LIMIT_BALANCED=60                  # Balanced quality requests/min
RATE_LIMIT_HIGH=30                      # High quality requests/min
RATE_LIMIT_PREMIUM=10                   # Premium quality requests/min

# ===============================
# PERFORMANCE TARGETS
# ===============================
TARGET_RESPONSE_TIME=2.5                # Target response time (seconds)
TARGET_LOCAL_PROCESSING=0.85            # Target local processing ratio
MAX_CONCURRENT_REQUESTS=100             # Max concurrent requests
REQUEST_TIMEOUT=30                      # Request timeout (seconds)

# Streaming Configuration
STREAMING_CHUNK_SIZE=1024               # Streaming chunk size (bytes)
STREAMING_BUFFER_SIZE=8192              # Streaming buffer size
STREAMING_TIMEOUT=60                    # Streaming timeout (seconds)

# ===============================
# SECURITY CONFIGURATION
# ===============================
ENABLE_AUTHENTICATION=false            # Enable authentication
JWT_SECRET_KEY=                         # JWT secret key
JWT_EXPIRATION_HOURS=24                # JWT token expiration
API_KEY_REQUIRED=false                  # Require API key

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
ALLOW_CREDENTIALS=true                  # Allow credentials in CORS
ALLOWED_METHODS=GET,POST,PUT,DELETE     # Allowed HTTP methods
ALLOWED_HEADERS=*                       # Allowed headers

# Security Headers
ENABLE_SECURITY_HEADERS=true            # Enable security headers
HSTS_MAX_AGE=31536000                  # HSTS max age
CONTENT_SECURITY_POLICY=default-src 'self'  # CSP policy

# ===============================
# ADVANCED FEATURES
# ===============================
ENABLE_MEMORY_SYSTEM=false             # Enable memory system
ENABLE_CLICKHOUSE=false                # Enable ClickHouse analytics
ENABLE_ROUTER_MIGRATION=true           # Enable router migration
ENABLE_ADAPTIVE_ROUTING=true           # Enable adaptive routing
ENABLE_SHADOW_TRAFFIC=false            # Enable shadow traffic

# Memory System Configuration
MEMORY_RETENTION_DAYS=30               # Memory retention period
MEMORY_COMPRESSION_ENABLED=true        # Enable memory compression
MEMORY_SUMMARY_INTERVAL=3600           # Memory summary interval (seconds)

# ===============================
# GPU AND HARDWARE ACCELERATION
# ===============================
USE_GPU=false                          # Enable GPU acceleration
CUDA_VISIBLE_DEVICES=0                 # Visible CUDA devices
GPU_MEMORY_FRACTION=0.8                # GPU memory fraction to use
ENABLE_MIXED_PRECISION=true            # Enable mixed precision

# Document Search GPU Settings
EMBEDDING_DIM=384                      # Embedding dimensions
FAISS_USE_GPU=true                     # Use GPU for FAISS
HNSW_EF_SEARCH=150                     # HNSW ef_search parameter
HNSW_MAX_CONNECTIONS=16                # HNSW max connections

# ===============================
# MONITORING AND OBSERVABILITY
# ===============================
ENABLE_METRICS=true                    # Enable metrics collection
METRICS_PORT=9090                      # Metrics server port
METRICS_PATH=/metrics                  # Metrics endpoint path

# Logging Configuration
LOG_FORMAT=json                        # Log format (json, text)
LOG_FILE_PATH=/var/log/unified-ai.log  # Log file path
LOG_MAX_SIZE=100MB                     # Max log file size
LOG_BACKUP_COUNT=5                     # Log backup count

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30               # Health check interval (seconds)
HEALTH_CHECK_TIMEOUT=10                # Health check timeout (seconds)
HEALTH_CHECK_RETRIES=3                 # Health check retry count

# ===============================
# DEVELOPMENT AND DEBUGGING
# ===============================
ENABLE_PROFILING=false                 # Enable performance profiling
ENABLE_TRACING=false                   # Enable request tracing
DEBUG_SQL=false                        # Debug SQL queries
MOCK_EXTERNAL_APIS=false               # Mock external API calls

# Development Tools
HOT_RELOAD=true                        # Enable hot reload in development
AUTO_RELOAD_DIRS=app,config            # Directories to watch for changes
ENABLE_API_DOCS=true                   # Enable API documentation
API_DOCS_URL=/docs                     # API documentation URL

# ===============================
# BACKUP AND DISASTER RECOVERY
# ===============================
ENABLE_BACKUP=false                    # Enable automatic backups
BACKUP_INTERVAL=3600                   # Backup interval (seconds)
BACKUP_RETENTION_DAYS=7                # Backup retention period
BACKUP_STORAGE_PATH=/backup            # Backup storage path

# ===============================
# FEATURE FLAGS
# ===============================
ENABLE_WEB_SEARCH=true                 # Enable web search features
ENABLE_DOCUMENT_UPLOAD=true            # Enable document upload
ENABLE_RAG=true                        # Enable RAG functionality
ENABLE_STREAMING=true                  # Enable streaming responses
ENABLE_CACHING=true                    # Enable response caching

# Experimental Features
ENABLE_EXPERIMENTAL_FEATURES=false     # Enable experimental features
ENABLE_A_B_TESTING=false              # Enable A/B testing
ENABLE_FEATURE_TOGGLES=false          # Enable feature toggles
```

## 📊 Service Monitoring

### Health Check Endpoints

```bash
# AI Chat Service Health
curl http://localhost:8003/health
curl http://localhost:8003/health/ready
curl http://localhost:8003/health/live

# Document Search Service Health  
curl http://localhost:8001/health

# System Status
curl http://localhost:8003/system/status

# Metrics
curl http://localhost:8003/metrics
```

### Monitoring Stack with Prometheus

Create `monitoring/docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml

volumes:
  prometheus_data:
  grafana_data:
```

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-chat-service'
    static_configs:
      - targets: ['host.docker.internal:8003']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'document-search-service'
    static_configs:
      - targets: ['host.docker.internal:8001']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'redis'
    static_configs:
      - targets: ['host.docker.internal:6379']

  - job_name: 'ollama'
    static_configs:
      - targets: ['host.docker.internal:11434']
```

### Log Aggregation with ELK Stack

Create `logging/docker-compose.yml`:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5000:5000"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## ⚡ Performance Optimization

### System Tuning

```bash
# Linux system optimization
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_keepalive_time = 600
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# Apply changes
sudo sysctl -p
```

### Docker Optimization

```yaml
# Docker daemon configuration
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
```

### Application Performance Tuning

```python
# gunicorn.conf.py for production
bind = "0.0.0.0:8003"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 60
keepalive = 2
preload_app = True

# Worker tuning
worker_tmp_dir = "/dev/shm"
worker_rlimit_nofile = 65535

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Services Not Starting

**Problem:** Services fail to start or crash immediately.

**Solutions:**
```bash
# Check logs
docker-compose logs -f service-name

# Check system resources
free -h
df -h
docker system df

# Check port conflicts
netstat -tulpn | grep :8003
lsof -i :8003

# Restart with clean state
docker-compose down -v
docker system prune -f
docker-compose up --build
```

#### 2. High Memory Usage

**Problem:** System running out of memory.

**Solutions:**
```bash
# Monitor memory usage
docker stats

# Limit container memory
# In docker-compose.yml:
services:
  ai-chat:
    deploy:
      resources:
        limits:
          memory: 4G

# Clear unused Docker resources
docker system prune -a -f
```

#### 3. Slow Response Times

**Problem:** API responses are slow.

**Solutions:**
```bash
# Check system load
htop
iostat 1

# Monitor database performance
redis-cli info stats

# Profile application
docker-compose exec ai-chat python -m cProfile -o profile.stats app/main.py

# Enable caching
export CACHE_TTL_RESPONSES=3600
```

#### 4. Model Loading Issues

**Problem:** AI models fail to load in Ollama.

**Solutions:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Download models manually
docker-compose exec ollama ollama pull phi3:mini
docker-compose exec ollama ollama pull llama3.2:latest

# Check disk space
df -h

# Reset Ollama
docker-compose down
docker volume rm unified-ai-system-clean_ollama_data
docker-compose up ollama
```

#### 5. Network Connectivity Issues

**Problem:** Services can't communicate with each other.

**Solutions:**
```bash
# Check Docker network
docker network ls
docker network inspect unified-ai-system-clean_unified-network

# Test connectivity
docker-compose exec ai-chat curl http://document-search:8001/health
docker-compose exec ai-chat curl http://redis:6379

# Recreate network
docker-compose down
docker network prune
docker-compose up
```

### Debug Mode Setup

```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug logging
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up

# Access debug endpoints (development only)
curl http://localhost:8003/debug/state
curl http://localhost:8003/debug/test-chat
curl http://localhost:8003/debug/test-search
```

### Performance Monitoring Commands

```bash
# Monitor system resources
htop
iotop
nethogs
docker stats

# Monitor application metrics
curl -s http://localhost:8003/metrics | grep response_time
curl -s http://localhost:8003/system/status | jq '.components'

# Database monitoring
redis-cli info stats
redis-cli info memory
redis-cli slowlog get 10

# Network monitoring
tcpdump -i any port 8003
netstat -tulpn | grep -E ':(8001|8003|6379|11434)'
```

### Backup and Recovery

```bash
# Backup Redis data
docker exec unified-redis redis-cli BGSAVE
docker cp unified-redis:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Backup Ollama models
docker cp unified-ollama:/root/.ollama ./backup/ollama-$(date +%Y%m%d)

# Backup application data
tar -czf backup/app-data-$(date +%Y%m%d).tar.gz \
  ./ai-chat-service/data \
  ./document-search-service/data

# Restore from backup
docker cp ./backup/redis-backup.rdb unified-redis:/data/dump.rdb
docker-compose restart redis
```

### Automated Health Monitoring Script

Create `scripts/health-monitor.sh`:

```bash
#!/bin/bash

SERVICES=("ai-chat:8003" "document-search:8001" "redis:6379" "ollama:11434")
LOG_FILE="/var/log/health-monitor.log"

check_service() {
    local service=$1
    local host=$(echo $service | cut -d: -f1)
    local port=$(echo $service | cut -d: -f2)
    
    if [ "$host" = "redis" ]; then
        timeout 5 redis-cli -h localhost -p $port ping > /dev/null 2>&1
    elif [ "$host" = "ollama" ]; then
        timeout 5 curl -s http://localhost:$port/api/tags > /dev/null 2>&1
    else
        timeout 5 curl -s http://localhost:$port/health > /dev/null 2>&1
    fi
    
    return $?
}

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    all_healthy=true
    
    for service in "${SERVICES[@]}"; do
        if check_service $service; then
            echo "[$timestamp] $service: HEALTHY" >> $LOG_FILE
        else
            echo "[$timestamp] $service: UNHEALTHY" >> $LOG_FILE
            all_healthy=false
            
            # Send alert (customize as needed)
            echo "ALERT: $service is unhealthy at $timestamp" | \
                mail -s "Service Health Alert" admin@yourdomain.com
        fi
    done
    
    if $all_healthy; then
        echo "[$timestamp] All services healthy" >> $LOG_FILE
    fi
    
    sleep 60
done
```

---

## 📞 Support and Resources

### Documentation Links
- **API Documentation**: http://localhost:8003/docs
- **System Health**: http://localhost:8003/health
- **Metrics**: http://localhost:8003/metrics

### Community Resources
- **GitHub Repository**: [Project Repository]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]

### Professional Support
- **Enterprise Support**: contact@yourdomain.com
- **Consulting**: consulting@yourdomain.com
- **Training**: training@yourdomain.com

**Deployment Guide Version:** 2.0  
**Last Updated:** January 2025  
**Compatibility:** Docker 20.10+, Python 3.10+, CUDA 11.8+ (GPU)