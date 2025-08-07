"""
RAG Orchestration Node for ChatGraph
Implements smart RAG enhancement with fallback patterns
"""

import asyncio
import time
from typing import Dict, Any, Optional

from app.core.logging import get_logger
from app.graphs.base import BaseGraphNode, NodeType, NodeResult, GraphState
from app.services.rag_orchestrator import get_rag_orchestrator, RAGEnhancement

logger = get_logger("graphs.rag_orchestration")


class RAGOrchestrationNode(BaseGraphNode):
    """
    RAG Orchestration Node that enhances queries with document retrieval
    
    Implements Service Orchestration pattern:
    - Non-blocking RAG calls with timeout
    - Circuit breaker for resilience  
    - Graceful degradation when RAG unavailable
    - Smart caching of RAG results
    """
    
    def __init__(self):
        super().__init__("rag_orchestration", NodeType.PROCESSING)
        self._orchestrator = None
    
    async def _get_orchestrator(self):
        """Get or initialize the RAG orchestrator"""
        if self._orchestrator is None:
            self._orchestrator = await get_rag_orchestrator()
        return self._orchestrator
    
    def _determine_search_strategy(self, state: GraphState) -> Dict[str, Any]:
        """
        Determine optimal search strategy based on query characteristics
        
        Returns:
            Dict with search_type, max_chunks, and priority
        """
        query = state.processed_query or state.original_query
        intent = getattr(state, 'query_intent', 'conversation')
        complexity = getattr(state, 'query_complexity', 0.5)
        
        # Default strategy
        strategy = {
            "search_type": "hybrid",
            "max_chunks": 3,
            "priority": "normal"
        }
        
        # Adjust based on intent
        if intent == "question":
            # Questions benefit from semantic search
            strategy["search_type"] = "semantic" 
            strategy["max_chunks"] = 5
            strategy["priority"] = "high"
            
        elif intent == "code":
            # Code queries benefit from keyword matching
            strategy["search_type"] = "keyword"
            strategy["max_chunks"] = 3
            strategy["priority"] = "normal"
            
        elif intent == "analysis":
            # Analysis benefits from comprehensive hybrid search
            strategy["search_type"] = "hybrid"
            strategy["max_chunks"] = 7
            strategy["priority"] = "high"
            
        # Adjust based on complexity
        if complexity > 0.7:
            strategy["max_chunks"] = min(strategy["max_chunks"] + 2, 10)
        elif complexity < 0.3:
            strategy["max_chunks"] = max(strategy["max_chunks"] - 1, 2)
        
        # Check for specific indicators
        query_lower = query.lower()
        
        # Documentation queries
        if any(term in query_lower for term in ['docs', 'documentation', 'api', 'reference']):
            strategy["search_type"] = "keyword"
            strategy["max_chunks"] = 5
            strategy["priority"] = "high"
        
        # Factual queries  
        if any(term in query_lower for term in ['what is', 'explain', 'define', 'describe']):
            strategy["search_type"] = "semantic"
            strategy["max_chunks"] = 4
            strategy["priority"] = "high"
        
        return strategy
    
    def _build_enhanced_context(self, rag_enhancement: RAGEnhancement) -> Dict[str, Any]:
        """Build enhanced context from RAG results"""
        if not rag_enhancement or not rag_enhancement.sources:
            return {}
        
        # Format sources for prompt inclusion
        formatted_sources = []
        for i, source in enumerate(rag_enhancement.sources[:5], 1):  # Limit to top 5
            formatted_source = {
                "index": i,
                "content": source.content[:500],  # Limit content length
                "title": source.title,
                "score": source.score,
                "source_id": source.source or source.chunk_id
            }
            formatted_sources.append(formatted_source)
        
        return {
            "rag_sources": formatted_sources,
            "rag_confidence": rag_enhancement.confidence,
            "search_type": rag_enhancement.search_type,
            "total_sources": rag_enhancement.total_chunks,
            "response_time": rag_enhancement.response_time_ms,
            "query_id": rag_enhancement.query_id,
            "has_factual_context": True
        }
    
    async def execute(self, state: GraphState, **kwargs) -> NodeResult:
        """
        Execute RAG orchestration with smart fallback patterns
        
        Flow:
        1. Determine if RAG enhancement is needed
        2. Select optimal search strategy  
        3. Execute RAG query with timeout and circuit breaker
        4. Enhance state with RAG results or continue without
        5. Never fail - always provide graceful degradation
        """
        start_time = time.time()
        correlation_id = getattr(state, 'query_id', None)
        
        logger.info(f"[RAGOrchestrationNode] *** STARTING RAG ORCHESTRATION *** | correlation_id={correlation_id}")
        print(f"[DEBUG] RAGOrchestrationNode.execute() called - query: {state.original_query}")
        
        try:
            # Get RAG orchestrator
            orchestrator = await self._get_orchestrator()
            
            # Build context for RAG decision
            context = {
                "intent": getattr(state, 'query_intent', 'conversation'),
                "complexity": getattr(state, 'query_complexity', 0.5),
                "intent_requires_facts": getattr(state, 'query_intent', '') in ['question', 'analysis'],
                "session_history": getattr(state, 'conversation_history', [])
            }
            
            # Determine search strategy
            strategy = self._determine_search_strategy(state)
            logger.debug(f"[RAGOrchestrationNode] Search strategy: {strategy} | correlation_id={correlation_id}")
            
            # Attempt RAG enhancement
            query = state.processed_query or state.original_query
            
            # Execute RAG orchestration (with built-in circuit breaker and timeout)
            rag_enhancement = await orchestrator.enhance_query(
                query=query,
                context=context,
                max_chunks=strategy["max_chunks"],
                search_type=strategy["search_type"]
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if rag_enhancement:
                # RAG enhancement successful
                enhanced_context = self._build_enhanced_context(rag_enhancement)
                
                # Store RAG results in state for response generator
                state.intermediate_results["rag_enhancement"] = enhanced_context
                
                logger.info(f"[RAGOrchestrationNode] RAG enhancement successful: "
                          f"{len(rag_enhancement.sources)} sources, "
                          f"confidence={rag_enhancement.confidence:.2f}, "
                          f"time={execution_time:.1f}ms | correlation_id={correlation_id}")
                
                return NodeResult(
                    success=True,
                    data={
                        "rag_enhanced": True,
                        "sources_found": len(rag_enhancement.sources),
                        "confidence": rag_enhancement.confidence,
                        "search_type": rag_enhancement.search_type,
                        "rag_response_time_ms": rag_enhancement.response_time_ms
                    },
                    confidence=0.9,
                    execution_time=execution_time / 1000,
                    metadata=enhanced_context
                )
                
            else:
                # RAG enhancement not needed or failed - continue gracefully
                logger.debug(f"[RAGOrchestrationNode] No RAG enhancement - continuing without | correlation_id={correlation_id}")
                
                return NodeResult(
                    success=True,
                    data={
                        "rag_enhanced": False,
                        "reason": "not_needed_or_unavailable",
                        "fallback_mode": True
                    },
                    confidence=0.8,
                    execution_time=execution_time / 1000
                )
        
        except Exception as e:
            # Even on error, we continue gracefully
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"[RAGOrchestrationNode] *** ERROR in RAG orchestration ***: {str(e)} | correlation_id={correlation_id}")
            print(f"[DEBUG] RAGOrchestrationNode FAILED: {str(e)}")
            
            return NodeResult(
                success=True,  # Still successful - we gracefully degraded
                data={
                    "rag_enhanced": False,
                    "reason": "orchestration_error",
                    "error": str(e),
                    "fallback_mode": True
                },
                confidence=0.7,
                execution_time=execution_time / 1000
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for RAG orchestration"""
        try:
            orchestrator = await self._get_orchestrator()
            return await orchestrator.health_check()
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }