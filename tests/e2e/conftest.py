"""
E2E Test Configuration and Fixtures

This module provides comprehensive test configuration for end-to-end testing
across the unified AI system services.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

import docker
import pytest
import pytest_asyncio
from httpx import AsyncClient, Timeout
from docker.models.containers import Container

# Service configuration
SERVICES_CONFIG = {
    "redis": {
        "container_name": "e2e-test-redis",
        "image": "redis:7-alpine",
        "ports": {"6379/tcp": 6380},
        "environment": {},
        "health_check": {"endpoint": None, "command": ["redis-cli", "ping"]},
        "startup_timeout": 30
    },
    "document-search": {
        "container_name": "e2e-test-document-search",
        "build_path": "./document-search-service",
        "ports": {"8001/tcp": 8002},
        "environment": {
            "REDIS_URL": "redis://localhost:6380",
            "ENVIRONMENT": "test",
            "DEBUG": "true"
        },
        "health_check": {"endpoint": "http://localhost:8002/health"},
        "startup_timeout": 60
    },
    "ai-chat": {
        "container_name": "e2e-test-ai-chat",
        "build_path": "./ai-chat-service",
        "ports": {"8003/tcp": 8004},
        "environment": {
            "REDIS_URL": "redis://localhost:6380",
            "DOCUMENT_SEARCH_URL": "http://localhost:8002",
            "ENVIRONMENT": "test",
            "DEBUG": "true",
            "DEFAULT_MONTHLY_BUDGET": "50.0"
        },
        "health_check": {"endpoint": "http://localhost:8004/health"},
        "startup_timeout": 60
    }
}


class E2ETestEnvironment:
    """Manages E2E test environment with containerized services."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.containers: Dict[str, Container] = {}
        self.temp_data_dir = None
        
    async def setup(self):
        """Set up the complete test environment."""
        # Create temporary data directory
        self.temp_data_dir = tempfile.mkdtemp(prefix="e2e_test_")
        
        # Start services in dependency order
        await self._start_service("redis")
        await self._start_service("document-search")
        await self._start_service("ai-chat")
        
        # Wait for all services to be healthy
        await self._wait_for_services_healthy()
        
    async def teardown(self):
        """Tear down the test environment."""
        # Stop and remove containers
        for service_name, container in self.containers.items():
            try:
                container.stop(timeout=10)
                container.remove()
                print(f"Stopped and removed {service_name} container")
            except Exception as e:
                print(f"Error stopping {service_name}: {e}")
        
        # Clean up temporary data
        if self.temp_data_dir and os.path.exists(self.temp_data_dir):
            import shutil
            shutil.rmtree(self.temp_data_dir, ignore_errors=True)
            
    async def _start_service(self, service_name: str):
        """Start a specific service container."""
        config = SERVICES_CONFIG[service_name]
        
        try:
            # Remove existing container if it exists
            try:
                existing = self.docker_client.containers.get(config["container_name"])
                existing.stop(timeout=5)
                existing.remove()
            except docker.errors.NotFound:
                pass
            
            # Prepare container arguments
            container_args = {
                "name": config["container_name"],
                "ports": config["ports"],
                "environment": config["environment"],
                "detach": True,
                "remove": False,
                "network_mode": "bridge"
            }
            
            # Build or use image
            if "build_path" in config:
                # Build image for the service
                print(f"Building image for {service_name}...")
                image, logs = self.docker_client.images.build(
                    path=config["build_path"],
                    tag=f"e2e-test-{service_name}:latest",
                    forcerm=True
                )
                container_args["image"] = image.id
            else:
                container_args["image"] = config["image"]
            
            # Add volumes for services that need data persistence
            if service_name == "document-search":
                container_args["volumes"] = {
                    f"{self.temp_data_dir}/documents": {"bind": "/app/data", "mode": "rw"},
                    f"{self.temp_data_dir}/indexes": {"bind": "/app/indexes", "mode": "rw"}
                }
            elif service_name == "ai-chat":
                container_args["volumes"] = {
                    f"{self.temp_data_dir}/chat": {"bind": "/app/data", "mode": "rw"}
                }
            
            # Start container
            container = self.docker_client.containers.run(**container_args)
            self.containers[service_name] = container
            
            print(f"Started {service_name} container: {container.short_id}")
            
            # Wait for container to be ready
            await self._wait_for_service_ready(service_name)
            
        except Exception as e:
            print(f"Failed to start {service_name}: {e}")
            raise
            
    async def _wait_for_service_ready(self, service_name: str):
        """Wait for a service to be ready."""
        config = SERVICES_CONFIG[service_name]
        container = self.containers[service_name]
        timeout = config["startup_timeout"]
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check container is running
                container.reload()
                if container.status != "running":
                    await asyncio.sleep(2)
                    continue
                
                # Check health endpoint if available
                if config["health_check"]["endpoint"]:
                    async with AsyncClient(timeout=Timeout(10.0)) as client:
                        response = await client.get(config["health_check"]["endpoint"])
                        if response.status_code == 200:
                            print(f"{service_name} is ready")
                            return
                else:
                    # For Redis, check with command
                    if service_name == "redis":
                        result = container.exec_run(["redis-cli", "ping"])
                        if result.exit_code == 0 and b"PONG" in result.output:
                            print(f"{service_name} is ready")
                            return
                            
            except Exception as e:
                print(f"Health check failed for {service_name}: {e}")
                
            await asyncio.sleep(2)
            
        raise TimeoutError(f"{service_name} failed to become ready within {timeout}s")
        
    async def _wait_for_services_healthy(self):
        """Wait for all services to be healthy."""
        print("Waiting for all services to be healthy...")
        
        # Additional integration checks
        try:
            # Test Redis connection from document-search
            doc_container = self.containers["document-search"]
            result = doc_container.exec_run([
                "python", "-c", 
                "import redis; r = redis.from_url('redis://localhost:6380'); print(r.ping())"
            ])
            
            if result.exit_code != 0:
                print(f"Redis connection test failed: {result.output}")
                
        except Exception as e:
            print(f"Service health check warning: {e}")


@pytest_asyncio.fixture(scope="session")
async def e2e_environment():
    """Session-scoped fixture for E2E test environment."""
    # Skip in CI environments unless explicitly enabled
    if os.getenv("CI") and not os.getenv("E2E_TESTS_ENABLED"):
        pytest.skip("E2E tests skipped in CI environment")
        
    # Check Docker availability
    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")
        
    environment = E2ETestEnvironment()
    
    try:
        await environment.setup()
        yield environment
    finally:
        await environment.teardown()


@pytest_asyncio.fixture
async def document_search_client(e2e_environment):
    """HTTP client for document search service."""
    async with AsyncClient(
        base_url="http://localhost:8002",
        timeout=Timeout(30.0)
    ) as client:
        yield client


@pytest_asyncio.fixture
async def ai_chat_client(e2e_environment):
    """HTTP client for AI chat service."""
    async with AsyncClient(
        base_url="http://localhost:8004",
        timeout=Timeout(30.0)
    ) as client:
        yield client


@pytest_asyncio.fixture
async def test_documents(e2e_environment):
    """Create test documents for E2E testing."""
    documents = [
        {
            "id": "test_doc_1",
            "title": "Artificial Intelligence Overview",
            "content": """
            Artificial Intelligence (AI) is a branch of computer science that aims to create 
            intelligent machines capable of performing tasks that typically require human intelligence. 
            These tasks include learning, reasoning, problem-solving, perception, and language understanding.
            
            Machine Learning is a subset of AI that enables computers to learn and improve from experience 
            without being explicitly programmed. Deep Learning, a subset of machine learning, uses neural 
            networks with multiple layers to model and understand complex patterns in data.
            
            Applications of AI include natural language processing, computer vision, robotics, 
            autonomous vehicles, recommendation systems, and medical diagnosis.
            """,
            "metadata": {
                "category": "technology",
                "tags": ["AI", "machine learning", "deep learning"],
                "source": "test_document"
            }
        },
        {
            "id": "test_doc_2", 
            "title": "Climate Change and Sustainability",
            "content": """
            Climate change refers to long-term shifts in global temperatures and weather patterns. 
            While climate variations are natural, human activities have been the main driver of 
            climate change since the 1800s, primarily through burning fossil fuels.
            
            The greenhouse effect is caused by greenhouse gases trapping heat in Earth's atmosphere. 
            Key greenhouse gases include carbon dioxide (CO2), methane (CH4), and nitrous oxide (N2O).
            
            Sustainability involves meeting present needs without compromising future generations' 
            ability to meet their needs. This includes renewable energy, sustainable agriculture, 
            waste reduction, and conservation efforts.
            """,
            "metadata": {
                "category": "environment",
                "tags": ["climate change", "sustainability", "environment"],
                "source": "test_document"  
            }
        },
        {
            "id": "test_doc_3",
            "title": "Financial Markets and Investment",
            "content": """
            Financial markets are platforms where buyers and sellers trade financial securities, 
            commodities, and other fungible items at prices determined by supply and demand.
            
            Key types of financial markets include stock markets, bond markets, foreign exchange 
            markets, and commodity markets. Investment strategies range from conservative approaches 
            like bonds and index funds to more aggressive strategies involving individual stocks 
            and derivatives.
            
            Risk management is crucial in investing. Diversification helps spread risk across 
            different asset classes, sectors, and geographic regions. Portfolio allocation should 
            align with individual risk tolerance and investment goals.
            """,
            "metadata": {
                "category": "finance",
                "tags": ["investing", "financial markets", "portfolio management"],
                "source": "test_document"
            }
        }
    ]
    
    # Upload documents to document search service
    async with AsyncClient(
        base_url="http://localhost:8002",
        timeout=Timeout(30.0)
    ) as client:
        for doc in documents:
            response = await client.post("/upload", json=doc)
            if response.status_code not in [200, 201]:
                print(f"Failed to upload document {doc['id']}: {response.text}")
    
    # Wait for indexing to complete
    await asyncio.sleep(5)
    
    return documents


