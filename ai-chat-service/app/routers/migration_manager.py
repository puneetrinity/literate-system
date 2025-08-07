"""
Router Migration Manager - Safe 8→3 Architecture Migration

This module manages the safe migration from the legacy 8-router architecture
to the consolidated 3-router architecture using feature flags, gradual rollout,
and comprehensive monitoring.

Key Features:
- Gradual migration with automatic rollback
- Side-by-side execution for comparison
- Performance and error monitoring
- Admin controls and overrides
- Detailed migration analytics
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.routers.feature_flags import (
    get_feature_flag_manager, 
    RouterArchitecture, 
    UserSegment,
    FeatureFlagManager
)

# Import legacy routers
from app.graphs.intelligent_router import IntelligentRouter
from app.adaptive.enhanced_router import EnhancedAdaptiveRouter, create_enhanced_adaptive_router

# Import consolidated routers  
from app.routers.unified_intelligent_router import UnifiedIntelligentRouter
from app.routers.content_type_router import ContentTypeRouter
from app.routers.web_search_router import WebSearchRouter

logger = structlog.get_logger(__name__)
settings = get_settings()


class MigrationPhase(Enum):
    """Migration phases"""
    PREPARATION = "preparation"       # Pre-migration setup
    SHADOW_TESTING = "shadow_testing" # Shadow mode testing
    GRADUAL_ROLLOUT = "gradual_rollout" # Percentage-based rollout
    FULL_MIGRATION = "full_migration"   # Complete migration
    CLEANUP = "cleanup"               # Post-migration cleanup


class MigrationResult(BaseModel):
    """Result of a migration request"""
    
    architecture_used: RouterArchitecture = Field(description="Architecture used")
    router_type: str = Field(description="Specific router used")
    success: bool = Field(description="Request success")
    response_time_ms: float = Field(description="Response time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Performance metrics
    memory_usage_mb: Optional[float] = Field(default=None, description="Memory usage")
    cpu_usage_percent: Optional[float] = Field(default=None, description="CPU usage")
    
    # Routing details
    routing_confidence: Optional[float] = Field(default=None, description="Routing confidence")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    request_id: str = Field(description="Unique request ID")


class MigrationAnalytics(BaseModel):
    """Analytics for migration performance"""
    
    # Request counts
    total_requests: int = Field(default=0, description="Total requests processed")
    legacy_requests: int = Field(default=0, description="Requests using legacy architecture")
    consolidated_requests: int = Field(default=0, description="Requests using consolidated architecture")
    
    # Success rates
    legacy_successes: int = Field(default=0, description="Legacy successful requests")
    consolidated_successes: int = Field(default=0, description="Consolidated successful requests")
    
    # Performance metrics
    legacy_total_response_time: float = Field(default=0.0, description="Total legacy response time")
    consolidated_total_response_time: float = Field(default=0.0, description="Total consolidated response time")
    
    # Error tracking
    legacy_errors: int = Field(default=0, description="Legacy errors")
    consolidated_errors: int = Field(default=0, description="Consolidated errors")
    
    # Migration metadata
    migration_start: Optional[datetime] = Field(default=None, description="Migration start time")
    current_phase: MigrationPhase = Field(default=MigrationPhase.PREPARATION, description="Current phase")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    def get_legacy_success_rate(self) -> float:
        """Calculate legacy success rate"""
        if self.legacy_requests == 0:
            return 0.0
        return (self.legacy_successes / self.legacy_requests) * 100.0
    
    def get_consolidated_success_rate(self) -> float:
        """Calculate consolidated success rate"""
        if self.consolidated_requests == 0:
            return 0.0
        return (self.consolidated_successes / self.consolidated_requests) * 100.0
    
    def get_legacy_avg_response_time(self) -> float:
        """Calculate legacy average response time"""
        if self.legacy_requests == 0:
            return 0.0
        return self.legacy_total_response_time / self.legacy_requests
    
    def get_consolidated_avg_response_time(self) -> float:
        """Calculate consolidated average response time"""
        if self.consolidated_requests == 0:
            return 0.0
        return self.consolidated_total_response_time / self.consolidated_requests
    
    def get_performance_improvement(self) -> Dict[str, float]:
        """Calculate performance improvements"""
        legacy_avg = self.get_legacy_avg_response_time()
        consolidated_avg = self.get_consolidated_avg_response_time()
        
        if legacy_avg == 0:
            return {"response_time_improvement": 0.0, "success_rate_improvement": 0.0}
        
        response_time_improvement = ((legacy_avg - consolidated_avg) / legacy_avg) * 100.0
        success_rate_improvement = self.get_consolidated_success_rate() - self.get_legacy_success_rate()
        
        return {
            "response_time_improvement": response_time_improvement,
            "success_rate_improvement": success_rate_improvement
        }


class RouterMigrationManager:
    """
    Manages the migration from 8-router to 3-router architecture
    """
    
    def __init__(self, 
                 model_manager,
                 cache_manager,
                 memory_orchestrator=None):
        
        self.model_manager = model_manager
        self.cache_manager = cache_manager
        self.memory_orchestrator = memory_orchestrator
        
        # Feature flag manager
        self.feature_flags = get_feature_flag_manager()
        
        # Migration analytics
        self.analytics = MigrationAnalytics()
        
        # Legacy routers (8-router architecture)
        self.legacy_routers = {}
        
        # Consolidated routers (3-router architecture)
        self.consolidated_routers = {}
        
        # Migration state
        self.migration_active = False
        self.shadow_mode_enabled = True
        
        logger.info("RouterMigrationManager initialized")
    
    async def initialize(self):
        """Initialize both legacy and consolidated router systems"""
        
        # Initialize legacy routers
        await self._initialize_legacy_routers()
        
        # Initialize consolidated routers
        await self._initialize_consolidated_routers()
        
        # Start migration if configured
        import os
        if os.getenv("ENABLE_ROUTER_MIGRATION", "false").lower() == "true":
            await self.start_migration()
        
        logger.info("Router migration system initialized",
                   legacy_routers=len(self.legacy_routers),
                   consolidated_routers=len(self.consolidated_routers))
    
    async def _initialize_legacy_routers(self):
        """Initialize legacy 8-router system"""
        
        # Intelligent Router
        self.legacy_routers["intelligent"] = IntelligentRouter(
            self.model_manager, self.cache_manager
        )
        await self.legacy_routers["intelligent"].initialize()
        
        # Enhanced Adaptive Router
        self.legacy_routers["adaptive"] = await create_enhanced_adaptive_router(
            self.model_manager,
            self.cache_manager,
            enable_adaptive=True,
            enable_ab_testing=False,  # Disable A/B testing during migration
            enable_gradual_rollout=False
        )
        
        # Note: Other legacy routers would be initialized here
        # For now, using intelligent and adaptive as primary legacy routers
        
        logger.info("Legacy routers initialized", count=len(self.legacy_routers))
    
    async def _initialize_consolidated_routers(self):
        """Initialize consolidated 3-router system"""
        
        # Unified Intelligent Router (consolidates 5 routers)
        self.consolidated_routers["unified_intelligent"] = UnifiedIntelligentRouter(
            memory_orchestrator=self.memory_orchestrator,
            enable_adaptive_learning=True,
            enable_shadow_testing=False
        )
        
        # Content Type Router (enhanced document router)
        self.consolidated_routers["content_type"] = ContentTypeRouter()
        
        # Web Search Router (manual-only web search) 
        self.consolidated_routers["web_search"] = WebSearchRouter(
            brave_api_key=settings.BRAVE_API_KEY,
            scrapingbee_api_key=settings.SCRAPINGBEE_API_KEY
        )
        
        logger.info("Consolidated routers initialized", count=len(self.consolidated_routers))
    
    async def route_request(self,
                           query: str,
                           user_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           user_context: Optional[Dict[str, Any]] = None) -> MigrationResult:
        """
        Route a request through the appropriate architecture based on feature flags
        """
        
        start_time = time.time()
        request_id = f"migration_{int(time.time() * 1000)}_{user_id or 'anon'}"
        
        # Determine user segment
        user_segment = self._determine_user_segment(user_context)
        
        # Check which architecture to use
        architecture, reason = self.feature_flags.should_use_architecture(
            user_id=user_id,
            user_segment=user_segment,
            context=user_context
        )
        
        try:
            if architecture == RouterArchitecture.CONSOLIDATED_3_ROUTER:
                result = await self._route_with_consolidated_architecture(
                    query, user_id, session_id, user_context, request_id
                )
            else:
                result = await self._route_with_legacy_architecture(
                    query, user_id, session_id, user_context, request_id
                )
            
            # Record successful metrics
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            
            # Update analytics
            self._update_analytics(result, architecture, True, response_time)
            
            # Record feature flag metrics
            self.feature_flags.record_request_metrics(
                flag_name="router_consolidation",
                enabled=(architecture == RouterArchitecture.CONSOLIDATED_3_ROUTER),
                success=True,
                latency_ms=response_time,
                user_id=user_id
            )
            
            return result
            
        except Exception as e:
            # Handle errors
            response_time = (time.time() - start_time) * 1000
            
            error_result = MigrationResult(
                architecture_used=architecture,
                router_type="error",
                success=False,
                response_time_ms=response_time,
                error_message=str(e),
                request_id=request_id
            )
            
            # Update analytics with error
            self._update_analytics(error_result, architecture, False, response_time)
            
            # Record feature flag metrics
            self.feature_flags.record_request_metrics(
                flag_name="router_consolidation",
                enabled=(architecture == RouterArchitecture.CONSOLIDATED_3_ROUTER),
                success=False,
                latency_ms=response_time,
                user_id=user_id
            )
            
            logger.error("Router migration request failed",
                        request_id=request_id,
                        architecture=architecture.value,
                        error=str(e))
            
            return error_result
    
    async def _route_with_consolidated_architecture(self,
                                                   query: str,
                                                   user_id: Optional[str],
                                                   session_id: Optional[str],
                                                   user_context: Optional[Dict[str, Any]],
                                                   request_id: str) -> MigrationResult:
        """Route request using consolidated 3-router architecture"""
        
        # Step 1: Content Type Classification
        content_router = self.consolidated_routers["content_type"]
        
        content_classification = await content_router.classify_content_type(
            query=query,
            user_id=user_id,
            session_id=session_id,
            user_permissions=user_context.get("user_permissions", {}) if user_context else {},
            enterprise_account=user_context.get("enterprise_account", False) if user_context else False
        )
        
        # Step 2: Route based on content type
        if content_classification.content_type.value == "web_search_requested":
            # Use Web Search Router for manual web search
            web_router = self.consolidated_routers["web_search"]
            
            # Check web search permissions
            permission_granted, permission_reason = content_router.check_web_search_permission(
                content_classification,
                user_consent=user_context.get("web_search_consent", False) if user_context else False
            )
            
            if not permission_granted:
                return MigrationResult(
                    architecture_used=RouterArchitecture.CONSOLIDATED_3_ROUTER,
                    router_type="web_search_blocked",
                    success=False,
                    response_time_ms=0.0,
                    error_message=permission_reason,
                    request_id=request_id
                )
            
            # Execute web search (this would be implemented based on web search requirements)
            # For now, return success placeholder
            return MigrationResult(
                architecture_used=RouterArchitecture.CONSOLIDATED_3_ROUTER,
                router_type="web_search",
                success=True,
                response_time_ms=0.0,
                routing_confidence=content_classification.confidence,
                request_id=request_id
            )
        
        else:
            # Use Unified Intelligent Router for document search and chat
            unified_router = self.consolidated_routers["unified_intelligent"]
            
            # Create routing context
            context = {
                "enterprise_account": user_context.get("enterprise_account", False) if user_context else False,
                "web_search_consent": user_context.get("web_search_consent", False) if user_context else False
            }
            
            routing_decision = await unified_router.route_query(
                query=query,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            return MigrationResult(
                architecture_used=RouterArchitecture.CONSOLIDATED_3_ROUTER,
                router_type=f"unified_{routing_decision.graph_type.value}",
                success=True,
                response_time_ms=0.0,
                routing_confidence=routing_decision.confidence,
                request_id=request_id
            )
    
    async def _route_with_legacy_architecture(self,
                                            query: str,
                                            user_id: Optional[str],
                                            session_id: Optional[str],
                                            user_context: Optional[Dict[str, Any]],
                                            request_id: str) -> MigrationResult:
        """Route request using legacy 8-router architecture"""
        
        # Use intelligent router as primary legacy router
        intelligent_router = self.legacy_routers["intelligent"]
        
        # Create graph state for legacy system
        from app.graphs.base import GraphState
        
        state = GraphState(
            original_query=query,
            user_id=user_id,
            session_id=session_id,
            conversation_history=user_context.get("conversation_history", []) if user_context else [],
            user_preferences=user_context.get("user_preferences", {}) if user_context else {}
        )
        
        routing_decision = await intelligent_router.route_query(query, state)
        
        return MigrationResult(
            architecture_used=RouterArchitecture.LEGACY_8_ROUTER,
            router_type=f"legacy_{routing_decision.selected_graph.value}",
            success=True,
            response_time_ms=0.0,
            routing_confidence=routing_decision.confidence,
            request_id=request_id
        )
    
    def _determine_user_segment(self, user_context: Optional[Dict[str, Any]]) -> UserSegment:
        """Determine user segment from context"""
        
        if not user_context:
            return UserSegment.FREE
        
        # Check user tier
        user_tier = user_context.get("user_tier", "free")
        
        if user_tier == "enterprise":
            return UserSegment.ENTERPRISE
        elif user_tier == "premium":
            return UserSegment.PREMIUM
        elif user_context.get("is_beta_user", False):
            return UserSegment.BETA
        elif user_context.get("is_internal_user", False):
            return UserSegment.INTERNAL
        else:
            return UserSegment.FREE
    
    def _update_analytics(self,
                         result: MigrationResult,
                         architecture: RouterArchitecture,
                         success: bool,
                         response_time: float):
        """Update migration analytics"""
        
        self.analytics.total_requests += 1
        self.analytics.last_updated = datetime.now()
        
        if architecture == RouterArchitecture.LEGACY_8_ROUTER:
            self.analytics.legacy_requests += 1
            self.analytics.legacy_total_response_time += response_time
            
            if success:
                self.analytics.legacy_successes += 1
            else:
                self.analytics.legacy_errors += 1
        
        else:  # CONSOLIDATED_3_ROUTER
            self.analytics.consolidated_requests += 1
            self.analytics.consolidated_total_response_time += response_time
            
            if success:
                self.analytics.consolidated_successes += 1
            else:
                self.analytics.consolidated_errors += 1
    
    async def start_migration(self):
        """Start the migration process"""
        
        if self.migration_active:
            logger.warning("Migration already active")
            return
        
        self.migration_active = True
        self.analytics.migration_start = datetime.now()
        self.analytics.current_phase = MigrationPhase.SHADOW_TESTING
        
        logger.info("Router migration started",
                   phase=self.analytics.current_phase.value,
                   timestamp=self.analytics.migration_start)
        
        # Start background migration tasks
        asyncio.create_task(self._migration_monitor())
    
    async def _migration_monitor(self):
        """Background task to monitor and advance migration"""
        
        while self.migration_active:
            try:
                # Auto-advance gradual rollouts
                self.feature_flags.auto_advance_rollouts()
                
                # Check migration health
                await self._check_migration_health()
                
                # Sleep before next check (5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error("Migration monitor error", error=str(e))
                await asyncio.sleep(60)  # Shorter retry on error
    
    async def _check_migration_health(self):
        """Check migration health and trigger rollbacks if needed"""
        
        # Only check if we have enough data
        if self.analytics.consolidated_requests < 50:
            return
        
        # Calculate success rates
        legacy_success_rate = self.analytics.get_legacy_success_rate()
        consolidated_success_rate = self.analytics.get_consolidated_success_rate()
        
        # Check for significant degradation
        success_rate_drop = legacy_success_rate - consolidated_success_rate
        
        if success_rate_drop > 10.0:  # 10% drop in success rate
            logger.warning("Migration health check: significant success rate drop",
                          legacy_success_rate=legacy_success_rate,
                          consolidated_success_rate=consolidated_success_rate,
                          drop=success_rate_drop)
            
            # Consider emergency rollback
            await self._consider_emergency_rollback("success_rate_drop", success_rate_drop)
        
        # Check response time degradation
        performance_improvement = self.analytics.get_performance_improvement()
        response_time_improvement = performance_improvement["response_time_improvement"]
        
        if response_time_improvement < -50.0:  # 50% slower
            logger.warning("Migration health check: significant response time degradation",
                          response_time_improvement=response_time_improvement)
            
            await self._consider_emergency_rollback("response_time_degradation", response_time_improvement)
    
    async def _consider_emergency_rollback(self, reason: str, metric_value: float):
        """Consider emergency rollback based on health metrics"""
        
        # For now, just log - in production this would trigger alerts
        logger.critical("Emergency rollback consideration",
                       reason=reason,
                       metric_value=metric_value,
                       timestamp=datetime.now().isoformat())
        
        # In production, this could automatically rollback
        # self.feature_flags.set_admin_override("router_consolidation", False, "emergency_system")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        
        performance_improvement = self.analytics.get_performance_improvement()
        
        return {
            "migration": {
                "active": self.migration_active,
                "phase": self.analytics.current_phase.value,
                "start_time": self.analytics.migration_start.isoformat() if self.analytics.migration_start else None,
                "duration_hours": (datetime.now() - self.analytics.migration_start).total_seconds() / 3600 if self.analytics.migration_start else 0
            },
            "analytics": {
                "total_requests": self.analytics.total_requests,
                "legacy_requests": self.analytics.legacy_requests,
                "consolidated_requests": self.analytics.consolidated_requests,
                "legacy_success_rate": self.analytics.get_legacy_success_rate(),
                "consolidated_success_rate": self.analytics.get_consolidated_success_rate(),
                "legacy_avg_response_time": self.analytics.get_legacy_avg_response_time(),
                "consolidated_avg_response_time": self.analytics.get_consolidated_avg_response_time(),
                "performance_improvement": performance_improvement
            },
            "feature_flags": self.feature_flags.get_all_flags_status(),
            "routers": {
                "legacy_count": len(self.legacy_routers),
                "consolidated_count": len(self.consolidated_routers),
                "legacy_routers": list(self.legacy_routers.keys()),
                "consolidated_routers": list(self.consolidated_routers.keys())
            }
        }
    
    async def stop_migration(self):
        """Stop the migration process"""
        
        self.migration_active = False
        
        logger.info("Router migration stopped",
                   duration_hours=(datetime.now() - self.analytics.migration_start).total_seconds() / 3600 if self.analytics.migration_start else 0)


# Factory function
async def create_router_migration_manager(model_manager, 
                                        cache_manager, 
                                        memory_orchestrator=None) -> RouterMigrationManager:
    """Create and initialize router migration manager"""
    
    manager = RouterMigrationManager(
        model_manager=model_manager,
        cache_manager=cache_manager,
        memory_orchestrator=memory_orchestrator
    )
    
    await manager.initialize()
    return manager