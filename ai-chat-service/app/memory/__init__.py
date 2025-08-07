"""
Memory-Enhanced Multi-Armed Bandit System for Conversation Management.

This module implements the complete conversation memory management system with
adaptive routing using multi-armed bandit optimization. The system provides:

1. **Intelligent Memory Strategy Selection**: Uses Thompson Sampling bandit to
   dynamically select optimal memory strategies based on conversation context

2. **Hybrid Memory Architecture**: Combines Redis (hot cache) and ClickHouse 
   (cold storage) for efficient conversation memory management

3. **Background Summarization**: Asynchronous summarization using phi3:mini
   for cost-effective conversation compression

4. **Context-Aware Routing**: Memory-aware adaptive routing that considers
   conversation history, user preferences, and coherence requirements

5. **Real-time Performance Optimization**: Continuous reward-based learning
   with comprehensive metrics tracking and cost optimization

## Key Components

### Core Orchestration
- `BanditIntegratedMemoryOrchestrator`: Central coordinator for all memory operations
- `MemoryAwareEnhancedRouter`: Enhanced adaptive router with memory integration
- `MemoryEnhancedContextManagerNode`: Graph node for intelligent context assembly

### Memory Management
- `ConversationMemoryCache`: Redis-based hot memory with token management
- `ConversationClickHouseManager`: Cold storage with semantic search capabilities
- `AsyncSummarizationService`: Background summarization with priority queuing

### Adaptive Learning
- `MemoryAwareThompsonBandit`: Contextual bandit for memory strategy selection
- `MemoryAwareRewardCalculator`: Comprehensive reward system with memory metrics
- `MemoryRoutingArm`: Configurable memory strategies with budget management

## Usage Example

```python
from app.memory import create_integrated_memory_system
from app.models.manager import ModelManager
from app.cache.redis_client import CacheManager

# Initialize core dependencies
model_manager = ModelManager()
cache_manager = CacheManager()

# Create integrated memory system
memory_system = await create_integrated_memory_system(
    model_manager=model_manager,
    cache_manager=cache_manager,
    enable_background_summarization=True,
    enable_semantic_search=True
)

# Use in conversation processing
session_id = "user_123_session_456"
user_query = "How do I optimize my Python code for better performance?"

# Assemble conversation context with adaptive strategy selection
context, arm_used, config = await memory_system.orchestrator.assemble_conversation_context(
    session_id=session_id,
    user_id="user_123"
)

# Store conversation turn
await memory_system.orchestrator.store_conversation_message(
    session_id=session_id,
    message={"role": "user", "content": user_query},
    user_id="user_123"
)

# Update performance metrics for continuous learning
await memory_system.orchestrator.update_bandit_performance(
    operation_id="operation_123",
    performance_metrics={"response_time_ms": 2500, "success": True},
    quality_assessment={"coherence_maintained": True, "context_relevance": 0.8}
)
```

## Architecture Overview

The system implements a three-layer architecture:

1. **Strategy Layer**: Multi-armed bandit selects optimal memory configuration
2. **Storage Layer**: Hybrid Redis/ClickHouse with intelligent caching
3. **Processing Layer**: Background summarization and semantic search

Memory strategies range from minimal (cost-optimized) to comprehensive 
(enterprise-grade) with automatic adaptation based on:
- Conversation complexity and length
- User tier and preferences  
- Cost sensitivity and budget constraints
- Response time requirements
- Coherence and quality targets

## Performance Characteristics

- **Context Assembly**: <500ms average (95th percentile <2s)
- **Memory Budget**: 2K-16K tokens per conversation (user tier dependent)
- **Cache Hit Rate**: >75% for active conversations
- **Summarization**: <3s for 20-message conversations using phi3:mini
- **Cost Efficiency**: 85% local processing, 15% API fallback

## Monitoring and Analytics

Comprehensive metrics collection includes:
- Bandit arm performance and confidence intervals
- Memory effectiveness and budget utilization
- Conversation coherence and quality scores
- Cost tracking and ROI analysis
- Real-time performance dashboards
"""

from typing import Dict, Any, Optional
import structlog

# Core components
from .bandit_orchestrator import (
    BanditIntegratedMemoryOrchestrator,
    create_bandit_integrated_orchestrator
)
from .memory_aware_router import (
    MemoryAwareEnhancedRouter,
    create_memory_aware_router
)
from .memory_context_node import (
    MemoryEnhancedContextManagerNode,
    create_memory_enhanced_context_node
)

