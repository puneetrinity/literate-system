"""
Complete User Journey E2E Tests

Tests that simulate complete user workflows from document upload through search to chat interactions.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestCompleteUserJourney:
    """Test complete user workflows end-to-end."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, document_search_client, ai_chat_client, performance_monitor):
        """Set up test clients and monitoring for each test."""
        self.doc_client = document_search_client
        self.chat_client = ai_chat_client
        self.monitor = performance_monitor

    async def _make_monitored_request(self, client: AsyncClient, method: str, endpoint: str, **kwargs):
        """Make a request and record performance metrics."""
        start_time = time.time()
        
        if method.upper() == "GET":
            response = await client.get(endpoint, **kwargs)
        elif method.upper() == "POST":
            response = await client.post(endpoint, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration = time.time() - start_time
        self.monitor["record_request"](endpoint, method, duration, response.status_code)
        
        return response

    async def test_complete_research_workflow(self):
        """Test a complete research workflow: upload documents → search → ask questions."""
        user_id = "research_user"
        session_id = "research_session"
        
        # Step 1: Upload research documents
        research_documents = [
            {
                "id": "quantum_computing_basics",
                "title": "Introduction to Quantum Computing",
                "content": """
                Quantum computing is a revolutionary approach to computation that harnesses the principles 
                of quantum mechanics. Unlike classical computers that use bits (0 or 1), quantum computers 
                use quantum bits or qubits that can exist in superposition states.
                
                Key concepts include:
                - Superposition: Qubits can be in multiple states simultaneously
                - Entanglement: Qubits can be correlated in ways that classical systems cannot
                - Quantum interference: Probability amplitudes can interfere constructively or destructively
                
                Applications include cryptography, optimization, drug discovery, and financial modeling.
                Current challenges include quantum decoherence, error correction, and scaling to more qubits.
                """,
                "metadata": {
                    "category": "technology",
                    "tags": ["quantum computing", "physics", "computer science"],
                    "source": "research_paper",
                    "difficulty": "intermediate"
                }
            },
            {
                "id": "machine_learning_ethics",
                "title": "Ethics in Machine Learning",
                "content": """
                As machine learning systems become more prevalent, ethical considerations become increasingly 
                important. Key ethical challenges include:
                
                1. Bias and Fairness: ML models can perpetuate or amplify existing societal biases
                2. Privacy: Models may inadvertently expose sensitive information about training data
                3. Transparency: Complex models can be difficult to interpret and explain
                4. Accountability: Determining responsibility when AI systems make harmful decisions
                
                Best practices include diverse development teams, bias testing, privacy-preserving techniques,
                explainable AI methods, and robust governance frameworks. Organizations must balance innovation
                with responsible development and deployment.
                """,
                "metadata": {
                    "category": "technology",
                    "tags": ["machine learning", "ethics", "AI safety"],
                    "source": "research_paper",
                    "difficulty": "advanced"
                }
            }
        ]
        
        # Upload documents and track performance
        for doc in research_documents:
            response = await self._make_monitored_request(
                self.doc_client, "POST", "/upload", json=doc
            )
            assert response.status_code in [200, 201], f"Failed to upload {doc['id']}"
        
        # Wait for indexing
        await asyncio.sleep(3)
        
        # Step 2: Perform targeted searches
        search_queries = [
            {
                "query": "quantum computing superposition entanglement",
                "expected_doc": "quantum_computing_basics"
            },
            {
                "query": "machine learning bias fairness ethics",
                "expected_doc": "machine_learning_ethics"
            }
        ]
        
        for search_query in search_queries:
            response = await self._make_monitored_request(
                self.doc_client, "POST", "/search", 
                json={"query": search_query["query"], "limit": 5}
            )
            
            assert response.status_code == 200
            search_results = response.json()
            
            # Verify expected document appears in results
            found_expected = any(
                result.get("id") == search_query["expected_doc"]
                for result in search_results.get("results", [])
            )
            assert found_expected, f"Expected document {search_query['expected_doc']} not found"
        
        # Step 3: Interactive chat session with document context
        chat_interactions = [
            {
                "message": "What are the key principles of quantum computing?",
                "expected_topics": ["superposition", "entanglement", "quantum"]
            },
            {
                "message": "How does superposition work in quantum computing?",
                "expected_topics": ["superposition", "qubit", "states"]
            },
            {
                "message": "What are the main ethical concerns in machine learning?",
                "expected_topics": ["bias", "fairness", "privacy", "ethics"]
            },
            {
                "message": "Can you compare quantum computing applications with ML ethics challenges?",
                "expected_topics": ["quantum", "machine learning", "ethics", "applications"]
            }
        ]
        
        for i, interaction in enumerate(chat_interactions):
            chat_request = {
                "message": interaction["message"],
                "user_id": user_id,
                "session_id": session_id,
                "use_documents": True,
                "context_window": 5  # Keep conversation context
            }
            
            response = await self._make_monitored_request(
                self.chat_client, "POST", "/chat", json=chat_request
            )
            
            assert response.status_code == 200, f"Chat interaction {i+1} failed"
            
            chat_data = response.json()
            assert "response" in chat_data
            assert len(chat_data["response"]) > 50, "Response too short"
            
            # Check if response contains expected topics
            response_text = chat_data["response"].lower()
            found_topics = [
                topic for topic in interaction["expected_topics"]
                if topic.lower() in response_text
            ]
            
            assert len(found_topics) > 0, \
                f"Response doesn't contain expected topics: {interaction['expected_topics']}"
            
            # Verify sources are provided for document-based responses
            if "sources" in chat_data:
                assert len(chat_data["sources"]) > 0, "No document sources provided"

    async def test_multi_domain_knowledge_synthesis(self):
        """Test user journey across multiple knowledge domains."""
        user_id = "synthesis_user"
        session_id = "synthesis_session"
        
        # Upload documents from different domains
        multi_domain_docs = [
            {
                "id": "renewable_energy_tech",
                "title": "Renewable Energy Technologies",
                "content": """
                Renewable energy technologies are rapidly advancing to address climate change and energy security.
                Key technologies include:
                
                Solar Power: Photovoltaic cells convert sunlight directly into electricity. Efficiency improvements
                and cost reductions have made solar competitive with fossil fuels in many regions.
                
                Wind Energy: Wind turbines convert kinetic energy from moving air into electricity. Offshore wind
                farms can generate more power due to stronger, more consistent winds.
                
                Energy Storage: Battery technologies are crucial for storing renewable energy when production
                exceeds demand. Lithium-ion batteries are currently dominant, but alternatives like flow batteries
                and compressed air storage are being developed.
                """,
                "metadata": {
                    "category": "energy",
                    "tags": ["renewable energy", "solar", "wind", "batteries"],
                    "source": "technical_report"
                }
            },
            {
                "id": "financial_sustainability",
                "title": "Sustainable Finance and ESG Investing",
                "content": """
                Environmental, Social, and Governance (ESG) investing has become mainstream as investors
                recognize that sustainability factors can affect long-term returns.
                
                Environmental factors include climate change, resource depletion, and pollution.
                Social factors encompass human rights, labor standards, and community relations.
                Governance factors involve board diversity, executive compensation, and business ethics.
                
                Green bonds finance projects with environmental benefits. Sustainable investing strategies
                include ESG integration, screening, and impact investing. Regulatory frameworks are evolving
                to require better sustainability disclosure and prevent greenwashing.
                """,
                "metadata": {
                    "category": "finance",
                    "tags": ["ESG", "sustainable finance", "green bonds", "impact investing"],
                    "source": "financial_report"
                }
            }
        ]
        
        # Upload documents
        for doc in multi_domain_docs:
            response = await self._make_monitored_request(
                self.doc_client, "POST", "/upload", json=doc
            )
            assert response.status_code in [200, 201]
        
        await asyncio.sleep(3)
        
        # Test cross-domain synthesis through conversation
        synthesis_conversation = [
            {
                "message": "What are the latest developments in renewable energy?",
                "validate": lambda resp: any(word in resp.lower() for word in ["solar", "wind", "renewable"])
            },
            {
                "message": "How does ESG investing relate to renewable energy investments?",
                "validate": lambda resp: any(word in resp.lower() for word in ["esg", "environmental", "sustainable"])
            },
            {
                "message": "Can you analyze the investment potential of renewable energy from both technical and financial perspectives?",
                "validate": lambda resp: any(word in resp.lower() for word in ["investment", "technology", "financial"])
            }
        ]
        
        for i, turn in enumerate(synthesis_conversation):
            chat_request = {
                "message": turn["message"],
                "user_id": user_id,
                "session_id": session_id,
                "use_documents": True,
                "synthesis_mode": True  # Request cross-domain synthesis
            }
            
            response = await self._make_monitored_request(
                self.chat_client, "POST", "/chat", json=chat_request
            )
            
            assert response.status_code == 200
            chat_data = response.json()
            
            # Validate response content
            assert turn["validate"](chat_data["response"]), \
                f"Turn {i+1} response validation failed"

    async def test_collaborative_research_session(self):
        """Test a collaborative research session with multiple users."""
        session_id = "collaborative_session"
        users = ["researcher_a", "researcher_b", "researcher_c"]
        
        # Upload shared research documents
        shared_doc = {
            "id": "collaborative_research_doc",
            "title": "Collaborative AI Research Framework",
            "content": """
            Collaborative AI research requires effective coordination between multiple researchers,
            shared access to data and computational resources, and standardized methodologies.
            
            Key components include:
            - Version control for code and data
            - Reproducible experiment frameworks
            - Shared documentation and knowledge bases
            - Collaborative annotation tools
            - Distributed computing resources
            
            Best practices involve establishing clear roles, regular communication, and
            standardized evaluation metrics across the research team.
            """,
            "metadata": {
                "category": "research",
                "tags": ["collaboration", "AI research", "methodology"],
                "source": "research_framework"
            }
        }
        
        response = await self._make_monitored_request(
            self.doc_client, "POST", "/upload", json=shared_doc
        )
        assert response.status_code in [200, 201]
        
        await asyncio.sleep(2)
        
        # Simulate collaborative interaction
        collaborative_turns = [
            ("researcher_a", "What are the key components of collaborative AI research?"),
            ("researcher_b", "How can we ensure reproducibility in our shared experiments?"),
            ("researcher_c", "What tools should we use for version control and documentation?"),
            ("researcher_a", "Based on the previous discussions, what's our action plan?")
        ]
        
        conversation_context = []
        
        for user_id, message in collaborative_turns:
            chat_request = {
                "message": message,
                "user_id": user_id,
                "session_id": session_id,
                "use_documents": True,
                "collaborative_mode": True
            }
            
            response = await self._make_monitored_request(
                self.chat_client, "POST", "/chat", json=chat_request
            )
            
            assert response.status_code == 200
            chat_data = response.json()
            
            conversation_context.append({
                "user": user_id,
                "message": message,
                "response": chat_data["response"]
            })
            
            # Response should be relevant to collaborative research
            response_text = chat_data["response"].lower()
            assert any(
                keyword in response_text 
                for keyword in ["collaborative", "research", "team", "shared"]
            ), f"Response not relevant to collaborative research for user {user_id}"
        
        # Final validation: ensure conversation maintains coherence
        assert len(conversation_context) == len(collaborative_turns)
        
        # Last response should reference previous discussion
        final_response = conversation_context[-1]["response"].lower()
        assert any(
            keyword in final_response 
            for keyword in ["plan", "action", "previous", "discussion"]
        ), "Final response doesn't reference collaborative context"

    async def test_error_recovery_workflow(self):
        """Test user workflow resilience to various error conditions."""
        user_id = "error_recovery_user"
        session_id = "error_recovery_session"
        
        # Test 1: Invalid document upload handling
        invalid_doc = {
            "id": "",  # Invalid empty ID
            "title": "Test Document",
            "content": "Test content"
        }
        
        response = await self._make_monitored_request(
            self.doc_client, "POST", "/upload", json=invalid_doc
        )
        
        # Should return appropriate error status
        assert response.status_code in [400, 422]
        
        # Test 2: Recovery with valid document
        valid_doc = {
            "id": "recovery_test_doc",
            "title": "Recovery Test Document", 
            "content": "This document tests error recovery in the upload workflow.",
            "metadata": {
                "category": "test",
                "tags": ["error_recovery"],
                "source": "test"
            }
        }
        
        response = await self._make_monitored_request(
            self.doc_client, "POST", "/upload", json=valid_doc
        )
        assert response.status_code in [200, 201]
        
        await asyncio.sleep(2)
        
        # Test 3: Chat with malformed request handling
        malformed_chat = {
            "message": "",  # Empty message
            "user_id": user_id,
            "session_id": session_id
        }
        
        response = await self._make_monitored_request(
            self.chat_client, "POST", "/chat", json=malformed_chat
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
        
        # Test 4: Recovery with valid chat request
        valid_chat = {
            "message": "Can you find information about error recovery?",
            "user_id": user_id,
            "session_id": session_id,
            "use_documents": True
        }
        
        response = await self._make_monitored_request(
            self.chat_client, "POST", "/chat", json=valid_chat
        )
        assert response.status_code == 200
        
        chat_data = response.json()
        assert "response" in chat_data
        assert len(chat_data["response"]) > 0

    async def test_performance_under_load_workflow(self):
        """Test complete workflow performance under simulated load."""
        base_user_id = "load_test_user"
        concurrent_users = 3
        documents_per_user = 2
        
        async def user_workflow(user_index: int):
            """Simulate a complete user workflow."""
            user_id = f"{base_user_id}_{user_index}"
            session_id = f"load_session_{user_index}"
            
            # Upload documents
            for doc_index in range(documents_per_user):
                doc = {
                    "id": f"load_doc_{user_index}_{doc_index}",
                    "title": f"Load Test Document {user_index}-{doc_index}",
                    "content": f"""
                    This is load test document {doc_index} for user {user_index}.
                    It contains information about performance testing and system scalability.
                    Load testing helps identify bottlenecks and capacity limits in distributed systems.
                    User {user_index} is testing document {doc_index} for concurrent operations.
                    """,
                    "metadata": {
                        "category": "test",
                        "tags": ["load_test", f"user_{user_index}"],
                        "source": "load_testing"
                    }
                }
                
                response = await self._make_monitored_request(
                    self.doc_client, "POST", "/upload", json=doc
                )
                assert response.status_code in [200, 201]
            
            # Wait for indexing
            await asyncio.sleep(1)
            
            # Perform searches
            search_response = await self._make_monitored_request(
                self.doc_client, "POST", "/search",
                json={"query": f"load test user {user_index}", "limit": 5}
            )
            assert search_response.status_code == 200
            
            # Chat interactions
            for chat_index in range(2):
                chat_request = {
                    "message": f"What information do you have about load testing for user {user_index}?",
                    "user_id": user_id,
                    "session_id": session_id,
                    "use_documents": True
                }
                
                response = await self._make_monitored_request(
                    self.chat_client, "POST", "/chat", json=chat_request
                )
                assert response.status_code == 200
            
            return user_index
        
        # Execute concurrent user workflows
        start_time = time.time()
        
        results = await asyncio.gather(
            *[user_workflow(i) for i in range(concurrent_users)],
            return_exceptions=True
        )
        
        total_time = time.time() - start_time
        
        # Validate results
        successful_users = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_users) == concurrent_users, \
            f"Only {len(successful_users)}/{concurrent_users} user workflows completed successfully"
        
        # Performance validation
        max_acceptable_time = 30.0  # 30 seconds for all concurrent workflows
        assert total_time < max_acceptable_time, \
            f"Load test took {total_time:.2f}s, expected < {max_acceptable_time}s"
        
        print(f"Load test completed: {concurrent_users} users, {total_time:.2f}s total time")