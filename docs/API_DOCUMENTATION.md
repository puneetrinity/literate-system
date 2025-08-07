# 🚀 Unified AI System - API Documentation

## 📖 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Schemas](#requestresponse-schemas)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Cost Management](#cost-management)
9. [WebSocket Streaming](#websocket-streaming)
10. [Code Examples](#code-examples)

## 🎯 Overview

The Unified AI System provides two main APIs:

- **AI Chat Service** (Port 8003): LangGraph orchestration, multi-agent workflows, web search
- **Document Search Service** (Port 8001): Ultra-fast document search with RAG capabilities

Both services provide OpenAPI/Swagger documentation at `/docs` and `/redoc` endpoints.

## 🔐 Authentication

### API Key Authentication

```bash
# Include API key in headers
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     http://localhost:8003/api/v1/chat/complete
```

### Rate Limiting Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
```

## 🌐 Base URLs

### Development
- AI Chat Service: `http://localhost:8003`
- Document Search Service: `http://localhost:8001`

### Production (Docker)
- AI Chat Service: `http://your-domain:8003`
- Document Search Service: `http://your-domain:8001`

### RunPod Deployment
- AI Chat Service: `https://your-pod-id-8003.proxy.runpod.net`
- Document Search Service: `https://your-pod-id-8001.proxy.runpod.net`

## 🔌 API Endpoints

### AI Chat Service (Port 8003)

#### Chat Endpoints

##### POST `/api/v1/chat/complete`
Complete chat conversation with intelligent routing.

**Request Body:**
```json
{
  "message": "Explain machine learning concepts",
  "session_id": "session_123",
  "quality_requirement": "balanced",
  "max_cost": 0.10,
  "max_execution_time": 30.0,
  "include_sources": true,
  "include_debug_info": false
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "response": "Machine learning is a subset of artificial intelligence...",
    "session_id": "session_123",
    "context": {
      "session_id": "session_123",
      "message_count": 5,
      "last_updated": "2024-01-01T10:00:00Z"
    },
    "sources": [
      {
        "title": "Machine Learning Basics",
        "url": "https://example.com/ml-basics",
        "relevance_score": 0.95
      }
    ],
    "citations": ["[1] Machine Learning Basics - Example.com"]
  },
  "metadata": {
    "query_id": "query_456",
    "correlation_id": "corr_789",
    "execution_time": 2.3,
    "cost": 0.08,
    "models_used": ["phi3:mini"],
    "confidence": 0.92,
    "cached": false,
    "timestamp": "2024-01-01T10:00:00Z"
  }
}
```

##### POST `/api/v1/chat/stream`
OpenAI-compatible streaming chat completion.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Tell me about AI"}
  ],
  "model": "auto",
  "max_tokens": 300,
  "temperature": 0.7,
  "stream": true
}
```

**Streaming Response:**
```json
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1640995200,"model":"phi3:mini","choices":[{"index":0,"delta":{"content":"AI"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1640995200,"model":"phi3:mini","choices":[{"index":0,"delta":{"content":" is"},"finish_reason":null}]}

data: [DONE]
```

#### Research Endpoints

##### POST `/api/v1/research/deep-dive`
Deep research with web search integration.

**Request Body:**
```json
{
  "research_question": "What are the latest AI trends in 2024?",
  "methodology": "systematic",
  "time_budget": 300,
  "cost_budget": 0.50,
  "sources": ["web", "academic"],
  "depth_level": 3
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "research_findings": "Based on comprehensive analysis...",
    "sources_consulted": 15,
    "academic_papers": 8,
    "web_sources": 7,
    "confidence_score": 0.94,
    "methodology_used": "systematic"
  },
  "metadata": {
    "query_id": "research_001",
    "execution_time": 45.2,
    "cost": 0.35,
    "models_used": ["phi3:mini", "llama3.2"]
  }
}
```

#### Search Endpoints

##### POST `/api/v1/search/basic`
Basic web search functionality.

**Request Body:**
```json
{
  "query": "artificial intelligence trends",
  "max_results": 10,
  "search_type": "web",
  "include_summary": true,
  "budget": 2.0,
  "quality": "standard"
}
```

##### POST `/api/v1/search/advanced`
Advanced search with filtering and optimization.

**Request Body:**
```json
{
  "query": "machine learning papers 2024",
  "max_results": 20,
  "search_type": "academic",
  "quality_requirement": "high",
  "budget": 5.0,
  "include_content": true,
  "filters": {
    "date_range": "2024",
    "paper_type": "research"
  },
  "domains": ["arxiv.org", "ieee.org"],
  "timeout": 120
}
```

#### Model Management

##### GET `/api/v1/models/list`
List available AI models.

**Response:**
```json
{
  "status": "success",
  "data": {
    "models": [
      {
        "name": "phi3:mini",
        "size": "3.8GB",
        "status": "ready",
        "capabilities": ["chat", "code", "analysis"]
      },
      {
        "name": "llama3.2",
        "size": "7.4GB", 
        "status": "ready",
        "capabilities": ["chat", "reasoning"]
      }
    ],
    "total_models": 2,
    "loaded_models": 2
  }
}
```

##### POST `/api/v1/models/download`
Download new model.

**Request Body:**
```json
{
  "model_name": "llama3.2:8b",
  "priority": "high"
}
```

#### Monitoring & Analytics

##### GET `/api/v1/monitoring/metrics`
Get system performance metrics.

**Response:**
```json
{
  "status": "success",
  "data": {
    "performance": {
      "avg_response_time": 2.1,
      "cache_hit_rate": 0.85,
      "active_sessions": 42
    },
    "costs": {
      "total_today": 5.23,
      "avg_per_request": 0.08
    },
    "models": {
      "total_requests": 1250,
      "popular_models": ["phi3:mini", "llama3.2"]
    }
  }
}
```

##### GET `/api/v1/analytics/usage`
Get usage statistics.

**Response:**
```json
{
  "status": "success", 
  "data": {
    "requests_today": 150,
    "requests_this_month": 4200,
    "cost_today": 12.50,
    "cost_this_month": 380.25,
    "budget_remaining": 119.75,
    "top_endpoints": [
      {"endpoint": "/chat/complete", "count": 89},
      {"endpoint": "/research/deep-dive", "count": 34}
    ]
  }
}
```

### Document Search Service (Port 8001)

#### Ultra-Fast Search

##### POST `/api/v2/search/ultra-fast`
Ultra-fast document search with ML ranking.

**Request Body:**
```json
{
  "query": "machine learning algorithms",
  "max_results": 10,
  "search_type": "hybrid",
  "include_content": true,
  "similarity_threshold": 0.7
}
```

**Response:**
```json
{
  "status": "success",
  "results": [
    {
      "document_id": "doc_123",
      "title": "Advanced ML Algorithms",
      "content": "Machine learning algorithms are computational methods...",
      "score": 0.95,
      "similarity": 0.92,
      "bm25_score": 0.88,
      "metadata": {
        "document_type": "pdf",
        "page_count": 25,
        "creation_date": "2024-01-01"
      }
    }
  ],
  "search_metadata": {
    "total_results": 1,
    "search_time_ms": 125.1,
    "algorithm_used": "lambdamart",
    "index_type": "hnsw_ivf_pq"
  }
}
```

#### RAG (Retrieval Augmented Generation)

##### POST `/api/v2/rag/query`
RAG-enhanced document querying.

**Request Body:**
```json
{
  "query": "What are the benefits of transformer models?",
  "max_context_length": 4000,
  "temperature": 0.7,
  "include_sources": true
}
```

**Response:**
```json
{
  "status": "success",
  "answer": "Transformer models offer several key benefits...",
  "sources": [
    {
      "document_id": "doc_456",
      "title": "Attention Is All You Need",
      "relevance_score": 0.94,
      "content_snippet": "The Transformer model relies entirely on attention mechanisms..."
    }
  ],
  "confidence": 0.91,
  "generation_metadata": {
    "model_used": "phi3:mini",
    "tokens_generated": 245,
    "context_documents": 3
  }
}
```

#### Document Management

##### POST `/api/v2/documents/upload`
Upload documents for indexing.

**Form Data:**
```
file: document.pdf
metadata: {"category": "research", "tags": ["AI", "ML"]}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "doc_789",
  "message": "Document uploaded and indexed successfully",
  "indexing_time_ms": 1250.5
}
```

##### GET `/api/v2/documents/{document_id}`
Get document details.

**Response:**
```json
{
  "status": "success",
  "document": {
    "id": "doc_789",
    "title": "AI Research Paper",
    "content_length": 15000,
    "metadata": {
      "upload_date": "2024-01-01T10:00:00Z",
      "file_type": "pdf",
      "page_count": 12
    },
    "indexed": true,
    "vector_embeddings_count": 150
  }
}
```

## 📊 Request/Response Schemas

### Common Request Fields

```typescript
interface BaseRequest {
  query?: string;                    // Search/chat query
  session_id?: string;              // Session identifier
  max_cost?: number;                // Maximum cost in INR (0.01-1.00)
  max_execution_time?: number;      // Maximum time in seconds
  quality_requirement?: "minimal" | "balanced" | "high" | "premium";
  include_debug_info?: boolean;     // Include debug information
}
```

### Common Response Fields

```typescript
interface BaseResponse {
  status: "success" | "error" | "partial";
  metadata: {
    query_id: string;               // Unique query identifier
    correlation_id: string;         // Request correlation ID
    execution_time: number;         // Execution time in seconds
    cost: number;                   // Cost in INR
    models_used: string[];          // Models used
    confidence: number;             // Confidence score (0-1)
    cached: boolean;                // Cache hit/miss
    timestamp: string;              // ISO timestamp
  };
  cost_prediction?: {
    estimated_cost: number;
    cost_breakdown: Array<{
      step: string;
      service: string;
      cost: number;
    }>;
    savings_tips: string[];
  };
  developer_hints?: {
    suggested_next_queries: string[];
    potential_optimizations: Record<string, string>;
    routing_explanation: string;
    performance_hints: Record<string, any>;
  };
}
```

## ⚠️ Error Handling

### Error Response Format

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "error_details": {
    "error_code": "RATE_LIMIT_EXCEEDED", 
    "error_type": "RATE_LIMIT",
    "user_message": "Too many requests. Please try again later.",
    "technical_details": "Exceeded 60 requests per minute limit",
    "suggestions": [
      "Wait 60 seconds before retrying",
      "Upgrade to premium tier for higher limits"
    ],
    "retry_after": 60
  },
  "query_id": "query_123",
  "correlation_id": "corr_456",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

### Common Error Codes

| Code | Description | HTTP Status | Retry |
|------|-------------|-------------|-------|
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 | Yes, after delay |
| `INSUFFICIENT_BUDGET` | Cost exceeds budget | 402 | No |
| `MODEL_UNAVAILABLE` | Requested model offline | 503 | Yes |
| `INVALID_REQUEST` | Malformed request | 400 | No |
| `TIMEOUT_EXCEEDED` | Request timeout | 408 | Yes |
| `INTERNAL_SERVER_ERROR` | Server error | 500 | Yes |

## 🚦 Rate Limiting

### Default Limits

| Tier | Requests/Minute | Requests/Day | Cost/Month |
|------|----------------|--------------|------------|
| Free | 20 | 1,000 | ₹0 |
| Basic | 60 | 5,000 | ₹50 |
| Pro | 200 | 20,000 | ₹200 |
| Enterprise | Unlimited | Unlimited | Custom |

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995260
X-RateLimit-Tier: basic
```