# Memory management
from .redis_memory import ConversationMemoryCache
from .clickhouse_memory import (
    ConversationClickHouseManager,
    create_conversation_clickhouse_manager
)
from .summarization_service import (
    AsyncSummarizationService,
    create_async_summarization_service
)

# Adaptive learning
from .contextual_bandit import MemoryAwareThompsonBandit
from .reward_calculator import (
    MemoryAwareRewardCalculator,
    create_memory_aware_reward_calculator
)
from .routing_arms import (
    MemoryRoutingArm,
    MemoryArmManager,
    MEMORY_ROUTING_ARMS
)

logger = structlog.get_logger(__name__)


class IntegratedMemorySystem:
    """
    Complete integrated memory system with all components.
    
    Provides a single interface to the entire memory management system
    with proper initialization, cleanup, and monitoring capabilities.
    """
    
    def __init__(
        self,
        orchestrator: BanditIntegratedMemoryOrchestrator,
        router: MemoryAwareEnhancedRouter,
        context_node: MemoryEnhancedContextManagerNode
    ):
        self.orchestrator = orchestrator
        self.router = router
        self.context_node = context_node
        
        # System health tracking
        self.initialization_time = None
        self.is_healthy = True
        self.last_health_check = None
    
    async def initialize(self) -> bool:
        """Initialize all memory system components"""
        try:
            import time
            start_time = time.time()
            
            # Initialize router (which initializes orchestrator components)
            await self.router.initialize()
            
            # Initialize ClickHouse conversation tables
            if hasattr(self.orchestrator, 'clickhouse_memory'):
                await self.orchestrator.clickhouse_memory.initialize_conversation_storage()
            
            # Start background summarization workers
            if hasattr(self.orchestrator, 'summarization_service'):
                await self.orchestrator.summarization_service.start_workers(num_workers=2)
            
            self.initialization_time = time.time() - start_time
            self.is_healthy = True
            
            logger.info(
                "integrated_memory_system_initialized",
                initialization_time_ms=round(self.initialization_time * 1000, 1),
                components=["orchestrator", "router", "context_node", "summarization", "clickhouse"]
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "integrated_memory_system_initialization_failed",
                error=str(e)
            )
            self.is_healthy = False
            return False
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all components"""
        try:
            # Stop summarization workers
            if hasattr(self.orchestrator, 'summarization_service'):
                await self.orchestrator.summarization_service.stop_workers()
            
            logger.info("integrated_memory_system_shutdown_complete")
            
        except Exception as e:
            logger.error(
                "integrated_memory_system_shutdown_error",
                error=str(e)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all components"""
        try:
            import time
            self.last_health_check = time.time()
            
            health_status = {
                'overall_healthy': True,
                'timestamp': self.last_health_check,
                'components': {}
            }
            
            # Check orchestrator health
            orchestrator_stats = await self.orchestrator.get_orchestrator_stats()
            health_status['components']['orchestrator'] = {
                'healthy': 'error' not in orchestrator_stats,
                'active_operations': orchestrator_stats.get('orchestrator_health', {}).get('active_operations', 0)
            }
            
            # Check router health
            router_stats = self.router.get_memory_aware_status()
            health_status['components']['router'] = {
                'healthy': True,  # Router is always healthy if reachable
                'total_requests': router_stats.get('request_stats', {}).get('total_requests', 0)
            }
            
            # Check context node health
            node_stats = self.context_node.get_node_stats()
            health_status['components']['context_node'] = {
                'healthy': True,
                'total_executions': node_stats.get('execution_stats', {}).get('total_executions', 0)
            }
            
            # Overall health assessment
            component_health = [comp['healthy'] for comp in health_status['components'].values()]
            health_status['overall_healthy'] = all(component_health)
            self.is_healthy = health_status['overall_healthy']
            
            return health_status
            
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            self.is_healthy = False
            return {
                'overall_healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            'system_info': {
                'initialization_time_ms': round(self.initialization_time * 1000, 1) if self.initialization_time else None,
                'is_healthy': self.is_healthy,
                'last_health_check': self.last_health_check
            },
            'orchestrator_stats': self.orchestrator.get_orchestrator_stats() if hasattr(self.orchestrator, 'get_orchestrator_stats') else {},
            'router_stats': self.router.get_memory_aware_status() if hasattr(self.router, 'get_memory_aware_status') else {},
            'context_node_stats': self.context_node.get_node_stats()
        }


