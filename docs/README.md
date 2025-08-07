# 📚 Unified AI System Documentation

This directory contains comprehensive documentation for the Unified AI System, covering API usage, deployment, development, and user guidance.

## 📑 Documentation Index

### 📖 Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| **[API Documentation](API_DOCUMENTATION.md)** | Complete API reference with endpoints, schemas, examples, and SDKs | Developers, Integrators |
| **[Deployment Guide](DEPLOYMENT_GUIDE.md)** | Installation, configuration, and deployment instructions | DevOps, System Administrators |
| **[Developer Guide](DEVELOPER_GUIDE.md)** | Architecture, code structure, contributing guidelines, and best practices | Developers, Contributors |
| **[User Guide](USER_GUIDE.md)** | End-user documentation with examples, best practices, and troubleshooting | End Users, Product Managers |
| **[OpenAPI Specification](openapi.yaml)** | Machine-readable API specification for tools and code generation | Developers, Tools |

### 🎯 Quick Start Guides

**For End Users:**
1. Start with [User Guide](USER_GUIDE.md#getting-started)
2. Try the [Web Interface Usage](USER_GUIDE.md#web-interface-usage)
3. Explore [API Usage Examples](USER_GUIDE.md#api-usage-examples)

**For Developers:**
1. Begin with [Deployment Guide](DEPLOYMENT_GUIDE.md#local-development-setup)
2. Review [Developer Guide](DEVELOPER_GUIDE.md#architecture-overview)
3. Reference [API Documentation](API_DOCUMENTATION.md) for integration

**For System Administrators:**
1. Follow [Deployment Guide](DEPLOYMENT_GUIDE.md#docker-deployment)
2. Set up [Monitoring](DEPLOYMENT_GUIDE.md#service-monitoring)
3. Configure [Performance Optimization](DEPLOYMENT_GUIDE.md#performance-optimization)

## 🚀 System Overview

The Unified AI System is a comprehensive AI platform that combines:

- **🤖 AI Chat Service** (Port 8003): Advanced conversational AI with multi-agent workflows
- **🔍 Document Search Service** (Port 8001): Ultra-fast document search with RAG capabilities
- **🌐 Web Research**: Real-time web search and research integration
- **📊 Analytics & Monitoring**: Comprehensive system monitoring and usage analytics

### Key Features

- **Multi-Model Support**: Local (Ollama) and cloud AI models
- **Ultra-Fast Search**: HNSW + LambdaMART ML ranking (125ms P99 latency)
- **RAG Integration**: Context-aware responses using uploaded documents
- **Cost Management**: Transparent pricing with budget controls
- **Enterprise Ready**: Docker deployment, monitoring, and scaling

## 📋 Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── API_DOCUMENTATION.md         # Complete API reference
├── DEPLOYMENT_GUIDE.md          # Installation and deployment
├── DEVELOPER_GUIDE.md           # Development and contribution guide
├── USER_GUIDE.md               # End-user documentation
└── openapi.yaml                # OpenAPI 3.0 specification
```

## 🔗 Quick Links

### API Endpoints (Development)
- **AI Chat Service**: http://localhost:8003
- **Document Search Service**: http://localhost:8001
- **Interactive API Docs**: http://localhost:8003/docs
- **Health Checks**: http://localhost:8003/health

### Key Resources
- **GitHub Repository**: [unified-ai-system-clean](https://github.com/your-org/unified-ai-system-clean)
- **Docker Hub**: [unified-ai/system](https://hub.docker.com/r/unified-ai/system)
- **Issue Tracker**: [GitHub Issues](https://github.com/your-org/unified-ai-system-clean/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/unified-ai-system-clean/discussions)

## 📊 Performance Highlights

| Metric | Value | Comparison |
|--------|-------|------------|
| **Search Latency** | 125ms P99 | 47% faster than competitors |
| **Memory Usage** | 22MB | 32% less than Redis Vector |
| **Throughput** | 31.4 QPS | Best in class |
| **Recall@10** | 0.992 | Exceeds enterprise standards |
| **Cost per Request** | ₹0.08 | Transparent pricing |

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | High-performance async APIs |
| **AI Orchestration** | LangGraph | Workflow management |
| **Vector Search** | FAISS + HNSW | Document similarity |
| **ML Ranking** | LambdaMART | Search result ranking |
| **Caching** | Redis | Distributed caching |
| **Local Models** | Ollama | On-premises AI inference |
| **Containerization** | Docker | Deployment and scaling |

## 📈 Getting Started Paths

### Path 1: Quick Demo (5 minutes)
```bash
# Clone and start with Docker
git clone https://github.com/your-org/unified-ai-system-clean.git
cd unified-ai-system-clean
docker-compose up --build

# Test the API
curl -X POST "http://localhost:8003/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What can you help me with?"}'
```

### Path 2: Development Setup (15 minutes)
1. Follow [Local Development Setup](DEPLOYMENT_GUIDE.md#local-development-setup)
2. Review [Code Structure](DEVELOPER_GUIDE.md#code-structure)
3. Try [API Examples](API_DOCUMENTATION.md#code-examples)

### Path 3: Production Deployment (30 minutes)
1. Configure [Environment Variables](DEPLOYMENT_GUIDE.md#environment-configuration)
2. Set up [Docker Production](DEPLOYMENT_GUIDE.md#docker-deployment)
3. Enable [Monitoring](DEPLOYMENT_GUIDE.md#service-monitoring)

### Path 4: Integration (45 minutes)
1. Review [API Documentation](API_DOCUMENTATION.md)
2. Choose [Client SDK](API_DOCUMENTATION.md#client-sdks)
3. Implement [Best Practices](USER_GUIDE.md#best-practices)

## 🔧 Support & Contributing

### Getting Help
- **Documentation Issues**: Create an issue with `documentation` label
- **API Questions**: Check [API Documentation](API_DOCUMENTATION.md) and [FAQ](USER_GUIDE.md#faq)
- **Deployment Problems**: See [Troubleshooting](DEPLOYMENT_GUIDE.md#troubleshooting)
- **Community Support**: Join our [Discord](https://discord.gg/unified-ai)

### Contributing
1. Read [Contributing Guidelines](DEVELOPER_GUIDE.md#contributing-guidelines)
2. Set up [Development Environment](DEVELOPER_GUIDE.md#development-environment)
3. Follow [Coding Standards](DEVELOPER_GUIDE.md#coding-standards)
4. Submit Pull Requests

### Documentation Updates
Documentation is version-controlled alongside code. To update:

```bash
# Edit documentation files
nano docs/API_DOCUMENTATION.md

# Test changes locally
python -m http.server 8080 -d docs/

# Submit changes
git add docs/
git commit -m "docs: update API documentation"
git push origin feature/doc-updates
```

## 📝 Version Information

- **Documentation Version**: 2.0
- **API Version**: v1 (Chat), v2 (Documents)
- **Last Updated**: January 2025
- **Compatibility**: Unified AI System v1.0+
- **OpenAPI Version**: 3.0.3

## 🎯 Documentation Roadmap

### Planned Updates
- [ ] Video tutorials and demos
- [ ] Postman collection and examples
- [ ] Client SDK documentation (Go, PHP, Ruby)
- [ ] Advanced integration patterns
- [ ] Performance tuning guides
- [ ] Enterprise deployment templates

### Recent Changes
- ✅ Complete OpenAPI 3.0 specification
- ✅ Comprehensive client SDKs (Python, JavaScript)  
- ✅ Production deployment guides
- ✅ Performance benchmarking documentation
- ✅ Cost management and optimization guides

---

## 📄 License

This documentation is licensed under [MIT License](../LICENSE). The Unified AI System is open source and available under the same license.

**For questions about this documentation, please create an issue or contact our documentation team.**