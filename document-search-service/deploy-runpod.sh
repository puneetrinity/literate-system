#!/bin/bash
# Deploy document-search-service to RunPod

set -e

echo "Building Docker image for RunPod..."
docker build -f Dockerfile.runpod -t document-search-runpod:latest .

echo "Tagging image..."
docker tag document-search-runpod:latest <your-docker-username>/document-search-runpod:latest

echo "Pushing to Docker Hub..."
docker push <your-docker-username>/document-search-runpod:latest

echo ""
echo "✅ Image pushed successfully!"
echo ""
echo "Next steps:"
echo "1. Go to RunPod: https://www.runpod.io/console/serverless"
echo "2. Create new Serverless Endpoint"
echo "3. Use image: <your-docker-username>/document-search-runpod:latest"
echo "4. Set environment variables if needed"
echo "5. Deploy and get your endpoint URL"
echo ""
echo "Example API call:"
echo 'curl -X POST https://api.runpod.ai/v2/<endpoint-id>/runsync \\'
echo '  -H "Authorization: Bearer <your-api-key>" \\'
echo '  -H "Content-Type: application/json" \\'
echo '  -d '"'"'{"input": {"action": "search", "query": "your search query", "top_k": 5}}'"'"
