"""
Memory-aware reward calculator for the multi-armed bandit system.

Extends the base reward calculator with memory-specific metrics:
- Memory efficiency and utilization
- Context relevance and coherence
- Cost-effectiveness of memory usage
- Conversation quality improvements
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional, List

import structlog

from app.adaptive.rewards.enhanced_calculator import EnhancedRouteMetrics, EnhancedRewardCalculator

logger = structlog.get_logger(__name__)


@dataclass  
class MemoryAwareRouteMetrics(EnhancedRouteMetrics):
    """Extended metrics including memory-specific measurements"""
    
    # Memory usage metrics
    memory_tokens_used: int = 0
    memory_retrieval_time_ms: float = 0.0
    redis_cache_hits: int = 0
    clickhouse_queries: int = 0
    embedding_searches: int = 0
    
    # Memory effectiveness metrics
    context_relevance_score: float = 0.5  # How relevant was retrieved context (0.0-1.0)
    context_utilization_rate: float = 0.5  # How much context was actually used (0.0-1.0)
    memory_efficiency: float = 0.5  # Cost/benefit ratio of memory usage (0.0-1.0)
    
    # Conversation quality metrics
    coherence_score: float = 0.5  # Conversation coherence maintained (0.0-1.0)
    coherence_maintained: bool = False  # Binary coherence check
    topic_continuity_score: float = 0.5  # Topic flow maintained (0.0-1.0)
    user_satisfaction_inferred: float = 0.5  # Inferred user satisfaction (0.0-1.0)
    
    # Summary quality metrics (when applicable)
    summary_generated: bool = False
    summary_quality_score: float = 0.5  # Quality of generated summary (0.0-1.0)
    summary_compression_ratio: float = 0.0  # Input tokens / summary tokens
    
    # Cost efficiency metrics
    cost_per_quality_unit: float = 0.0  # Cost per unit of conversation quality
    memory_cost_ratio: float = 0.0  # Memory costs as fraction of total cost
    
    # Retrieval performance
    cache_hit_rate: float = 0.0  # Redis hits / total memory operations
    avg_retrieval_latency_ms: float = 0.0  # Average latency for memory operations
    
    # Memory budget utilization
    memory_budget_allocated: int = 0  # Tokens allocated
    memory_budget_used: int = 0  # Tokens actually used
    memory_budget_efficiency: float = 0.0  # Used / allocated ratio


class MemoryAwareRewardCalculator(EnhancedRewardCalculator):
    """
    Enhanced reward calculator incorporating memory effectiveness metrics.
    
    Reward components:
    - Base performance (response time, success rate): 35%
    - Cost efficiency (including memory costs): 25%
    - Memory effectiveness: 20%
    - User experience (including coherence): 15%
    - Business impact: 5%
    """
    
    def __init__(
        self,
        # Base reward weights
        performance_weight: float = 0.35,
        cost_weight: float = 0.25,
        ux_weight: float = 0.15,
        business_weight: float = 0.05,
        # Memory-specific weight
        memory_weight: float = 0.20,
        # Performance targets
        target_response_time: float = 2.5,
        max_response_time: float = 10.0,
        # Cost targets
        target_cost_cents: float = 2.0,
        max_cost_cents: float = 10.0,
        # Memory targets
        target_memory_efficiency: float = 0.7,
        target_context_relevance: float = 0.6,
        target_coherence_score: float = 0.7,
        # Budget settings
        monthly_budget_usd: float = 50.0,
        cost_penalty_threshold: float = 0.8,
    ):
        # Initialize base calculator with adjusted weights
        super().__init__(
            performance_weight=performance_weight,
            cost_weight=cost_weight,
            ux_weight=ux_weight,
            business_weight=business_weight,
            target_response_time=target_response_time,
            max_response_time=max_response_time,
            target_cost_cents=target_cost_cents,
            max_cost_cents=max_cost_cents,
            monthly_budget_usd=monthly_budget_usd,
            cost_penalty_threshold=cost_penalty_threshold
        )
        
        # Memory-specific parameters
        self.memory_weight = memory_weight
        self.target_memory_efficiency = target_memory_efficiency
        self.target_context_relevance = target_context_relevance
        self.target_coherence_score = target_coherence_score
        
        # Validate weights sum to 1.0
        total_weight = performance_weight + cost_weight + ux_weight + business_weight + memory_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                "reward_weights_dont_sum_to_one",
                total_weight=total_weight,
                weights={
                    "performance": performance_weight,
                    "cost": cost_weight,
                    "ux": ux_weight,
                    "business": business_weight,
                    "memory": memory_weight
                }
            )
        
        logger.info(
            "memory_aware_reward_calculator_initialized",
            weights={
                "performance": performance_weight,
                "cost": cost_weight,
                "memory": memory_weight,
                "ux": ux_weight,
                "business": business_weight
            },
            targets={
                "memory_efficiency": target_memory_efficiency,
                "context_relevance": target_context_relevance,
                "coherence_score": target_coherence_score
            }
        )
    
    def calculate_memory_aware_reward(self, metrics: MemoryAwareRouteMetrics) -> Dict:
        """
        Calculate comprehensive reward including memory effectiveness.
        
        Args:
            metrics: Complete metrics including memory-specific data
            
        Returns:
            Dict with detailed reward breakdown
        """
        
        # Calculate base components
        performance_score = self._calculate_performance_score(metrics)
        cost_score = self._calculate_enhanced_cost_score(metrics)  # Enhanced with memory costs
        ux_score = self._calculate_enhanced_ux_score(metrics)  # Enhanced with coherence
        business_score = self._calculate_business_score(metrics)
        
        # Calculate memory-specific score
        memory_score = self._calculate_memory_score(metrics)
        
        # Weighted combination
        total_reward = (
            performance_score * self.performance_weight +
            cost_score * self.cost_weight +
            memory_score * self.memory_weight +
            ux_score * self.ux_weight +
            business_score * self.business_weight
        )
        
        # Apply global penalties
        total_reward = self._apply_global_penalties(total_reward, metrics)
        
        # Clamp to valid range
        total_reward = max(0.0, min(1.0, total_reward))
        
        reward_breakdown = {
            'total_reward': total_reward,
            'components': {
                'performance': {
                    'score': performance_score,
                    'weight': self.performance_weight,
                    'contribution': performance_score * self.performance_weight
                },
                'cost': {
                    'score': cost_score,
                    'weight': self.cost_weight,
                    'contribution': cost_score * self.cost_weight
                },
                'memory': {
                    'score': memory_score,
                    'weight': self.memory_weight,
                    'contribution': memory_score * self.memory_weight
                },
                'ux': {
                    'score': ux_score,
                    'weight': self.ux_weight,
                    'contribution': ux_score * self.ux_weight
                },
                'business': {
                    'score': business_score,
                    'weight': self.business_weight,
                    'contribution': business_score * self.business_weight
                }
            },
            'memory_details': self._get_memory_details(metrics),
            'quality_indicators': self._get_quality_indicators(metrics),
            'recommendations': self._generate_recommendations(metrics)
        }
        
        logger.debug(
            "memory_aware_reward_calculated",
            total_reward=round(total_reward, 3),
            memory_score=round(memory_score, 3),
            memory_efficiency=round(metrics.memory_efficiency, 3),
            coherence_maintained=metrics.coherence_maintained,
            context_relevance=round(metrics.context_relevance_score, 3)
        )
        
        return reward_breakdown
    
    def _calculate_memory_score(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Calculate memory effectiveness score (0.0-1.0)"""
        memory_score = 0.0
        
        # 1. Memory efficiency (30% of memory score)
        efficiency_score = self._score_memory_efficiency(metrics)
        memory_score += efficiency_score * 0.30
        
        # 2. Context relevance (25% of memory score)
        relevance_score = self._score_context_relevance(metrics)
        memory_score += relevance_score * 0.25
        
        # 3. Conversation coherence (25% of memory score)
        coherence_score = self._score_conversation_coherence(metrics)
        memory_score += coherence_score * 0.25
        
        # 4. Retrieval performance (20% of memory score)
        retrieval_score = self._score_retrieval_performance(metrics)
        memory_score += retrieval_score * 0.20
        
        return min(1.0, max(0.0, memory_score))
    
    def _score_memory_efficiency(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Score memory usage efficiency"""
        
        # Base efficiency score
        efficiency = metrics.memory_efficiency
        score = efficiency / self.target_memory_efficiency if self.target_memory_efficiency > 0 else efficiency
        
        # Budget utilization bonus/penalty
        if metrics.memory_budget_allocated > 0:
            utilization = metrics.memory_budget_used / metrics.memory_budget_allocated
            
            # Optimal utilization is 70-90%
            if 0.7 <= utilization <= 0.9:
                score *= 1.1  # Bonus for good utilization
            elif utilization < 0.5:
                score *= 0.8  # Penalty for under-utilization
            elif utilization > 0.95:
                score *= 0.9  # Slight penalty for over-utilization
        
        # Memory cost ratio consideration
        if metrics.memory_cost_ratio > 0.5:  # Memory costs > 50% of total
            score *= 0.9  # Slight penalty for high memory costs
        
        return min(1.0, max(0.0, score))
    
    def _score_context_relevance(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Score context relevance and utilization"""
        
        # Base relevance score
        relevance = metrics.context_relevance_score
        score = relevance / self.target_context_relevance if self.target_context_relevance > 0 else relevance
        
        # Context utilization modifier
        utilization = metrics.context_utilization_rate
        if utilization > 0.7:
            score *= 1.1  # Bonus for high utilization
        elif utilization < 0.3:
            score *= 0.8  # Penalty for low utilization
        
        # Topic continuity bonus
        if metrics.topic_continuity_score > 0.7:
            score *= 1.05
        
        return min(1.0, max(0.0, score))
    
    def _score_conversation_coherence(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Score conversation coherence maintenance"""
        
        # Base coherence score
        coherence = metrics.coherence_score
        score = coherence / self.target_coherence_score if self.target_coherence_score > 0 else coherence
        
        # Binary coherence maintenance bonus
        if metrics.coherence_maintained:
            score += 0.2
        
        # Summary quality contribution (if applicable)
        if metrics.summary_generated and metrics.summary_quality_score > 0.6:
            score += 0.1
        
        # User satisfaction correlation
        if metrics.user_satisfaction_inferred > 0.7:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _score_retrieval_performance(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Score memory retrieval performance"""
        
        score = 0.5  # Base score
        
        # Cache hit rate bonus
        if metrics.cache_hit_rate > 0.7:
            score += 0.3
        elif metrics.cache_hit_rate > 0.5:
            score += 0.1
        elif metrics.cache_hit_rate < 0.3:
            score -= 0.2
        
        # Retrieval latency score
        if metrics.avg_retrieval_latency_ms < 100:
            score += 0.2
        elif metrics.avg_retrieval_latency_ms < 200:
            score += 0.1
        elif metrics.avg_retrieval_latency_ms > 500:
            score -= 0.2
        
        # Memory retrieval time penalty
        if metrics.memory_retrieval_time_ms > 300:
            penalty = min(0.2, (metrics.memory_retrieval_time_ms - 300) / 1000)
            score -= penalty
        
        return min(1.0, max(0.0, score))
    
    def _calculate_enhanced_cost_score(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Enhanced cost calculation including memory costs"""
        
        # Base cost score
        base_cost_score = super()._calculate_cost_efficiency_score(metrics)
        
        # Memory cost efficiency adjustment
        if metrics.memory_cost_ratio > 0:
            if metrics.cost_per_quality_unit > 0:
                # Penalty for high cost per quality
                cost_efficiency = min(1.0, 1.0 / metrics.cost_per_quality_unit)
                base_cost_score *= (0.8 + cost_efficiency * 0.4)  # 0.8-1.2 multiplier
        
        return base_cost_score
    
    def _calculate_enhanced_ux_score(self, metrics: MemoryAwareRouteMetrics) -> float:
        """Enhanced UX calculation including coherence"""
        
        # Base UX score
        base_ux_score = super()._calculate_ux_score(metrics)
        
        # Coherence bonus
        if metrics.coherence_maintained:
            base_ux_score += 0.1
        
        # User satisfaction correlation
        if metrics.user_satisfaction_inferred > 0.7:
            base_ux_score += 0.1
        elif metrics.user_satisfaction_inferred < 0.3:
            base_ux_score -= 0.1
        
        return min(1.0, max(0.0, base_ux_score))
    
    def _apply_global_penalties(self, reward: float, metrics: MemoryAwareRouteMetrics) -> float:
        """Apply global penalties for critical failures"""
        
        # Severe coherence loss penalty
        if metrics.coherence_score < 0.2:
            reward *= 0.5
        
        # Memory failure penalty
        if metrics.memory_efficiency < 0.1:
            reward *= 0.7
        
        # Extreme cost overrun penalty
        if hasattr(metrics, 'estimated_cost_usd') and metrics.estimated_cost_usd > self.max_cost_cents / 100 * 2:
            reward *= 0.6
        
        # Response time failure penalty
        if metrics.response_time_seconds > self.max_response_time * 1.5:
            reward *= 0.8
        
        return reward
    
    def _get_memory_details(self, metrics: MemoryAwareRouteMetrics) -> Dict:
        """Extract memory-specific details for analysis"""
        return {
            'efficiency': round(metrics.memory_efficiency, 3),
            'context_relevance': round(metrics.context_relevance_score, 3),
            'context_utilization': round(metrics.context_utilization_rate, 3),
            'coherence_score': round(metrics.coherence_score, 3),
            'coherence_maintained': metrics.coherence_maintained,
            'cache_hit_rate': round(metrics.cache_hit_rate, 3),
            'retrieval_time_ms': round(metrics.memory_retrieval_time_ms, 1),
            'budget_utilization': round(
                metrics.memory_budget_used / metrics.memory_budget_allocated 
                if metrics.memory_budget_allocated > 0 else 0.0, 3
            ),
            'tokens_used': metrics.memory_tokens_used,
            'summary_generated': metrics.summary_generated,
            'summary_quality': round(metrics.summary_quality_score, 3) if metrics.summary_generated else None
        }
    
    def _get_quality_indicators(self, metrics: MemoryAwareRouteMetrics) -> Dict:
        """Extract quality indicators for monitoring"""
        return {
            'response_quality': 'high' if metrics.user_satisfaction_inferred > 0.7 else 
                               'medium' if metrics.user_satisfaction_inferred > 0.4 else 'low',
            'memory_effectiveness': 'high' if metrics.memory_efficiency > 0.7 else
                                   'medium' if metrics.memory_efficiency > 0.4 else 'low',
            'coherence_status': 'maintained' if metrics.coherence_maintained else 'degraded',
            'cost_efficiency': 'efficient' if metrics.cost_per_quality_unit < 2.0 else
                              'acceptable' if metrics.cost_per_quality_unit < 5.0 else 'expensive'
        }
    
    def _generate_recommendations(self, metrics: MemoryAwareRouteMetrics) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        if metrics.memory_efficiency < 0.4:
            recommendations.append("Consider reducing memory budget or improving relevance filtering")
        
        if metrics.cache_hit_rate < 0.3:
            recommendations.append("Review caching strategy - low cache hit rate detected")
        
        if not metrics.coherence_maintained:
            recommendations.append("Investigate coherence loss - may need more context")
        
        if metrics.context_utilization_rate < 0.3:
            recommendations.append("High context retrieval but low utilization - improve relevance")
        
        if metrics.memory_retrieval_time_ms > 500:
            recommendations.append("Memory retrieval too slow - optimize queries or indexing")
        
        if metrics.cost_per_quality_unit > 5.0:
            recommendations.append("High cost per quality unit - consider cost optimization")
        
        return recommendations


def create_memory_aware_reward_calculator(**kwargs) -> MemoryAwareRewardCalculator:
    """Factory function to create memory-aware reward calculator with defaults"""
    return MemoryAwareRewardCalculator(**kwargs)