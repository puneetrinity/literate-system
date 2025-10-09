"""
RAG Query Orchestrator with Circuit Breaker Pattern
Implements Service Orchestration pattern for RAG integration
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.providers.document_search.ultra_fast_provider import UltraFastSearchProvider, DocumentSearchResult

logger = get_logger("services.rag_orchestrator")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    success_threshold: int = 3
    timeout_seconds: float = 2.0


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    total_requests: int = 0
    total_failures: int = 0
    total_timeouts: int = 0


class CircuitBreaker:
    """Circuit breaker for RAG service calls"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """Check if request can be executed"""
        async with self._lock:
            if self.stats.state == CircuitState.CLOSED:
                return True
            
            elif self.stats.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if (self.stats.last_failure_time and 
                    datetime.now() - self.stats.last_failure_time > 
                    timedelta(seconds=self.config.recovery_timeout_seconds)):
                    
                    self.stats.state = CircuitState.HALF_OPEN
                    self.stats.success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False
            
            elif self.stats.state == CircuitState.HALF_OPEN:
                return True
        
        return False
    
    async def record_success(self):
        """Record successful execution"""
        async with self._lock:
            self.stats.total_requests += 1
            
            if self.stats.state == CircuitState.HALF_OPEN:
                self.stats.success_count += 1
                if self.stats.success_count >= self.config.success_threshold:
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    logger.info("Circuit breaker transitioned to CLOSED")
            
            elif self.stats.state == CircuitState.CLOSED:
                self.stats.failure_count = 0
    
    async def record_failure(self, is_timeout: bool = False):
        """Record failed execution"""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.total_failures += 1
            if is_timeout:
                self.stats.total_timeouts += 1
            
            self.stats.failure_count += 1
            self.stats.last_failure_time = datetime.now()
            
            if (self.stats.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN] and
                self.stats.failure_count >= self.config.failure_threshold):
                
                self.stats.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened due to {self.stats.failure_count} failures")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_timeouts": self.stats.total_timeouts,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None
        }


@dataclass
class RAGEnhancement:
    """RAG enhancement data for chat responses"""
    sources: List[DocumentSearchResult] = field(default_factory=list)
    confidence: float = 0.0
    search_type: str = "hybrid"
    response_time_ms: float = 0.0
    total_chunks: int = 0
    query_id: str = ""


class RAGOrchestrator:
    """RAG Query Orchestrator with Service Orchestration pattern"""
    
    def __init__(self, rag_service_url: Optional[str] = None):
        from app.core.config import get_settings
        settings = get_settings()
        service_url = rag_service_url or settings.document_search_url
        self.rag_provider = UltraFastSearchProvider(base_url=service_url)
        
        # Circuit breaker configuration
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout_seconds=30.0,
            success_threshold=3,
            timeout_seconds=2.0
        )
        self.circuit_breaker = CircuitBreaker(circuit_config)
        
        # Cache for recent queries
        self.query_cache: Dict[str, RAGEnhancement] = {}
        self.cache_max_size = 100
        self.cache_ttl_seconds = 300  # 5 minutes
        
        logger.info(f"RAG Orchestrator initialized with service URL: {rag_service_url}")
    
    async def initialize(self):
        """Initialize the orchestrator"""
        await self.rag_provider.initialize()
        logger.info("RAG Orchestrator initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.rag_provider.cleanup()
    
    def _needs_rag_enhancement(self, query: str, context: Dict[str, Any]) -> bool:
        """Determine if query needs RAG enhancement"""
        
        # Skip for very short queries
        if len(query.strip()) < 10:
            return False
        
        # Skip for greetings and simple responses
        greeting_words = {'hi', 'hello', 'hey', 'thanks', 'bye', 'goodbye'}
        query_words = set(query.lower().split())
        if query_words.intersection(greeting_words) and len(query_words) <= 3:
            return False
        
        # Check for factual question indicators
        factual_indicators = {
            'what', 'how', 'when', 'where', 'why', 'who', 
            'explain', 'describe', 'define', 'tell me', 'show me',
            'find', 'search', 'lookup', 'documentation', 'docs'
        }
        
        query_lower = query.lower()
        for indicator in factual_indicators:
            if indicator in query_lower:
                return True
        
        # Check if context suggests need for factual data
        if context.get('intent_requires_facts', False):
            return True
        
        return False
    
    def _get_cache_key(self, query: str, search_type: str = "hybrid", max_chunks: int = 5) -> str:
        """Generate cache key for query"""
        return f"{hash(query.lower())}:{search_type}:{max_chunks}"
    
    def _is_cache_valid(self, cached_time: float) -> bool:
        """Check if cached result is still valid"""
        return time.time() - cached_time < self.cache_ttl_seconds
    
    async def enhance_query(
        self, 
        query: str, 
        context: Dict[str, Any], 
        max_chunks: int = 3,
        search_type: str = "hybrid"
    ) -> Optional[RAGEnhancement]:
        """
        Enhance query with RAG data using Service Orchestration pattern
        
        Args:
            query: User query
            context: Chat context
            max_chunks: Maximum chunks to retrieve
            search_type: Type of search (semantic, keyword, hybrid)
            
        Returns:
            RAGEnhancement object or None if enhancement not needed/failed
        """
        
        # 1. Check if RAG enhancement is needed
        if not self._needs_rag_enhancement(query, context):
            logger.debug(f"Query doesn't need RAG enhancement: {query[:50]}...")
            return None
        
        # 2. Check cache first
        cache_key = self._get_cache_key(query, search_type, max_chunks)
        if cache_key in self.query_cache:
            cached_result, cached_time = self.query_cache[cache_key]
            if self._is_cache_valid(cached_time):
                logger.debug(f"Using cached RAG result for query: {query[:50]}...")
                return cached_result
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        
        # 3. Check circuit breaker
        if not await self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker is OPEN, skipping RAG enhancement")
            return None
        
        start_time = time.time()
        
        try:
            # 4. Query RAG service with timeout
            logger.debug(f"Querying RAG service: {query[:50]}...")
            
            response = await asyncio.wait_for(
                self.rag_provider.search_documents(
                    query=query,
                    num_results=max_chunks,
                    search_type=search_type
                ),
                timeout=self.circuit_breaker.config.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.success and response.data:
                # 5. Create enhancement object
                enhancement = RAGEnhancement(
                    sources=response.data,
                    confidence=response.metadata.get("confidence_score", 0.0),
                    search_type=search_type,
                    response_time_ms=response_time,
                    total_chunks=len(response.data),
                    query_id=response.metadata.get("query_id", "")
                )
                
                # 6. Cache the result
                if len(self.query_cache) >= self.cache_max_size:
                    # Remove oldest entry
                    oldest_key = min(self.query_cache.keys(), 
                                   key=lambda k: self.query_cache[k][1])
                    del self.query_cache[oldest_key]
                
                self.query_cache[cache_key] = (enhancement, time.time())
                
                # 7. Record success
                await self.circuit_breaker.record_success()
                
                logger.info(f"RAG enhancement successful: {len(response.data)} sources in {response_time:.1f}ms")
                return enhancement
                
            else:
                # RAG service returned no results
                logger.debug(f"RAG service returned no results for: {query[:50]}...")
                await self.circuit_breaker.record_success()  # Service is working, just no results
                return None
                
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"RAG service timeout after {response_time:.1f}ms")
            await self.circuit_breaker.record_failure(is_timeout=True)
            return None
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"RAG service error after {response_time:.1f}ms: {str(e)}")
            await self.circuit_breaker.record_failure(is_timeout=False)
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on RAG orchestrator"""
        
        health_status = {
            "orchestrator_healthy": True,
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "cache_size": len(self.query_cache),
            "cache_max_size": self.cache_max_size
        }
        
        try:
            # Test RAG service connectivity
            service_healthy = await self.rag_provider.health_check()
            health_status["rag_service_healthy"] = service_healthy
            
        except Exception as e:
            health_status["orchestrator_healthy"] = False
            health_status["error"] = str(e)
        
        return health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "cache_stats": {
                "size": len(self.query_cache),
                "max_size": self.cache_max_size,
                "ttl_seconds": self.cache_ttl_seconds
            }
        }


# Global orchestrator instance
_rag_orchestrator: Optional[RAGOrchestrator] = None


async def get_rag_orchestrator() -> RAGOrchestrator:
    """Get or create RAG orchestrator instance"""
    global _rag_orchestrator
    
    if _rag_orchestrator is None:
        _rag_orchestrator = RAGOrchestrator()
        await _rag_orchestrator.initialize()
    
    return _rag_orchestrator


async def shutdown_rag_orchestrator():
    """Shutdown global RAG orchestrator"""
    global _rag_orchestrator
    
    if _rag_orchestrator:
        await _rag_orchestrator.cleanup()
        _rag_orchestrator = None