## 💰 Cost Management

### Cost Structure

| Service | Cost per Request | Notes |
|---------|------------------|-------|
| Chat (Local Model) | ₹0.00 | Free with Ollama |
| Chat (Premium) | ₹0.08 | Advanced reasoning |
| Web Search | ₹0.15 | Per search query |
| Document Search | ₹0.02 | Per search |
| RAG Query | ₹0.05 | Including generation |

### Budget Tracking

```bash
# Get current usage
curl http://localhost:8003/api/v1/analytics/usage

# Set monthly budget
curl -X POST http://localhost:8003/api/v1/user/budget \
  -d '{"monthly_budget": 100.0}'
```

## 🔄 WebSocket Streaming

### Chat Streaming

```javascript
const ws = new WebSocket('ws://localhost:8003/api/v1/chat/stream');

ws.onopen = function() {
  ws.send(JSON.stringify({
    message: "Explain quantum computing",
    stream: true,
    session_id: "session_123"
  }));
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'content') {
    console.log(data.content); // Streaming content
  } else if (data.type === 'done') {
    console.log('Stream completed');
  }
};
```

## 💻 Code Examples

### Python Client

```python
import requests
import json

class UnifiedAIClient:
    def __init__(self, base_url="http://localhost:8003", api_key=None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else None
        }
    
    def chat_complete(self, message, session_id=None, **kwargs):
        """Complete chat conversation"""
        payload = {
            "message": message,
            "session_id": session_id,
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/chat/complete",
            headers=self.headers,
            json=payload
        )
        
        return response.json()
    
    def research_deep_dive(self, question, **kwargs):
        """Perform deep research"""
        payload = {
            "research_question": question,
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/research/deep-dive", 
            headers=self.headers,
            json=payload
        )
        
        return response.json()
    
    def document_search(self, query, **kwargs):
        """Search documents"""
        payload = {
            "query": query,
            **kwargs
        }
        
        # Switch to document search service
        doc_url = self.base_url.replace(":8003", ":8001")
        response = requests.post(
            f"{doc_url}/api/v2/search/ultra-fast",
            headers=self.headers, 
            json=payload
        )
        
        return response.json()

# Usage
client = UnifiedAIClient()

# Chat
result = client.chat_complete(
    "Explain machine learning",
    quality_requirement="high",
    max_cost=0.15
)
print(result['data']['response'])

# Research
research = client.research_deep_dive(
    "Latest AI trends in 2024",
    methodology="systematic",
    depth_level=3
)
print(research['data']['research_findings'])

# Search
docs = client.document_search(
    "transformer architecture",
    max_results=5
)
print(f"Found {len(docs['results'])} documents")
```

### JavaScript Client

```javascript
class UnifiedAIClient {
  constructor(baseUrl = 'http://localhost:8003', apiKey = null) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json',
      ...(apiKey && { 'Authorization': `Bearer ${apiKey}` })
    };
  }

  async chatComplete(message, options = {}) {
    const payload = {
      message,
      ...options
    };

    const response = await fetch(`${this.baseUrl}/api/v1/chat/complete`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(payload)
    });

    return await response.json();
  }

  async streamChat(message, onChunk, options = {}) {
    const payload = {
      messages: [{ role: 'user', content: message }],
      stream: true,
      ...options
    };

    const response = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(payload)
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          
          try {
            const parsed = JSON.parse(data);
            onChunk(parsed);
          } catch (e) {
            console.warn('Failed to parse chunk:', data);
          }
        }
      }
    }
  }

  async documentSearch(query, options = {}) {
    const payload = {
      query,
      ...options
    };

    const docUrl = this.baseUrl.replace(':8003', ':8001');
    const response = await fetch(`${docUrl}/api/v2/search/ultra-fast`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(payload)
    });

    return await response.json();
  }
}

// Usage
const client = new UnifiedAIClient();

// Chat
const result = await client.chatComplete(
  "What is quantum computing?",
  { quality_requirement: "high" }
);
console.log(result.data.response);

// Streaming chat
await client.streamChat(
  "Explain AI step by step",
  (chunk) => {
    if (chunk.choices?.[0]?.delta?.content) {
      process.stdout.write(chunk.choices[0].delta.content);
    }
  }
);

// Document search
const docs = await client.documentSearch("neural networks");
console.log(`Found ${docs.results.length} documents`);
```

