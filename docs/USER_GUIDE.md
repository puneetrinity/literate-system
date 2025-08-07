# 🚀 Unified AI System - User Guide

## 📖 Table of Contents

1. [Getting Started](#getting-started)
2. [Web Interface Usage](#web-interface-usage)
3. [API Usage Examples](#api-usage-examples)
4. [Client SDKs](#client-sdks)
5. [Best Practices](#best-practices)
6. [Limitations & Guidelines](#limitations--guidelines)
7. [Cost Management](#cost-management)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

## 🎯 Getting Started

### What is the Unified AI System?

The Unified AI System is a comprehensive AI platform that combines:

- **🤖 Intelligent Chat**: Advanced conversational AI with multi-model support
- **🔍 Ultra-Fast Search**: High-performance document search with ML ranking
- **📚 RAG (Retrieval Augmented Generation)**: Context-aware responses using your documents
- **🌐 Web Research**: Deep-dive research with real-time web search integration
- **💡 Multi-Agent Workflows**: Specialized AI agents for different tasks

### Quick Start Guide

#### 1. Access the System

**Web Interface:**
- Development: http://localhost:8000
- Production: https://your-domain.com

**API Endpoints:**
- AI Chat Service: http://localhost:8003
- Document Search: http://localhost:8001
- API Documentation: http://localhost:8003/docs

#### 2. First Chat Request

Try your first chat interaction:

```bash
curl -X POST "http://localhost:8003/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Can you explain what you can help me with?",
    "session_id": "getting_started"
  }'
```

#### 3. Upload Your First Document

```bash
curl -X POST "http://localhost:8001/api/v2/documents/upload" \
  -F "file=@your_document.pdf" \
  -F "metadata={\"category\":\"general\",\"tags\":[\"test\"]}"
```

#### 4. Search Your Documents

```bash
curl -X POST "http://localhost:8001/api/v2/search/ultra-fast" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "key topics from my document",
    "max_results": 5
  }'
```

## 🌐 Web Interface Usage

### Chat Interface

The web interface provides an intuitive chat experience with advanced features:

#### Basic Chat Features

1. **Message Input**: Type your message in the text area
2. **Send Message**: Click "Send" or press Ctrl+Enter
3. **Session Management**: Conversations are automatically saved
4. **Response Streaming**: Watch responses generate in real-time

#### Advanced Chat Options

**Quality Settings:**
- **Minimal**: Fast responses, basic quality (Free)
- **Balanced**: Good balance of speed and quality (Default)
- **High**: Better reasoning, slower responses
- **Premium**: Best quality, highest cost

**Cost Controls:**
```javascript
// Set maximum cost per request
{
  "max_cost": 0.15,  // Maximum ₹0.15 per request
  "quality_requirement": "high"
}
```

**Response Customization:**
```javascript
{
  "response_style": "detailed",     // concise, balanced, detailed
  "include_sources": true,          // Include source citations
  "include_debug_info": false       // Show internal processing info
}
```

#### Chat Interface Examples

**Basic Conversation:**
```
User: What is machine learning?

AI Assistant: Machine learning is a subset of artificial intelligence (AI) that enables computers to learn and improve from experience without being explicitly programmed for every task. Here's a comprehensive overview:

## Core Concepts

**Definition**: Machine learning uses algorithms to analyze data, identify patterns, and make predictions or decisions with minimal human intervention.

**Key Components**:
- **Data**: Training information used to teach the algorithm
- **Algorithm**: Mathematical model that processes the data
- **Features**: Specific data points the algorithm analyzes
- **Model**: The trained algorithm ready to make predictions

## Types of Machine Learning

1. **Supervised Learning**
   - Uses labeled training data
   - Examples: Classification, regression
   - Applications: Email spam detection, price prediction

2. **Unsupervised Learning**
   - Finds patterns in unlabeled data
   - Examples: Clustering, dimensionality reduction
   - Applications: Customer segmentation, anomaly detection

3. **Reinforcement Learning**
   - Learns through interaction and feedback
   - Examples: Game playing, robotics
   - Applications: Autonomous vehicles, recommendation systems

## Real-World Applications

- **Healthcare**: Disease diagnosis, drug discovery
- **Finance**: Fraud detection, algorithmic trading
- **Technology**: Search engines, voice assistants
- **Transportation**: Route optimization, autonomous driving

**Sources**: Based on current machine learning literature and industry practices.

*Response generated in 2.3 seconds | Cost: ₹0.08 | Confidence: 94%*
```

**Research Query:**
```
User: What are the latest developments in quantum computing for 2024?

AI Assistant: I'll research the latest quantum computing developments for 2024. Let me gather comprehensive information from recent sources.

*[Initiating deep research mode...]*
*[Searching recent publications and news...]*
*[Found 23 relevant sources from 2024...]*

# Latest Quantum Computing Developments in 2024

## Major Breakthroughs

### Hardware Advances
- **IBM's 1000+ Qubit Processor**: IBM unveiled their "Flamingo" processor with over 1,000 qubits, marking a significant scaling milestone
- **Google's Logical Qubit Achievement**: Demonstrated error correction with logical qubits showing lower error rates than physical qubits
- **IonQ's Commercial Milestones**: Achieved 99.8% two-qubit gate fidelity in their trapped-ion systems

### Software & Algorithms
- **Quantum Error Mitigation**: New techniques reducing error rates by 50-80% without full error correction
- **Quantum Machine Learning**: Hybrid algorithms showing quantum advantage in specific optimization problems
- **Quantum Networking**: Progress in quantum internet protocols and long-distance entanglement

## Industry Impact

### Investment & Funding
- **$2.4B+ Global Investment**: Quantum computing attracted record venture capital in 2024
- **Government Initiatives**: US, EU, and China announced multi-billion dollar quantum programs
- **Corporate R&D**: Major tech companies increased quantum research budgets by 40%

### Commercial Applications
- **Financial Services**: JP Morgan and Goldman Sachs deployed quantum algorithms for risk analysis
- **Pharmaceuticals**: Roche used quantum simulation for drug molecule optimization
- **Logistics**: DHL implemented quantum optimization for route planning

## Technical Milestones

### Error Correction Progress
- **Surface Code Implementations**: Multiple companies demonstrated surface code error correction
- **Logical Qubit Lifetimes**: Extended from microseconds to milliseconds in leading systems
- **Threshold Achievement**: Several systems crossed the error correction threshold

### Connectivity Improvements
- **All-to-All Connectivity**: New architectures allowing any qubit to interact with any other
- **Modular Systems**: Advances in connecting multiple quantum processors
- **Quantum Networks**: City-scale quantum communication networks deployed

## Challenges & Limitations

### Current Obstacles
- **Decoherence Times**: Still limited to microseconds for most systems
- **Scaling Issues**: Engineering challenges in building larger systems
- **Cost Barriers**: High operational costs limiting widespread adoption

### Near-term Outlook
- **NISQ Era Continues**: Noisy Intermediate-Scale Quantum devices remain dominant
- **Hybrid Approaches**: Classical-quantum hybrid algorithms showing most promise
- **Specialized Applications**: Focus on specific problems where quantum advantage is clear

## Key Players in 2024

### Technology Leaders
1. **IBM**: Leading in gate-based superconducting systems
2. **Google**: Advancing quantum supremacy research
3. **IonQ**: Pioneering trapped-ion quantum computers
4. **Rigetti**: Developing quantum cloud services
5. **PsiQuantum**: Building fault-tolerant photonic systems

### Emerging Companies
- **Atom Computing**: Neutral atom quantum computers
- **QuEra**: Analog quantum simulation platforms
- **Xanadu**: Photonic quantum computing
- **Oxford Quantum Computing**: Ion-trap quantum computers

## Future Projections

### 2025-2027 Timeline
- **10,000+ Qubit Systems**: Expected from multiple vendors
- **Commercial Quantum Advantage**: First clear business applications
- **Quantum Software Maturity**: Better development tools and languages

### Investment Outlook
- **Market Size**: Projected to reach $8.6B by 2027
- **Talent Demand**: 40,000+ quantum computing jobs expected
- **Patent Activity**: Over 5,000 quantum patents filed in 2024

## Sources Consulted
1. Nature Quantum Information - Q1 2024 Special Issue
2. IEEE Quantum Computing Summit 2024 Proceedings
3. McKinsey Quantum Technology Report 2024
4. MIT Technology Review Quantum Computing Analysis
5. Quantum Computing Report Industry Updates
6. [Additional 18 sources...]

*Research completed in 45.2 seconds | Sources: 23 academic and industry publications | Cost: ₹0.35 | Confidence: 97%*

Would you like me to dive deeper into any specific aspect of these developments?
```

**Document-Based Query:**
```
User: Based on my uploaded research papers, what are the key findings about neural network optimization?

AI Assistant: I'll analyze your uploaded research papers to identify key findings about neural network optimization.

*[Searching your document collection...]*
*[Found 12 relevant papers on neural network optimization...]*
*[Analyzing content with RAG system...]*

# Neural Network Optimization: Key Findings from Your Research Collection

## Overview
Based on analysis of 12 research papers in your collection, here are the key findings about neural network optimization:

## Major Optimization Techniques

### 1. Adaptive Learning Rates
**From: "Advanced Optimization Methods for Deep Learning" (Paper ID: doc_445)**
- **Adam Optimizer**: Combines momentum with adaptive learning rates, showing 15-20% faster convergence
- **AdaGrad Limitations**: Performance degrades on long sequences due to aggressive learning rate decay
- **RMSprop Benefits**: Maintains good performance on non-stationary objectives

### 2. Regularization Strategies
**From: "Regularization in Deep Neural Networks" (Paper ID: doc_267)**
- **Dropout**: 30-50% reduction in overfitting, but can slow training by 2x
- **Batch Normalization**: Accelerates training by 3-5x and acts as implicit regularization
- **Weight Decay**: L2 regularization coefficient of 1e-4 to 1e-5 shows optimal results

### 3. Architecture-Specific Optimizations
**From: "CNN Optimization Strategies" (Paper ID: doc_891)**
- **Residual Connections**: Enable training of 100+ layer networks without vanishing gradients
- **Attention Mechanisms**: 20-30% improvement in sequence modeling tasks
- **Skip Connections**: Reduce training time by 40% while maintaining accuracy

## Loss Function Innovations

### Advanced Loss Functions
**From: "Novel Loss Functions for Deep Learning" (Paper ID: doc_523)**
- **Focal Loss**: Addresses class imbalance, improving F1-score by 15-25%
- **Label Smoothing**: Reduces overconfidence, improves generalization by 2-3%
- **Contrastive Loss**: Enhances representation learning in siamese networks

### Multi-Task Learning
**From: "Multi-Task Optimization in Neural Networks" (Paper ID: doc_178)**
- **Gradient Balancing**: Prevents task interference in multi-objective training
- **Task Weighting**: Dynamic weighting schemes improve overall performance by 10-15%
- **Shared Representations**: Lower layers benefit from shared learning across tasks

## Hardware-Specific Optimizations

### GPU Acceleration
**From: "Efficient GPU Training Strategies" (Paper ID: doc_634)**
- **Mixed Precision**: Reduces memory usage by 50% with minimal accuracy loss
- **Gradient Accumulation**: Enables larger effective batch sizes on limited memory
- **Data Parallelism**: Linear scaling up to 8 GPUs, diminishing returns beyond

### Memory Optimization
**From: "Memory-Efficient Deep Learning" (Paper ID: doc_756)**
- **Gradient Checkpointing**: Trades compute for memory, enabling 2x larger models
- **Model Sharding**: Distributes large models across multiple devices
- **Activation Compression**: Reduces memory footprint by 30-40%

## Convergence Analysis

### Training Dynamics
**From: "Understanding Neural Network Convergence" (Paper ID: doc_389)**
- **Learning Rate Schedules**: Cosine annealing outperforms step decay by 2-3%
- **Warm-up Strategies**: Critical for large batch training, prevents early divergence
- **Early Stopping**: Patience of 10-20 epochs optimal for most architectures

### Generalization Insights
**From: "Generalization in Over-parameterized Networks" (Paper ID: doc_912)**
- **Double Descent**: Test error can decrease again after initial overfitting
- **Implicit Bias**: SGD favors solutions with better generalization properties
- **Lottery Ticket Hypothesis**: Sparse subnetworks can achieve full network performance

## Practical Recommendations

### Training Best Practices
1. **Initialization**: Xavier/He initialization for different activation functions
2. **Batch Size**: Larger batches (256-1024) with learning rate scaling
3. **Data Augmentation**: Essential for computer vision, 5-10% improvement
4. **Curriculum Learning**: Gradual difficulty increase improves final performance

### Hyperparameter Tuning
- **Learning Rate**: Most critical hyperparameter, use grid search or Bayesian optimization
- **Architecture Search**: Neural Architecture Search (NAS) showing promising results
- **Automated ML**: AutoML tools reducing manual tuning effort by 70%

## Recent Trends (2023-2024)

### Emerging Techniques
**From: "Future Directions in Neural Optimization" (Paper ID: doc_445)**
- **Sharpness-Aware Minimization**: Improves generalization by seeking flat minima
- **Lion Optimizer**: Memory-efficient alternative to Adam with comparable performance
- **Adversarial Training**: Robustness improvements with 10-15% accuracy trade-off

### Large Model Optimization
- **Parameter-Efficient Fine-tuning**: LoRA and adapters reduce training costs by 90%
- **Gradient Compression**: Reduces communication overhead in distributed training
- **Model Pruning**: Structured pruning maintains performance with 50% parameter reduction

## Summary Statistics
- **Papers Analyzed**: 12 research papers from your collection
- **Key Techniques Identified**: 25+ optimization methods
- **Performance Improvements**: 15-50% across different metrics
- **Implementation Complexity**: Low to High (categorized by difficulty)

## Recommended Reading Order
1. Start with "Advanced Optimization Methods for Deep Learning" (doc_445)
2. Follow with "Regularization in Deep Neural Networks" (doc_267)
3. Deep dive into "Understanding Neural Network Convergence" (doc_389)

*Document analysis completed in 15.7 seconds | Documents processed: 12 | Cost: ₹0.22 | Confidence: 96%*

Would you like me to elaborate on any specific optimization technique or analyze additional papers in your collection?
```

### Document Management Interface

#### Upload Documents

The system supports multiple document formats:

**Supported Formats:**
- PDF files (.pdf)
- Word documents (.docx, .doc)
- Text files (.txt)
- Markdown files (.md)
- CSV files (.csv)
- JSON files (.json)

**Upload Process:**
1. Click "Upload Document" button
2. Select file(s) from your computer
3. Add metadata (optional but recommended):
   ```json
   {
     "category": "research",
     "tags": ["machine learning", "optimization"],
     "author": "Dr. Smith",
     "date": "2024-01-15",
     "priority": "high"
   }
   ```
4. Click "Process & Index"
5. Wait for indexing completion

#### Document Search Interface

**Search Features:**
- **Keyword Search**: Traditional text-based search
- **Semantic Search**: Meaning-based search using AI embeddings
- **Hybrid Search**: Combines keyword and semantic search
- **Filtered Search**: Search within specific categories or date ranges

**Search Examples:**
```
Query: "optimization techniques for neural networks"
Filters: Category = "research", Date > 2023-01-01
Results: 15 documents found, sorted by relevance
```

### Research Assistant Mode

The research assistant provides deep, comprehensive research on complex topics:

**Research Types:**
- **Fact Gathering**: Quick factual information with citations
- **Trend Analysis**: Latest developments and market trends
- **Literature Review**: Comprehensive academic research
- **Comparative Analysis**: Side-by-side comparison of topics

**Research Process:**
1. Submit research question
2. AI analyzes and plans research approach
3. Searches multiple sources (web + documents)
4. Synthesizes findings into comprehensive report
5. Provides citations and confidence metrics

## 📱 API Usage Examples

### Basic Chat API

#### Simple Chat Request

```python
import requests

def simple_chat(message, session_id=None):
    url = "http://localhost:8003/api/v1/chat/complete"
    
    payload = {
        "message": message,
        "session_id": session_id or "default_session",
        "quality_requirement": "balanced",
        "max_cost": 0.10
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        return {
            "response": data["data"]["response"],
            "cost": data["metadata"]["cost"],
            "execution_time": data["metadata"]["execution_time"]
        }
    else:
        return {"error": response.text}

# Usage
result = simple_chat("Explain quantum computing in simple terms")
print(f"Response: {result['response']}")
print(f"Cost: ₹{result['cost']:.3f}")
```

#### Streaming Chat Response

```python
import requests
import json

def streaming_chat(message):
    url = "http://localhost:8003/api/v1/chat/stream"
    
    payload = {
        "messages": [{"role": "user", "content": message}],
        "stream": True,
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if chunk['choices'][0]['delta'].get('content'):
                        print(chunk['choices'][0]['delta']['content'], end='', flush=True)
                except json.JSONDecodeError:
                    continue

# Usage
streaming_chat("Write a poem about artificial intelligence")
```

### Document Search API

#### Upload and Search Documents

```python
import requests
import os

class DocumentSearchClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
    
    def upload_document(self, file_path, metadata=None):
        """Upload a document for indexing."""
        url = f"{self.base_url}/api/v2/documents/upload"
        
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {}
            if metadata:
                data['metadata'] = json.dumps(metadata)
            
            response = requests.post(url, files=files, data=data)
        
        return response.json()
    
    def search_documents(self, query, max_results=10, search_type="hybrid"):
        """Search through uploaded documents."""
        url = f"{self.base_url}/api/v2/search/ultra-fast"
        
        payload = {
            "query": query,
            "max_results": max_results,
            "search_type": search_type,
            "include_content": True
        }
        
        response = requests.post(url, json=payload)
        return response.json()
    
    def rag_query(self, query, max_context_length=4000):
        """Perform RAG query on documents."""
        url = f"{self.base_url}/api/v2/rag/query"
        
        payload = {
            "query": query,
            "max_context_length": max_context_length,
            "include_sources": True
        }
        
        response = requests.post(url, json=payload)
        return response.json()

# Usage Example
client = DocumentSearchClient()

# Upload document
metadata = {
    "category": "research",
    "tags": ["AI", "machine learning"],
    "author": "Research Team"
}

upload_result = client.upload_document("research_paper.pdf", metadata)
print(f"Document uploaded: {upload_result['document_id']}")

# Search documents
search_results = client.search_documents(
    "neural network optimization techniques", 
    max_results=5
)

for result in search_results["results"]:
    print(f"Title: {result['title']}")
    print(f"Score: {result['score']:.3f}")
    print(f"Content snippet: {result['content'][:200]}...")
    print("---")

# RAG query
rag_result = client.rag_query(
    "What are the best practices for training deep neural networks?"
)

print(f"RAG Answer: {rag_result['answer']}")
print(f"Sources used: {len(rag_result['sources'])}")
```

### Research API

#### Deep Research Request

```python
import requests
import time

def deep_research(research_question, methodology="systematic"):
    url = "http://localhost:8003/api/v1/research/deep-dive"
    
    payload = {
        "research_question": research_question,
        "methodology": methodology,
        "time_budget": 300,  # 5 minutes
        "cost_budget": 0.50,  # ₹0.50
        "sources": ["web", "academic"],
        "depth_level": 3
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

# Usage
research_result = deep_research(
    "What are the environmental impacts of cryptocurrency mining in 2024?",
    methodology="systematic"
)

print(f"Research Findings:")
print(research_result["data"]["research_findings"])
print(f"\nSources consulted: {research_result['data']['sources_consulted']}")
print(f"Cost: ₹{research_result['metadata']['cost']:.3f}")
```

## 🛠️ Client SDKs

### Python SDK

Create a comprehensive Python client:

```python
# unified_ai_client.py
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
import logging

class UnifiedAIClient:
    """Comprehensive Python client for Unified AI System."""
    
    def __init__(self, 
                 chat_base_url: str = "http://localhost:8003",
                 doc_base_url: str = "http://localhost:8001",
                 api_key: Optional[str] = None,
                 timeout: int = 30):
        
        self.chat_base_url = chat_base_url.rstrip('/')
        self.doc_base_url = doc_base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "UnifiedAI-Python-Client/1.0"
        }
        
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # Chat Methods
    async def chat_complete(self, 
                           message: str,
                           session_id: Optional[str] = None,
                           quality: str = "balanced",
                           max_cost: float = 0.10,
                           **kwargs) -> Dict[str, Any]:
        """Complete chat conversation."""
        
        payload = {
            "message": message,
            "session_id": session_id,
            "quality_requirement": quality,
            "max_cost": max_cost,
            **kwargs
        }
        
        async with self.session.post(
            f"{self.chat_base_url}/api/v1/chat/complete",
            json=payload
        ) as response:
            return await response.json()
    
    async def chat_stream(self, 
                         message: str,
                         session_id: Optional[str] = None,
                         **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response."""
        
        payload = {
            "messages": [{"role": "user", "content": message}],
            "session_id": session_id,
            "stream": True,
            **kwargs
        }
        
        async with self.session.post(
            f"{self.chat_base_url}/api/v1/chat/stream",
            json=payload
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk['choices'][0]['delta'].get('content', '')
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    # Research Methods
    async def research_deep_dive(self,
                                research_question: str,
                                methodology: str = "systematic",
                                depth_level: int = 3,
                                **kwargs) -> Dict[str, Any]:
        """Perform deep research."""
        
        payload = {
            "research_question": research_question,
            "methodology": methodology,
            "depth_level": depth_level,
            **kwargs
        }
        
        async with self.session.post(
            f"{self.chat_base_url}/api/v1/research/deep-dive",
            json=payload
        ) as response:
            return await response.json()
    
    # Document Methods
    async def upload_document(self,
                             file_path: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload document for indexing."""
        
        data = aiohttp.FormData()
        data.add_field('file', 
                      open(file_path, 'rb'),
                      filename=file_path.split('/')[-1])
        
        if metadata:
            data.add_field('metadata', json.dumps(metadata))
        
        # Remove Content-Type header for multipart upload
        headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
        
        async with self.session.post(
            f"{self.doc_base_url}/api/v2/documents/upload",
            data=data,
            headers=headers
        ) as response:
            return await response.json()
    
    async def search_documents(self,
                              query: str,
                              max_results: int = 10,
                              search_type: str = "hybrid",
                              **kwargs) -> Dict[str, Any]:
        """Search documents."""
        
        payload = {
            "query": query,
            "max_results": max_results,
            "search_type": search_type,
            **kwargs
        }
        
        async with self.session.post(
            f"{self.doc_base_url}/api/v2/search/ultra-fast",
            json=payload
        ) as response:
            return await response.json()
    
    async def rag_query(self,
                       query: str,
                       max_context_length: int = 4000,
                       **kwargs) -> Dict[str, Any]:
        """Perform RAG query."""
        
        payload = {
            "query": query,
            "max_context_length": max_context_length,
            **kwargs
        }
        
        async with self.session.post(
            f"{self.doc_base_url}/api/v2/rag/query",
            json=payload
        ) as response:
            return await response.json()
    
    # Utility Methods
    async def get_health(self) -> Dict[str, Any]:
        """Check system health."""
        health_results = {}
        
        # Check chat service health
        try:
            async with self.session.get(f"{self.chat_base_url}/health") as response:
                health_results["chat_service"] = await response.json()
        except Exception as e:
            health_results["chat_service"] = {"status": "unhealthy", "error": str(e)}
        
        # Check document service health
        try:
            async with self.session.get(f"{self.doc_base_url}/health") as response:
                health_results["document_service"] = await response.json()
        except Exception as e:
            health_results["document_service"] = {"status": "unhealthy", "error": str(e)}
        
        return health_results
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        async with self.session.get(
            f"{self.chat_base_url}/api/v1/analytics/usage"
        ) as response:
            return await response.json()

# Usage Example
async def main():
    async with UnifiedAIClient() as client:
        # Check health
        health = await client.get_health()
        print(f"System Health: {health}")
        
        # Chat completion
        chat_result = await client.chat_complete(
            "Explain the benefits of renewable energy",
            quality="high",
            max_cost=0.15
        )
        print(f"Chat Response: {chat_result['data']['response'][:200]}...")
        
        # Streaming chat
        print("\nStreaming Response:")
        async for chunk in client.chat_stream("Tell me a short story about AI"):
            print(chunk, end='', flush=True)
        print("\n")
        
        # Document upload
        upload_result = await client.upload_document(
            "sample_document.pdf",
            metadata={"category": "test", "tags": ["sample"]}
        )
        print(f"Document uploaded: {upload_result}")
        
        # Document search
        search_result = await client.search_documents(
            "renewable energy benefits",
            max_results=5
        )
        print(f"Found {len(search_result['results'])} documents")
        
        # Deep research
        research_result = await client.research_deep_dive(
            "What are the latest developments in solar panel technology?",
            depth_level=2
        )
        print(f"Research completed: {research_result['data']['research_findings'][:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript/Node.js SDK

```javascript
// unified-ai-client.js
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class UnifiedAIClient {
    constructor(options = {}) {
        this.chatBaseUrl = (options.chatBaseUrl || 'http://localhost:8003').replace(/\/$/, '');
        this.docBaseUrl = (options.docBaseUrl || 'http://localhost:8001').replace(/\/$/, '');
        this.apiKey = options.apiKey;
        this.timeout = options.timeout || 30000;
        
        this.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'UnifiedAI-Node-Client/1.0'
        };
        
        if (this.apiKey) {
            this.headers['Authorization'] = `Bearer ${this.apiKey}`;
        }
        
        // Create axios instances
        this.chatClient = axios.create({
            baseURL: this.chatBaseUrl,
            timeout: this.timeout,
            headers: this.headers
        });
        
        this.docClient = axios.create({
            baseURL: this.docBaseUrl,
            timeout: this.timeout,
            headers: this.headers
        });
    }
    
    // Chat Methods
    async chatComplete(message, options = {}) {
        const payload = {
            message,
            session_id: options.sessionId,
            quality_requirement: options.quality || 'balanced',
            max_cost: options.maxCost || 0.10,
            ...options
        };
        
        try {
            const response = await this.chatClient.post('/api/v1/chat/complete', payload);
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    async chatStream(message, options = {}) {
        const payload = {
            messages: [{ role: 'user', content: message }],
            session_id: options.sessionId,
            stream: true,
            ...options
        };
        
        try {
            const response = await this.chatClient.post('/api/v1/chat/stream', payload, {
                responseType: 'stream'
            });
            
            return new Promise((resolve, reject) => {
                let fullResponse = '';
                
                response.data.on('data', (chunk) => {
                    const lines = chunk.toString().split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') {
                                resolve(fullResponse);
                                return;
                            }
                            
                            try {
                                const parsed = JSON.parse(data);
                                const content = parsed.choices?.[0]?.delta?.content || '';
                                if (content) {
                                    fullResponse += content;
                                    if (options.onChunk) {
                                        options.onChunk(content);
                                    }
                                }
                            } catch (e) {
                                // Ignore parsing errors for incomplete chunks
                            }
                        }
                    }
                });
                
                response.data.on('error', reject);
            });
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    // Research Methods
    async researchDeepDive(researchQuestion, options = {}) {
        const payload = {
            research_question: researchQuestion,
            methodology: options.methodology || 'systematic',
            depth_level: options.depthLevel || 3,
            time_budget: options.timeBudget || 300,
            cost_budget: options.costBudget || 0.50,
            ...options
        };
        
        try {
            const response = await this.chatClient.post('/api/v1/research/deep-dive', payload);
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    // Document Methods
    async uploadDocument(filePath, metadata = {}) {
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        
        if (metadata && Object.keys(metadata).length > 0) {
            form.append('metadata', JSON.stringify(metadata));
        }
        
        try {
            const response = await this.docClient.post('/api/v2/documents/upload', form, {
                headers: {
                    ...form.getHeaders(),
                    ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
                }
            });
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    async searchDocuments(query, options = {}) {
        const payload = {
            query,
            max_results: options.maxResults || 10,
            search_type: options.searchType || 'hybrid',
            include_content: options.includeContent !== false,
            ...options
        };
        
        try {
            const response = await this.docClient.post('/api/v2/search/ultra-fast', payload);
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    async ragQuery(query, options = {}) {
        const payload = {
            query,
            max_context_length: options.maxContextLength || 4000,
            include_sources: options.includeSources !== false,
            ...options
        };
        
        try {
            const response = await this.docClient.post('/api/v2/rag/query', payload);
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    // Utility Methods
    async getHealth() {
        const healthResults = {};
        
        try {
            const chatHealth = await this.chatClient.get('/health');
            healthResults.chatService = chatHealth.data;
        } catch (error) {
            healthResults.chatService = { status: 'unhealthy', error: error.message };
        }
        
        try {
            const docHealth = await this.docClient.get('/health');
            healthResults.documentService = docHealth.data;
        } catch (error) {
            healthResults.documentService = { status: 'unhealthy', error: error.message };
        }
        
        return healthResults;
    }
    
    async getUsageStats() {
        try {
            const response = await this.chatClient.get('/api/v1/analytics/usage');
            return response.data;
        } catch (error) {
            throw this._handleError(error);
        }
    }
    
    _handleError(error) {
        if (error.response) {
            return new Error(`API Error: ${error.response.status} - ${error.response.data.message || error.response.statusText}`);
        } else if (error.request) {
            return new Error('Network Error: No response received from server');
        } else {
            return new Error(`Request Error: ${error.message}`);
        }
    }
}

module.exports = UnifiedAIClient;

// Usage Example
async function main() {
    const client = new UnifiedAIClient({
        // apiKey: 'your-api-key-here' // Optional
    });
    
    try {
        // Check health
        const health = await client.getHealth();
        console.log('System Health:', health);
        
        // Chat completion
        const chatResult = await client.chatComplete(
            'Explain machine learning in simple terms',
            { quality: 'high', maxCost: 0.15 }
        );
        console.log('Chat Response:', chatResult.data.response.substring(0, 200) + '...');
        
        // Streaming chat
        console.log('\nStreaming Response:');
        await client.chatStream('Tell me about quantum computing', {
            onChunk: (chunk) => process.stdout.write(chunk)
        });
        console.log('\n');
        
        // Document search
        const searchResult = await client.searchDocuments('artificial intelligence', {
            maxResults: 5
        });
        console.log(`Found ${searchResult.results?.length || 0} documents`);
        
        // Deep research
        const researchResult = await client.researchDeepDive(
            'What are the benefits of renewable energy?',
            { depthLevel: 2 }
        );
        console.log('Research completed:', researchResult.data.research_findings.substring(0, 200) + '...');
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

if (require.main === module) {
    main();
}
```

## 🎯 Best Practices

### Effective Prompt Engineering

#### Chat Conversations

**Good Prompts:**
```
❌ Bad: "Tell me about AI"
✅ Good: "Explain how machine learning algorithms work in recommender systems, focusing on collaborative filtering and content-based approaches. Include practical examples from Netflix or Amazon."

❌ Bad: "Help with coding"
✅ Good: "I'm building a REST API in Python using FastAPI. Show me how to implement JWT authentication with proper error handling and security best practices."

❌ Bad: "Research topic"
✅ Good: "Conduct a comprehensive analysis of renewable energy adoption trends in Europe from 2020-2024, focusing on policy impacts, cost reductions, and grid integration challenges."
```

**Conversation Context:**
```python
# Maintain conversation context for better responses
session_id = "project_planning_session"

# First message
response1 = client.chat_complete(
    "I'm planning a machine learning project to predict customer churn. What approach should I take?",
    session_id=session_id
)

# Follow-up message (uses previous context)
response2 = client.chat_complete(
    "What about data preprocessing steps for the approach you suggested?",
    session_id=session_id
)
```

#### Document Search Queries

**Search Query Optimization:**

```python
# Specific queries yield better results
❌ vague_query = "AI stuff"
✅ specific_query = "transformer architecture attention mechanisms BERT"

# Use domain-specific terminology
❌ general_query = "how to make things faster"
✅ technical_query = "algorithm optimization techniques computational complexity"

# Combine concepts for hybrid search
❌ simple_query = "neural networks"
✅ comprehensive_query = "neural network optimization gradient descent backpropagation"
```

#### Research Requests

**Structured Research Questions:**

```python
# Well-structured research request
research_request = {
    "research_question": "What are the most effective strategies for reducing carbon emissions in urban transportation systems, and what evidence exists for their implementation success?",
    "methodology": "systematic",
    "depth_level": 4,
    "sources": ["academic", "government", "industry"],
    "focus_areas": [
        "Electric vehicle adoption",
        "Public transportation improvements", 
        "Active transportation infrastructure",
        "Policy effectiveness"
    ]
}
```

### Cost Optimization Strategies

#### Budget Management

```python
# Set appropriate cost limits for different use cases
cost_limits = {
    "quick_questions": 0.05,      # Simple factual queries
    "detailed_analysis": 0.20,    # Complex analysis requests
    "research_projects": 0.50,    # Deep research tasks
    "document_processing": 0.10   # Document upload and indexing
}

# Use quality levels strategically
quality_mapping = {
    "draft_responses": "minimal",    # For brainstorming
    "standard_work": "balanced",     # Most common use
    "final_deliverables": "high",    # Important outputs
    "critical_analysis": "premium"   # Highest stakes work
}
```

#### Efficient Usage Patterns

```python
# Batch similar requests
def batch_document_analysis(documents, query_template):
    results = []
    session_id = "batch_analysis_session"
    
    for doc in documents:
        query = query_template.format(document=doc['title'])
        result = client.chat_complete(
            query,
            session_id=session_id,  # Reuse context
            quality="balanced",
            max_cost=0.08
        )
        results.append(result)
    
    return results

# Cache frequently used information
cache = {}
def cached_search(query):
    if query in cache:
        return cache[query]
    
    result = client.search_documents(query)
    cache[query] = result
    return result
```

### Quality and Performance

#### Response Quality Control

```python
# Verify response quality
def quality_check(response_data):
    metadata = response_data.get('metadata', {})
    
    quality_indicators = {
        'confidence': metadata.get('confidence', 0),
        'execution_time': metadata.get('execution_time', 0),
        'sources_count': len(response_data.get('data', {}).get('sources', [])),
        'response_length': len(response_data.get('data', {}).get('response', ''))
    }
    
    # Quality thresholds
    if quality_indicators['confidence'] < 0.7:
        print("⚠️ Low confidence response - consider rephrasing query")
    
    if quality_indicators['execution_time'] > 10:
        print("⚠️ Slow response - consider simplifying request")
    
    if quality_indicators['sources_count'] == 0:
        print("⚠️ No sources provided - response may lack context")
    
    return quality_indicators
```

#### Performance Monitoring

```python
import time
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def track_request(self, endpoint, execution_time, cost, success):
        self.metrics[endpoint].append({
            'timestamp': time.time(),
            'execution_time': execution_time,
            'cost': cost,
            'success': success
        })
    
    def get_performance_report(self):
        report = {}
        
        for endpoint, metrics in self.metrics.items():
            successful_requests = [m for m in metrics if m['success']]
            
            if successful_requests:
                avg_time = sum(m['execution_time'] for m in successful_requests) / len(successful_requests)
                avg_cost = sum(m['cost'] for m in successful_requests) / len(successful_requests)
                success_rate = len(successful_requests) / len(metrics)
                
                report[endpoint] = {
                    'avg_execution_time': round(avg_time, 2),
                    'avg_cost': round(avg_cost, 4),
                    'success_rate': round(success_rate, 2),
                    'total_requests': len(metrics)
                }
        
        return report

# Usage
monitor = PerformanceMonitor()

# Track requests
start_time = time.time()
try:
    result = client.chat_complete("Your query here")
    execution_time = time.time() - start_time
    cost = result['metadata']['cost']
    monitor.track_request('chat_complete', execution_time, cost, True)
except Exception:
    execution_time = time.time() - start_time
    monitor.track_request('chat_complete', execution_time, 0, False)

# Generate report
performance_report = monitor.get_performance_report()
```

## ⚖️ Limitations & Guidelines

### System Limitations

#### Technical Limitations

**Response Limits:**
- Maximum message length: 8,000 characters
- Maximum response length: 4,000 tokens (~3,000 words)
- Session timeout: 2 hours of inactivity
- File upload size limit: 100MB per document
- Concurrent requests: 100 per user

**Processing Limitations:**
- Document indexing time: 30 seconds - 5 minutes depending on size
- Research queries: Maximum 5 minutes processing time
- Context window: 4,000 tokens for conversation history
- Search results: Maximum 100 results per query

#### Content Guidelines

**Supported Content Types:**
- ✅ Educational and informational content
- ✅ Technical documentation and analysis
- ✅ Business and professional content
- ✅ Creative writing and brainstorming
- ✅ Code development and debugging

**Restricted Content:**
- ❌ Personal medical advice (general health info is OK)
- ❌ Legal advice (legal information is OK)
- ❌ Financial advice (market analysis is OK)
- ❌ Harmful or illegal content
- ❌ Personal information processing

#### Accuracy Considerations

**High Accuracy Areas:**
- Technical documentation and code
- Mathematical calculations
- Scientific concepts and principles
- Historical facts and events

**Variable Accuracy Areas:**
- Current events (depends on training data cutoff)
- Rapidly changing information
- Highly specialized domain knowledge
- Subjective analysis and opinions

**Quality Indicators:**
```python
def interpret_confidence_score(confidence):
    if confidence >= 0.9:
        return "Very High - Information is well-supported"
    elif confidence >= 0.8:
        return "High - Information is reliable"
    elif confidence >= 0.7:
        return "Moderate - Cross-check important details"
    elif confidence >= 0.6:
        return "Low - Verify information independently"
    else:
        return "Very Low - Use with caution"
```

### Usage Guidelines

#### Effective System Usage

**Do's:**
- ✅ Provide clear, specific requests
- ✅ Use session IDs for related conversations
- ✅ Set appropriate cost and quality limits
- ✅ Provide context for complex questions
- ✅ Use document upload for domain-specific knowledge
- ✅ Verify important information independently

**Don'ts:**
- ❌ Don't rely solely on AI for critical decisions
- ❌ Don't ignore confidence scores and quality indicators
- ❌ Don't upload sensitive or confidential documents
- ❌ Don't exceed reasonable usage patterns
- ❌ Don't expect perfect accuracy on all topics

#### Security Best Practices

**Data Protection:**
```python
# Sanitize sensitive data before requests
import re

def sanitize_request(text):
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Remove phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Remove potential credit card numbers
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
    
    return text

# Use before sending requests
safe_message = sanitize_request(user_message)
result = client.chat_complete(safe_message)
```

**Document Security:**
- Only upload documents you have permission to process
- Avoid uploading documents with personal information
- Use metadata to categorize and manage document access
- Regularly review and clean up uploaded documents

## 💰 Cost Management

### Understanding Costs

#### Cost Structure

**AI Chat Service Costs:**
```python
cost_breakdown = {
    "local_models": {
        "phi3:mini": 0.00,      # Free (local processing)
        "llama3.2": 0.00        # Free (local processing)
    },
    "premium_processing": {
        "high_quality": 0.08,   # Per request
        "premium_quality": 0.15  # Per request
    },
    "web_search": {
        "basic_search": 0.05,   # Per search query
        "deep_research": 0.25   # Per research session
    }
}
```

**Document Search Service Costs:**
```python
document_costs = {
    "indexing": {
        "per_document": 0.02,   # One-time indexing cost
        "per_page": 0.001       # For large documents
    },
    "searching": {
        "basic_search": 0.01,   # Per search query
        "rag_query": 0.03       # Per RAG generation
    }
}
```

#### Budget Planning

```python
class BudgetPlanner:
    def __init__(self, monthly_budget=50.0):
        self.monthly_budget = monthly_budget
        self.current_spend = 0.0
        self.usage_log = []
    
    def estimate_costs(self, usage_plan):
        """Estimate monthly costs based on usage plan."""
        estimates = {
            'chat_requests': usage_plan.get('chat_requests', 0) * 0.08,
            'research_queries': usage_plan.get('research_queries', 0) * 0.25,
            'document_uploads': usage_plan.get('document_uploads', 0) * 0.02,
            'document_searches': usage_plan.get('document_searches', 0) * 0.01
        }
        
        total_estimate = sum(estimates.values())
        
        return {
            'breakdown': estimates,
            'total_monthly_estimate': total_estimate,
            'budget_utilization': (total_estimate / self.monthly_budget) * 100,
            'recommendations': self._get_cost_recommendations(estimates)
        }
    
    def _get_cost_recommendations(self, estimates):
        recommendations = []
        
        if estimates['chat_requests'] > self.monthly_budget * 0.5:
            recommendations.append("Consider using 'balanced' quality for routine queries")
        
        if estimates['research_queries'] > self.monthly_budget * 0.3:
            recommendations.append("Use research queries for complex topics only")
        
        if estimates['document_searches'] > estimates['document_uploads'] * 5:
            recommendations.append("Upload more documents to reduce web search costs")
        
        return recommendations

# Usage example
planner = BudgetPlanner(monthly_budget=100.0)

# Estimate costs for planned usage
usage_plan = {
    'chat_requests': 200,      # 200 chat requests per month
    'research_queries': 10,    # 10 research sessions per month
    'document_uploads': 50,    # 50 document uploads per month
    'document_searches': 300   # 300 document searches per month
}

cost_estimate = planner.estimate_costs(usage_plan)
print(f"Estimated monthly cost: ₹{cost_estimate['total_monthly_estimate']:.2f}")
print(f"Budget utilization: {cost_estimate['budget_utilization']:.1f}%")
```

### Cost Optimization Strategies

#### Smart Quality Selection

```python
def smart_quality_selection(query_type, importance_level, budget_remaining):
    """Select optimal quality based on context."""
    
    quality_map = {
        ('factual', 'low', 'any'): 'minimal',
        ('factual', 'medium', 'any'): 'balanced',
        ('factual', 'high', 'any'): 'high',
        
        ('analysis', 'low', 'high'): 'balanced',
        ('analysis', 'medium', 'high'): 'high',
        ('analysis', 'high', 'any'): 'premium',
        
        ('creative', 'any', 'any'): 'balanced',
        ('research', 'any', 'high'): 'high'
    }
    
    budget_level = 'high' if budget_remaining > 0.5 else 'low'
    
    key = (query_type, importance_level, budget_level)
    
    # Try exact match first, then fallbacks
    for fallback_key in [key, (query_type, importance_level, 'any'), ('any', 'any', 'any')]:
        if fallback_key in quality_map:
            return quality_map[fallback_key]
    
    return 'balanced'

# Example usage
query_info = {
    'type': 'analysis',
    'importance': 'high',
    'budget_remaining_ratio': 0.3
}

recommended_quality = smart_quality_selection(
    query_info['type'],
    query_info['importance'],
    query_info['budget_remaining_ratio']
)
```

#### Efficient Workflows

```python
class EfficientWorkflow:
    def __init__(self, client):
        self.client = client
        self.document_cache = {}
        self.response_cache = {}
    
    async def research_with_documents_first(self, topic, uploaded_docs=None):
        """Try document search before web research."""
        
        # Step 1: Search uploaded documents first (cheaper)
        if uploaded_docs:
            doc_results = await self.client.search_documents(
                topic, 
                max_results=10
            )
            
            if doc_results.get('results'):
                # Use RAG if we have good document matches
                rag_response = await self.client.rag_query(
                    f"Based on the available documents, {topic}",
                    max_context_length=3000
                )
                
                # Check if document-based response is sufficient
                if rag_response['confidence'] > 0.8:
                    return {
                        'response': rag_response['answer'],
                        'cost': 0.03,  # RAG cost
                        'source': 'documents',
                        'confidence': rag_response['confidence']
                    }
        
        # Step 2: Fall back to web research if needed
        research_response = await self.client.research_deep_dive(
            topic,
            depth_level=2  # Start with moderate depth
        )
        
        return {
            'response': research_response['data']['research_findings'],
            'cost': research_response['metadata']['cost'],
            'source': 'web_research',
            'confidence': research_response['metadata'].get('confidence', 0.8)
        }
    
    async def progressive_quality_refinement(self, query, max_cost=0.50):
        """Start with lower quality and refine if needed."""
        
        # Start with balanced quality
        initial_response = await self.client.chat_complete(
            query,
            quality="balanced",
            max_cost=0.10
        )
        
        # Check if refinement is needed
        if (initial_response['metadata']['confidence'] < 0.8 and 
            initial_response['metadata']['cost'] < max_cost * 0.5):
            
            refined_response = await self.client.chat_complete(
                f"Please provide a more detailed and accurate response to: {query}",
                quality="high",
                max_cost=max_cost - initial_response['metadata']['cost']
            )
            
            return refined_response
        
        return initial_response
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Connection Issues

**Problem**: Cannot connect to services
```python
import requests
import time

def diagnose_connection():
    services = {
        'AI Chat': 'http://localhost:8003/health',
        'Document Search': 'http://localhost:8001/health',
        'API Docs': 'http://localhost:8003/docs'
    }
    
    results = {}
    
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            results[name] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            results[name] = {
                'status': 'unreachable',
                'error': str(e)
            }
    
    return results

# Run diagnosis
diagnosis = diagnose_connection()
for service, status in diagnosis.items():
    print(f"{service}: {status}")
```

**Solutions:**
1. Check if services are running: `docker-compose ps`
2. Verify port availability: `netstat -tulpn | grep :8003`
3. Check firewall settings
4. Restart services: `docker-compose restart`

#### API Response Issues

**Problem**: Slow or failed API responses
```python
import asyncio
from datetime import datetime

async def test_api_performance():
    """Test API performance and identify issues."""
    
    test_cases = [
        {
            'name': 'Simple Query',
            'payload': {'message': 'Hello', 'max_cost': 0.05},
            'expected_time': 2.0
        },
        {
            'name': 'Complex Analysis',
            'payload': {'message': 'Analyze the economic impact of AI', 'max_cost': 0.15},
            'expected_time': 8.0
        },
        {
            'name': 'Document Search',
            'payload': {'query': 'machine learning'},
            'expected_time': 1.0
        }
    ]
    
    async with UnifiedAIClient() as client:
        for test in test_cases:
            start_time = datetime.now()
            
            try:
                if 'query' in test['payload']:
                    # Document search test
                    result = await client.search_documents(**test['payload'])
                else:
                    # Chat test
                    result = await client.chat_complete(**test['payload'])
                
                elapsed = (datetime.now() - start_time).total_seconds()
                
                status = 'PASS' if elapsed <= test['expected_time'] else 'SLOW'
                print(f"{test['name']}: {status} ({elapsed:.2f}s)")
                
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"{test['name']}: FAILED ({elapsed:.2f}s) - {e}")

# Run performance test
asyncio.run(test_api_performance())
```

#### Document Processing Issues

**Problem**: Documents not indexing properly
```python
def debug_document_upload(file_path):
    """Debug document upload and indexing issues."""
    
    import os
    import mimetypes
    
    # Check file
    if not os.path.exists(file_path):
        return {"error": "File does not exist"}
    
    file_size = os.path.getsize(file_path)
    file_type = mimetypes.guess_type(file_path)[0]
    
    print(f"File: {file_path}")
    print(f"Size: {file_size / (1024*1024):.2f} MB")
    print(f"Type: {file_type}")
    
    # Check file size limit
    if file_size > 100 * 1024 * 1024:  # 100MB
        return {"error": "File too large (>100MB)"}
    
    # Check supported formats
    supported_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/csv',
        'application/json'
    ]
    
    if file_type not in supported_types:
        return {"error": f"Unsupported file type: {file_type}"}
    
    # Try upload
    try:
        client = DocumentSearchClient()
        result = client.upload_document(file_path, {"test": "debug"})
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": f"Upload failed: {e}"}

# Usage
debug_result = debug_document_upload("problem_document.pdf")
print(debug_result)
```

### Performance Optimization

#### Client-Side Optimizations

```python
import asyncio
from typing import List, Dict, Any

class OptimizedClient:
    def __init__(self):
        self.client = UnifiedAIClient()
        self.request_queue = asyncio.Queue()
        self.response_cache = {}
        self.batch_size = 5
    
    async def batch_chat_requests(self, messages: List[str]) -> List[Dict[str, Any]]:
        """Process multiple chat requests efficiently."""
        
        # Group into batches
        batches = [messages[i:i+self.batch_size] for i in range(0, len(messages), self.batch_size)]
        
        results = []
        
        for batch in batches:
            # Process batch concurrently
            tasks = [
                self.client.chat_complete(msg, max_cost=0.08) 
                for msg in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        'error': str(result),
                        'original_message': batch[i]
                    })
                else:
                    results.append(result)
            
            # Small delay between batches to avoid overwhelming the server
            await asyncio.sleep(0.5)
        
        return results
    
    async def smart_document_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Optimized document search with caching."""
        
        cache_key = f"{query}:{max_results}"
        
        # Check cache first
        if cache_key in self.response_cache:
            cached_result = self.response_cache[cache_key]
            # Use cached result if less than 1 hour old
            if time.time() - cached_result['timestamp'] < 3600:
                return cached_result['data']
        
        # Perform search
        result = await self.client.search_documents(query, max_results=max_results)
        
        # Cache result
        self.response_cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        return result

# Usage
async def optimized_workflow():
    opt_client = OptimizedClient()
    
    # Batch process multiple questions
    questions = [
        "What is machine learning?",
        "Explain neural networks",
        "How does AI work?",
        "What are transformers in AI?"
    ]
    
    results = await opt_client.batch_chat_requests(questions)
    
    for i, result in enumerate(results):
        if 'error' in result:
            print(f"Question {i+1} failed: {result['error']}")
        else:
            print(f"Question {i+1}: {result['data']['response'][:100]}...")

# Run optimized workflow
asyncio.run(optimized_workflow())
```

## ❓ FAQ

### General Questions

**Q: What's the difference between the AI Chat Service and Document Search Service?**

A: The AI Chat Service handles conversational AI, web research, and multi-agent workflows. The Document Search Service specializes in fast document indexing, searching, and RAG (Retrieval Augmented Generation). They work together to provide comprehensive AI capabilities.

**Q: Can I use the system offline?**

A: Partially. The local AI models (Ollama) work offline, but web search features require internet connectivity. Document search works offline once documents are indexed.

**Q: How accurate are the AI responses?**

A: Accuracy varies by topic and is indicated by confidence scores:
- 90%+: Very reliable for well-documented topics
- 80-90%: Generally accurate, suitable for most use cases
- 70-80%: Good but verify important details
- Below 70%: Use with caution, cross-check information

### Technical Questions

**Q: What file formats are supported for document upload?**

A: Supported formats include:
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Plain text (.txt)
- Markdown (.md)
- CSV (.csv)
- JSON (.json)

Maximum file size: 100MB per document.

**Q: How long does document indexing take?**

A: Indexing time depends on document size and complexity:
- Small text files: 5-15 seconds
- PDF documents: 30 seconds - 2 minutes
- Large documents (50MB+): 2-5 minutes

**Q: Can I delete or update uploaded documents?**

A: Currently, documents persist in the system once uploaded. Future versions will include document management features. For now, use descriptive metadata to organize documents.

**Q: What's the maximum conversation length?**

A: Conversations can continue indefinitely, but the system maintains context for the last 4,000 tokens (approximately 3,000 words) per session.

### Cost and Usage Questions

**Q: How much does it cost to use the system?**

A: Local processing (using Ollama models) is free. Costs apply for:
- Premium processing: ₹0.08-0.15 per request
- Web search: ₹0.05-0.25 per query
- Document indexing: ₹0.02 per document
- RAG queries: ₹0.03 per query

**Q: How can I monitor my usage costs?**

A: Use the usage analytics endpoint:
```python
usage_stats = await client.get_usage_stats()
print(f"Cost today: ₹{usage_stats['data']['cost_today']}")
print(f"Monthly cost: ₹{usage_stats['data']['cost_this_month']}")
```

**Q: What happens if I exceed my budget?**

A: Requests are rejected with a budget exceeded error. You can:
- Increase your monthly budget
- Wait for the next billing cycle
- Use lower-cost quality settings

### Security and Privacy Questions

**Q: Is my data secure?**

A: Security measures include:
- Local processing for sensitive data
- No permanent storage of conversation content
- Document encryption at rest
- Secure API communication (HTTPS in production)

**Q: What data is logged?**

A: The system logs:
- Request metadata (timestamps, costs, performance)
- Error information for debugging
- Usage statistics (anonymized)

We do NOT log:
- Message content
- Document content
- Personal information

**Q: Can I run this completely on-premises?**

A: Yes, the system is designed for on-premises deployment. Only web search features require external API access, which can be disabled for fully isolated deployments.

### Integration Questions

**Q: Can I integrate this with my existing applications?**

A: Yes, the system provides:
- REST APIs for all functionality
- Python and JavaScript SDKs
- OpenAPI/Swagger documentation
- Webhook support (planned)

**Q: Does it support multiple users?**

A: The current version supports multiple concurrent users through session management. Enterprise features like user authentication and access control are available in the premium version.

**Q: Can I customize the AI models?**

A: You can:
- Add new Ollama models
- Configure model selection preferences
- Adjust quality and cost parameters
- Fine-tune responses through prompt engineering

**Q: How do I backup my data?**

A: Regular backups should include:
- Document storage directory
- Redis database (for cache and sessions)
- Configuration files
- Uploaded document indexes

```bash
# Example backup script
docker exec unified-redis redis-cli BGSAVE
docker cp unified-redis:/data/dump.rdb ./backup/
tar -czf backup/documents-$(date +%Y%m%d).tar.gz ./document-search-service/data/
```

### Performance Questions

**Q: How fast are the responses?**

A: Typical response times:
- Simple chat: 1-3 seconds
- Complex analysis: 5-15 seconds
- Document search: 0.1-0.5 seconds
- Web research: 30-60 seconds
- Document indexing: 30 seconds - 5 minutes

**Q: How many concurrent users are supported?**

A: The system supports 100+ concurrent users with proper resource allocation. Performance depends on:
- Available CPU and memory
- GPU availability for faster processing
- Network bandwidth
- Storage I/O capacity

**Q: Can I improve performance?**

A: Performance optimization strategies:
- Use appropriate quality settings
- Enable GPU acceleration
- Implement request caching
- Use document search before web search
- Batch similar requests

---

## 📞 Support Resources

### Documentation
- **API Documentation**: http://localhost:8003/docs
- **Interactive Examples**: http://localhost:8003/redoc
- **Health Status**: http://localhost:8003/health

### Community
- **GitHub Repository**: [Project Repository]
- **Issue Tracker**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]
- **Discord Community**: [Community Discord]

### Professional Support
- **Enterprise Support**: enterprise@yourdomain.com
- **Technical Consulting**: consulting@yourdomain.com
- **Training Services**: training@yourdomain.com

---

**User Guide Version**: 2.0  
**Last Updated**: January 2025  
**Compatible with**: Unified AI System v1.0+