@pytest_asyncio.fixture
async def performance_monitor():
    """Monitor performance metrics during E2E tests."""
    metrics = {
        "start_time": time.time(),
        "requests": [],
        "errors": [],
        "response_times": []
    }
    
    def record_request(endpoint: str, method: str, duration: float, status_code: int):
        metrics["requests"].append({
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": status_code,
            "timestamp": time.time()
        })
        metrics["response_times"].append(duration)
        
        if status_code >= 400:
            metrics["errors"].append({
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "timestamp": time.time()
            })
    
    metrics["record_request"] = record_request
    
    yield metrics
    
    # Generate performance report
    total_time = time.time() - metrics["start_time"]
    avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"]) if metrics["response_times"] else 0
    error_rate = len(metrics["errors"]) / len(metrics["requests"]) if metrics["requests"] else 0
    
    print(f"\n=== E2E Performance Report ===")
    print(f"Total test duration: {total_time:.2f}s")
    print(f"Total requests: {len(metrics['requests'])}")
    print(f"Average response time: {avg_response_time:.3f}s")
    print(f"Error rate: {error_rate:.2%}")
    
    if metrics["errors"]:
        print(f"Errors encountered: {len(metrics['errors'])}")
        for error in metrics["errors"][:5]:  # Show first 5 errors
            print(f"  - {error['method']} {error['endpoint']}: {error['status_code']}")


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(e2e_environment):
    """Automatically cleanup test data after each test."""
    yield
    
    # Clear Redis cache
    try:
        import redis
        r = redis.from_url("redis://localhost:6380")
        r.flushall()
    except Exception as e:
        print(f"Failed to clear Redis cache: {e}")


# Helper functions for common E2E operations
async def wait_for_async_operation(operation_func, timeout: int = 30, interval: float = 1.0):
    """Wait for an async operation to complete successfully."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            result = await operation_func()
            if result:
                return result
        except Exception as e:
            print(f"Operation failed, retrying: {e}")
            
        await asyncio.sleep(interval)
        
    raise TimeoutError(f"Operation failed to complete within {timeout}s")


def assert_response_structure(response_data: dict, expected_fields: List[str]):
    """Assert that response contains expected fields."""
    for field in expected_fields:
        assert field in response_data, f"Missing field '{field}' in response"


def assert_performance_acceptable(duration: float, max_duration: float):
    """Assert that operation completed within acceptable time."""
    assert duration <= max_duration, f"Operation took {duration:.2f}s, expected <= {max_duration}s"