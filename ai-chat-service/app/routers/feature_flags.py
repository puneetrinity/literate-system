"""
Feature Flags System for Router Consolidation

This module provides feature flags to enable gradual migration from the 8-router
architecture to the consolidated 3-router architecture, ensuring safe rollout
and easy rollback capabilities.

Key Features:
- User-based gradual rollout (percentage-based)
- Admin override controls
- A/B testing support
- Safety circuit breakers
- Real-time monitoring and metrics
- Rollback capabilities
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import random

import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RouterArchitecture(Enum):
    """Router architecture versions"""
    LEGACY_8_ROUTER = "legacy_8_router"       # Original 8-router system
    CONSOLIDATED_3_ROUTER = "consolidated_3_router"  # New 3-router system


class FeatureFlagState(Enum):
    """Feature flag states"""
    DISABLED = "disabled"           # Feature completely disabled
    SHADOW = "shadow"              # Feature runs in shadow mode (no impact)
    GRADUAL_ROLLOUT = "gradual_rollout"  # Gradual percentage-based rollout
    ENABLED = "enabled"            # Feature fully enabled
    EMERGENCY_DISABLED = "emergency_disabled"  # Emergency circuit breaker


class UserSegment(Enum):
    """User segments for targeted rollouts"""
    INTERNAL = "internal"          # Internal users/developers
    BETA = "beta"                 # Beta testers
    PREMIUM = "premium"           # Premium users
    FREE = "free"                 # Free tier users
    ENTERPRISE = "enterprise"     # Enterprise customers


class FeatureFlag(BaseModel):
    """Feature flag configuration"""
    
    flag_name: str = Field(description="Feature flag name")
    state: FeatureFlagState = Field(description="Current flag state")
    rollout_percentage: float = Field(default=0.0, description="Rollout percentage (0-100)")
    target_segments: List[UserSegment] = Field(default_factory=list, description="Target user segments")
    
    # Rollout configuration
    max_rollout_percentage: float = Field(default=100.0, description="Maximum rollout percentage")
    rollout_increment: float = Field(default=5.0, description="Percentage increment per step")
    rollout_interval_minutes: int = Field(default=60, description="Minutes between rollout steps")
    
    # Safety configuration
    error_threshold: float = Field(default=5.0, description="Error rate threshold for circuit breaker")
    latency_threshold_ms: float = Field(default=10000.0, description="Latency threshold for circuit breaker")
    min_requests_for_evaluation: int = Field(default=100, description="Minimum requests before evaluation")
    
    # A/B testing
    ab_test_enabled: bool = Field(default=False, description="Enable A/B testing")
    control_percentage: float = Field(default=50.0, description="Control group percentage")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    created_by: str = Field(default="system", description="Creator")
    description: str = Field(default="", description="Flag description")
    
    # Override controls
    admin_override: Optional[bool] = Field(default=None, description="Admin override (forces on/off)")
    emergency_disabled: bool = Field(default=False, description="Emergency disable flag")


class FeatureFlagMetrics(BaseModel):
    """Metrics for feature flag evaluation"""
    
    flag_name: str = Field(description="Feature flag name")
    
    # Request metrics
    total_requests: int = Field(default=0, description="Total requests")
    enabled_requests: int = Field(default=0, description="Requests with feature enabled")
    disabled_requests: int = Field(default=0, description="Requests with feature disabled")
    
    # Success metrics
    enabled_successes: int = Field(default=0, description="Successful enabled requests")
    disabled_successes: int = Field(default=0, description="Successful disabled requests")
    
    # Error metrics
    enabled_errors: int = Field(default=0, description="Errors with feature enabled")
    disabled_errors: int = Field(default=0, description="Errors with feature disabled")
    
    # Performance metrics
    enabled_total_latency_ms: float = Field(default=0.0, description="Total latency for enabled requests")
    disabled_total_latency_ms: float = Field(default=0.0, description="Total latency for disabled requests")
    
    # Time tracking
    last_updated: datetime = Field(default_factory=datetime.now, description="Last metrics update")
    
    def get_enabled_error_rate(self) -> float:
        """Calculate error rate for enabled requests"""
        if self.enabled_requests == 0:
            return 0.0
        return (self.enabled_errors / self.enabled_requests) * 100.0
    
    def get_disabled_error_rate(self) -> float:
        """Calculate error rate for disabled requests"""
        if self.disabled_requests == 0:
            return 0.0
        return (self.disabled_errors / self.disabled_requests) * 100.0
    
    def get_enabled_avg_latency_ms(self) -> float:
        """Calculate average latency for enabled requests"""
        if self.enabled_requests == 0:
            return 0.0
        return self.enabled_total_latency_ms / self.enabled_requests
    
    def get_disabled_avg_latency_ms(self) -> float:
        """Calculate average latency for disabled requests"""
        if self.disabled_requests == 0:
            return 0.0
        return self.disabled_total_latency_ms / self.disabled_requests


class FeatureFlagManager:
    """
    Feature flag manager for router consolidation
    """
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.metrics: Dict[str, FeatureFlagMetrics] = {}
        self.user_overrides: Dict[str, Dict[str, bool]] = {}  # user_id -> flag_name -> enabled
        
        # Initialize router consolidation flags
        self._init_router_consolidation_flags()
        
        logger.info("FeatureFlagManager initialized with router consolidation flags")
    
    def _init_router_consolidation_flags(self):
        """Initialize feature flags for router consolidation"""
        
        # Main consolidation flag
        self.flags["router_consolidation"] = FeatureFlag(
            flag_name="router_consolidation",
            state=FeatureFlagState.SHADOW,
            rollout_percentage=0.0,
            target_segments=[UserSegment.INTERNAL, UserSegment.BETA],
            max_rollout_percentage=100.0,
            rollout_increment=10.0,
            rollout_interval_minutes=30,
            error_threshold=2.0,
            latency_threshold_ms=5000.0,
            min_requests_for_evaluation=50,
            ab_test_enabled=True,
            control_percentage=50.0,
            description="Main flag for router consolidation (8→3 architecture)"
        )
        
        # Unified Intelligent Router flag
        self.flags["unified_intelligent_router"] = FeatureFlag(
            flag_name="unified_intelligent_router",
            state=FeatureFlagState.SHADOW,
            rollout_percentage=0.0,
            target_segments=[UserSegment.INTERNAL],
            max_rollout_percentage=100.0,
            rollout_increment=5.0,
            rollout_interval_minutes=60,
            error_threshold=1.0,
            latency_threshold_ms=3000.0,
            min_requests_for_evaluation=100,
            description="Unified router replacing 5 legacy routers"
        )
        
        # Content Type Router flag
        self.flags["content_type_router"] = FeatureFlag(
            flag_name="content_type_router",
            state=FeatureFlagState.SHADOW,
            rollout_percentage=0.0,
            target_segments=[UserSegment.INTERNAL, UserSegment.BETA],
            max_rollout_percentage=100.0,
            rollout_increment=10.0,
            rollout_interval_minutes=45,
            error_threshold=1.5,
            latency_threshold_ms=2000.0,
            min_requests_for_evaluation=75,
            description="Enhanced document router with enterprise controls"
        )
        
        # Web Search Router flag
        self.flags["manual_web_search"] = FeatureFlag(
            flag_name="manual_web_search",
            state=FeatureFlagState.GRADUAL_ROLLOUT,
            rollout_percentage=5.0,
            target_segments=[UserSegment.INTERNAL, UserSegment.ENTERPRISE],
            max_rollout_percentage=100.0,
            rollout_increment=15.0,
            rollout_interval_minutes=120,
            error_threshold=0.5,
            latency_threshold_ms=8000.0,
            min_requests_for_evaluation=25,
            description="Manual-only web search with enterprise controls"
        )
        
        # Initialize metrics for all flags
        for flag_name in self.flags.keys():
            self.metrics[flag_name] = FeatureFlagMetrics(flag_name=flag_name)
    
    def is_feature_enabled(self, 
                          flag_name: str, 
                          user_id: Optional[str] = None,
                          user_segment: Optional[UserSegment] = None,
                          context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Check if a feature is enabled for a given user/context
        
        Returns:
            Tuple of (is_enabled, reason)
        """
        
        if flag_name not in self.flags:
            return False, f"Flag '{flag_name}' not found"
        
        flag = self.flags[flag_name]
        
        # Check emergency disable
        if flag.emergency_disabled or flag.state == FeatureFlagState.EMERGENCY_DISABLED:
            return False, "Feature emergency disabled"
        
        # Check admin override
        if flag.admin_override is not None:
            return flag.admin_override, f"Admin override: {flag.admin_override}"
        
        # Check user-specific override
        if user_id and user_id in self.user_overrides:
            user_flags = self.user_overrides[user_id]
            if flag_name in user_flags:
                return user_flags[flag_name], f"User override: {user_flags[flag_name]}"
        
        # Check flag state
        if flag.state == FeatureFlagState.DISABLED:
            return False, "Feature disabled"
        
        if flag.state == FeatureFlagState.ENABLED:
            return True, "Feature fully enabled"
        
        if flag.state == FeatureFlagState.SHADOW:
            # Shadow mode - feature is enabled but results are not used
            return True, "Shadow mode enabled"
        
        # Gradual rollout logic
        if flag.state == FeatureFlagState.GRADUAL_ROLLOUT:
            
            # Check user segment targeting
            if user_segment and flag.target_segments:
                if user_segment not in flag.target_segments:
                    return False, f"User segment '{user_segment.value}' not in target segments"
            
            # Check rollout percentage
            if user_id:
                user_hash = self._hash_user_for_rollout(user_id, flag_name)
                if user_hash <= flag.rollout_percentage:
                    return True, f"User in rollout ({flag.rollout_percentage}%)"
                else:
                    return False, f"User not in rollout ({flag.rollout_percentage}%)"
            else:
                # No user ID - use random rollout
                if random.random() * 100 <= flag.rollout_percentage:
                    return True, f"Random rollout hit ({flag.rollout_percentage}%)"
                else:
                    return False, f"Random rollout miss ({flag.rollout_percentage}%)"
        
        return False, f"Unknown flag state: {flag.state}"
    
    def _hash_user_for_rollout(self, user_id: str, flag_name: str) -> float:
        """Create consistent hash for user rollout (0-100)"""
        hash_input = f"{user_id}:{flag_name}".encode('utf-8')
        hash_digest = hashlib.md5(hash_input).hexdigest()
        # Convert first 8 chars of hash to int, then normalize to 0-100
        hash_int = int(hash_digest[:8], 16)
        return (hash_int % 10000) / 100.0  # 0-99.99
    
    def should_use_architecture(self, 
                               user_id: Optional[str] = None,
                               user_segment: Optional[UserSegment] = None,
                               context: Optional[Dict[str, Any]] = None) -> Tuple[RouterArchitecture, str]:
        """
        Determine which router architecture to use
        
        Returns:
            Tuple of (architecture, reason)
        """
        
        # Check main consolidation flag
        consolidation_enabled, reason = self.is_feature_enabled(
            "router_consolidation", user_id, user_segment, context
        )
        
        if consolidation_enabled:
            return RouterArchitecture.CONSOLIDATED_3_ROUTER, f"Consolidation enabled: {reason}"
        else:
            return RouterArchitecture.LEGACY_8_ROUTER, f"Using legacy: {reason}"
    
    def record_request_metrics(self,
                              flag_name: str,
                              enabled: bool,
                              success: bool,
                              latency_ms: float,
                              user_id: Optional[str] = None):
        """Record metrics for a feature flag request"""
        
        if flag_name not in self.metrics:
            self.metrics[flag_name] = FeatureFlagMetrics(flag_name=flag_name)
        
        metrics = self.metrics[flag_name]
        
        # Update request counts
        metrics.total_requests += 1
        if enabled:
            metrics.enabled_requests += 1
            if success:
                metrics.enabled_successes += 1
            else:
                metrics.enabled_errors += 1
            metrics.enabled_total_latency_ms += latency_ms
        else:
            metrics.disabled_requests += 1
            if success:
                metrics.disabled_successes += 1
            else:
                metrics.disabled_errors += 1
            metrics.disabled_total_latency_ms += latency_ms
        
        metrics.last_updated = datetime.now()
        
        # Check circuit breaker conditions
        self._check_circuit_breaker(flag_name)
    
    def _check_circuit_breaker(self, flag_name: str):
        """Check if circuit breaker should trigger for a flag"""
        
        if flag_name not in self.flags or flag_name not in self.metrics:
            return
        
        flag = self.flags[flag_name]
        metrics = self.metrics[flag_name]
        
        # Skip if not enough requests for evaluation
        if metrics.enabled_requests < flag.min_requests_for_evaluation:
            return
        
        # Check error rate threshold
        enabled_error_rate = metrics.get_enabled_error_rate()
        if enabled_error_rate > flag.error_threshold:
            logger.error("Circuit breaker triggered - high error rate",
                        flag_name=flag_name,
                        error_rate=enabled_error_rate,
                        threshold=flag.error_threshold)
            self._trigger_emergency_disable(flag_name, f"Error rate {enabled_error_rate}% > {flag.error_threshold}%")
            return
        
        # Check latency threshold
        enabled_avg_latency = metrics.get_enabled_avg_latency_ms()
        if enabled_avg_latency > flag.latency_threshold_ms:
            logger.error("Circuit breaker triggered - high latency",
                        flag_name=flag_name,
                        avg_latency_ms=enabled_avg_latency,
                        threshold_ms=flag.latency_threshold_ms)
            self._trigger_emergency_disable(flag_name, f"Latency {enabled_avg_latency}ms > {flag.latency_threshold_ms}ms")
            return
    
    def _trigger_emergency_disable(self, flag_name: str, reason: str):
        """Trigger emergency disable for a flag"""
        
        if flag_name in self.flags:
            self.flags[flag_name].emergency_disabled = True
            self.flags[flag_name].state = FeatureFlagState.EMERGENCY_DISABLED
            self.flags[flag_name].updated_at = datetime.now()
            
            logger.critical("Feature flag emergency disabled",
                           flag_name=flag_name,
                           reason=reason,
                           timestamp=datetime.now().isoformat())
    
    def advance_gradual_rollout(self, flag_name: str) -> bool:
        """Advance gradual rollout for a flag"""
        
        if flag_name not in self.flags:
            return False
        
        flag = self.flags[flag_name]
        
        # Only advance if in gradual rollout state
        if flag.state != FeatureFlagState.GRADUAL_ROLLOUT:
            return False
        
        # Check if enough time has passed
        time_since_update = datetime.now() - flag.updated_at
        if time_since_update.total_seconds() < (flag.rollout_interval_minutes * 60):
            return False
        
        # Advance rollout percentage
        new_percentage = min(
            flag.rollout_percentage + flag.rollout_increment,
            flag.max_rollout_percentage
        )
        
        flag.rollout_percentage = new_percentage
        flag.updated_at = datetime.now()
        
        # Check if rollout is complete
        if new_percentage >= flag.max_rollout_percentage:
            flag.state = FeatureFlagState.ENABLED
            logger.info("Gradual rollout completed",
                       flag_name=flag_name,
                       final_percentage=new_percentage)
        else:
            logger.info("Gradual rollout advanced",
                       flag_name=flag_name,
                       new_percentage=new_percentage)
        
        return True
    
    def set_user_override(self, user_id: str, flag_name: str, enabled: bool):
        """Set user-specific flag override"""
        
        if user_id not in self.user_overrides:
            self.user_overrides[user_id] = {}
        
        self.user_overrides[user_id][flag_name] = enabled
        
        logger.info("User override set",
                   user_id=user_id,
                   flag_name=flag_name,
                   enabled=enabled)
    
    def set_admin_override(self, flag_name: str, enabled: Optional[bool], admin_user: str):
        """Set admin override for a flag"""
        
        if flag_name not in self.flags:
            return False
        
        self.flags[flag_name].admin_override = enabled
        self.flags[flag_name].updated_at = datetime.now()
        
        logger.info("Admin override set",
                   flag_name=flag_name,
                   enabled=enabled,
                   admin_user=admin_user)
        
        return True
    
    def get_flag_status(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status for a flag"""
        
        if flag_name not in self.flags:
            return None
        
        flag = self.flags[flag_name]
        metrics = self.metrics.get(flag_name)
        
        status = {
            "flag": {
                "name": flag.flag_name,
                "state": flag.state.value,
                "rollout_percentage": flag.rollout_percentage,
                "target_segments": [seg.value for seg in flag.target_segments],
                "admin_override": flag.admin_override,
                "emergency_disabled": flag.emergency_disabled,
                "description": flag.description,
                "created_at": flag.created_at.isoformat(),
                "updated_at": flag.updated_at.isoformat()
            }
        }
        
        if metrics:
            status["metrics"] = {
                "total_requests": metrics.total_requests,
                "enabled_requests": metrics.enabled_requests,
                "disabled_requests": metrics.disabled_requests,
                "enabled_error_rate": metrics.get_enabled_error_rate(),
                "disabled_error_rate": metrics.get_disabled_error_rate(),
                "enabled_avg_latency_ms": metrics.get_enabled_avg_latency_ms(),
                "disabled_avg_latency_ms": metrics.get_disabled_avg_latency_ms(),
                "last_updated": metrics.last_updated.isoformat()
            }
        
        return status
    
    def get_all_flags_status(self) -> Dict[str, Any]:
        """Get status for all flags"""
        
        return {
            flag_name: self.get_flag_status(flag_name)
            for flag_name in self.flags.keys()
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current feature flag configuration"""
        
        config = {
            "flags": {},
            "user_overrides": self.user_overrides,
            "exported_at": datetime.now().isoformat()
        }
        
        for flag_name, flag in self.flags.items():
            config["flags"][flag_name] = {
                "state": flag.state.value,
                "rollout_percentage": flag.rollout_percentage,
                "target_segments": [seg.value for seg in flag.target_segments],
                "admin_override": flag.admin_override,
                "emergency_disabled": flag.emergency_disabled,
                "error_threshold": flag.error_threshold,
                "latency_threshold_ms": flag.latency_threshold_ms,
                "description": flag.description
            }
        
        return config
    
    def auto_advance_rollouts(self):
        """Automatically advance all eligible gradual rollouts"""
        
        advanced_flags = []
        
        for flag_name in self.flags.keys():
            if self.advance_gradual_rollout(flag_name):
                advanced_flags.append(flag_name)
        
        if advanced_flags:
            logger.info("Auto-advanced rollouts", flags=advanced_flags)
        
        return advanced_flags


# Global feature flag manager instance
_feature_flag_manager = None

def get_feature_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance"""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager