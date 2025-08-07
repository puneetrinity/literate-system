# End-to-End (E2E) Testing Suite

This comprehensive E2E testing suite validates cross-service workflows, performance characteristics, and deployment configurations for the unified AI system.

## 🏗️ Architecture Overview

The E2E testing suite is designed with a multi-layered approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Orchestrator                        │
│  • Test sequencing and dependency management               │
│  • Performance monitoring and reporting                    │
│  • CI/CD pipeline integration                             │
└─────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│  Performance   │    │   API Workflow  │    │   Data Flow     │
│   Testing      │    │    Testing      │    │   Validation    │
│                │    │                 │    │                 │
│ • Load testing │    │ • Multi-step    │    │ • Document      │
│ • Latency      │    │   workflows     │    │   processing    │
│ • Concurrency  │    │ • Streaming     │    │ • Memory        │
│ • Memory usage │    │ • Error handling│    │   persistence   │
└────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
    ┌───────────────────────────▼───────────────────────────┐
    │              Cross-Service Integration                │
    │  • Service health validation                          │
    │  • Document upload → search → chat workflows         │
    │  • User journey simulation                           │
    │  • Service resilience testing                       │
    └─────────────────────────────────────────────────────────┘
                                │
    ┌───────────────────────────▼───────────────────────────┐
    │             Deployment Validation                     │
    │  • Docker Compose configuration                       │
    │  • RunPod deployment validation                      │
    │  • Health checks and monitoring                      │
    │  • Configuration security                            │
    └─────────────────────────────────────────────────────────┘
```

## 📋 Test Suite Components

### 1. Performance E2E Tests (`test_performance_e2e.py`)
- **Load Testing**: Validates system behavior under concurrent user load
- **Latency Validation**: Ensures response times meet SLA requirements
- **Memory Monitoring**: Tracks memory usage during sustained operations
- **Concurrent User Simulation**: Tests realistic multi-user scenarios

### 2. API Workflow Tests (`test_api_workflow_e2e.py`)
- **Multi-step Workflows**: Complete document → search → chat pipelines
- **Streaming Validation**: Tests streaming response characteristics
- **Error Handling**: Validates graceful error recovery across services
- **Rate Limiting**: Tests rate limiting and cost management features

### 3. Data Flow Validation (`test_data_flow_e2e.py`)
- **Document Processing Pipeline**: End-to-end document ingestion validation
- **Memory Persistence**: Conversation memory across service interactions
- **Cache Consistency**: Redis cache behavior validation
- **Database Synchronization**: Data consistency across service boundaries

### 4. Cross-Service Integration (`test_cross_service_integration.py`)
- **Health Checks**: Service availability and responsiveness
- **Workflow Integration**: Complete user workflows across services
- **Service Resilience**: Behavior during service degradation
- **Multi-language Support**: International content handling

### 5. User Journey Tests (`test_user_journey.py`)
- **Research Workflows**: Academic/professional research scenarios
- **Collaborative Sessions**: Multi-user collaboration simulation
- **Error Recovery**: User experience during system issues
- **Performance Under Load**: User experience during high traffic

### 6. Deployment Validation (`test_deployment_validation_e2e.py`)
- **Docker Compose Validation**: Container orchestration testing
- **RunPod Configuration**: Cloud deployment validation
- **Security Configuration**: Security settings verification
- **Backup and Recovery**: Data persistence validation

### 7. Test Orchestrator (`test_orchestrator.py`)
- **Intelligent Sequencing**: Dependency-aware test execution
- **Resource Management**: Optimal resource utilization
- **CI/CD Integration**: Pipeline-friendly execution and reporting
- **Comprehensive Reporting**: Multi-format result generation

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Redis (for caching tests)
- At least 4GB RAM for performance tests

### Installation

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx docker pyyaml psutil redis aiofiles

# Or use the test runner to install automatically
python run_e2e_tests.py --install-deps
```

### Running Tests

#### Option 1: Orchestrated Execution (Recommended)
```bash
# Run complete E2E suite with intelligent orchestration
python run_e2e_tests.py --orchestrated --verbose

# Run specific test suites with orchestration  
python run_e2e_tests.py --orchestrated --filter "Health Checks" "Basic Integration"
```

#### Option 2: Individual Test Suites
```bash
# Run all tests
python run_e2e_tests.py --suite all

# Run specific test suite
python run_e2e_tests.py --suite performance --timeout 600

# Run tests matching pattern
python run_e2e_tests.py --pattern "*workflow*" --verbose
```

#### Option 3: Direct Pytest Execution
```bash
# Run from the e2e directory
cd tests/e2e

# Run all E2E tests
pytest -v

# Run specific test file
pytest test_performance_e2e.py -v

# Run with specific markers
pytest -m "performance" -v

# Run with custom timeout
pytest --timeout=600 -v
```

## 🏃 CI/CD Integration

The test suite includes comprehensive CI/CD integration via GitHub Actions:

### Workflow Triggers
- **Push/Pull Request**: Basic integration tests
- **Nightly Runs**: Complete performance and load testing
- **Manual Dispatch**: Custom test suite selection

### Test Matrix
The CI pipeline runs tests across multiple configurations:
- Environment: staging, production, local
- Test Types: health, integration, performance, data-flow
- Execution Mode: parallel vs sequential

### Reporting
- **JUnit XML**: For test result visualization
- **JSON Reports**: For programmatic analysis
- **Performance Metrics**: Response times, throughput, resource usage
- **PR Comments**: Automated result summaries

## 📊 Test Configuration

