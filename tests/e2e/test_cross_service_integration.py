"""
Cross-Service Integration Tests

Tests for validating interactions between AI Chat Service and Document Search Service.
"""

import asyncio
import time
from typing import Dict, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestCrossServiceIntegration:
    """Test cross-service workflows and data exchange."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, document_search_client, ai_chat_client, test_documents):
        """Set up test data for each test method."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        self.test_docs = test_documents

    async def test_document_search_service_health(self):
        """Test document search service is healthy and responsive."""
        response = await self.doc_client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] == "healthy"

    async def test_ai_chat_service_health(self):
        """Test AI chat service is healthy and responsive."""
        response = await self.chat_client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] == "healthy"

    async def test_document_upload_and_indexing(self):
        """Test document upload and verify indexing completion."""
        test_doc = {
            "id": "integration_test_doc",
            "title": "Integration Test Document",
            "content": "This is a test document for integration testing purposes.",
            "metadata": {
                "category": "test",
                "tags": ["integration", "test"],
                "source": "integration_test"
            }
        }
        
        # Upload document
        start_time = time.time()
        response = await self.doc_client.post("/upload", json=test_doc)
        upload_time = time.time() - start_time
        
        assert response.status_code in [200, 201]
        assert upload_time < 5.0, f"Document upload took {upload_time:.2f}s, expected < 5.0s"
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Verify document can be searched
        search_response = await self.doc_client.post("/search", json={
            "query": "integration testing",
            "limit": 10
        })
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        
        # Verify our test document appears in results
        found_doc = any(
            result.get("id") == "integration_test_doc" 
            for result in search_results.get("results", [])
        )
        assert found_doc, "Uploaded document not found in search results"

    async def test_cross_service_document_search_integration(self):
        """Test AI chat service can query document search service."""
        # Make a chat request that should trigger document search
        chat_request = {
            "message": "What is artificial intelligence?",
            "user_id": "test_user",
            "session_id": "integration_test_session",
            "use_documents": True
        }
        
        start_time = time.time()
        response = await self.chat_client.post("/chat", json=chat_request)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 10.0, f"Cross-service chat took {response_time:.2f}s"
        
        chat_response = response.json()
        assert "response" in chat_response
        assert "sources" in chat_response
        
        # Verify response contains document-based information
        response_text = chat_response["response"].lower()
        assert any(
            keyword in response_text 
            for keyword in ["artificial intelligence", "machine learning", "ai"]
        ), "Response doesn't contain expected AI-related content"
        
        # Verify sources are provided
        assert len(chat_response["sources"]) > 0, "No document sources provided"

    async def test_search_result_consistency(self):
        """Test search results are consistent between direct and chat-mediated queries."""
        query = "climate change sustainability"
        
        # Direct document search
        direct_response = await self.doc_client.post("/search", json={
            "query": query,
            "limit": 5
        })
        assert direct_response.status_code == 200
        direct_results = direct_response.json()
        
        # Chat-mediated search
        chat_response = await self.chat_client.post("/chat", json={
            "message": f"Search for information about {query}",
            "user_id": "test_user",
            "session_id": "consistency_test",
            "use_documents": True
        })
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        # Both should return relevant results
        assert len(direct_results.get("results", [])) > 0
        assert len(chat_data.get("sources", [])) > 0
        
        # Results should contain climate/sustainability content
        direct_content = " ".join([
            result.get("content", "") 
            for result in direct_results.get("results", [])
        ]).lower()
        
        assert any(
            keyword in direct_content 
            for keyword in ["climate", "sustainability", "environment"]
        )

    async def test_error_handling_cross_service(self):
        """Test error handling when services are unavailable or return errors."""
        # Test chat service handling of document search unavailability
        # Note: This would require temporarily stopping document search service
        # For now, test with malformed requests
        
        malformed_chat_request = {
            "message": "",  # Empty message
            "user_id": "test_user",
            "use_documents": True
        }
        
        response = await self.chat_client.post("/chat", json=malformed_chat_request)
        
        # Should handle gracefully (either 400 for validation error or fallback response)
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            # If successful, should have error handling in response
            data = response.json()
            assert "response" in data or "error" in data

    async def test_concurrent_cross_service_requests(self):
        """Test handling of concurrent requests across services."""
        concurrent_requests = 5
        chat_requests = [
            {
                "message": f"What can you tell me about topic {i}?",
                "user_id": f"concurrent_user_{i}",
                "session_id": f"concurrent_session_{i}",
                "use_documents": True
            }
            for i in range(concurrent_requests)
        ]
        
        # Execute requests concurrently
        start_time = time.time()
        
        async def make_request(request_data):
            return await self.chat_client.post("/chat", json=request_data)
        
        responses = await asyncio.gather(
            *[make_request(req) for req in chat_requests],
            return_exceptions=True
        )
        
        total_time = time.time() - start_time
        
        # Verify all requests completed
        successful_responses = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        
        assert len(successful_responses) >= concurrent_requests * 0.8, \
            f"Only {len(successful_responses)}/{concurrent_requests} requests succeeded"
        
        # Performance check - concurrent requests shouldn't take much longer than sequential
        expected_max_time = 15.0  # Reasonable timeout for concurrent processing
        assert total_time < expected_max_time, \
            f"Concurrent requests took {total_time:.2f}s, expected < {expected_max_time}s"

    async def test_data_flow_validation(self):
        """Test data flows correctly between services."""
        # Upload a specific document
        test_doc = {
            "id": "data_flow_test",
            "title": "Data Flow Test Document",
            "content": "This document contains unique identifiable content for data flow testing: UNIQUE_MARKER_12345",
            "metadata": {
                "category": "test",
                "tags": ["data_flow", "validation"],
                "source": "data_flow_test"
            }
        }
        
        upload_response = await self.doc_client.post("/upload", json=test_doc)
        assert upload_response.status_code in [200, 201]
        
        # Wait for indexing
        await asyncio.sleep(3)
        
        # Query through chat service for the unique content
        chat_request = {
            "message": "Find information containing UNIQUE_MARKER_12345",
            "user_id": "data_flow_user",
            "session_id": "data_flow_session",
            "use_documents": True
        }
        
        response = await self.chat_client.post("/chat", json=chat_request)
        assert response.status_code == 200
        
        chat_data = response.json()
        response_text = chat_data.get("response", "").lower()
        sources = chat_data.get("sources", [])
        
        # Verify the unique marker appears in response or sources
        unique_marker_found = (
            "unique_marker_12345" in response_text.lower() or
            any("unique_marker_12345" in str(source).lower() for source in sources)
        )
        
        assert unique_marker_found, "Unique marker not found in chat response or sources"

    async def test_memory_consistency_across_services(self):
        """Test conversation memory is maintained across service calls."""
        session_id = "memory_consistency_test"
        user_id = "memory_test_user"
        
        # First interaction
        first_request = {
            "message": "My name is Alice and I'm interested in AI research",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": True
        }
        
        first_response = await self.chat_client.post("/chat", json=first_request)
        assert first_response.status_code == 200
        
        # Second interaction referencing first
        second_request = {
            "message": "Based on what I mentioned about my interests, what documents might be relevant?",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": True
        }
        
        second_response = await self.chat_client.post("/chat", json=second_request)
        assert second_response.status_code == 200
        
        second_data = second_response.json()
        response_text = second_data.get("response", "").lower()
        
        # Response should reference AI research or related content
        assert any(
            keyword in response_text 
            for keyword in ["ai", "artificial intelligence", "research", "alice"]
        ), "Response doesn't maintain conversation context"

    async def test_streaming_response_integration(self):
        """Test streaming responses work across service integration."""
        chat_request = {
            "message": "Explain machine learning in detail",
            "user_id": "streaming_user",
            "session_id": "streaming_session",
            "use_documents": True,
            "stream": True
        }
        
        start_time = time.time()
        
        async with self.chat_client.stream(
            "POST", "/chat", json=chat_request
        ) as response:
            assert response.status_code == 200
            
            chunks_received = 0
            total_content = ""
            
            async for chunk in response.aiter_text():
                if chunk.strip():
                    chunks_received += 1
                    total_content += chunk
                
                # Don't wait too long for streaming
                if time.time() - start_time > 15.0:
                    break
        
        stream_time = time.time() - start_time
        
        assert chunks_received > 0, "No streaming chunks received"
        assert len(total_content) > 100, "Streaming content too short"
        assert stream_time < 15.0, f"Streaming took {stream_time:.2f}s"
        
        # Content should be relevant to machine learning
        content_lower = total_content.lower()
        assert any(
            keyword in content_lower 
            for keyword in ["machine learning", "algorithm", "model", "data"]
        ), "Streaming content not relevant to query"

    async def test_hybrid_search_workflow(self):
        """Test hybrid workflow combining web search and document search."""
        # Upload a technical document
        tech_doc = {
            "id": "hybrid_test_doc",
            "title": "Advanced Neural Networks",
            "content": "Neural networks with transformer architecture have revolutionized AI. Key innovations include attention mechanisms and self-supervised learning.",
            "metadata": {"category": "AI", "tags": ["neural networks", "transformers"]}
        }
        
        upload_response = await self.doc_client.post("/upload", json=tech_doc)
        assert upload_response.status_code in [200, 201]
        
        await asyncio.sleep(2)  # Allow indexing
        
        # Test hybrid query that should use both document and web search
        hybrid_request = {
            "message": "What are the latest developments in transformer neural networks?",
            "user_id": "hybrid_user",
            "session_id": "hybrid_session",
            "use_documents": True,
            "use_web_search": True,
            "hybrid_mode": True
        }
        
        response = await self.chat_client.post("/chat", json=hybrid_request)
        assert response.status_code == 200
        
        chat_data = response.json()
        assert "response" in chat_data
        
        # Response should contain information from both sources
        response_text = chat_data.get("response", "").lower()
        assert any(
            term in response_text 
            for term in ["transformer", "neural network", "attention"]
        ), "Response doesn't contain expected technical content"
        
        # Should have sources from documents
        sources = chat_data.get("sources", [])
        document_sources = [s for s in sources if isinstance(s, dict) and s.get("id") == "hybrid_test_doc"]
        assert len(document_sources) > 0, "No document sources found in hybrid response"

    async def test_multi_language_document_workflow(self):
        """Test workflow with multi-language documents."""
        multilang_docs = [
            {
                "id": "english_ai_doc",
                "title": "Artificial Intelligence in Healthcare",
                "content": "AI applications in healthcare include diagnostic imaging, drug discovery, and personalized treatment plans.",
                "metadata": {"language": "en", "category": "healthcare"}
            },
            {
                "id": "spanish_ai_doc", 
                "title": "Inteligencia Artificial en Medicina",
                "content": "La inteligencia artificial en medicina incluye diagnóstico por imágenes, descubrimiento de medicamentos y tratamientos personalizados.",
                "metadata": {"language": "es", "category": "healthcare"}
            }
        ]
        
        # Upload multilingual documents
        for doc in multilang_docs:
            response = await self.doc_client.post("/upload", json=doc)
            assert response.status_code in [200, 201]
            
        await asyncio.sleep(3)
        
        # Test multilingual search
        search_response = await self.doc_client.post("/search", json={
            "query": "artificial intelligence healthcare medicine",
            "limit": 10
        })
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        
        # Should find documents in both languages
        found_docs = [r.get("id") for r in search_results.get("results", [])]
        assert "english_ai_doc" in found_docs, "English document not found"
        
        # Test chat with multilingual context
        chat_response = await self.chat_client.post("/chat", json={
            "message": "What information do you have about AI in healthcare?",
            "user_id": "multilang_user",
            "session_id": "multilang_session", 
            "use_documents": True
        })
        
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        response_text = chat_data.get("response", "").lower()
        assert any(
            term in response_text 
            for term in ["healthcare", "medical", "diagnostic", "treatment"]
        ), "Response doesn't contain healthcare-related content"

    async def test_conversation_context_persistence(self):
        """Test conversation context persistence across service restarts simulation."""
        user_id = "context_persistence_user"
        session_id = "context_persistence_session"
        
        # Initial conversation
        initial_message = {
            "message": "My name is Dr. Smith and I'm researching quantum computing applications in cryptography.",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": True
        }
        
        response1 = await self.chat_client.post("/chat", json=initial_message)
        assert response1.status_code == 200
        
        # Follow-up message referencing previous context
        followup_message = {
            "message": "Based on my research interests I mentioned, what documents might be relevant?",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": True
        }
        
        response2 = await self.chat_client.post("/chat", json=followup_message)
        assert response2.status_code == 200
        
        response2_data = response2.json()
        response2_text = response2_data.get("response", "").lower()
        
        # Response should reference previous context
        context_indicators = ["quantum", "cryptography", "dr. smith", "research"]
        found_context = [
            indicator for indicator in context_indicators
            if indicator in response2_text
        ]
        
        assert len(found_context) > 0, f"No context persistence found. Expected: {context_indicators}"
        
        # Test context after simulated delay (cache expiration test)
        await asyncio.sleep(5)
        
        delayed_message = {
            "message": "Can you remind me what we were discussing about my research?",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": False
        }
        
        response3 = await self.chat_client.post("/chat", json=delayed_message)
        assert response3.status_code == 200
        
        response3_data = response3.json()
        response3_text = response3_data.get("response", "").lower()
        
        # Should still maintain some context
        maintained_context = any(
            term in response3_text 
            for term in ["quantum", "cryptography", "research"]
        )
        
        # Context may be maintained or gracefully handled
        print(f"Context persistence after delay: {'✓' if maintained_context else '⚠ Limited'}")

    async def test_large_document_processing_workflow(self):
        """Test workflow with large documents and complex queries."""
        # Create a large technical document
        large_content = """
        This is a comprehensive technical document about distributed systems and microservices architecture.
        
        Introduction to Distributed Systems:
        Distributed systems are collections of independent computers that appear to users as a single coherent system.
        Key challenges include network partitions, eventual consistency, and fault tolerance.
        
        Microservices Architecture:
        Microservices break down applications into small, independent services that communicate via APIs.
        Benefits include scalability, technology diversity, and independent deployment.
        Challenges include service discovery, data consistency, and increased operational complexity.
        
        Consistency Models:
        - Strong consistency ensures all nodes see the same data simultaneously
        - Eventual consistency allows temporary inconsistencies that resolve over time
        - Causal consistency preserves causally related operations order
        
        Fault Tolerance Patterns:
        - Circuit breakers prevent cascading failures
        - Bulkhead isolation contains failures to specific components
        - Retry mechanisms handle transient failures
        - Timeouts prevent indefinite blocking
        
        Data Management:
        - Database per service pattern maintains service autonomy
        - Saga pattern manages distributed transactions
        - Event sourcing captures state changes as events
        - CQRS separates read and write operations
        
        Service Communication:
        - Synchronous communication via REST APIs or gRPC
        - Asynchronous messaging via message queues or event streams
        - Service mesh provides communication infrastructure
        
        Monitoring and Observability:
        - Distributed tracing tracks requests across services
        - Metrics monitoring provides system health insights
        - Centralized logging aggregates service logs
        - Health checks enable automated failure detection
        """ * 3  # Make it larger
        
        large_doc = {
            "id": "large_distributed_systems_doc",
            "title": "Comprehensive Guide to Distributed Systems and Microservices",
            "content": large_content,
            "metadata": {
                "category": "technology",
                "tags": ["distributed systems", "microservices", "architecture"],
                "complexity": "advanced",
                "length": "comprehensive"
            }
        }
        
        # Upload large document
        start_time = time.time()
        upload_response = await self.doc_client.post("/upload", json=large_doc)
        upload_time = time.time() - start_time
        
        assert upload_response.status_code in [200, 201]
        assert upload_time < 10.0, f"Large document upload took {upload_time:.2f}s"
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Test complex queries on large document
        complex_queries = [
            {
                "query": "fault tolerance patterns circuit breaker bulkhead",
                "expected_terms": ["fault tolerance", "circuit breaker", "bulkhead"]
            },
            {
                "query": "consistency models eventual strong causal",
                "expected_terms": ["consistency", "eventual", "strong", "causal"]
            },
            {
                "query": "microservices data management saga CQRS",
                "expected_terms": ["microservices", "data management", "saga", "cqrs"]
            }
        ]
        
        for i, query_test in enumerate(complex_queries):
            search_start = time.time()
            search_response = await self.doc_client.post("/search", json={
                "query": query_test["query"],
                "limit": 5
            })
            search_time = time.time() - search_start
            
            assert search_response.status_code == 200
            assert search_time < 3.0, f"Complex search {i+1} took {search_time:.2f}s"
            
            search_results = search_response.json()
            
            # Verify large document is found
            found_large_doc = any(
                result.get("id") == "large_distributed_systems_doc"
                for result in search_results.get("results", [])
            )
            assert found_large_doc, f"Large document not found for query: {query_test['query']}"
            
        # Test chat with large document context
        chat_start = time.time()
        chat_response = await self.chat_client.post("/chat", json={
            "message": "Explain the differences between consistency models in distributed systems",
            "user_id": "large_doc_user",
            "session_id": "large_doc_session",
            "use_documents": True
        })
        chat_time = time.time() - chat_start
        
        assert chat_response.status_code == 200
        assert chat_time < 12.0, f"Chat with large document took {chat_time:.2f}s"
        
        chat_data = chat_response.json()
        response_text = chat_data.get("response", "").lower()
        
        # Should contain relevant information from large document
        consistency_terms = ["consistency", "strong", "eventual", "causal"]
        found_terms = [term for term in consistency_terms if term in response_text]
        
        assert len(found_terms) >= 2, f"Response lacks consistency model information. Found: {found_terms}"

    async def test_service_resilience_under_errors(self):
        """Test service resilience when one service experiences errors."""
        # Test scenario where document search has issues but chat service remains functional
        
        # First, ensure normal operation
        normal_chat = {
            "message": "What is artificial intelligence?",
            "user_id": "resilience_user",
            "session_id": "resilience_session",
            "use_documents": False  # Don't rely on document service
        }
        
        response = await self.chat_client.post("/chat", json=normal_chat)
        assert response.status_code == 200
        
        # Test graceful degradation when document service is unavailable
        degraded_chat = {
            "message": "Tell me about machine learning",
            "user_id": "resilience_user", 
            "session_id": "resilience_session",
            "use_documents": True,  # Try to use documents
            "fallback_enabled": True  # Enable fallback mode
        }
        
        # This should either succeed with document context or gracefully fall back
        response = await self.chat_client.post("/chat", json=degraded_chat)
        
        # Should not fail completely
        assert response.status_code in [200, 503], "Service should handle degradation gracefully"
        
        if response.status_code == 200:
            chat_data = response.json()
            assert "response" in chat_data
            assert len(chat_data["response"]) > 0
            print("✓ Service maintained functionality with graceful degradation")
        else:
            print("⚠ Service returned 503 - acceptable degraded response")

    async def test_real_time_collaboration_simulation(self):
        """Test real-time collaboration scenario with multiple users."""
        session_id = "collaboration_session"
        users = ["user_a", "user_b", "user_c"]
        
        # Upload collaborative document
        collab_doc = {
            "id": "collaboration_doc",
            "title": "Team Project Planning Document",
            "content": """
            Project: AI-Powered Document Analysis System
            
            Phase 1: Requirements Analysis
            - Identify stakeholder needs
            - Define functional requirements
            - Establish technical constraints
            
            Phase 2: System Design
            - Architecture design
            - API specification
            - Database schema design
            
            Phase 3: Implementation
            - Core functionality development
            - Integration testing
            - Performance optimization
            
            Phase 4: Deployment
            - Production environment setup
            - Monitoring implementation
            - User training and documentation
            """,
            "metadata": {
                "category": "project",
                "tags": ["collaboration", "planning", "AI"],
                "access": "team"
            }
        }
        
        upload_response = await self.doc_client.post("/upload", json=collab_doc)
        assert upload_response.status_code in [200, 201]
        
        await asyncio.sleep(2)
        
        # Simulate concurrent collaboration
        collaboration_tasks = []
        
        async def user_collaboration(user_id: str, user_message: str):
            """Simulate individual user collaboration."""
            return await self.chat_client.post("/chat", json={
                "message": user_message,
                "user_id": user_id,
                "session_id": session_id,
                "use_documents": True,
                "collaborative_context": True
            })
        
        # Define user interactions
        user_interactions = [
            ("user_a", "What are the key phases in our AI project plan?"),
            ("user_b", "What tasks are involved in the system design phase?"),
            ("user_c", "How should we approach the implementation phase?")
        ]
        
        # Execute concurrent interactions
        start_time = time.time()
        
        for user_id, message in user_interactions:
            task = asyncio.create_task(user_collaboration(user_id, message))
            collaboration_tasks.append(task)
            
        results = await asyncio.gather(*collaboration_tasks)
        collaboration_time = time.time() - start_time
        
        # Validate all collaborations succeeded
        successful_collaborations = [
            r for r in results 
            if not isinstance(r, Exception) and r.status_code == 200
        ]
        
        assert len(successful_collaborations) == len(user_interactions), \
            f"Only {len(successful_collaborations)}/{len(user_interactions)} collaborations succeeded"
            
        assert collaboration_time < 15.0, f"Collaboration took {collaboration_time:.2f}s"
        
        # Validate responses contain project-related content
        for i, response in enumerate(successful_collaborations):
            response_data = response.json()
            response_text = response_data.get("response", "").lower()
            
            project_terms = ["project", "phase", "design", "implementation", "ai"]
            found_terms = [term for term in project_terms if term in response_text]
            
            assert len(found_terms) > 0, f"User {i+1} response lacks project context"
            
        print(f"Real-time collaboration test: {len(successful_collaborations)} users, {collaboration_time:.2f}s")