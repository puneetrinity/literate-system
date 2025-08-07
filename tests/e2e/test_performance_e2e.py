"""
Performance End-to-End Tests

Comprehensive performance testing across services including load testing,
latency validation, memory usage monitoring, and concurrent user simulation.
"""

import asyncio
import json
import time
import statistics
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import pytest
import pytest_asyncio
from httpx import AsyncClient, Timeout
import aiofiles


@dataclass
class PerformanceMetrics:
    """Container for performance test metrics."""
    test_name: str
    start_time: float
    end_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_95_response_time: float
    requests_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    concurrent_users: int = 1
    total_data_transferred_kb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return asdict(self)


class PerformanceMonitor:
    """Monitor system resources during performance tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
        
    async def start_monitoring(self, interval: float = 1.0):
        """Start continuous performance monitoring."""
        self.monitoring = True
        self.metrics = []
        
        while self.monitoring:
            try:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                
                self.metrics.append({
                    'timestamp': time.time(),
                    'memory_mb': memory_mb,
                    'cpu_percent': cpu_percent
                })
                
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                
    def stop_monitoring(self) -> Dict[str, float]:
        """Stop monitoring and return aggregated metrics."""
        self.monitoring = False
        
        if not self.metrics:
            return {'memory_mb': 0.0, 'cpu_percent': 0.0}
            
        memory_values = [m['memory_mb'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        
        return {
            'memory_mb': statistics.mean(memory_values),
            'cpu_percent': statistics.mean(cpu_values),
            'peak_memory_mb': max(memory_values),
            'peak_cpu_percent': max(cpu_values)
        }


class LoadTester:
    """Advanced load testing utility."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self.results = []
        
    async def execute_load_test(
        self,
        test_config: Dict[str, Any],
        concurrent_users: int = 10,
        requests_per_user: int = 10,
        ramp_up_time: float = 0.0
    ) -> PerformanceMetrics:
        """Execute a load test with specified configuration."""
        
        start_time = time.time()
        monitor = PerformanceMonitor()
        
        # Start system monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        try:
            # Execute concurrent load test
            tasks = []
            
            for user_id in range(concurrent_users):
                # Stagger user start times for ramp-up
                delay = (ramp_up_time / concurrent_users) * user_id if ramp_up_time > 0 else 0
                
                task = asyncio.create_task(
                    self._simulate_user_load(
                        user_id, 
                        test_config, 
                        requests_per_user, 
                        delay
                    )
                )
                tasks.append(task)
                
            # Wait for all users to complete
            user_results = await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            # Stop monitoring
            system_metrics = monitor.stop_monitoring()
            monitor_task.cancel()
            
        end_time = time.time()
        
        # Aggregate results
        all_response_times = []
        successful_requests = 0
        failed_requests = 0
        total_data_kb = 0.0
        
        for user_result in user_results:
            if isinstance(user_result, Exception):
                failed_requests += requests_per_user
                continue
                
            all_response_times.extend(user_result['response_times'])
            successful_requests += user_result['successful']
            failed_requests += user_result['failed']
            total_data_kb += user_result['data_transferred_kb']
            
        total_requests = successful_requests + failed_requests
        duration = end_time - start_time
        
        # Calculate metrics
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            min_response_time = min(all_response_times)
            max_response_time = max(all_response_times)
            p95_response_time = statistics.quantiles(all_response_times, n=20)[18]  # 95th percentile
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0.0
            
        return PerformanceMetrics(
            test_name=test_config.get('name', 'Load Test'),
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            percentile_95_response_time=p95_response_time,
            requests_per_second=total_requests / duration if duration > 0 else 0,
            error_rate=failed_requests / total_requests if total_requests > 0 else 0,
            memory_usage_mb=system_metrics['memory_mb'],
            cpu_usage_percent=system_metrics['cpu_percent'],
            concurrent_users=concurrent_users,
            total_data_transferred_kb=total_data_kb
        )
        
    async def _simulate_user_load(
        self, 
        user_id: int, 
        test_config: Dict[str, Any], 
        requests_count: int,
        delay: float = 0.0
    ) -> Dict[str, Any]:
        """Simulate load from a single user."""
        
        if delay > 0:
            await asyncio.sleep(delay)
            
        response_times = []
        successful = 0
        failed = 0
        data_transferred_kb = 0.0
        
        timeout = Timeout(self.timeout)
        
        async with AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            for request_num in range(requests_count):
                try:
                    # Prepare request
                    method = test_config.get('method', 'GET')
                    endpoint = test_config.get('endpoint', '/')
                    
                    # Dynamic data generation for variety
                    request_data = self._generate_request_data(
                        test_config, user_id, request_num
                    )
                    
                    # Execute request
                    request_start = time.time()
                    
                    if method.upper() == 'POST':
                        response = await client.post(endpoint, json=request_data)
                    elif method.upper() == 'GET':
                        response = await client.get(endpoint, params=request_data)
                    else:
                        response = await client.request(method, endpoint, json=request_data)
                        
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    
                    # Track data transfer
                    if hasattr(response, 'content'):
                        data_transferred_kb += len(response.content) / 1024
                        
                    if response.status_code < 400:
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    failed += 1
                    print(f"User {user_id} request {request_num} failed: {e}")
                    
                # Optional think time between requests
                think_time = test_config.get('think_time', 0.1)
                if think_time > 0:
                    await asyncio.sleep(think_time)
                    
        return {
            'response_times': response_times,
            'successful': successful,
            'failed': failed,
            'data_transferred_kb': data_transferred_kb
        }
        
    def _generate_request_data(
        self, 
        test_config: Dict[str, Any], 
        user_id: int, 
        request_num: int
    ) -> Dict[str, Any]:
        """Generate dynamic request data for testing variety."""
        
        base_data = test_config.get('data', {})
        
        # Add unique identifiers
        dynamic_data = base_data.copy()
        dynamic_data['user_id'] = f"perf_user_{user_id}"
        dynamic_data['request_id'] = f"req_{user_id}_{request_num}"
        
        # Add timestamp for uniqueness
        dynamic_data['timestamp'] = time.time()
        
        return dynamic_data


class TestPerformanceE2E:
    """Comprehensive performance testing suite."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, document_search_client, ai_chat_client, test_documents):
        """Set up test environment and clients."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        self.test_docs = test_documents
        self.performance_results = []
        
        # Pre-warm services
        await self._warm_up_services()
        
    async def _warm_up_services(self):
        """Pre-warm services to ensure fair performance testing."""
        try:
            # Warm up document search
            await self.doc_client.get("/health")
            await self.doc_client.post("/search", json={"query": "test", "limit": 1})
            
            # Warm up AI chat
            await self.chat_client.get("/health")
            await self.chat_client.post("/chat", json={
                "message": "test",
                "user_id": "warmup_user",
                "session_id": "warmup_session"
            })
            
            # Allow warmup to complete
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"Service warmup warning: {e}")
    
    async def test_document_search_load_performance(self):
        """Test document search service under load."""
        test_config = {
            'name': 'Document Search Load Test',
            'method': 'POST',
            'endpoint': '/search',
            'data': {
                'query': 'artificial intelligence machine learning',
                'limit': 10
            },
            'think_time': 0.05  # 50ms between requests
        }
        
        load_tester = LoadTester("http://localhost:8002")
        
        # Execute load test
        metrics = await load_tester.execute_load_test(
            test_config=test_config,
            concurrent_users=15,
            requests_per_user=8,
            ramp_up_time=5.0
        )
        
        self.performance_results.append(metrics)
        
        # Performance assertions
        assert metrics.error_rate < 0.05, f"Error rate {metrics.error_rate:.2%} too high"
        assert metrics.average_response_time < 2.0, f"Average response time {metrics.average_response_time:.2f}s too slow"
        assert metrics.percentile_95_response_time < 4.0, f"95th percentile {metrics.percentile_95_response_time:.2f}s too slow"
        assert metrics.requests_per_second > 10, f"RPS {metrics.requests_per_second:.1f} too low"
        
        print(f"Document Search Load Test Results:")
        print(f"  - Total Requests: {metrics.total_requests}")
        print(f"  - Success Rate: {(1-metrics.error_rate):.1%}")
        print(f"  - Average Response Time: {metrics.average_response_time:.3f}s")
        print(f"  - 95th Percentile: {metrics.percentile_95_response_time:.3f}s")
        print(f"  - Requests/Second: {metrics.requests_per_second:.1f}")
        
    async def test_ai_chat_load_performance(self):
        """Test AI chat service under load."""
        test_config = {
            'name': 'AI Chat Load Test',
            'method': 'POST',
            'endpoint': '/chat',
            'data': {
                'message': 'What is machine learning?',
                'use_documents': True
            },
            'think_time': 0.5  # 500ms between requests (more realistic for chat)
        }
        
        load_tester = LoadTester("http://localhost:8004")
        
        # Execute load test
        metrics = await load_tester.execute_load_test(
            test_config=test_config,
            concurrent_users=8,
            requests_per_user=5,
            ramp_up_time=3.0
        )
        
        self.performance_results.append(metrics)
        
        # Performance assertions (more lenient for AI processing)
        assert metrics.error_rate < 0.10, f"Error rate {metrics.error_rate:.2%} too high"
        assert metrics.average_response_time < 8.0, f"Average response time {metrics.average_response_time:.2f}s too slow"
        assert metrics.percentile_95_response_time < 15.0, f"95th percentile {metrics.percentile_95_response_time:.2f}s too slow"
        
        print(f"AI Chat Load Test Results:")
        print(f"  - Total Requests: {metrics.total_requests}")
        print(f"  - Success Rate: {(1-metrics.error_rate):.1%}")
        print(f"  - Average Response Time: {metrics.average_response_time:.3f}s")
        print(f"  - 95th Percentile: {metrics.percentile_95_response_time:.3f}s")
        print(f"  - Memory Usage: {metrics.memory_usage_mb:.1f}MB")
        
    async def test_cross_service_workflow_performance(self):
        """Test complete workflow performance across services."""
        # Document upload + indexing + search + chat workflow
        start_time = time.time()
        
        # 1. Upload document
        test_doc = {
            "id": "perf_test_doc",
            "title": "Performance Test Document",
            "content": "This is a comprehensive performance test document with detailed content for testing cross-service workflows.",
            "metadata": {"category": "performance", "tags": ["test"]}
        }
        
        upload_start = time.time()
        upload_response = await self.doc_client.post("/upload", json=test_doc)
        upload_time = time.time() - upload_start
        
        assert upload_response.status_code in [200, 201]
        assert upload_time < 3.0, f"Document upload took {upload_time:.2f}s"
        
        # 2. Wait for indexing (simulate real-world delay)
        await asyncio.sleep(2)
        
        # 3. Search for document
        search_start = time.time()
        search_response = await self.doc_client.post("/search", json={
            "query": "performance test document",
            "limit": 5
        })
        search_time = time.time() - search_start
        
        assert search_response.status_code == 200
        assert search_time < 1.0, f"Document search took {search_time:.2f}s"
        
        # 4. Chat with document context
        chat_start = time.time()
        chat_response = await self.chat_client.post("/chat", json={
            "message": "What can you tell me about the performance test document?",
            "user_id": "perf_workflow_user",
            "session_id": "perf_workflow_session",
            "use_documents": True
        })
        chat_time = time.time() - chat_start
        
        total_workflow_time = time.time() - start_time
        
        assert chat_response.status_code == 200
        assert chat_time < 6.0, f"Chat response took {chat_time:.2f}s"
        assert total_workflow_time < 12.0, f"Total workflow took {total_workflow_time:.2f}s"
        
        print(f"Cross-Service Workflow Performance:")
        print(f"  - Upload Time: {upload_time:.3f}s")
        print(f"  - Search Time: {search_time:.3f}s")  
        print(f"  - Chat Time: {chat_time:.3f}s")
        print(f"  - Total Workflow Time: {total_workflow_time:.3f}s")
        
    async def test_memory_usage_under_load(self):
        """Test memory usage behavior under sustained load."""
        monitor = PerformanceMonitor()
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring(interval=0.5))
        
        try:
            # Generate sustained load on both services
            tasks = []
            
            # Document search load
            for i in range(20):
                task = asyncio.create_task(
                    self.doc_client.post("/search", json={
                        "query": f"test query {i}",
                        "limit": 10
                    })
                )
                tasks.append(task)
                
            # AI chat load
            for i in range(10):
                task = asyncio.create_task(
                    self.chat_client.post("/chat", json={
                        "message": f"Question number {i} about the test documents",
                        "user_id": f"memory_test_user_{i}",
                        "session_id": f"memory_test_session_{i}",
                        "use_documents": True
                    })
                )
                tasks.append(task)
                
            # Execute all requests
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            # Stop monitoring and get metrics
            system_metrics = monitor.stop_monitoring()
            monitor_task.cancel()
            
        # Force garbage collection
        gc.collect()
        
        # Memory usage assertions
        assert system_metrics['memory_mb'] < 1000, f"Memory usage {system_metrics['memory_mb']:.1f}MB too high"
        assert system_metrics['peak_memory_mb'] < 1500, f"Peak memory {system_metrics['peak_memory_mb']:.1f}MB too high"
        
        print(f"Memory Usage Under Load:")
        print(f"  - Average Memory: {system_metrics['memory_mb']:.1f}MB")
        print(f"  - Peak Memory: {system_metrics['peak_memory_mb']:.1f}MB")
        print(f"  - Average CPU: {system_metrics['cpu_percent']:.1f}%")
        print(f"  - Peak CPU: {system_metrics['peak_cpu_percent']:.1f}%")
        
    async def test_concurrent_user_simulation(self):
        """Simulate realistic concurrent user behavior."""
        
        async def simulate_user_session(user_id: int):
            """Simulate a complete user session."""
            session_id = f"concurrent_session_{user_id}"
            session_start = time.time()
            
            try:
                # User uploads a document
                doc_response = await self.doc_client.post("/upload", json={
                    "id": f"user_{user_id}_doc",
                    "title": f"User {user_id} Document",
                    "content": f"This is a test document from user {user_id} containing important information.",
                    "metadata": {"user": f"user_{user_id}"}
                })
                
                # Wait briefly (realistic user behavior)
                await asyncio.sleep(1)
                
                # User searches for content
                search_response = await self.doc_client.post("/search", json={
                    "query": f"user {user_id} important information",
                    "limit": 5
                })
                
                # User engages in conversation
                chat_responses = []
                for msg_num in range(3):
                    chat_response = await self.chat_client.post("/chat", json={
                        "message": f"Message {msg_num}: Tell me about user {user_id} documents",
                        "user_id": f"concurrent_user_{user_id}",
                        "session_id": session_id,
                        "use_documents": True
                    })
                    chat_responses.append(chat_response)
                    
                    # Think time between messages
                    await asyncio.sleep(0.5)
                    
                session_time = time.time() - session_start
                
                return {
                    'user_id': user_id,
                    'session_time': session_time,
                    'doc_status': doc_response.status_code,
                    'search_status': search_response.status_code,
                    'chat_statuses': [r.status_code for r in chat_responses]
                }
                
            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'session_time': time.time() - session_start
                }
        
        # Simulate 12 concurrent users
        concurrent_users = 12
        start_time = time.time()
        
        user_tasks = [
            asyncio.create_task(simulate_user_session(user_id))
            for user_id in range(concurrent_users)
        ]
        
        user_results = await asyncio.gather(*user_tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_sessions = [r for r in user_results if 'error' not in r]
        failed_sessions = [r for r in user_results if 'error' in r]
        
        assert len(successful_sessions) >= concurrent_users * 0.8, \
            f"Only {len(successful_sessions)}/{concurrent_users} sessions succeeded"
            
        if successful_sessions:
            avg_session_time = statistics.mean([s['session_time'] for s in successful_sessions])
            assert avg_session_time < 15.0, f"Average session time {avg_session_time:.2f}s too long"
            
        print(f"Concurrent User Simulation Results:")
        print(f"  - Concurrent Users: {concurrent_users}")
        print(f"  - Successful Sessions: {len(successful_sessions)}")
        print(f"  - Failed Sessions: {len(failed_sessions)}")
        print(f"  - Total Test Time: {total_time:.2f}s")
        if successful_sessions:
            print(f"  - Average Session Time: {avg_session_time:.2f}s")
            
    async def test_streaming_performance(self):
        """Test streaming response performance."""
        streaming_metrics = []
        
        for test_num in range(5):
            start_time = time.time()
            first_chunk_time = None
            chunks_received = 0
            total_content = ""
            
            try:
                async with self.chat_client.stream(
                    "POST", "/chat", json={
                        "message": f"Streaming test {test_num}: Explain machine learning in detail",
                        "user_id": f"streaming_user_{test_num}",
                        "session_id": f"streaming_session_{test_num}",
                        "use_documents": True,
                        "stream": True
                    }
                ) as response:
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            if first_chunk_time is None:
                                first_chunk_time = time.time() - start_time
                            chunks_received += 1
                            total_content += chunk
                            
                        # Timeout protection
                        if time.time() - start_time > 10.0:
                            break
                            
            except Exception as e:
                print(f"Streaming test {test_num} error: {e}")
                continue
                
            total_time = time.time() - start_time
            
            streaming_metrics.append({
                'first_chunk_time': first_chunk_time or total_time,
                'total_time': total_time,
                'chunks_received': chunks_received,
                'content_length': len(total_content)
            })
            
        # Analyze streaming performance
        if streaming_metrics:
            avg_first_chunk = statistics.mean([m['first_chunk_time'] for m in streaming_metrics])
            avg_total_time = statistics.mean([m['total_time'] for m in streaming_metrics])
            avg_chunks = statistics.mean([m['chunks_received'] for m in streaming_metrics])
            
            assert avg_first_chunk < 3.0, f"First chunk time {avg_first_chunk:.2f}s too slow"
            assert avg_total_time < 10.0, f"Total streaming time {avg_total_time:.2f}s too long"
            assert avg_chunks > 5, f"Too few chunks received: {avg_chunks:.1f}"
            
            print(f"Streaming Performance Results:")
            print(f"  - Average First Chunk Time: {avg_first_chunk:.3f}s")
            print(f"  - Average Total Time: {avg_total_time:.3f}s")
            print(f"  - Average Chunks: {avg_chunks:.1f}")
            
    @pytest_asyncio.fixture(autouse=True, scope="class")
    async def save_performance_report(self):
        """Save comprehensive performance report after all tests."""
        yield
        
        if hasattr(self, 'performance_results') and self.performance_results:
            report_data = {
                'timestamp': time.time(),
                'test_environment': 'e2e_docker',
                'metrics': [metrics.to_dict() for metrics in self.performance_results]
            }
            
            report_path = f"/tmp/e2e_performance_report_{int(time.time())}.json"
            async with aiofiles.open(report_path, 'w') as f:
                await f.write(json.dumps(report_data, indent=2))
                
            print(f"Performance report saved to: {report_path}")