### Environment Variables
```bash
# Test Environment Configuration
export E2E_TESTS_ENABLED=true
export TEST_ENVIRONMENT=local
export REDIS_URL=redis://localhost:6380
export DOCUMENT_SEARCH_URL=http://localhost:8002
export AI_CHAT_URL=http://localhost:8004

# Performance Test Configuration
export MAX_CONCURRENT_USERS=15
export LOAD_TEST_DURATION=300
export PERFORMANCE_SLA_RESPONSE_TIME=2.0

# Resource Limits
export TEST_MEMORY_LIMIT_GB=4
export TEST_CPU_CORES=2
```

### Pytest Markers
Use markers to run specific test categories:

```bash
# Run only critical tests
pytest -m "critical" -v

# Run performance tests with extended timeout
pytest -m "performance" --timeout=600 -v

# Run tests that require Docker
pytest -m "requires_docker" -v

# Run integration tests excluding slow ones
pytest -m "integration and not slow" -v
```

## 🔧 Configuration Files

### `pytest.ini`
- Test discovery and execution configuration
- Marker definitions and timeout settings
- Logging and reporting configuration

### `conftest.py`
- Shared fixtures for all test modules
- Docker environment management
- Service client configuration
- Test data generation

### GitHub Actions (`../.github/workflows/e2e-tests.yml`)
- Multi-stage CI/CD pipeline
- Service orchestration in CI environment
- Result aggregation and reporting
- PR integration and notifications

## 📈 Performance Benchmarks

### Expected Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| Document Upload | < 3s | < 5s |
| Search Response | < 1s | < 2s |
| Chat Response | < 5s | < 8s |
| Streaming First Chunk | < 2s | < 3s |
| Concurrent Users | 15+ | 10+ |
| Memory Usage | < 1GB | < 1.5GB |
| Error Rate | < 2% | < 5% |

### Load Testing Scenarios

1. **Document Processing Load**
   - 15 concurrent users
   - 8 requests per user
   - 50ms think time between requests

2. **Chat Service Load**
   - 8 concurrent users
   - 5 requests per user
   - 500ms think time (realistic chat pace)

3. **Cross-Service Workflow**
   - Complete document upload → search → chat pipeline
   - End-to-end latency validation
   - Memory consistency verification

## 🐛 Troubleshooting

### Common Issues

#### Docker Connection Errors
```bash
# Check Docker daemon status
docker info

# Restart Docker service
sudo systemctl restart docker

# Clean up test containers
docker container prune -f
```

#### Redis Connection Issues
```bash
# Start Redis for testing
docker run -d -p 6380:6379 redis:7-alpine

# Check Redis connectivity
redis-cli -p 6380 ping
```

#### Memory Issues During Performance Tests
```bash
# Check available memory
free -h

# Monitor memory usage during tests
watch -n 1 'ps aux --sort=-%mem | head -10'

# Reduce concurrent users if needed
export MAX_CONCURRENT_USERS=8
```

#### Service Startup Timeouts
```bash
# Increase health check timeouts
export HEALTH_CHECK_TIMEOUT=60

# Check service logs
docker-compose logs ai-chat
docker-compose logs document-search
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Run with debug logging
pytest -v --log-cli-level=DEBUG

# Save debug logs to file
pytest -v --log-file=debug_test.log --log-file-level=DEBUG
```

## 📚 Advanced Usage

### Custom Test Data

Create custom test documents for specific scenarios:

```python
# In your test file
async def test_custom_scenario(test_documents):
    custom_doc = {
        "id": "custom_test_doc",
        "title": "Custom Test Document",
        "content": "Your custom content here...",
        "metadata": {"category": "custom", "tags": ["test"]}
    }
    
    # Upload and test with custom document
    response = await doc_client.post("/upload", json=custom_doc)
    # ... continue with test
```

### Performance Monitoring Integration

Integrate with monitoring systems:

```python
# Custom performance monitoring
@pytest.fixture
async def performance_monitor():
    monitor = PerformanceMonitor()
    await monitor.start()
    yield monitor
    metrics = await monitor.stop()
    
    # Send to monitoring system
    send_to_datadog(metrics)  # Example integration
```

### Custom Reporting

Generate custom reports:

```python
# Custom report generation
def generate_custom_report(results):
    report = CustomReportGenerator()
    report.add_performance_data(results)
    report.add_business_metrics(results)
    report.export_to_dashboard()
```

## 🤝 Contributing

### Adding New Tests

1. **Choose the appropriate test module** based on test category
2. **Follow naming conventions**: `test_*` for functions, `Test*` for classes
3. **Use appropriate markers** to categorize tests
4. **Include performance assertions** where relevant
5. **Add proper cleanup** in fixtures or teardown methods

### Test Development Guidelines

1. **Isolation**: Tests should not depend on external state
2. **Repeatability**: Tests should produce consistent results
3. **Performance**: Include performance validations where appropriate
4. **Error Handling**: Test both success and failure scenarios
5. **Documentation**: Include clear docstrings and comments

### Example Test Structure

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient

class TestNewFeature:
    """Test suite for new feature validation."""
    
    @pytest_asyncio.fixture(autouse=True) 
    async def setup_method(self, document_search_client, ai_chat_client):
        """Setup test environment for each test."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        
    @pytest.mark.integration
    @pytest.mark.requires_services
    async def test_new_feature_workflow(self):
        """Test complete workflow for new feature."""
        # Arrange
        test_data = {"key": "value"}
        
        # Act
        response = await self.doc_client.post("/new-endpoint", json=test_data)
        
        # Assert
        assert response.status_code == 200
        assert "expected_field" in response.json()
        
        # Performance assertion
        assert response.elapsed.total_seconds() < 2.0
```

## 📄 License

This E2E testing suite is part of the unified AI system project and follows the same licensing terms as the main project.

---

For questions, issues, or contributions, please refer to the main project documentation or create an issue in the project repository.