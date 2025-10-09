#!/bin/bash
# Deploy all services to RunPod

set -e

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-docker-username}"
DOCKER_TAG="${DOCKER_TAG:-latest}"

echo "========================================"
echo "RunPod Deployment Script"
echo "========================================"
echo ""
echo "Docker Username: $DOCKER_USERNAME"
echo "Docker Tag: $DOCKER_TAG"
echo ""

# Function to build and push a service
build_and_push() {
    local service_name=$1
    local service_dir=$2
    local image_name="${DOCKER_USERNAME}/${service_name}-runpod:${DOCKER_TAG}"

    echo "----------------------------------------"
    echo "Building ${service_name}..."
    echo "----------------------------------------"

    cd "$service_dir"

    docker build -f Dockerfile.runpod -t "$image_name" .

    echo "Pushing ${service_name} to Docker Hub..."
    docker push "$image_name"

    echo "✅ ${service_name} pushed successfully!"
    echo ""

    cd - > /dev/null
}

# Build and push all services
build_and_push "document-search" "document-search-service"
build_and_push "ai-chat" "ai-chat-service"
build_and_push "chainlit-frontend" "chainlit-frontend"

echo "========================================"
echo "✅ All services built and pushed!"
echo "========================================"
echo ""
echo "Docker Images:"
echo "  - ${DOCKER_USERNAME}/document-search-runpod:${DOCKER_TAG}"
echo "  - ${DOCKER_USERNAME}/ai-chat-runpod:${DOCKER_TAG}"
echo "  - ${DOCKER_USERNAME}/chainlit-frontend-runpod:${DOCKER_TAG}"
echo ""
echo "Next Steps:"
echo "----------------------------------------"
echo "1. Go to RunPod: https://www.runpod.io/console/serverless"
echo ""
echo "2. Create Serverless Endpoints for each service:"
echo ""
echo "   📄 Document Search Service (RAG)"
echo "   Image: ${DOCKER_USERNAME}/document-search-runpod:${DOCKER_TAG}"
echo "   Environment Variables:"
echo "     - REDIS_URL=<your-redis-url>"
echo "     - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2"
echo ""
echo "   💬 AI Chat Service"
echo "   Image: ${DOCKER_USERNAME}/ai-chat-runpod:${DOCKER_TAG}"
echo "   Environment Variables:"
echo "     - RUNPOD_API_KEY=<your-runpod-api-key>"
echo "     - RUNPOD_ENDPOINT_ID=<your-runpod-endpoint-id>"
echo "     - REDIS_URL=<your-redis-url>"
echo "     - DOCUMENT_SEARCH_URL=<document-search-endpoint-url>"
echo ""
echo "   🎨 Chainlit Frontend"
echo "   Image: ${DOCKER_USERNAME}/chainlit-frontend-runpod:${DOCKER_TAG}"
echo "   Environment Variables:"
echo "     - AI_CHAT_SERVICE_URL=<ai-chat-endpoint-url>"
echo ""
echo "3. Test your endpoints:"
echo ""
echo "   # Document Search"
echo "   curl -X POST https://api.runpod.ai/v2/<doc-search-endpoint-id>/runsync \\"
echo "     -H 'Authorization: Bearer <your-runpod-api-key>' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"input\": {\"action\": \"search\", \"query\": \"test query\"}}'"
echo ""
echo "   # AI Chat"
echo "   curl -X POST https://api.runpod.ai/v2/<chat-endpoint-id>/runsync \\"
echo "     -H 'Authorization: Bearer <your-runpod-api-key>' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"input\": {\"action\": \"chat\", \"message\": \"Hello!\"}}'"
echo ""
echo "========================================"