### cURL Examples

```bash
# Basic chat
curl -X POST "http://localhost:8003/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain blockchain technology",
    "quality_requirement": "high",
    "max_cost": 0.20
  }'

# Streaming chat
curl -X POST "http://localhost:8003/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me about AI"}],
    "stream": true,
    "temperature": 0.7
  }' \
  --no-buffer

# Deep research
curl -X POST "http://localhost:8003/api/v1/research/deep-dive" \
  -H "Content-Type: application/json" \
  -d '{
    "research_question": "Impact of AI on healthcare 2024",
    "methodology": "systematic",
    "depth_level": 3,
    "cost_budget": 0.50
  }'

# Document search
curl -X POST "http://localhost:8001/api/v2/search/ultra-fast" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning optimization",
    "max_results": 10,
    "search_type": "hybrid"
  }'

# Upload document
curl -X POST "http://localhost:8001/api/v2/documents/upload" \
  -F "file=@research_paper.pdf" \
  -F "metadata={\"category\":\"research\",\"tags\":[\"AI\"]}"

# Get system health
curl "http://localhost:8003/health"
curl "http://localhost:8001/health"

# Get metrics
curl "http://localhost:8003/api/v1/monitoring/metrics"

# List models
curl "http://localhost:8003/api/v1/models/list"
```

## 🔗 Interactive API Documentation

### Swagger UI
- AI Chat Service: http://localhost:8003/docs
- Document Search Service: http://localhost:8001/docs

### ReDoc
- AI Chat Service: http://localhost:8003/redoc  
- Document Search Service: http://localhost:8001/redoc

### Health Endpoints
- AI Chat Health: http://localhost:8003/health
- Document Search Health: http://localhost:8001/health
- System Status: http://localhost:8003/system/status

---

## 📞 Support

For API support, please refer to:
- GitHub Issues: [Project Repository]
- Documentation: `/docs` endpoints
- Health Checks: `/health` endpoints
- System Metrics: `/metrics` endpoints

**Latest API Version:** v1 (AI Chat), v2 (Document Search)  
**Last Updated:** January 2025