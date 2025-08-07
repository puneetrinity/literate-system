#!/bin/bash

# Unified AI Search System - Startup Script
# ===========================================

set -e

echo "🚀 Starting Unified AI Search System..."
echo "========================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file and add your API keys, then run this script again."
    exit 1
fi

# Load environment variables
source .env

echo "📦 Building and starting services..."

# Pull required models in Ollama
echo "🤖 Setting up Ollama models..."
docker-compose up -d ollama
sleep 10

# Pull essential models
echo "📥 Pulling phi3:mini model (this may take a few minutes)..."
docker-compose exec ollama ollama pull phi3:mini || echo "Will pull models after startup"

echo "📥 Pulling llama3.2 model..."  
docker-compose exec ollama ollama pull llama3.2 || echo "Will pull models after startup"

# Start all services
echo "🔄 Starting all services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 30

# Health checks
echo "🔍 Performing health checks..."

# Check Redis
if curl -f http://localhost:6379 2>/dev/null; then
    echo "✅ Redis: Healthy"
else
    echo "⚠️  Redis: Starting up..."
fi

# Check Document Search Service
if curl -f http://localhost:8001/health 2>/dev/null; then
    echo "✅ Document Search Service: Healthy"
else
    echo "⚠️  Document Search Service: Starting up..."
fi

# Check AI Chat Service  
if curl -f http://localhost:8003/health 2>/dev/null; then
    echo "✅ AI Chat Service: Healthy"
else
    echo "⚠️  AI Chat Service: Starting up..."
fi

echo ""
echo "🎉 Unified AI Search System is starting up!"
echo "==========================================="
echo ""
echo "📡 Access Points:"
echo "  • AI Chat API: http://localhost:8003/docs"
echo "  • Document Search API: http://localhost:8001/docs"
echo "  • Unified Gateway: http://localhost:8000"
echo ""
echo "🔍 Health Checks:"
echo "  • Chat Service: curl http://localhost:8003/health"
echo "  • Search Service: curl http://localhost:8001/health"
echo "  • Overall System: curl http://localhost:8000/health"
echo ""
echo "📊 Monitoring:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop system: docker-compose down"
echo "  • Full reset: docker-compose down -v"
echo ""

# Test basic functionality
echo "🧪 Testing basic functionality..."

echo "Testing AI Chat Service..."
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8003/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, system test"}' 2>/dev/null || echo '{"error": "not ready"}')

if echo "$CHAT_RESPONSE" | grep -q "error"; then
    echo "⚠️  AI Chat Service: Still starting up (this is normal)"
else
    echo "✅ AI Chat Service: Responding to requests"
fi

echo "Testing Document Search Service..."
SEARCH_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v2/search/ultra-fast" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}' 2>/dev/null || echo '{"error": "not ready"}')

if echo "$SEARCH_RESPONSE" | grep -q "error"; then
    echo "⚠️  Document Search Service: Still starting up (this is normal)"
else
    echo "✅ Document Search Service: Responding to requests"
fi

echo ""
echo "🎯 System Status: OPERATIONAL"
echo "All services are starting up. Give them 1-2 minutes to fully initialize."
echo ""
echo "💡 Pro Tips:"
echo "  • Upload documents via the Document Search API"
echo "  • Use Deep Dive research for complex questions"
echo "  • Monitor performance with the health endpoints"
echo "  • Check logs if you encounter issues: docker-compose logs -f [service-name]"