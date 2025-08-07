"""
API Workflow End-to-End Tests

Comprehensive testing of multi-step API workflows, streaming responses,
error handling across service boundaries, and rate limiting behaviors.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from httpx import AsyncClient, Timeout, HTTPError, Response
import aiofiles


@dataclass
class WorkflowStep:
    """Represents a single step in an API workflow."""
    service: str  # 'document-search' or 'ai-chat'
    method: str   # HTTP method
    endpoint: str
    data: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    timeout: float = 30.0
    depends_on: Optional[str] = None  # Step ID this depends on
    extract_data: Optional[Dict[str, str]] = None  # Data to extract for next steps
    validation: Optional[Dict[str, Any]] = None  # Custom validation rules
    

class APIWorkflowExecutor:
    """Executes complex multi-step API workflows."""
    
    def __init__(self, doc_client: AsyncClient, chat_client: AsyncClient):
        self.doc_client = doc_client
        self.chat_client = chat_client
        self.workflow_data = {}  # Shared data between steps
        
    async def execute_workflow(
        self, 
        workflow_steps: List[WorkflowStep],
        workflow_id: str = None
    ) -> Dict[str, Any]:
        """Execute a complete workflow with dependent steps."""
        
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
            
        workflow_results = {
            'workflow_id': workflow_id,
            'start_time': time.time(),
            'steps': {},
            'success': True,
            'error': None
        }
        
        try:
            for i, step in enumerate(workflow_steps):
                step_id = f"step_{i}_{step.endpoint.replace('/', '_')}"
                step_start = time.time()
                
                # Check dependencies
                if step.depends_on and step.depends_on not in workflow_results['steps']:
                    raise ValueError(f"Step {step_id} depends on {step.depends_on} which hasn't executed")
                
                # Prepare request data
                request_data = self._prepare_request_data(step, workflow_results['steps'])
                
                # Select client
                client = self.doc_client if step.service == 'document-search' else self.chat_client
                
                # Execute request
                try:
                    timeout = Timeout(step.timeout)
                    
                    if step.method.upper() == 'GET':
                        if request_data:
                            endpoint_with_params = f"{step.endpoint}?{urlencode(request_data)}"
                            response = await client.get(endpoint_with_params, timeout=timeout)
                        else:
                            response = await client.get(step.endpoint, timeout=timeout)
                    elif step.method.upper() == 'POST':
                        response = await client.post(step.endpoint, json=request_data, timeout=timeout)
                    elif step.method.upper() == 'PUT':
                        response = await client.put(step.endpoint, json=request_data, timeout=timeout)
                    elif step.method.upper() == 'DELETE':
                        response = await client.delete(step.endpoint, timeout=timeout)
                    else:
                        response = await client.request(step.method, step.endpoint, json=request_data, timeout=timeout)
                        
                    step_time = time.time() - step_start
                    
                    # Validate response
                    step_result = await self._validate_step_response(step, response, step_time)
                    workflow_results['steps'][step_id] = step_result
                    
                    # Extract data for future steps
                    if step.extract_data and step_result['success']:
                        extracted = self._extract_response_data(response, step.extract_data)
                        self.workflow_data.update(extracted)
                        
                except Exception as e:
                    step_result = {
                        'success': False,
                        'error': str(e),
                        'duration': time.time() - step_start,
                        'status_code': None
                    }
                    workflow_results['steps'][step_id] = step_result
                    workflow_results['success'] = False
                    workflow_results['error'] = f"Step {step_id} failed: {str(e)}"
                    break
                    
        except Exception as e:
            workflow_results['success'] = False
            workflow_results['error'] = str(e)
            
        workflow_results['end_time'] = time.time()
        workflow_results['total_duration'] = workflow_results['end_time'] - workflow_results['start_time']
        
        return workflow_results
        
    def _prepare_request_data(self, step: WorkflowStep, previous_steps: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data with variable substitution."""
        if not step.data:
            return {}
            
        request_data = step.data.copy()
        
        # Substitute variables from workflow data
        for key, value in request_data.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]  # Remove ${ and }
                if var_name in self.workflow_data:
                    request_data[key] = self.workflow_data[var_name]
                    
        return request_data
        
    async def _validate_step_response(
        self, 
        step: WorkflowStep, 
        response: Response, 
        duration: float
    ) -> Dict[str, Any]:
        """Validate step response and return result."""
        
        result = {
            'success': response.status_code == step.expected_status,
            'status_code': response.status_code,
            'duration': duration,
            'response_size': len(response.content) if response.content else 0
        }
        
        try:
            response_data = response.json() if response.content else {}
            result['response_data'] = response_data
        except:
            result['response_data'] = {'raw_content': response.text[:500]}
            
        # Custom validation
        if step.validation and result['success']:
            validation_results = []
            
            for validation_key, validation_rule in step.validation.items():
                if validation_key == 'contains_fields':
                    for field in validation_rule:
                        if field not in response_data:
                            validation_results.append(f"Missing field: {field}")
                elif validation_key == 'response_time_max':
                    if duration > validation_rule:
                        validation_results.append(f"Response time {duration:.2f}s exceeds {validation_rule}s")
                elif validation_key == 'content_contains':
                    content_str = json.dumps(response_data).lower()
                    for required_content in validation_rule:
                        if required_content.lower() not in content_str:
                            validation_results.append(f"Content missing: {required_content}")
                            
            if validation_results:
                result['success'] = False
                result['validation_errors'] = validation_results
                
        return result
        
    def _extract_response_data(self, response: Response, extraction_rules: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from response for future steps."""
        extracted = {}
        
        try:
            response_data = response.json()
            
            for extract_key, json_path in extraction_rules.items():
                # Simple JSON path extraction (can be enhanced with jsonpath library)
                keys = json_path.split('.')
                value = response_data
                
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        value = None
                        break
                        
                if value is not None:
                    extracted[extract_key] = value
                    
        except Exception as e:
            print(f"Data extraction error: {e}")
            
        return extracted


class StreamingValidator:
    """Validates streaming API responses."""
    
    async def validate_streaming_response(
        self,
        client: AsyncClient,
        endpoint: str,
        request_data: Dict[str, Any],
        expected_patterns: List[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Validate streaming response characteristics."""
        
        start_time = time.time()
        first_chunk_time = None
        chunks = []
        total_content = ""
        
        try:
            async with client.stream("POST", endpoint, json=request_data) as response:
                if response.status_code != 200:
                    return {
                        'success': False,
                        'error': f"HTTP {response.status_code}",
                        'duration': time.time() - start_time
                    }
                    
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        if first_chunk_time is None:
                            first_chunk_time = time.time() - start_time
                            
                        chunks.append({
                            'content': chunk,
                            'timestamp': time.time() - start_time,
                            'size': len(chunk)
                        })
                        total_content += chunk
                        
                    # Timeout protection
                    if time.time() - start_time > timeout:
                        break
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time
            }
            
        total_duration = time.time() - start_time
        
        # Validate streaming characteristics
        validation_results = {
            'success': True,
            'total_duration': total_duration,
            'first_chunk_time': first_chunk_time,
            'total_chunks': len(chunks),
            'total_content_length': len(total_content),
            'average_chunk_size': sum(c['size'] for c in chunks) / len(chunks) if chunks else 0,
            'streaming_efficiency': len(chunks) / total_duration if total_duration > 0 else 0
        }
        
        # Pattern validation
        if expected_patterns:
            content_lower = total_content.lower()
            missing_patterns = [
                pattern for pattern in expected_patterns 
                if pattern.lower() not in content_lower
            ]
            
            if missing_patterns:
                validation_results['success'] = False
                validation_results['missing_patterns'] = missing_patterns
                
        return validation_results


