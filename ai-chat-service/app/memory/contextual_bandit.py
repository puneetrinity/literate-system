"""
Memory-aware Thompson Sampling bandit for adaptive conversation memory routing.

Extends the base Thompson Sampling bandit with:
- Memory-specific context filtering
- Contextual performance tracking
- Memory effectiveness reward adjustments
- Dynamic arm viability based on conversation characteristics
"""

import time
from typing import Dict, List, Tuple, Optional
from dataclasses import asdict

import structlog

from app.adaptive.bandit.thompson_sampling import ThompsonSamplingBandit, BanditArm
from app.memory.routing_arms import MemoryRoutingArm, MemoryArmManager, MEMORY_ROUTING_ARMS

logger = structlog.get_logger(__name__)


class MemoryAwareThompsonBandit(ThompsonSamplingBandit):
    """
    Thompson Sampling bandit enhanced with memory-specific context awareness.
    
    Features:
    - Contextual arm filtering based on conversation characteristics
    - Memory effectiveness tracking and reward adjustments
    - Dynamic performance learning per context type
    - Intelligent fallback mechanisms
    """
    
    def __init__(self, memory_arms: List[MemoryRoutingArm] = None, min_exploration_rate: float = 0.05):
        # Initialize with memory arms
        self.memory_arm_manager = MemoryArmManager(memory_arms or MEMORY_ROUTING_ARMS)
        
        # Convert memory arms to standard bandit arms
        standard_arms = [
            {"arm_id": arm.arm_id, "name": arm.name} 
            for arm in self.memory_arm_manager.arms.values()
        ]
        
        super().__init__(standard_arms, min_exploration_rate)
        
        # Memory-specific tracking
        self.contextual_weights = {}  # context_key -> {arm_id -> performance_weight}
        self.context_counts = {}      # context_key -> count
        self.memory_metrics_history = {}  # arm_id -> List[memory_metrics]
        
        # Learning parameters
        self.contextual_learning_rate = 0.1
        self.context_decay_factor = 0.95  # Decay old context performance
        self.min_context_observations = 5  # Minimum observations before trusting contextual weights
        
        logger.info(
            "memory_aware_bandit_initialized",
            arms=list(self.arms.keys()),
            min_exploration_rate=min_exploration_rate,
            contextual_learning_rate=self.contextual_learning_rate
        )
    
    def select_arm_with_memory_context(self, context: Dict) -> Tuple[str, float, Dict]:
        """
        Select optimal arm based on conversation memory context.
        
        Args:
            context: Conversation and user context information
            
        Returns:
            Tuple of (selected_arm_id, confidence_score, memory_config)
        """
        
        # 1. Filter viable arms based on context constraints
        viable_arms = self.memory_arm_manager.get_viable_arms(context)
        
        # 2. Get context-specific performance weights
        context_key = self._create_context_key(context)
        contextual_weights = self.contextual_weights.get(context_key, {})
        
        # 3. Context-aware Thompson sampling
        arm_samples = {}
        context_scores = self.memory_arm_manager.calculate_context_scores(context, viable_arms)
        
        for arm_id in viable_arms:
            if arm_id not in self.arms:
                logger.warning("viable_arm_not_in_bandit", arm_id=arm_id)
                continue
                
            # Base Thompson sampling
            base_sample = self.arms[arm_id].sample_reward_probability()
            
            # Apply contextual adjustments
            contextual_boost = self._calculate_contextual_boost(
                arm_id, context, contextual_weights, context_scores.get(arm_id, 0.5)
            )
            
            # Final adjusted sample
            adjusted_sample = min(1.0, base_sample * contextual_boost)
            arm_samples[arm_id] = adjusted_sample
        
        # 4. Select arm with highest sample (with exploration fallback)
        if not arm_samples:
            logger.error("no_viable_arms_with_samples", context=context)
            selected_arm_id = "minimal_memory"  # Emergency fallback
            confidence = 0.1
        else:
            selected_arm_id = max(arm_samples.items(), key=lambda x: x[1])[0]
            confidence = arm_samples[selected_arm_id]
        
        # 5. Get memory configuration for selected arm
        memory_config = self.memory_arm_manager.get_memory_config(selected_arm_id, context)
        
        # 6. Update context tracking
        self.context_counts[context_key] = self.context_counts.get(context_key, 0) + 1
        
        # 7. Log selection decision
        logger.info(
            "memory_bandit_selection",
            selected_arm=selected_arm_id,
            confidence=round(confidence, 3),
            viable_arms=viable_arms,
            context_key=context_key,
            context_observations=self.context_counts[context_key],
            arm_samples={k: round(v, 3) for k, v in arm_samples.items()},
            memory_config_summary={
                'budget_tokens': memory_config['memory_budget_tokens'],
                'target_time_ms': memory_config['target_response_time_ms'],
                'strategy': memory_config['strategy']
            }
        )
        
        return selected_arm_id, confidence, memory_config
    
    def update_with_memory_context(self, arm_id: str, reward: float, context: Dict, 
                                 memory_metrics: Dict) -> None:
        """
        Update bandit with memory-specific reward and contextual learning.
        
        Args:
            arm_id: Selected arm identifier
            reward: Base reward score (0.0-1.0)
            context: Conversation context used for selection
            memory_metrics: Memory effectiveness metrics
        """
        
        # 1. Calculate memory-adjusted reward
        memory_adjusted_reward = self._calculate_memory_reward(reward, memory_metrics)
        
        # 2. Standard Thompson sampling update
        self.arms[arm_id].update(memory_adjusted_reward)
        
        # 3. Update contextual performance tracking
        context_key = self._create_context_key(context)
        self._update_contextual_weights(arm_id, context_key, memory_adjusted_reward)
        
        # 4. Store memory metrics for analysis
        if arm_id not in self.memory_metrics_history:
            self.memory_metrics_history[arm_id] = []
        
        self.memory_metrics_history[arm_id].append({
            'timestamp': time.time(),
            'reward': reward,
            'memory_adjusted_reward': memory_adjusted_reward,
            'memory_metrics': memory_metrics.copy(),
            'context_key': context_key
        })
        
        # Keep only recent history (last 1000 observations)
        if len(self.memory_metrics_history[arm_id]) > 1000:
            self.memory_metrics_history[arm_id] = self.memory_metrics_history[arm_id][-1000:]
        
        # 5. Log update
        logger.info(
            "memory_bandit_update",
            arm_id=arm_id,
            original_reward=round(reward, 3),
            memory_adjusted_reward=round(memory_adjusted_reward, 3),
            context_key=context_key,
            memory_efficiency=round(memory_metrics.get('memory_efficiency', 0.5), 3),
            coherence_maintained=memory_metrics.get('coherence_maintained', False),
            arm_stats={
                'alpha': round(self.arms[arm_id].alpha, 2),
                'beta': round(self.arms[arm_id].beta_param, 2),
                'success_rate': round(self.arms[arm_id].success_rate, 3),
                'total_pulls': self.arms[arm_id].total_pulls
            }
        )
    
    def _calculate_contextual_boost(self, arm_id: str, context: Dict, 
                                  contextual_weights: Dict, context_score: float) -> float:
        """Calculate contextual performance boost for arm selection"""
        boost = 1.0
        
        # 1. Context fitness boost (how well arm matches context)
        boost *= (0.8 + context_score * 0.4)  # 0.8-1.2 multiplier
        
        # 2. Historical contextual performance
        if arm_id in contextual_weights:
            observations = self.context_counts.get(self._create_context_key(context), 0)
            if observations >= self.min_context_observations:
                historical_weight = contextual_weights[arm_id]
                boost *= (0.7 + historical_weight * 0.6)  # 0.7-1.3 multiplier
        
        # 3. Arm-specific adjustments based on context
        arm_info = self.memory_arm_manager.get_arm_info(arm_id)
        if arm_info:
            # Boost for conversation length alignment
            conv_length = context.get('conversation_length', 0)
            optimal_range = (arm_info.conversation_length_min, arm_info.conversation_length_max)
            if optimal_range[0] <= conv_length <= optimal_range[1]:
                boost *= 1.1
            
            # Boost for complexity match
            complexity = context.get('conversation_complexity', 0.5)
            if complexity >= arm_info.complexity_threshold:
                boost *= 1.05
            
            # Boost for user tier alignment
            user_tier = context.get('user_tier', 'standard')
            if user_tier == arm_info.user_tier.value:
                boost *= 1.05
        
        return max(0.5, min(2.0, boost))  # Clamp to reasonable range
    
    def _calculate_memory_reward(self, base_reward: float, memory_metrics: Dict) -> float:
        """Calculate memory-effectiveness-adjusted reward"""
        memory_reward = base_reward
        
        # Memory efficiency component (±0.2)
        memory_efficiency = memory_metrics.get('memory_efficiency', 0.5)
        efficiency_adjustment = (memory_efficiency - 0.5) * 0.4
        memory_reward += efficiency_adjustment
        
        # Context relevance component (±0.15)
        context_relevance = memory_metrics.get('context_relevance_score', 0.5)
        relevance_adjustment = (context_relevance - 0.5) * 0.3
        memory_reward += relevance_adjustment
        
        # Coherence maintenance bonus (+0.1)
        if memory_metrics.get('coherence_maintained', False):
            memory_reward += 0.1
        
        # Response time penalty (up to -0.2)
        response_time = memory_metrics.get('response_time_ms', 2500)
        target_time = memory_metrics.get('target_response_time_ms', 2500)
        if response_time > target_time:
            time_penalty = min(0.2, (response_time - target_time) / target_time * 0.2)
            memory_reward -= time_penalty
        
        # Cost efficiency penalty (up to -0.15)
        cost_efficiency = memory_metrics.get('cost_efficiency', 1.0)
        if cost_efficiency < 0.8:
            cost_penalty = (0.8 - cost_efficiency) * 0.375  # Max penalty 0.15 when efficiency=0.4
            memory_reward -= cost_penalty
        
        # Context utilization bonus (±0.1)
        context_utilization = memory_metrics.get('context_utilization_rate', 0.5)
        utilization_adjustment = (context_utilization - 0.5) * 0.2
        memory_reward += utilization_adjustment
        
        return max(0.0, min(1.0, memory_reward))
    
    def _update_contextual_weights(self, arm_id: str, context_key: str, reward: float) -> None:
        """Update contextual performance weights with exponential moving average"""
        
        if context_key not in self.contextual_weights:
            self.contextual_weights[context_key] = {}
        
        current_weight = self.contextual_weights[context_key].get(arm_id, 0.5)
        
        # Apply decay to all arms in this context (non-selected arms decay toward 0.5)
        for existing_arm_id in self.contextual_weights[context_key]:
            if existing_arm_id != arm_id:
                self.contextual_weights[context_key][existing_arm_id] = (
                    self.contextual_weights[context_key][existing_arm_id] * self.context_decay_factor +
                    0.5 * (1 - self.context_decay_factor)
                )
        
        # Update selected arm with new reward
        new_weight = (
            current_weight * (1 - self.contextual_learning_rate) +
            reward * self.contextual_learning_rate
        )
        
        self.contextual_weights[context_key][arm_id] = new_weight
    
    def _create_context_key(self, context: Dict) -> str:
        """Create discrete context key for clustering similar contexts"""
        
        # Discretize continuous values
        conv_length_bucket = min(5, context.get('conversation_length', 0) // 5)  # 0-4, 5-9, 10-14, etc.
        complexity_bucket = int(context.get('conversation_complexity', 0.5) * 3)  # 0, 1, 2
        cost_sensitivity_bucket = int(context.get('cost_sensitivity', 0.5) * 2)  # 0, 1
        
        user_tier = context.get('user_tier', 'standard')
        
        return f"len{conv_length_bucket}_comp{complexity_bucket}_cost{cost_sensitivity_bucket}_{user_tier}"
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary for monitoring"""
        
        # Arm performance
        arm_performance = {}
        for arm_id, arm in self.arms.items():
            arm_performance[arm_id] = {
                'success_rate': round(arm.success_rate, 3),
                'confidence_interval': [round(x, 3) for x in arm.confidence_interval] if hasattr(arm, 'confidence_interval') else None,
                'total_pulls': arm.total_pulls,
                'total_rewards': round(arm.total_rewards, 2),
                'last_updated': arm.last_updated
            }
        
        # Contextual performance
        contextual_summary = {}
        for context_key, weights in self.contextual_weights.items():
            contextual_summary[context_key] = {
                'observations': self.context_counts.get(context_key, 0),
                'arm_weights': {k: round(v, 3) for k, v in weights.items()},
                'best_arm': max(weights.items(), key=lambda x: x[1])[0] if weights else None
            }
        
        # Memory metrics summary
        memory_summary = {}
        for arm_id, history in self.memory_metrics_history.items():
            if history:
                recent_metrics = history[-10:]  # Last 10 observations
                memory_summary[arm_id] = {
                    'avg_memory_efficiency': round(
                        sum(m['memory_metrics'].get('memory_efficiency', 0.5) for m in recent_metrics) / len(recent_metrics), 3
                    ),
                    'avg_coherence_rate': round(
                        sum(1 for m in recent_metrics if m['memory_metrics'].get('coherence_maintained', False)) / len(recent_metrics), 3
                    ),
                    'avg_context_relevance': round(
                        sum(m['memory_metrics'].get('context_relevance_score', 0.5) for m in recent_metrics) / len(recent_metrics), 3
                    ),
                    'total_observations': len(history)
                }
        
        return {
            'bandit_stats': {
                'total_pulls': self.total_pulls,
                'start_time': self.start_time,
                'arms_count': len(self.arms),
                'contexts_learned': len(self.contextual_weights)
            },
            'arm_performance': arm_performance,
            'contextual_performance': contextual_summary,
            'memory_effectiveness': memory_summary,
            'learning_parameters': {
                'contextual_learning_rate': self.contextual_learning_rate,
                'context_decay_factor': self.context_decay_factor,
                'min_context_observations': self.min_context_observations,
                'min_exploration_rate': self.min_exploration_rate
            }
        }
    
    def get_recommendations(self) -> Dict:
        """Get recommendations for bandit tuning and performance improvement"""
        recommendations = []
        
        # Check for cold start issues
        cold_arms = [arm_id for arm_id, arm in self.arms.items() if arm.total_pulls < 10]
        if cold_arms:
            recommendations.append({
                'type': 'cold_start',
                'message': f"Arms {cold_arms} have insufficient data. Consider increasing exploration.",
                'arms': cold_arms
            })
        
        # Check for context imbalance
        context_counts = list(self.context_counts.values())
        if context_counts and max(context_counts) > 5 * min(context_counts):
            recommendations.append({
                'type': 'context_imbalance',
                'message': "Some contexts are underrepresented. Monitor traffic distribution.",
                'context_distribution': dict(self.context_counts)
            })
        
        # Check for poor-performing arms
        poor_arms = [
            arm_id for arm_id, arm in self.arms.items() 
            if arm.total_pulls > 20 and arm.success_rate < 0.3
        ]
        if poor_arms:
            recommendations.append({
                'type': 'poor_performance',
                'message': f"Arms {poor_arms} consistently underperform. Consider configuration review.",
                'arms': poor_arms
            })
        
        return {
            'recommendations': recommendations,
            'generated_at': time.time()
        }