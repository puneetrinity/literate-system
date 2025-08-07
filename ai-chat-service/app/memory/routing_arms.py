"""
Memory-specialized routing arms for the multi-armed bandit system.

Each arm represents a different memory strategy optimized for specific
conversation characteristics, user tiers, and performance requirements.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class UserTier(Enum):
    """User tier enumeration for memory allocation"""
    FREE = "free"
    STANDARD = "standard" 
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class MemoryStrategy(Enum):
    """Memory strategy types"""
    MINIMAL = "minimal"
    BALANCED = "balanced"
    COMPREHENSIVE = "comprehensive"
    COST_OPTIMIZED = "cost_optimized"


@dataclass
class MemoryRoutingArm:
    """
    Routing arm specialized for different memory strategies
    
    Each arm defines:
    - Memory budget and retrieval characteristics
    - Performance targets (latency, cost)
    - Conversation context requirements
    - User tier access controls
    """
    
    arm_id: str
    name: str
    description: str
    strategy: MemoryStrategy
    
    # Memory characteristics
    memory_budget_tokens: int
    memory_retrieval_depth: int  # How many messages to consider
    summarization_enabled: bool
    embedding_search_enabled: bool
    
    # Performance targets
    target_response_time_ms: int
    max_cost_per_request_cents: float
    semantic_search_limit: int = 3
    
    # Context requirements
    conversation_length_min: int = 0
    conversation_length_max: int = 999999
    complexity_threshold: float = 0.0  # 0.0 = any complexity, 1.0 = max complexity
    
    # Access control
    user_tier: UserTier = UserTier.STANDARD
    requires_premium: bool = False
    
    # Quality settings
    coherence_priority: float = 0.5  # 0.0 = speed priority, 1.0 = quality priority
    cost_sensitivity: float = 0.5   # 0.0 = cost-insensitive, 1.0 = very cost-sensitive
    
    def is_viable_for_context(self, context: Dict) -> bool:
        """Check if this arm is viable for the given context"""
        
        # Check conversation length constraints
        conv_length = context.get('conversation_length', 0)
        if not (self.conversation_length_min <= conv_length <= self.conversation_length_max):
            return False
        
        # Check complexity requirements
        complexity = context.get('conversation_complexity', 0.5)
        if complexity < self.complexity_threshold:
            return False
        
        # Check user tier access
        user_tier_str = context.get('user_tier', UserTier.STANDARD.value)
        user_tier = UserTier(user_tier_str) if isinstance(user_tier_str, str) else user_tier_str
        
        if self.requires_premium and user_tier in [UserTier.FREE, UserTier.STANDARD]:
            return False
        
        if self.user_tier == UserTier.PREMIUM and user_tier == UserTier.FREE:
            return False
        
        # Check cost sensitivity
        user_cost_sensitivity = context.get('cost_sensitivity', 0.5)
        if user_cost_sensitivity > 0.7 and self.max_cost_per_request_cents > 2.0:
            return False
        
        return True
    
    def calculate_context_score(self, context: Dict) -> float:
        """Calculate how well this arm matches the context (0.0-1.0)"""
        score = 0.5  # Base score
        
        # Conversation length fitness
        conv_length = context.get('conversation_length', 0)
        optimal_length = (self.conversation_length_min + self.conversation_length_max) / 2
        if optimal_length > 0:
            length_fitness = 1.0 - abs(conv_length - optimal_length) / optimal_length
            score += length_fitness * 0.2
        
        # Complexity match
        complexity = context.get('conversation_complexity', 0.5)
        if complexity >= self.complexity_threshold:
            complexity_bonus = min(0.2, (complexity - self.complexity_threshold) * 0.4)
            score += complexity_bonus
        
        # User tier match
        user_tier_str = context.get('user_tier', UserTier.STANDARD.value)
        user_tier = UserTier(user_tier_str) if isinstance(user_tier_str, str) else user_tier_str
        if user_tier == self.user_tier:
            score += 0.1
        
        # Cost sensitivity alignment
        user_cost_sensitivity = context.get('cost_sensitivity', 0.5)
        cost_alignment = 1.0 - abs(user_cost_sensitivity - self.cost_sensitivity)
        score += cost_alignment * 0.1
        
        return min(1.0, max(0.0, score))
    
    def get_memory_config(self, context: Dict) -> Dict:
        """Generate memory configuration for this arm given the context"""
        return {
            'memory_budget_tokens': self.memory_budget_tokens,
            'memory_retrieval_depth': self.memory_retrieval_depth,
            'summarization_enabled': self.summarization_enabled,
            'embedding_search_enabled': self.embedding_search_enabled,
            'semantic_search_limit': self.semantic_search_limit,
            'target_response_time_ms': self.target_response_time_ms,
            'max_cost_per_request_cents': self.max_cost_per_request_cents,
            
            # Dynamic adjustments based on context
            'priority_recent_messages': context.get('requires_immediate_context', True),
            'summary_max_age_hours': 24 if self.summarization_enabled else 0,
            'coherence_priority': self.coherence_priority,
            'cost_sensitivity': self.cost_sensitivity,
            
            # Metadata
            'arm_id': self.arm_id,
            'strategy': self.strategy.value,
        }


# Define the standard memory routing arms
MEMORY_ROUTING_ARMS = [
    MemoryRoutingArm(
        arm_id="minimal_memory",
        name="Minimal Memory Route",
        description="Fast responses with minimal context for simple queries",
        strategy=MemoryStrategy.MINIMAL,
        memory_budget_tokens=1000,
        memory_retrieval_depth=5,
        summarization_enabled=False,
        embedding_search_enabled=False,
        semantic_search_limit=0,
        target_response_time_ms=1500,
        max_cost_per_request_cents=0.5,
        conversation_length_max=10,
        complexity_threshold=0.0,
        user_tier=UserTier.FREE,
        coherence_priority=0.2,
        cost_sensitivity=0.9
    ),
    
    MemoryRoutingArm(
        arm_id="standard_memory", 
        name="Standard Memory Route",
        description="Balanced memory and performance for typical conversations",
        strategy=MemoryStrategy.BALANCED,
        memory_budget_tokens=4000,
        memory_retrieval_depth=20,
        summarization_enabled=True,
        embedding_search_enabled=True,
        semantic_search_limit=3,
        target_response_time_ms=2500,
        max_cost_per_request_cents=2.0,
        conversation_length_min=3,
        conversation_length_max=50,
        complexity_threshold=0.2,
        user_tier=UserTier.STANDARD,
        coherence_priority=0.6,
        cost_sensitivity=0.5
    ),
    
    MemoryRoutingArm(
        arm_id="deep_context",
        name="Deep Context Route", 
        description="Maximum context with comprehensive memory for complex discussions",
        strategy=MemoryStrategy.COMPREHENSIVE,
        memory_budget_tokens=8000,
        memory_retrieval_depth=100,
        summarization_enabled=True,
        embedding_search_enabled=True,
        semantic_search_limit=5,
        target_response_time_ms=4000,
        max_cost_per_request_cents=5.0,
        conversation_length_min=15,
        complexity_threshold=0.7,
        user_tier=UserTier.PREMIUM,
        requires_premium=True,
        coherence_priority=0.9,
        cost_sensitivity=0.2
    ),
    
    MemoryRoutingArm(
        arm_id="cost_optimized",
        name="Cost-Optimized Route",
        description="Budget-conscious with smart memory usage prioritizing cost efficiency", 
        strategy=MemoryStrategy.COST_OPTIMIZED,
        memory_budget_tokens=2000,
        memory_retrieval_depth=10,
        summarization_enabled=True,
        embedding_search_enabled=False,  # Expensive vector searches disabled
        semantic_search_limit=0,
        target_response_time_ms=3000,
        max_cost_per_request_cents=1.0,
        conversation_length_min=5,
        conversation_length_max=30,
        complexity_threshold=0.1,
        user_tier=UserTier.STANDARD,
        coherence_priority=0.4,
        cost_sensitivity=0.8
    ),
    
    MemoryRoutingArm(
        arm_id="enterprise_comprehensive",
        name="Enterprise Comprehensive Route",
        description="Premium memory strategy with maximum context and quality for enterprise users",
        strategy=MemoryStrategy.COMPREHENSIVE,
        memory_budget_tokens=12000,
        memory_retrieval_depth=200,
        summarization_enabled=True,
        embedding_search_enabled=True,
        semantic_search_limit=7,
        target_response_time_ms=5000,
        max_cost_per_request_cents=10.0,
        conversation_length_min=10,
        complexity_threshold=0.5,
        user_tier=UserTier.ENTERPRISE,
        requires_premium=True,
        coherence_priority=1.0,
        cost_sensitivity=0.1
    )
]


class MemoryArmManager:
    """Manager for memory routing arms with filtering and selection logic"""
    
    def __init__(self, arms: List[MemoryRoutingArm] = None):
        self.arms = {arm.arm_id: arm for arm in (arms or MEMORY_ROUTING_ARMS)}
        logger.info("memory_arm_manager_initialized", arm_count=len(self.arms))
    
    def get_viable_arms(self, context: Dict) -> List[str]:
        """Get list of viable arm IDs for the given context"""
        viable_arms = []
        
        for arm_id, arm in self.arms.items():
            if arm.is_viable_for_context(context):
                viable_arms.append(arm_id)
        
        if not viable_arms:
            # Fallback to minimal_memory if no arms are viable
            logger.warning(
                "no_viable_arms_found_using_fallback",
                context=context,
                fallback_arm="minimal_memory"
            )
            viable_arms = ["minimal_memory"] if "minimal_memory" in self.arms else list(self.arms.keys())[:1]
        
        logger.debug(
            "viable_arms_determined",
            context_summary=self._summarize_context(context),
            viable_arms=viable_arms,
            total_arms=len(self.arms)
        )
        
        return viable_arms
    
    def calculate_context_scores(self, context: Dict, arm_ids: List[str] = None) -> Dict[str, float]:
        """Calculate context fitness scores for specified arms"""
        arm_ids = arm_ids or list(self.arms.keys())
        scores = {}
        
        for arm_id in arm_ids:
            if arm_id in self.arms:
                scores[arm_id] = self.arms[arm_id].calculate_context_score(context)
        
        return scores
    
    def get_memory_config(self, arm_id: str, context: Dict) -> Dict:
        """Get memory configuration for the specified arm and context"""
        if arm_id not in self.arms:
            logger.error("unknown_arm_requested", arm_id=arm_id)
            arm_id = "minimal_memory"  # Fallback
        
        return self.arms[arm_id].get_memory_config(context)
    
    def get_arm_info(self, arm_id: str) -> Optional[MemoryRoutingArm]:
        """Get full arm information"""
        return self.arms.get(arm_id)
    
    def list_arms(self) -> Dict[str, Dict]:
        """Get summary information for all arms"""
        return {
            arm_id: {
                'name': arm.name,
                'description': arm.description,
                'strategy': arm.strategy.value,
                'memory_budget_tokens': arm.memory_budget_tokens,
                'target_response_time_ms': arm.target_response_time_ms,
                'max_cost_cents': arm.max_cost_per_request_cents,
                'user_tier': arm.user_tier.value,
                'requires_premium': arm.requires_premium
            }
            for arm_id, arm in self.arms.items()
        }
    
    def _summarize_context(self, context: Dict) -> Dict:
        """Create a summary of context for logging"""
        return {
            'conversation_length': context.get('conversation_length', 0),
            'complexity': round(context.get('conversation_complexity', 0.5), 2),
            'user_tier': context.get('user_tier', 'standard'),
            'cost_sensitivity': round(context.get('cost_sensitivity', 0.5), 2)
        }


# Global instance for easy access
memory_arm_manager = MemoryArmManager()