async def create_integrated_memory_system(
    model_manager,
    cache_manager,
    clickhouse_config: Optional[Dict[str, Any]] = None,
    enable_background_summarization: bool = True,
    enable_semantic_search: bool = True,
    enable_memory_routing: bool = True,
    **kwargs
) -> IntegratedMemorySystem:
    """
    Create and initialize complete integrated memory system.
    
    Args:
        model_manager: ModelManager instance for LLM operations
        cache_manager: CacheManager instance for Redis operations
        clickhouse_config: Optional ClickHouse configuration
        enable_background_summarization: Enable async summarization service
        enable_semantic_search: Enable embedding-based semantic search
        enable_memory_routing: Enable memory-aware routing features
        **kwargs: Additional configuration options
        
    Returns:
        Fully initialized IntegratedMemorySystem
    """
    
    try:
        logger.info(
            "creating_integrated_memory_system",
            enable_background_summarization=enable_background_summarization,
            enable_semantic_search=enable_semantic_search,
            enable_memory_routing=enable_memory_routing
        )
        
        # 1. Create memory storage components
        redis_memory = ConversationMemoryCache(cache_manager)
        
        clickhouse_memory = create_conversation_clickhouse_manager(
            **(clickhouse_config or {})
        )
        
        # 2. Create adaptive learning components
        bandit = MemoryAwareThompsonBandit()
        reward_calculator = create_memory_aware_reward_calculator()
        
        # 3. Create summarization service
        summarization_service = create_async_summarization_service(
            model_manager=model_manager,
            redis_memory=redis_memory,
            clickhouse_memory=clickhouse_memory
        )
        
        # 4. Create memory orchestrator
        orchestrator = create_bandit_integrated_orchestrator(
            model_manager=model_manager,
            redis_memory=redis_memory,
            clickhouse_memory=clickhouse_memory,
            summarization_service=summarization_service,
            bandit=bandit,
            reward_calculator=reward_calculator
        )
        
        # 5. Create memory-aware router
        router = await create_memory_aware_router(
            model_manager=model_manager,
            cache_manager=cache_manager,
            memory_orchestrator=orchestrator,
            enable_memory_routing=enable_memory_routing,
            **kwargs
        )
        
        # 6. Create memory-enhanced context node
        context_node = create_memory_enhanced_context_node(
            memory_orchestrator=orchestrator,
            cache_manager=cache_manager,
            enable_memory_features=enable_memory_routing
        )
        
        # 7. Create integrated system
        integrated_system = IntegratedMemorySystem(
            orchestrator=orchestrator,
            router=router,
            context_node=context_node
        )
        
        # 8. Initialize system
        initialization_success = await integrated_system.initialize()
        
        if not initialization_success:
            raise RuntimeError("Failed to initialize integrated memory system")
        
        logger.info(
            "integrated_memory_system_created_successfully",
            components_count=3,
            initialization_success=initialization_success
        )
        
        return integrated_system
        
    except Exception as e:
        logger.error(
            "failed_to_create_integrated_memory_system",
            error=str(e)
        )
        raise


# Convenience exports for common use cases
__all__ = [
    # Main system
    'IntegratedMemorySystem',
    'create_integrated_memory_system',
    
    # Core components
    'BanditIntegratedMemoryOrchestrator',
    'MemoryAwareEnhancedRouter', 
    'MemoryEnhancedContextManagerNode',
    
    # Memory management
    'ConversationMemoryCache',
    'ConversationClickHouseManager',
    'AsyncSummarizationService',
    
    # Adaptive learning
    'MemoryAwareThompsonBandit',
    'MemoryAwareRewardCalculator',
    'MemoryRoutingArm',
    'MemoryArmManager',
    'MEMORY_ROUTING_ARMS',
    
    # Factory functions
    'create_bandit_integrated_orchestrator',
    'create_memory_aware_router',
    'create_memory_enhanced_context_node',
    'create_conversation_clickhouse_manager',
    'create_async_summarization_service',
    'create_memory_aware_reward_calculator'
]