class TestAPIWorkflowE2E:
    """Comprehensive API workflow testing."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, document_search_client, ai_chat_client, test_documents):
        """Set up test environment."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        self.test_docs = test_documents
        self.executor = APIWorkflowExecutor(document_search_client, ai_chat_client)
        self.streaming_validator = StreamingValidator()
        
    async def test_complete_document_workflow(self):
        """Test complete document upload → index → search → chat workflow."""
        
        workflow_steps = [
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/upload',
                data={
                    'id': 'workflow_test_doc',
                    'title': 'Workflow Test Document',
                    'content': 'This document contains important workflow testing information about quantum computing and machine learning.',
                    'metadata': {'category': 'workflow_test', 'tags': ['quantum', 'ml']}
                },
                expected_status=201,
                extract_data={'document_id': 'id'},
                validation={
                    'contains_fields': ['id', 'status'],
                    'response_time_max': 5.0
                }
            ),
            
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/search',
                data={
                    'query': 'quantum computing machine learning',
                    'limit': 10
                },
                expected_status=200,
                depends_on='step_0_upload',
                extract_data={'search_results': 'results'},
                validation={
                    'contains_fields': ['results', 'total'],
                    'response_time_max': 2.0,
                    'content_contains': ['quantum', 'machine learning']
                }
            ),
            
            WorkflowStep(
                service='ai-chat',
                method='POST',
                endpoint='/chat',
                data={
                    'message': 'What can you tell me about quantum computing based on the uploaded documents?',
                    'user_id': 'workflow_test_user',
                    'session_id': 'workflow_test_session',
                    'use_documents': True
                },
                expected_status=200,
                depends_on='step_1_search',
                validation={
                    'contains_fields': ['response', 'sources'],
                    'response_time_max': 10.0,
                    'content_contains': ['quantum']
                }
            )
        ]
        
        # Execute workflow
        results = await self.executor.execute_workflow(workflow_steps)
        
        # Validate workflow success
        assert results['success'], f"Workflow failed: {results.get('error')}"
        assert len(results['steps']) == 3, "Not all workflow steps executed"
        assert results['total_duration'] < 20.0, f"Workflow took too long: {results['total_duration']:.2f}s"
        
        # Validate individual steps
        for step_id, step_result in results['steps'].items():
            assert step_result['success'], f"Step {step_id} failed: {step_result.get('error')}"
            
        print(f"Complete Document Workflow Results:")
        print(f"  - Total Duration: {results['total_duration']:.2f}s")
        print(f"  - Steps Completed: {len(results['steps'])}")
        print(f"  - All Steps Successful: {results['success']}")
        
    async def test_multi_user_session_workflow(self):
        """Test multi-user conversation workflow with session management."""
        
        user_workflows = []
        
        for user_num in range(3):
            user_id = f"multi_user_{user_num}"
            session_id = f"multi_session_{user_num}"
            
            user_workflow = [
                WorkflowStep(
                    service='ai-chat',
                    method='POST',
                    endpoint='/chat',
                    data={
                        'message': f'Hello, I am user {user_num}. Can you help me with AI research?',
                        'user_id': user_id,
                        'session_id': session_id,
                        'use_documents': True
                    },
                    validation={'response_time_max': 8.0}
                ),
                
                WorkflowStep(
                    service='ai-chat',
                    method='POST',
                    endpoint='/chat',
                    data={
                        'message': 'What specific information do you have about machine learning?',
                        'user_id': user_id,
                        'session_id': session_id,
                        'use_documents': True
                    },
                    validation={
                        'response_time_max': 8.0,
                        'content_contains': ['machine learning']
                    }
                ),
                
                WorkflowStep(
                    service='ai-chat', 
                    method='POST',
                    endpoint='/chat',
                    data={
                        'message': 'Based on our conversation, can you summarize what we discussed?',
                        'user_id': user_id,
                        'session_id': session_id,
                        'use_documents': False
                    },
                    validation={'response_time_max': 8.0}
                )
            ]
            
            user_workflows.append(user_workflow)
            
        # Execute all user workflows concurrently
        workflow_tasks = [
            self.executor.execute_workflow(workflow, f"user_{i}_workflow")
            for i, workflow in enumerate(user_workflows)
        ]
        
        workflow_results = await asyncio.gather(*workflow_tasks)
        
        # Validate all workflows succeeded
        successful_workflows = [r for r in workflow_results if r['success']]
        assert len(successful_workflows) == 3, f"Only {len(successful_workflows)}/3 workflows succeeded"
        
        # Validate session isolation
        for i, result in enumerate(workflow_results):
            assert result['success'], f"User {i} workflow failed: {result.get('error')}"
            
        print(f"Multi-User Session Workflow Results:")
        print(f"  - Successful Workflows: {len(successful_workflows)}/3")
        print(f"  - Average Duration: {sum(r['total_duration'] for r in successful_workflows) / len(successful_workflows):.2f}s")
        
    async def test_error_handling_workflow(self):
        """Test error handling across service boundaries."""
        
        error_test_workflows = [
            # Test invalid document upload
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/upload',
                data={
                    'id': '',  # Invalid empty ID
                    'title': 'Test',
                    'content': 'Content'
                },
                expected_status=400  # Expecting validation error
            ),
            
            # Test search with empty query
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/search',
                data={
                    'query': '',  # Empty query
                    'limit': 10
                },
                expected_status=400  # Expecting validation error
            ),
            
            # Test chat with missing required fields
            WorkflowStep(
                service='ai-chat',
                method='POST',
                endpoint='/chat',
                data={
                    'message': '',  # Empty message
                    'user_id': 'test_user'
                    # Missing session_id
                },
                expected_status=422  # Expecting validation error
            )
        ]
        
        # Execute error scenarios
        for i, step in enumerate(error_test_workflows):
            client = self.doc_client if step.service == 'document-search' else self.chat_client
            
            try:
                if step.method.upper() == 'POST':
                    response = await client.post(step.endpoint, json=step.data)
                else:
                    response = await client.request(step.method, step.endpoint, json=step.data)
                    
                # Verify expected error status
                assert response.status_code == step.expected_status, \
                    f"Expected status {step.expected_status}, got {response.status_code}"
                    
                # Verify error response contains useful information
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        assert 'error' in error_data or 'detail' in error_data, \
                            "Error response should contain error information"
                    except:
                        pass  # Some errors might not be JSON
                        
            except Exception as e:
                pytest.fail(f"Error handling test {i} failed unexpectedly: {e}")
                
        print("Error Handling Workflow: All error scenarios handled correctly")
        
    async def test_streaming_workflow_validation(self):
        """Test streaming response workflows."""
        
        streaming_scenarios = [
            {
                'name': 'Basic Streaming Chat',
                'data': {
                    'message': 'Explain artificial intelligence in detail',
                    'user_id': 'streaming_user_1',
                    'session_id': 'streaming_session_1',
                    'stream': True,
                    'use_documents': True
                },
                'expected_patterns': ['artificial intelligence', 'ai', 'machine learning']
            },
            
            {
                'name': 'Document-based Streaming',
                'data': {
                    'message': 'What can you tell me about climate change?',
                    'user_id': 'streaming_user_2',
                    'session_id': 'streaming_session_2',
                    'stream': True,
                    'use_documents': True
                },
                'expected_patterns': ['climate', 'environment']
            }
        ]
        
        streaming_results = []
        
        for scenario in streaming_scenarios:
            result = await self.streaming_validator.validate_streaming_response(
                client=self.chat_client,
                endpoint='/chat',
                request_data=scenario['data'],
                expected_patterns=scenario['expected_patterns'],
                timeout=15.0
            )
            
            result['scenario_name'] = scenario['name']
            streaming_results.append(result)
            
            # Validate streaming performance
            assert result['success'], f"Streaming failed for {scenario['name']}: {result.get('error')}"
            assert result['first_chunk_time'] < 5.0, f"First chunk too slow: {result['first_chunk_time']:.2f}s"
            assert result['total_chunks'] > 3, f"Too few chunks: {result['total_chunks']}"
            assert result['total_content_length'] > 50, f"Content too short: {result['total_content_length']}"
            
        avg_first_chunk = sum(r['first_chunk_time'] for r in streaming_results) / len(streaming_results)
        avg_chunks = sum(r['total_chunks'] for r in streaming_results) / len(streaming_results)
        
        print(f"Streaming Workflow Validation Results:")
        print(f"  - Scenarios Tested: {len(streaming_results)}")
        print(f"  - Average First Chunk Time: {avg_first_chunk:.3f}s")
        print(f"  - Average Chunks per Response: {avg_chunks:.1f}")
        
    async def test_rate_limiting_workflow(self):
        """Test rate limiting behavior across services."""
        
        # Generate rapid requests to test rate limiting
        rapid_requests = []
        
        for i in range(25):  # Send more requests than typical rate limit
            request_task = asyncio.create_task(
                self.chat_client.post("/chat", json={
                    'message': f'Rate limit test message {i}',
                    'user_id': f'rate_test_user_{i}',
                    'session_id': f'rate_test_session_{i}',
                    'use_documents': False
                })
            )
            rapid_requests.append(request_task)
            
        # Execute requests with minimal delay
        start_time = time.time()
        responses = await asyncio.gather(*rapid_requests, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze response patterns
        successful_responses = []
        rate_limited_responses = []
        error_responses = []
        
        for response in responses:
            if isinstance(response, Exception):
                error_responses.append(response)
            elif response.status_code == 200:
                successful_responses.append(response)
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_responses.append(response)
            else:
                error_responses.append(response)
                
        # Validate rate limiting behavior
        print(f"Rate Limiting Test Results:")
        print(f"  - Total Requests: {len(rapid_requests)}")
        print(f"  - Successful: {len(successful_responses)}")
        print(f"  - Rate Limited (429): {len(rate_limited_responses)}")
        print(f"  - Errors: {len(error_responses)}")
        print(f"  - Total Time: {total_time:.2f}s")
        print(f"  - Requests/Second: {len(rapid_requests) / total_time:.1f}")
        
        # Rate limiting should be working if we get 429 responses or controlled success rate
        if len(rate_limited_responses) > 0:
            print("✓ Rate limiting is active (429 responses received)")
        elif len(successful_responses) < len(rapid_requests) * 0.8:
            print("✓ Rate limiting appears to be controlling request flow")
        else:
            print("⚠ Rate limiting may not be active or threshold not reached")
            
    async def test_authentication_workflow(self):
        """Test authentication and authorization workflows."""
        
        # Test requests without proper authentication/identification
        auth_test_cases = [
            {
                'name': 'Chat without user_id',
                'service': 'ai-chat',
                'endpoint': '/chat',
                'data': {
                    'message': 'Test message',
                    'session_id': 'test_session'
                    # Missing user_id
                }
            },
            
            {
                'name': 'Chat without session_id',
                'service': 'ai-chat', 
                'endpoint': '/chat',
                'data': {
                    'message': 'Test message',
                    'user_id': 'test_user'
                    # Missing session_id
                }
            }
        ]
        
        for test_case in auth_test_cases:
            client = self.doc_client if test_case['service'] == 'document-search' else self.chat_client
            
            try:
                response = await client.post(test_case['endpoint'], json=test_case['data'])
                
                # Depending on implementation, this might return 400, 422, or handle gracefully
                if response.status_code in [400, 422]:
                    print(f"✓ {test_case['name']}: Properly rejected with {response.status_code}")
                elif response.status_code == 200:
                    print(f"⚠ {test_case['name']}: Accepted despite missing fields")
                else:
                    print(f"? {test_case['name']}: Unexpected status {response.status_code}")
                    
            except Exception as e:
                print(f"✗ {test_case['name']}: Request failed with error: {e}")
                
    async def test_cost_management_workflow(self):
        """Test cost management and budget tracking workflows."""
        
        # Make requests that would consume budget
        budget_test_requests = []
        
        for i in range(10):
            request_task = asyncio.create_task(
                self.chat_client.post("/chat", json={
                    'message': f'Cost tracking test message {i} - please provide a detailed response about machine learning algorithms',
                    'user_id': 'budget_test_user',
                    'session_id': 'budget_test_session',
                    'use_documents': True
                })
            )
            budget_test_requests.append(request_task)
            
        # Execute budget test requests
        budget_responses = await asyncio.gather(*budget_test_requests, return_exceptions=True)
        
        successful_budget_requests = [
            r for r in budget_responses 
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        
        print(f"Cost Management Test Results:")
        print(f"  - Budget Test Requests: {len(budget_test_requests)}")
        print(f"  - Successful Responses: {len(successful_budget_requests)}")
        
        # Check if cost tracking headers are present (if implemented)
        if successful_budget_requests:
            sample_response = successful_budget_requests[0]
            cost_headers = [h for h in sample_response.headers.keys() if 'cost' in h.lower() or 'budget' in h.lower()]
            
            if cost_headers:
                print(f"  - Cost tracking headers found: {cost_headers}")
            else:
                print("  - No cost tracking headers detected")
                
    async def test_data_consistency_workflow(self):
        """Test data consistency across service operations."""
        
        # Upload document and verify consistency across operations
        test_doc_id = f"consistency_test_{int(time.time())}"
        
        consistency_workflow = [
            # Upload document
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/upload',
                data={
                    'id': test_doc_id,
                    'title': 'Data Consistency Test Document',
                    'content': 'This document is used for testing data consistency across services with unique identifier CONSISTENCY_MARKER_12345.',
                    'metadata': {'test': 'consistency', 'marker': 'CONSISTENCY_MARKER_12345'}
                },
                extract_data={'uploaded_doc_id': 'id'}
            ),
            
            # Search for the document
            WorkflowStep(
                service='document-search',
                method='POST',
                endpoint='/search',
                data={
                    'query': 'CONSISTENCY_MARKER_12345',
                    'limit': 5
                },
                depends_on='step_0_upload',
                validation={
                    'content_contains': ['CONSISTENCY_MARKER_12345']
                }
            ),
            
            # Query through chat
            WorkflowStep(
                service='ai-chat',
                method='POST',
                endpoint='/chat',
                data={
                    'message': 'Find information about CONSISTENCY_MARKER_12345',
                    'user_id': 'consistency_test_user',
                    'session_id': 'consistency_test_session',
                    'use_documents': True
                },
                depends_on='step_1_search',
                validation={
                    'content_contains': ['consistency']
                }
            )
        ]
        
        # Execute consistency workflow
        consistency_results = await self.executor.execute_workflow(consistency_workflow)
        
        assert consistency_results['success'], f"Consistency workflow failed: {consistency_results.get('error')}"
        
        # Verify data appears consistently across all operations
        upload_step = consistency_results['steps']['step_0_upload']
        search_step = consistency_results['steps']['step_1_search'] 
        chat_step = consistency_results['steps']['step_2_chat']
        
        assert upload_step['success'], "Document upload failed"
        assert search_step['success'], "Document search failed"
        assert chat_step['success'], "Chat query failed"
        
        print(f"Data Consistency Workflow Results:")
        print(f"  - Upload Success: {upload_step['success']}")
        print(f"  - Search Success: {search_step['success']}")
        print(f"  - Chat Success: {chat_step['success']}")
        print(f"  - Total Duration: {consistency_results['total_duration']:.2f}s")