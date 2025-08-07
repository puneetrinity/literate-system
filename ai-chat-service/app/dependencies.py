"""
Dependency providers for FastAPI DI: ModelManager, CacheManager, and SearchGraph singletons.
"""

from typing import Any, Optional

from app.cache.redis_client import CacheManager
from app.core.config import get_settings
from app.models.manager import ModelManager

# Global references to initialized instances
_initialized_model_manager: Optional[ModelManager] = None
_initialized_cache_manager: Optional[CacheManager] = None
_initialized_search_graph: Optional[Any] = None  # SearchGraph import will be dynamic
_initialized_audit_manager: Optional[Any] = None  # WebSearchAuditManager import will be dynamic


def set_initialized_model_manager(model_manager: ModelManager) -> None:
    """Set the initialized ModelManager instance for dependency injection."""
    global _initialized_model_manager
    _initialized_model_manager = model_manager


def set_initialized_cache_manager(cache_manager: CacheManager) -> None:
    """Set the initialized CacheManager instance for dependency injection."""
    global _initialized_cache_manager
    _initialized_cache_manager = cache_manager


def set_initialized_search_graph(search_graph: Any) -> None:
    """Set the initialized SearchGraph instance for dependency injection."""
    global _initialized_search_graph
    _initialized_search_graph = search_graph


def set_initialized_audit_manager(audit_manager: Any) -> None:
    """Set the initialized WebSearchAuditManager instance for dependency injection."""
    global _initialized_audit_manager
    _initialized_audit_manager = audit_manager


def get_model_manager(request: Any = None) -> ModelManager:
    """Get the ModelManager instance, preferring the initialized one."""
    global _initialized_model_manager
    if _initialized_model_manager is not None:
        return _initialized_model_manager

    # Fallback: create new instance (for startup or testing)
    import asyncio

    from app.core.logging import get_logger

    logger = get_logger("dependencies")
    logger.warning("⚠️ Using fallback ModelManager - singleton not set!")

    settings = get_settings()
    # Use consistent Ollama host configuration
    ollama_host = settings.ollama_host

    fallback_manager = ModelManager(ollama_host=ollama_host)

    # Try to initialize synchronously if possible
    try:
        # Check if we're in an async context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule initialization for later
            asyncio.create_task(fallback_manager.initialize())
        else:
            # Run initialization synchronously
            asyncio.run(fallback_manager.initialize())
    except Exception as e:
        logger.warning(f"Fallback ModelManager initialization failed: {e}")

    return fallback_manager


def get_cache_manager() -> CacheManager:
    """Get the CacheManager instance, preferring the initialized one."""
    global _initialized_cache_manager
    if _initialized_cache_manager is not None:
        return _initialized_cache_manager

    # Fallback: create new instance (for startup or testing)
    import asyncio

    from app.core.logging import get_logger

    logger = get_logger("dependencies")
    logger.warning("⚠️ Using fallback CacheManager - singleton not set!")

    settings = get_settings()
    fallback_cache = CacheManager(
        redis_url=settings.redis_url, max_connections=settings.redis_max_connections
    )

    # Try to initialize if possible
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(fallback_cache.initialize())
        else:
            asyncio.run(fallback_cache.initialize())
    except Exception as e:
        logger.warning(f"Fallback CacheManager initialization failed: {e}")

    return fallback_cache


def get_search_graph():
    """Get the SearchGraph instance, preferring the initialized one."""
    global _initialized_search_graph
    if _initialized_search_graph is not None:
        return _initialized_search_graph

    # Fallback: create new instance (for startup or testing)
    import asyncio

    from app.core.logging import get_logger

    logger = get_logger("dependencies")
    logger.warning("⚠️ Using fallback SearchGraph - singleton not set!")

    try:
        # Dynamic import to avoid circular dependencies
        from app.graphs.search_graph import create_search_graph
        
        model_manager = get_model_manager()
        cache_manager = get_cache_manager()
        
        # Try to create and initialize SearchGraph
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule initialization for later
                fallback_search_graph = asyncio.create_task(
                    create_search_graph(model_manager, cache_manager)
                )
                # Return a placeholder that will resolve later
                return None
            else:
                # Run initialization synchronously
                fallback_search_graph = asyncio.run(
                    create_search_graph(model_manager, cache_manager)
                )
                return fallback_search_graph
        except Exception as e:
            logger.warning(f"Fallback SearchGraph initialization failed: {e}")
            return None
            
    except ImportError as e:
        logger.warning(f"SearchGraph not available: {e}")
        return None


def get_audit_manager():
    """Get the WebSearchAuditManager instance, preferring the initialized one."""
    global _initialized_audit_manager
    if _initialized_audit_manager is not None:
        return _initialized_audit_manager
    
    # Fallback: create new instance (for startup or testing)
    import asyncio
    
    from app.core.logging import get_logger
    
    logger = get_logger("dependencies")
    logger.warning("⚠️ Using fallback WebSearchAuditManager - singleton not set!")
    
    try:
        # Dynamic import to avoid circular dependencies
        from app.services.web_search_audit_manager import WebSearchAuditManager
        
        cache_manager = get_cache_manager()
        fallback_audit_manager = WebSearchAuditManager(cache_manager)
        
        logger.info("✅ Fallback WebSearchAuditManager created successfully")
        return fallback_audit_manager
        
    except ImportError as e:
        logger.error(f"WebSearchAuditManager not available: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create fallback WebSearchAuditManager: {e}")
        raise
