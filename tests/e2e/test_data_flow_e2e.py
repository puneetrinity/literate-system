"""
Data Flow Validation End-to-End Tests

Comprehensive testing of data flows across services including document processing
pipelines, conversation memory persistence, cache consistency, and database synchronization.
"""

import asyncio
import json
import time
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
import redis.asyncio as redis
import aiofiles


@dataclass
class DataFlowCheckpoint:
    """Represents a checkpoint in data flow validation."""
    checkpoint_id: str
    service: str
    operation: str
    timestamp: float
    data_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    

class DataFlowTracker:
    """Tracks data flow across services and validates consistency."""
    
    def __init__(self):
        self.checkpoints: List[DataFlowCheckpoint] = []
        self.data_snapshots: Dict[str, Any] = {}
        
    def add_checkpoint(
        self,
        checkpoint_id: str,
        service: str,
        operation: str,
        data: Any,
        metadata: Dict[str, Any] = None
    ):
        """Add a data flow checkpoint."""
        data_str = json.dumps(data, sort_keys=True) if data else ""
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        checkpoint = DataFlowCheckpoint(
            checkpoint_id=checkpoint_id,
            service=service,
            operation=operation,
            timestamp=time.time(),
            data_hash=data_hash,
            metadata=metadata or {}
        )
        
        self.checkpoints.append(checkpoint)
        self.data_snapshots[checkpoint_id] = data
        
    def validate_data_consistency(self, checkpoint_ids: List[str]) -> Dict[str, Any]:
        """Validate data consistency across checkpoints."""
        results = {
            'consistent': True,
            'checkpoints_compared': len(checkpoint_ids),
            'inconsistencies': [],
            'hash_comparison': {}
        }
        
        if len(checkpoint_ids) < 2:
            return results
            
        # Get checkpoints
        checkpoints = [
            cp for cp in self.checkpoints 
            if cp.checkpoint_id in checkpoint_ids
        ]
        
        if len(checkpoints) != len(checkpoint_ids):
            results['consistent'] = False
            results['inconsistencies'].append('Some checkpoints not found')
            return results
            
        # Compare data hashes
        reference_hash = checkpoints[0].data_hash
        
        for checkpoint in checkpoints:
            results['hash_comparison'][checkpoint.checkpoint_id] = {
                'service': checkpoint.service,
                'operation': checkpoint.operation,
                'hash': checkpoint.data_hash,
                'matches_reference': checkpoint.data_hash == reference_hash
            }
            
            if checkpoint.data_hash != reference_hash:
                results['consistent'] = False
                results['inconsistencies'].append(
                    f"Data hash mismatch in {checkpoint.service}:{checkpoint.operation}"
                )
                
        return results
        
    def get_flow_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of data flow."""
        sorted_checkpoints = sorted(self.checkpoints, key=lambda cp: cp.timestamp)
        
        timeline = []
        for cp in sorted_checkpoints:
            timeline.append({
                'checkpoint_id': cp.checkpoint_id,
                'service': cp.service,
                'operation': cp.operation,
                'timestamp': cp.timestamp,
                'relative_time': cp.timestamp - sorted_checkpoints[0].timestamp if sorted_checkpoints else 0,
                'metadata': cp.metadata
            })
            
        return timeline


class CacheConsistencyValidator:
    """Validates cache consistency across services."""
    
    def __init__(self, redis_url: str = "redis://localhost:6380"):
        self.redis_url = redis_url
        self.redis_client = None
        
    async def connect(self):
        """Connect to Redis cache."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
            
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            
    async def validate_cache_consistency(
        self,
        cache_keys: List[str],
        expected_values: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate cache consistency."""
        if not self.redis_client:
            return {'error': 'Redis not connected', 'consistent': False}
            
        results = {
            'consistent': True,
            'cache_status': {},
            'inconsistencies': [],
            'timestamp': time.time()
        }
        
        try:
            for key in cache_keys:
                cached_value = await self.redis_client.get(key)
                
                results['cache_status'][key] = {
                    'exists': cached_value is not None,
                    'value_hash': hashlib.md5(str(cached_value).encode()).hexdigest() if cached_value else None,
                    'ttl': await self.redis_client.ttl(key) if cached_value else None
                }
                
                # Compare with expected values if provided
                if expected_values and key in expected_values:
                    expected_str = json.dumps(expected_values[key], sort_keys=True)
                    cached_str = cached_value.decode() if cached_value else None
                    
                    if cached_str != expected_str:
                        results['consistent'] = False
                        results['inconsistencies'].append(
                            f"Cache key '{key}' value mismatch"
                        )
                        
        except Exception as e:
            results['error'] = str(e)
            results['consistent'] = False
            
        return results
        
    async def clear_test_cache(self, pattern: str = "test_*"):
        """Clear test-related cache entries."""
        if not self.redis_client:
            return
            
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache clear error: {e}")


class MemoryPersistenceValidator:
    """Validates conversation memory persistence."""
    
    async def validate_conversation_memory(
        self,
        chat_client: AsyncClient,
        user_id: str,
        session_id: str,
        conversation_steps: List[str]
    ) -> Dict[str, Any]:
        """Validate conversation memory across multiple interactions."""
        
        results = {
            'memory_consistent': True,
            'conversation_flow': [],
            'memory_references': [],
            'errors': []
        }
        
        context_accumulator = []
        
        for i, message in enumerate(conversation_steps):
            step_start = time.time()
            
            try:
                response = await chat_client.post("/chat", json={
                    'message': message,
                    'user_id': user_id,
                    'session_id': session_id,
                    'use_documents': True
                })
                
                step_duration = time.time() - step_start
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get('response', '').lower()
                    
                    # Check if response references previous context
                    memory_references = []
                    for prev_context in context_accumulator:
                        if any(word in response_text for word in prev_context.split()[:3]):
                            memory_references.append(prev_context[:50])
                            
                    results['conversation_flow'].append({
                        'step': i,
                        'message': message,
                        'response_length': len(response_data.get('response', '')),
                        'duration': step_duration,
                        'memory_references': memory_references,
                        'sources_count': len(response_data.get('sources', []))
                    })
                    
                    context_accumulator.append(message)
                    
                    # For later steps, verify memory is being used
                    if i > 0 and not memory_references:
                        results['memory_consistent'] = False
                        results['errors'].append(f"Step {i}: No memory references found")
                        
                else:
                    results['errors'].append(f"Step {i}: HTTP {response.status_code}")
                    
            except Exception as e:
                results['errors'].append(f"Step {i}: {str(e)}")
                
            # Brief pause between messages
            await asyncio.sleep(0.5)
            
        return results


class DocumentProcessingValidator:
    """Validates document processing pipeline integrity."""
    
    async def validate_document_processing_pipeline(
        self,
        doc_client: AsyncClient,
        test_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate complete document processing pipeline."""
        
        results = {
            'pipeline_success': True,
            'documents_processed': 0,
            'processing_times': [],
            'search_validations': [],
            'errors': []
        }
        
        for doc in test_documents:
            doc_id = doc.get('id', str(uuid.uuid4()))
            doc['id'] = doc_id
            
            try:
                # Step 1: Upload document
                upload_start = time.time()
                upload_response = await doc_client.post("/upload", json=doc)
                upload_time = time.time() - upload_start
                
                if upload_response.status_code not in [200, 201]:
                    results['errors'].append(f"Upload failed for {doc_id}: {upload_response.status_code}")
                    continue
                    
                # Step 2: Wait for processing
                await asyncio.sleep(2)
                
                # Step 3: Verify document is searchable
                search_start = time.time()
                search_response = await doc_client.post("/search", json={
                    'query': doc.get('title', ''),
                    'limit': 10
                })
                search_time = time.time() - search_start
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    search_results = search_data.get('results', [])
                    
                    # Verify our document appears in results
                    doc_found = any(
                        result.get('id') == doc_id 
                        for result in search_results
                    )
                    
                    results['search_validations'].append({
                        'doc_id': doc_id,
                        'found_in_search': doc_found,
                        'search_time': search_time,
                        'results_count': len(search_results)
                    })
                    
                    if not doc_found:
                        results['pipeline_success'] = False
                        results['errors'].append(f"Document {doc_id} not found in search results")
                        
                else:
                    results['errors'].append(f"Search failed for {doc_id}: {search_response.status_code}")
                    
                total_processing_time = upload_time + 2.0 + search_time  # Include wait time
                results['processing_times'].append(total_processing_time)
                results['documents_processed'] += 1
                
            except Exception as e:
                results['errors'].append(f"Processing error for {doc_id}: {str(e)}")
                
        return results


class TestDataFlowE2E:
    """Comprehensive data flow validation tests."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, document_search_client, ai_chat_client, test_documents):
        """Set up test environment."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        self.test_docs = test_documents
        
        # Initialize validators
        self.data_tracker = DataFlowTracker()
        self.cache_validator = CacheConsistencyValidator()
        self.memory_validator = MemoryPersistenceValidator()
        self.doc_processor = DocumentProcessingValidator()
        
        # Connect to cache
        await self.cache_validator.connect()
        
        # Clear test cache
        await self.cache_validator.clear_test_cache()
        
    async def teardown_method(self):
        """Clean up after tests."""
        await self.cache_validator.clear_test_cache()
        await self.cache_validator.disconnect()
        
    async def test_document_processing_pipeline_flow(self):
        """Test complete document processing pipeline with data flow tracking."""
        
        test_doc = {
            'id': f'pipeline_test_{int(time.time())}',
            'title': 'Pipeline Flow Test Document',
            'content': 'This document tests the complete processing pipeline from upload to search to chat integration.',
            'metadata': {
                'category': 'pipeline_test',
                'tags': ['flow', 'pipeline', 'test'],
                'processing_marker': 'PIPELINE_FLOW_MARKER_789'
            }
        }
        
        # Track data flow through pipeline
        
        # Checkpoint 1: Pre-upload
        self.data_tracker.add_checkpoint(
            'pre_upload', 'client', 'prepare_document', test_doc,
            {'operation': 'document_preparation'}
        )
        
        # Checkpoint 2: Upload document
        upload_response = await self.doc_client.post("/upload", json=test_doc)
        assert upload_response.status_code in [200, 201]
        
        upload_data = upload_response.json()
        self.data_tracker.add_checkpoint(
            'post_upload', 'document-search', 'upload_document', upload_data,
            {'operation': 'document_upload', 'response_time': upload_response.elapsed.total_seconds()}
        )
        
        # Wait for indexing
        await asyncio.sleep(3)
        
        # Checkpoint 3: Search for document
        search_response = await self.doc_client.post("/search", json={
            'query': 'PIPELINE_FLOW_MARKER_789',
            'limit': 5
        })
        assert search_response.status_code == 200
        
        search_data = search_response.json()
        self.data_tracker.add_checkpoint(
            'post_search', 'document-search', 'search_document', search_data,
            {'operation': 'document_search', 'results_count': len(search_data.get('results', []))}
        )
        
        # Checkpoint 4: Chat with document context
        chat_response = await self.chat_client.post("/chat", json={
            'message': 'Tell me about the document with PIPELINE_FLOW_MARKER_789',
            'user_id': 'pipeline_test_user',
            'session_id': 'pipeline_test_session',
            'use_documents': True
        })
        assert chat_response.status_code == 200
        
        chat_data = chat_response.json()
        self.data_tracker.add_checkpoint(
            'post_chat', 'ai-chat', 'chat_with_documents', chat_data,
            {'operation': 'document_chat', 'sources_count': len(chat_data.get('sources', []))}
        )
        
        # Validate data flow consistency
        flow_timeline = self.data_tracker.get_flow_timeline()
        assert len(flow_timeline) == 4, f"Expected 4 checkpoints, got {len(flow_timeline)}"
        
        # Verify data consistency (document should be referenced consistently)
        document_found_in_search = any(
            result.get('id') == test_doc['id'] 
            for result in search_data.get('results', [])
        )
        assert document_found_in_search, "Document not found in search results"
        
        document_referenced_in_chat = (
            'PIPELINE_FLOW_MARKER_789'.lower() in chat_data.get('response', '').lower() or
            any('PIPELINE_FLOW_MARKER_789' in str(source) for source in chat_data.get('sources', []))
        )
        assert document_referenced_in_chat, "Document not referenced in chat response"
        
        print(f"Document Processing Pipeline Flow Results:")
        print(f"  - Checkpoints Tracked: {len(flow_timeline)}")
        print(f"  - Document Found in Search: {document_found_in_search}")
        print(f"  - Document Referenced in Chat: {document_referenced_in_chat}")
        print(f"  - Total Pipeline Time: {flow_timeline[-1]['relative_time']:.2f}s")
        
    async def test_conversation_memory_persistence(self):
        """Test conversation memory persistence across multiple interactions."""
        
        user_id = 'memory_test_user'
        session_id = f'memory_test_session_{int(time.time())}'
        
        conversation_steps = [
            "Hello, my name is Alice and I'm researching artificial intelligence.",
            "What information do you have about machine learning algorithms?",
            "Based on what I mentioned about my research interests, what would you recommend?",
            "Can you summarize our conversation so far, including my name and research focus?"
        ]
        
        memory_results = await self.memory_validator.validate_conversation_memory(
            self.chat_client, user_id, session_id, conversation_steps
        )
        
        assert memory_results['memory_consistent'], \
            f"Memory consistency failed: {memory_results['errors']}"
            
        # Validate specific memory aspects
        conversation_flow = memory_results['conversation_flow']
        assert len(conversation_flow) == len(conversation_steps)
        
        # Check that later responses reference earlier context
        later_responses = conversation_flow[2:]  # Steps 2 and 3
        memory_references_found = sum(
            len(step['memory_references']) for step in later_responses
        )
        
        assert memory_references_found > 0, "No memory references found in later conversation steps"
        
        # Verify final summary includes user information
        final_response = conversation_flow[-1]
        final_sources = final_response.get('sources_count', 0)
        
        print(f"Conversation Memory Persistence Results:")
        print(f"  - Conversation Steps: {len(conversation_flow)}")
        print(f"  - Memory Consistent: {memory_results['memory_consistent']}")
        print(f"  - Memory References Found: {memory_references_found}")
        print(f"  - Final Response Sources: {final_sources}")
        
    async def test_cache_consistency_across_services(self):
        """Test cache consistency between document search and AI chat services."""
        
        # Generate unique test data
        test_query = f"cache_test_query_{int(time.time())}"
        cache_test_doc = {
            'id': f'cache_test_doc_{int(time.time())}',
            'title': f'Cache Test Document {test_query}',
            'content': f'This document is for testing cache consistency: {test_query}',
            'metadata': {'cache_test': True}
        }
        
        # Upload document to populate cache
        upload_response = await self.doc_client.post("/upload", json=cache_test_doc)
        assert upload_response.status_code in [200, 201]
        
        await asyncio.sleep(2)  # Allow indexing
        
        # Perform search to populate search cache
        search_response = await self.doc_client.post("/search", json={
            'query': test_query,
            'limit': 5
        })
        assert search_response.status_code == 200
        
        # Perform chat query to potentially use cached data
        chat_response = await self.chat_client.post("/chat", json={
            'message': f'Search for information about {test_query}',
            'user_id': 'cache_test_user',
            'session_id': 'cache_test_session',
            'use_documents': True
        })
        assert chat_response.status_code == 200
        
        # Validate cache consistency
        potential_cache_keys = [
            f"search:{test_query}",
            f"doc:{cache_test_doc['id']}",
            f"session:cache_test_session",
            f"user:cache_test_user"
        ]
        
        cache_results = await self.cache_validator.validate_cache_consistency(
            potential_cache_keys
        )
        
        # Check if any cache entries were found
        cached_entries = sum(
            1 for status in cache_results['cache_status'].values() 
            if status['exists']
        )
        
        print(f"Cache Consistency Results:")
        print(f"  - Cache Keys Checked: {len(potential_cache_keys)}")
        print(f"  - Cache Entries Found: {cached_entries}")
        print(f"  - Cache Consistent: {cache_results['consistent']}")
        
        if cache_results['inconsistencies']:
            print(f"  - Inconsistencies: {cache_results['inconsistencies']}")
            
    async def test_concurrent_data_operations(self):
        """Test data consistency under concurrent operations."""
        
        # Create multiple concurrent operations that modify/access the same data
        base_doc_id = f"concurrent_test_{int(time.time())}"
        
        async def upload_document(doc_num: int):
            """Upload a test document."""
            doc = {
                'id': f"{base_doc_id}_{doc_num}",
                'title': f'Concurrent Test Document {doc_num}',
                'content': f'This is test document number {doc_num} for concurrent operations testing.',
                'metadata': {'concurrent_test': True, 'doc_num': doc_num}
            }
            
            response = await self.doc_client.post("/upload", json=doc)
            return {
                'doc_num': doc_num,
                'status_code': response.status_code,
                'doc_id': doc['id']
            }
            
        async def search_documents(search_num: int):
            """Search for concurrent test documents."""
            response = await self.doc_client.post("/search", json={
                'query': f'concurrent test document',
                'limit': 10
            })
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                concurrent_docs_found = len([
                    r for r in results 
                    if base_doc_id in r.get('id', '')
                ])
            else:
                concurrent_docs_found = 0
                
            return {
                'search_num': search_num,
                'status_code': response.status_code,
                'concurrent_docs_found': concurrent_docs_found
            }
            
        async def chat_with_documents(chat_num: int):
            """Chat using concurrent test documents."""
            response = await self.chat_client.post("/chat", json={
                'message': 'What concurrent test documents are available?',
                'user_id': f'concurrent_user_{chat_num}',
                'session_id': f'concurrent_session_{chat_num}',
                'use_documents': True
            })
            
            return {
                'chat_num': chat_num,
                'status_code': response.status_code,
                'sources_count': len(response.json().get('sources', [])) if response.status_code == 200 else 0
            }
            
        # Execute concurrent operations
        concurrent_tasks = []
        
        # Add upload tasks
        for i in range(5):
            concurrent_tasks.append(upload_document(i))
            
        # Add search tasks (some will run before uploads complete)
        for i in range(3):
            concurrent_tasks.append(search_documents(i))
            
        # Add chat tasks
        for i in range(3):
            concurrent_tasks.append(chat_with_documents(i))
            
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        upload_results = [r for r in results if isinstance(r, dict) and 'doc_num' in r]
        search_results = [r for r in results if isinstance(r, dict) and 'search_num' in r]
        chat_results = [r for r in results if isinstance(r, dict) and 'chat_num' in r]
        errors = [r for r in results if isinstance(r, Exception)]
        
        successful_uploads = len([r for r in upload_results if r['status_code'] in [200, 201]])
        successful_searches = len([r for r in search_results if r['status_code'] == 200])
        successful_chats = len([r for r in chat_results if r['status_code'] == 200])
        
        print(f"Concurrent Data Operations Results:")
        print(f"  - Total Concurrent Operations: {len(concurrent_tasks)}")
        print(f"  - Total Execution Time: {total_time:.2f}s")
        print(f"  - Successful Uploads: {successful_uploads}/5")
        print(f"  - Successful Searches: {successful_searches}/3")
        print(f"  - Successful Chats: {successful_chats}/3")
        print(f"  - Errors: {len(errors)}")
        
        # Validate no major failures occurred
        assert successful_uploads >= 4, f"Too many upload failures: {5 - successful_uploads}"
        assert successful_searches >= 2, f"Too many search failures: {3 - successful_searches}"
        assert len(errors) == 0, f"Unexpected errors occurred: {errors}"
        
    async def test_database_synchronization(self):
        """Test database synchronization across document operations."""
        
        # Create test documents with specific patterns
        sync_test_docs = []
        for i in range(3):
            doc = {
                'id': f'sync_test_doc_{i}_{int(time.time())}',
                'title': f'Synchronization Test Document {i}',
                'content': f'This document {i} tests database synchronization across services.',
                'metadata': {
                    'sync_test': True,
                    'doc_number': i,
                    'sync_marker': f'SYNC_MARKER_{i}'
                }
            }
            sync_test_docs.append(doc)
            
        # Upload documents sequentially
        uploaded_docs = []
        for doc in sync_test_docs:
            response = await self.doc_client.post("/upload", json=doc)
            assert response.status_code in [200, 201]
            uploaded_docs.append(doc)
            
            # Brief delay to ensure processing order
            await asyncio.sleep(1)
            
        # Wait for all documents to be indexed
        await asyncio.sleep(3)
        
        # Validate all documents are synchronized and searchable
        for doc in uploaded_docs:
            # Search for specific document
            search_response = await self.doc_client.post("/search", json={
                'query': doc['metadata']['sync_marker'],
                'limit': 5
            })
            
            assert search_response.status_code == 200
            search_data = search_response.json()
            
            # Verify document is found
            doc_found = any(
                result.get('id') == doc['id'] 
                for result in search_data.get('results', [])
            )
            
            assert doc_found, f"Document {doc['id']} not found in search - sync issue"
            
        # Test cross-document search consistency
        cross_search_response = await self.doc_client.post("/search", json={
            'query': 'synchronization test document',
            'limit': 10
        })
        
        assert cross_search_response.status_code == 200
        cross_search_data = cross_search_response.json()
        
        # Count how many of our test documents appear
        sync_docs_found = len([
            result for result in cross_search_data.get('results', [])
            if any(doc['id'] == result.get('id') for doc in uploaded_docs)
        ])
        
        assert sync_docs_found == len(uploaded_docs), \
            f"Database sync issue: {sync_docs_found}/{len(uploaded_docs)} documents found"
            
        print(f"Database Synchronization Results:")
        print(f"  - Documents Uploaded: {len(uploaded_docs)}")
        print(f"  - Documents Found in Individual Search: {len(uploaded_docs)}")
        print(f"  - Documents Found in Cross Search: {sync_docs_found}")
        print(f"  - Synchronization Status: {'✓ Complete' if sync_docs_found == len(uploaded_docs) else '✗ Issues detected'}")
        
    async def test_data_persistence_across_restarts(self):
        """Test data persistence simulation (without actual service restarts)."""
        
        # Upload a document that should persist
        persistence_doc = {
            'id': f'persistence_test_{int(time.time())}',
            'title': 'Data Persistence Test Document',
            'content': 'This document tests data persistence across service lifecycle events.',
            'metadata': {
                'persistence_test': True,
                'persistence_marker': 'PERSIST_MARKER_XYZ'
            }
        }
        
        # Initial upload and verification
        upload_response = await self.doc_client.post("/upload", json=persistence_doc)
        assert upload_response.status_code in [200, 201]
        
        await asyncio.sleep(2)  # Allow processing
        
        # Verify document is searchable
        initial_search = await self.doc_client.post("/search", json={
            'query': 'PERSIST_MARKER_XYZ',
            'limit': 5
        })
        
        assert initial_search.status_code == 200
        initial_results = initial_search.json()
        
        doc_found_initially = any(
            result.get('id') == persistence_doc['id'] 
            for result in initial_results.get('results', [])
        )
        
        assert doc_found_initially, "Document not found in initial search"
        
        # Simulate heavy load to test persistence under stress
        stress_tasks = []
        for i in range(10):
            task = asyncio.create_task(
                self.doc_client.post("/search", json={'query': f'stress test {i}', 'limit': 5})
            )
            stress_tasks.append(task)
            
        await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        # Verify document still exists after stress
        post_stress_search = await self.doc_client.post("/search", json={
            'query': 'PERSIST_MARKER_XYZ',
            'limit': 5
        })
        
        assert post_stress_search.status_code == 200
        post_stress_results = post_stress_search.json()
        
        doc_found_post_stress = any(
            result.get('id') == persistence_doc['id'] 
            for result in post_stress_results.get('results', [])
        )
        
        assert doc_found_post_stress, "Document lost after stress test - persistence issue"
        
        print(f"Data Persistence Test Results:")
        print(f"  - Document Found Initially: {doc_found_initially}")
        print(f"  - Document Found After Stress: {doc_found_post_stress}")
        print(f"  - Persistence Status: {'✓ Verified' if doc_found_post_stress else '✗ Failed'}")
        
    async def test_cross_service_data_integrity(self):
        """Test data integrity across service boundaries."""
        
        # Create a document with specific structure
        integrity_doc = {
            'id': f'integrity_test_{int(time.time())}',
            'title': 'Data Integrity Test Document',
            'content': 'This document has specific content for testing data integrity: INTEGRITY_MARKER_ABC123. It contains structured information that should remain consistent across services.',
            'metadata': {
                'integrity_test': True,
                'checksum': 'test_checksum_789',
                'version': '1.0',
                'tags': ['integrity', 'test', 'validation']
            }
        }
        
        # Track data at each service boundary
        self.data_tracker.add_checkpoint(
            'original_doc', 'client', 'prepare_document', integrity_doc
        )
        
        # Upload to document service
        upload_response = await self.doc_client.post("/upload", json=integrity_doc)
        assert upload_response.status_code in [200, 201]
        
        upload_data = upload_response.json()
        self.data_tracker.add_checkpoint(
            'doc_service_upload', 'document-search', 'upload_response', upload_data
        )
        
        await asyncio.sleep(2)
        
        # Search and verify data integrity
        search_response = await self.doc_client.post("/search", json={
            'query': 'INTEGRITY_MARKER_ABC123',
            'limit': 5
        })
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Find our document in search results
        found_doc = None
        for result in search_data.get('results', []):
            if result.get('id') == integrity_doc['id']:
                found_doc = result
                break
                
        assert found_doc is not None, "Document not found in search results"
        
        self.data_tracker.add_checkpoint(
            'doc_service_search', 'document-search', 'search_result', found_doc
        )
        
        # Use through chat service
        chat_response = await self.chat_client.post("/chat", json={
            'message': 'Find information about INTEGRITY_MARKER_ABC123',
            'user_id': 'integrity_test_user',
            'session_id': 'integrity_test_session',
            'use_documents': True
        })
        
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        self.data_tracker.add_checkpoint(
            'chat_service_response', 'ai-chat', 'chat_response', chat_data
        )
        
        # Validate data integrity across checkpoints
        integrity_checks = {
            'document_id_consistent': True,
            'content_marker_preserved': True,
            'metadata_preserved': True,
            'cross_service_reference': True
        }
        
        # Check ID consistency
        if found_doc.get('id') != integrity_doc['id']:
            integrity_checks['document_id_consistent'] = False
            
        # Check content marker preservation
        if 'INTEGRITY_MARKER_ABC123' not in found_doc.get('content', ''):
            integrity_checks['content_marker_preserved'] = False
            
        # Check if chat service found the document
        chat_response_text = chat_data.get('response', '').lower()
        chat_sources = chat_data.get('sources', [])
        
        marker_in_chat = (
            'integrity_marker_abc123' in chat_response_text or
            any('INTEGRITY_MARKER_ABC123' in str(source) for source in chat_sources)
        )
        
        if not marker_in_chat:
            integrity_checks['cross_service_reference'] = False
            
        all_integrity_maintained = all(integrity_checks.values())
        
        print(f"Cross-Service Data Integrity Results:")
        print(f"  - Document ID Consistent: {integrity_checks['document_id_consistent']}")
        print(f"  - Content Marker Preserved: {integrity_checks['content_marker_preserved']}")
        print(f"  - Cross-Service Reference: {integrity_checks['cross_service_reference']}")
        print(f"  - Overall Integrity: {'✓ Maintained' if all_integrity_maintained else '✗ Issues detected'}")
        
        assert all_integrity_maintained, f"Data integrity issues detected: {integrity_checks}"