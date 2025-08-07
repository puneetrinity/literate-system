"""
Memory System Initialization for Production Deployment

This module provides factory functions to initialize the memory system components
with proper configuration for production use.
"""

import os
from typing import Optional

import structlog
from app.core.config import get_settings
from app.models.manager import ModelManager
from app.cache.redis_client import CacheManager
from app.memory.bandit_orchestrator import BanditIntegratedMemoryOrchestrator
from app.memory.redis_memory import ConversationMemoryCache
from app.memory.clickhouse_memory import ConversationClickHouseManager
from app.memory.summarization_service import AsyncSummarizationService
from app.memory.contextual_bandit import MemoryAwareThompsonBandit
from app.memory.reward_calculator import MemoryAwareRewardCalculator

logger = structlog.get_logger(__name__)
settings = get_settings()


async def create_memory_orchestrator(
    model_manager: ModelManager,
    cache_manager: CacheManager,
    enable_clickhouse: bool = False
) -> Optional[BanditIntegratedMemoryOrchestrator]:
    """
    Create and initialize the memory orchestrator with all components
    
    Args:
        model_manager: Model manager for summarization
        cache_manager: Cache manager (provides Redis connection)
        enable_clickhouse: Whether to enable ClickHouse for cold storage
        
    Returns:
        Initialized BanditIntegratedMemoryOrchestrator or None if disabled
    """
    
    # Check if memory system is enabled
    if not os.getenv("ENABLE_MEMORY_SYSTEM", "false").lower() == "true":
        logger.info("Memory system disabled by configuration")
        return None
    
    try:
        logger.info("Initializing memory system components...")
        
        # Initialize Thompson Sampling bandit
        memory_bandit = MemoryAwareThompsonBandit(
            min_exploration_rate=0.05
        )
        
        # Initialize reward calculator
        reward_calculator = MemoryAwareRewardCalculator()
        
        # Initialize Redis-based memory cache
        memory_cache = ConversationMemoryCache(
            redis_client=cache_manager.redis,
            ttl_seconds=3600,  # 1 hour TTL for hot memory
            max_messages_per_session=100,
            max_context_tokens=2000
        )
        
        # Initialize ClickHouse manager if enabled
        clickhouse_manager = None
        if enable_clickhouse:
            clickhouse_host = os.getenv("CLICKHOUSE_HOST", "localhost")
            clickhouse_port = int(os.getenv("CLICKHOUSE_PORT", "9000"))
            clickhouse_database = os.getenv("CLICKHOUSE_DATABASE", "ai_chat_memory")
            
            if clickhouse_host and clickhouse_host != "localhost":
                clickhouse_manager = ConversationClickHouseManager(
                    host=clickhouse_host,
                    port=clickhouse_port,
                    database=clickhouse_database
                )
                await clickhouse_manager.initialize_tables()
                logger.info("ClickHouse memory storage initialized",
                           host=clickhouse_host,
                           database=clickhouse_database)
            else:
                logger.warning("ClickHouse configuration not found, using Redis only")
        
        # Initialize summarization service
        summarization_service = AsyncSummarizationService(
            model_manager=model_manager,
            cache_client=cache_manager.redis,
            max_concurrent_jobs=3,
            batch_size=5
        )
        
        # Create the orchestrator
        orchestrator = BanditIntegratedMemoryOrchestrator(
            model_manager=model_manager,
            memory_bandit=memory_bandit,
            reward_calculator=reward_calculator,
            memory_cache=memory_cache,
            clickhouse_manager=clickhouse_manager,
            summarization_service=summarization_service
        )
        
        # Initialize the orchestrator
        await orchestrator.initialize()
        
        logger.info("Memory orchestrator initialized successfully",
                   redis_enabled=True,
                   clickhouse_enabled=clickhouse_manager is not None,
                   bandit_arms=len(memory_bandit.arms))
        
        return orchestrator
        
    except Exception as e:
        logger.error("Failed to initialize memory orchestrator", error=str(e))
        return None


def get_memory_config() -> dict:
    """Get memory system configuration from environment"""
    
    return {
        "enabled": os.getenv("ENABLE_MEMORY_SYSTEM", "false").lower() == "true",
        "redis": {
            "ttl_seconds": int(os.getenv("MEMORY_REDIS_TTL", "3600")),
            "max_messages": int(os.getenv("MEMORY_MAX_MESSAGES", "100")),
            "max_tokens": int(os.getenv("MEMORY_MAX_TOKENS", "2000"))
        },
        "clickhouse": {
            "enabled": os.getenv("ENABLE_CLICKHOUSE", "false").lower() == "true",
            "host": os.getenv("CLICKHOUSE_HOST", "localhost"),
            "port": int(os.getenv("CLICKHOUSE_PORT", "9000")),
            "database": os.getenv("CLICKHOUSE_DATABASE", "ai_chat_memory")
        },
        "bandit": {
            "exploration_rate": float(os.getenv("MEMORY_EXPLORATION_RATE", "0.05")),
            "update_interval": int(os.getenv("MEMORY_UPDATE_INTERVAL", "10"))
        },
        "summarization": {
            "max_concurrent": int(os.getenv("MEMORY_SUMMARIZATION_CONCURRENT", "3")),
            "batch_size": int(os.getenv("MEMORY_SUMMARIZATION_BATCH", "5"))
        }
    }