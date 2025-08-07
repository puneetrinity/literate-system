"""
BanditIntegratedMemoryOrchestrator: Central coordinator for conversation memory management.

Integrates all memory components with the multi-armed bandit system:
- MemoryAwareThompsonBandit for adaptive routing
- ConversationMemoryCache (Redis) for hot memory
- ConversationClickHouseManager for cold storage
- AsyncSummarizationService for background processing
- MemoryAwareRewardCalculator for performance optimization

This orchestrator implements the Memory-Enhanced Multi-Armed Bandit strategy
with budget-aware context assembly and real-time performance tracking.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import structlog

from app.models.manager import ModelManager
from app.memory.contextual_bandit import MemoryAwareThompsonBandit
from app.memory.reward_calculator import MemoryAwareRewardCalculator, MemoryAwareRouteMetrics
from app.memory.redis_memory import ConversationMemoryCache
from app.memory.clickhouse_memory import ConversationClickHouseManager
from app.memory.summarization_service import AsyncSummarizationService, SummarizationPriority
from app.memory.routing_arms import MemoryArmManager, MEMORY_ROUTING_ARMS

logger = structlog.get_logger(__name__)


class MemoryOperationType(Enum):
    """Types of memory operations for metrics tracking"""
    CONTEXT_ASSEMBLY = "context_assembly"
    MESSAGE_STORAGE = "message_storage"
    SUMMARY_GENERATION = "summary_generation"
    SEMANTIC_SEARCH = "semantic_search"
    USER_MEMORY_UPDATE = "user_memory_update"


@dataclass
class MemoryOperationContext:
    """Context information for a memory operation"""
    session_id: str
    user_id: Optional[str]
    operation_type: MemoryOperationType
    conversation_length: int
    conversation_complexity: float
    user_tier: str
    cost_sensitivity: float
    response_urgency: str
    memory_budget_tokens: int
    target_response_time_ms: float
    existing_summary: bool = False
    cache_available: bool = True
    
    def to_context_dict(self) -> Dict[str, Any]:
        """Convert to context dict for bandit selection"""
        return {
            'conversation_length': self.conversation_length,
            'conversation_complexity': self.conversation_complexity,
            'user_tier': self.user_tier,
            'cost_sensitivity': self.cost_sensitivity,
            'response_urgency': self.response_urgency,
            'memory_budget_tokens': self.memory_budget_tokens,
            'target_response_time_ms': self.target_response_time_ms,
            'existing_summary': self.existing_summary,
            'cache_available': self.cache_available
        }


@dataclass
class AssembledContext:
    """Assembled conversation context for processing"""
    recent_messages: List[Dict[str, Any]]
    conversation_summary: Optional[str]
    relevant_facts: List[Dict[str, Any]]
    user_memory: Dict[str, Any]
    metadata: Dict[str, Any]
    total_tokens_used: int
    assembly_time_ms: float
    cache_hits: int
    cache_misses: int
    source_breakdown: Dict[str, int]  # redis, clickhouse, embedding counts
    

class BanditIntegratedMemoryOrchestrator:
    """
    Central orchestrator for conversation memory management with bandit optimization.
    
    Coordinates all memory subsystems:
    - Hot memory (Redis): Recent messages, summaries
    - Cold storage (ClickHouse): Long-term memory, analytics  
    - Background processing: Async summarization
    - Adaptive routing: Multi-armed bandit for strategy selection
    - Performance tracking: Real-time metrics and optimization
    """
    
    def __init__(
        self,
        model_manager: ModelManager,
        redis_memory: ConversationMemoryCache,
        clickhouse_memory: ConversationClickHouseManager,
        summarization_service: AsyncSummarizationService,
        bandit: Optional[MemoryAwareThompsonBandit] = None,
        reward_calculator: Optional[MemoryAwareRewardCalculator] = None
    ):
        self.model_manager = model_manager
        self.redis_memory = redis_memory 
        self.clickhouse_memory = clickhouse_memory
        self.summarization_service = summarization_service
        
        # Initialize bandit and reward calculator
        self.bandit = bandit or MemoryAwareThompsonBandit()
        self.reward_calculator = reward_calculator or MemoryAwareRewardCalculator()
        
        # Memory arm manager for configuration
        self.arm_manager = MemoryArmManager(MEMORY_ROUTING_ARMS)
        
        # Performance tracking
        self.operation_metrics = {}  # operation_id -> metrics
        self.session_contexts = {}   # session_id -> recent_context
        
        # Configuration
        self.max_recent_messages = 50
        self.default_embedding_limit = 5
        self.context_assembly_timeout_ms = 2000
        self.performance_window_hours = 24
        
        logger.info(
            "bandit_memory_orchestrator_initialized",
            bandit_arms=list(self.bandit.arms.keys()),
            reward_components=["performance", "cost", "memory", "ux", "business"]
        )
    
    async def assemble_conversation_context(
        self, 
        session_id: str,
        user_id: Optional[str] = None,
        operation_context: Optional[MemoryOperationContext] = None,
        specific_arm_id: Optional[str] = None
    ) -> Tuple[AssembledContext, str, Dict[str, Any]]:
        """
        Assemble conversation context using bandit-selected memory strategy.
        
        Args:
            session_id: Conversation session identifier
            user_id: Optional user identifier
            operation_context: Context for bandit arm selection
            specific_arm_id: Force specific arm (for testing/debugging)
            
        Returns:
            Tuple of (assembled_context, selected_arm_id, arm_config)
        """
        
        start_time = time.time()
        operation_id = f"{session_id}_{int(start_time * 1000)}"
        
        try:
            # 1. Create operation context if not provided
            if operation_context is None:
                operation_context = await self._infer_operation_context(session_id, user_id)
            
            # 2. Select memory strategy using bandit (unless forced)
            if specific_arm_id:
                selected_arm_id = specific_arm_id
                arm_config = self.arm_manager.get_memory_config(specific_arm_id, operation_context.to_context_dict())
                confidence = 1.0
            else:
                selected_arm_id, confidence, arm_config = self.bandit.select_arm_with_memory_context(
                    operation_context.to_context_dict()
                )
            
            # 3. Assemble context according to selected strategy
            assembled_context = await self._assemble_context_with_strategy(
                session_id, user_id, arm_config, operation_context
            )
            
            # 4. Track operation metrics
            assembly_time_ms = (time.time() - start_time) * 1000
            assembled_context.assembly_time_ms = assembly_time_ms
            
            self.operation_metrics[operation_id] = {
                'start_time': start_time,
                'session_id': session_id,
                'user_id': user_id,
                'selected_arm': selected_arm_id,
                'confidence': confidence,
                'arm_config': arm_config,
                'assembly_time_ms': assembly_time_ms,
                'tokens_used': assembled_context.total_tokens_used,
                'cache_performance': {
                    'hits': assembled_context.cache_hits,
                    'misses': assembled_context.cache_misses,
                    'hit_rate': assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses)
                }
            }
            
            # 5. Store session context for future operations
            self.session_contexts[session_id] = {
                'last_operation': operation_id,
                'last_arm_used': selected_arm_id,
                'last_updated': time.time(),
                'conversation_length': operation_context.conversation_length,
                'complexity': operation_context.conversation_complexity
            }
            
            logger.info(
                "context_assembled",
                session_id=session_id,
                operation_id=operation_id,
                selected_arm=selected_arm_id,
                confidence=round(confidence, 3),
                assembly_time_ms=round(assembly_time_ms, 1),
                tokens_used=assembled_context.total_tokens_used,
                cache_hit_rate=round(assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses), 3),
                strategy=arm_config.get('strategy', 'unknown')
            )
            
            return assembled_context, selected_arm_id, arm_config
            
        except Exception as e:
            logger.error(
                "context_assembly_failed",
                session_id=session_id,
                operation_id=operation_id,
                error=str(e),
                assembly_time_ms=(time.time() - start_time) * 1000
            )
            # Return minimal context as fallback
            fallback_context = AssembledContext(
                recent_messages=[],
                conversation_summary=None,
                relevant_facts=[],
                user_memory={},
                metadata={'error': str(e), 'fallback': True},
                total_tokens_used=0,
                assembly_time_ms=(time.time() - start_time) * 1000,
                cache_hits=0,
                cache_misses=1,
                source_breakdown={'error': 1}
            )
            return fallback_context, "minimal_memory", {}
    
    async def store_conversation_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        user_id: Optional[str] = None,
        trigger_summarization: bool = True
    ) -> Dict[str, Any]:
        """
        Store conversation message and potentially trigger background summarization.
        
        Args:
            session_id: Conversation session identifier
            message: Message data to store
            user_id: Optional user identifier
            trigger_summarization: Whether to queue summarization if needed
            
        Returns:
            Dict with storage results and metrics
        """
        
        start_time = time.time()
        
        try:
            # 1. Estimate message tokens
            message_tokens = self._estimate_message_tokens(message)
            
            # 2. Store in Redis with token management
            redis_result = await self.redis_memory.add_message(
                session_id, message, message_tokens
            )
            
            # 3. Update conversation metadata
            if redis_result['success']:
                await self._update_conversation_metadata(session_id, {
                    'last_message_at': str(time.time()),
                    'total_messages': str(redis_result['final_length']),
                    'total_tokens': str(redis_result['final_tokens'])
                }, user_id)
            
            # 4. Queue summarization if needed
            summarization_queued = False
            if trigger_summarization and redis_result['success']:
                should_summarize = await self._should_trigger_summarization(
                    session_id, redis_result['final_length'], redis_result['final_tokens']
                )
                
                if should_summarize:
                    priority = self._determine_summarization_priority(session_id, user_id)
                    summarization_queued = await self.summarization_service.queue_summarization(
                        session_id, user_id, priority
                    )
            
            storage_time_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                "message_stored",
                session_id=session_id,
                message_tokens=message_tokens,
                final_length=redis_result.get('final_length', 0),
                final_tokens=redis_result.get('final_tokens', 0),
                storage_time_ms=round(storage_time_ms, 1),
                summarization_queued=summarization_queued
            )
            
            return {
                'success': redis_result['success'],
                'message_tokens': message_tokens,
                'conversation_stats': {
                    'length': redis_result.get('final_length', 0),
                    'tokens': redis_result.get('final_tokens', 0),
                    'budget_utilization': redis_result.get('budget_utilization', 0.0)
                },
                'storage_time_ms': storage_time_ms,
                'summarization_queued': summarization_queued,
                'error': redis_result.get('error') if not redis_result['success'] else None
            }
            
        except Exception as e:
            logger.error(
                "message_storage_failed",
                session_id=session_id,
                error=str(e),
                storage_time_ms=(time.time() - start_time) * 1000
            )
            return {
                'success': False,
                'error': str(e),
                'storage_time_ms': (time.time() - start_time) * 1000
            }
    
    async def update_bandit_performance(
        self,
        operation_id: str,
        performance_metrics: Dict[str, Any],
        quality_assessment: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update bandit performance based on operation results.
        
        Args:
            operation_id: Operation identifier from context assembly
            performance_metrics: Performance metrics (response_time, success, etc.)
            quality_assessment: Optional quality metrics (coherence, relevance, etc.)
            
        Returns:
            Success boolean
        """
        
        try:
            # 1. Get operation context
            if operation_id not in self.operation_metrics:
                logger.warning("operation_id_not_found", operation_id=operation_id)
                return False
            
            operation_data = self.operation_metrics[operation_id]
            
            # 2. Build comprehensive metrics
            memory_metrics = MemoryAwareRouteMetrics(
                # Base metrics
                response_time_seconds=performance_metrics.get('response_time_ms', 2500) / 1000,
                success=performance_metrics.get('success', True),
                estimated_cost_usd=performance_metrics.get('cost_usd', 0.01),
                
                # Memory usage metrics
                memory_tokens_used=operation_data['tokens_used'],
                memory_retrieval_time_ms=operation_data['assembly_time_ms'],
                redis_cache_hits=operation_data['cache_performance']['hits'],
                clickhouse_queries=operation_data.get('clickhouse_queries', 0),
                embedding_searches=operation_data.get('embedding_searches', 0),
                
                # Memory effectiveness
                context_relevance_score=quality_assessment.get('context_relevance', 0.5) if quality_assessment else 0.5,
                context_utilization_rate=quality_assessment.get('context_utilization', 0.5) if quality_assessment else 0.5,
                memory_efficiency=self._calculate_memory_efficiency(operation_data, performance_metrics),
                
                # Conversation quality
                coherence_score=quality_assessment.get('coherence_score', 0.5) if quality_assessment else 0.5,
                coherence_maintained=quality_assessment.get('coherence_maintained', False) if quality_assessment else False,
                topic_continuity_score=quality_assessment.get('topic_continuity', 0.5) if quality_assessment else 0.5,
                user_satisfaction_inferred=quality_assessment.get('user_satisfaction', 0.5) if quality_assessment else 0.5,
                
                # Cost efficiency
                cost_per_quality_unit=self._calculate_cost_per_quality(performance_metrics, quality_assessment),
                memory_cost_ratio=0.3,  # Assume memory is ~30% of costs
                
                # Retrieval performance
                cache_hit_rate=operation_data['cache_performance']['hit_rate'],
                avg_retrieval_latency_ms=operation_data['assembly_time_ms'],
                
                # Budget utilization
                memory_budget_allocated=operation_data['arm_config'].get('memory_budget_tokens', 4000),
                memory_budget_used=operation_data['tokens_used'],
                memory_budget_efficiency=operation_data['tokens_used'] / max(1, operation_data['arm_config'].get('memory_budget_tokens', 4000))
            )
            
            # 3. Calculate reward
            reward_result = self.reward_calculator.calculate_memory_aware_reward(memory_metrics)
            total_reward = reward_result['total_reward']
            
            # 4. Update bandit
            context_dict = self._operation_to_context_dict(operation_data)
            memory_metrics_dict = asdict(memory_metrics)
            
            self.bandit.update_with_memory_context(
                operation_data['selected_arm'],
                total_reward,
                context_dict,
                memory_metrics_dict
            )
            
            # 5. Store quality metrics in ClickHouse
            await self.clickhouse_memory.store_conversation_quality_metrics(
                operation_data['session_id'],
                memory_metrics_dict,
                operation_data.get('user_id'),
                {
                    'arm_id': operation_data['selected_arm'],
                    'confidence': operation_data['confidence']
                }
            )
            
            # 6. Clean up operation tracking
            del self.operation_metrics[operation_id]
            
            logger.info(
                "bandit_performance_updated",
                operation_id=operation_id,
                selected_arm=operation_data['selected_arm'],
                total_reward=round(total_reward, 3),
                memory_efficiency=round(memory_metrics.memory_efficiency, 3),
                coherence_maintained=memory_metrics.coherence_maintained,
                cache_hit_rate=round(memory_metrics.cache_hit_rate, 3)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "bandit_update_failed",
                operation_id=operation_id,
                error=str(e)
            )
            return False
    
    async def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator statistics"""
        
        try:
            # 1. Bandit performance summary
            bandit_stats = self.bandit.get_performance_summary()
            
            # 2. Active operations
            active_operations = len(self.operation_metrics)
            recent_sessions = len([
                s for s in self.session_contexts.values()
                if time.time() - s['last_updated'] < 3600  # Last hour
            ])
            
            # 3. Memory subsystem health
            redis_stats = await self._get_redis_health_stats()
            clickhouse_stats = await self._get_clickhouse_health_stats()
            summarization_stats = self.summarization_service.get_service_stats()
            
            # 4. Performance metrics
            performance_summary = await self._get_performance_summary()
            
            return {
                'orchestrator_health': {
                    'active_operations': active_operations,
                    'recent_sessions': recent_sessions,
                    'uptime_hours': (time.time() - bandit_stats['bandit_stats']['start_time']) / 3600,
                    'memory_subsystems': {
                        'redis': redis_stats,
                        'clickhouse': clickhouse_stats,
                        'summarization': summarization_stats['configuration']
                    }
                },
                'bandit_performance': bandit_stats,
                'system_performance': performance_summary,
                'configuration': {
                    'max_recent_messages': self.max_recent_messages,
                    'default_embedding_limit': self.default_embedding_limit,
                    'context_assembly_timeout_ms': self.context_assembly_timeout_ms,
                    'performance_window_hours': self.performance_window_hours
                }
            }
            
        except Exception as e:
            logger.error("failed_to_get_orchestrator_stats", error=str(e))
            return {'error': str(e)}
    
    async def _assemble_context_with_strategy(
        self,
        session_id: str,
        user_id: Optional[str],
        arm_config: Dict[str, Any],
        operation_context: MemoryOperationContext
    ) -> AssembledContext:
        """Assemble context according to selected memory strategy"""
        
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        source_breakdown = {'redis': 0, 'clickhouse': 0, 'embeddings': 0}
        
        # 1. Get recent messages from Redis
        redis_result = await self.redis_memory.get_recent_messages(
            session_id, 
            limit=min(arm_config.get('max_recent_messages', self.max_recent_messages), self.max_recent_messages)
        )
        
        recent_messages = redis_result.get('messages', []) if redis_result['success'] else []
        if redis_result['success']:
            cache_hits += 1
            source_breakdown['redis'] += len(recent_messages)
        else:
            cache_misses += 1
        
        # 2. Get conversation summary (if strategy includes it)
        conversation_summary = None
        if arm_config.get('include_summary', False):
            summary_data = await self.redis_memory.get_summary(session_id)
            if summary_data:
                conversation_summary = summary_data.get('content')
                cache_hits += 1
                source_breakdown['redis'] += 1
            else:
                cache_misses += 1
        
        # 3. Get relevant facts via semantic search (if strategy includes it)
        relevant_facts = []
        if arm_config.get('semantic_search_enabled', False) and user_id:
            facts = await self._get_relevant_facts(
                session_id, user_id, recent_messages, 
                limit=arm_config.get('max_semantic_results', self.default_embedding_limit)
            )
            relevant_facts = facts
            if facts:
                cache_hits += 1
                source_breakdown['embeddings'] += len(facts)
            else:
                cache_misses += 1
        
        # 4. Get user memory (if strategy includes it)
        user_memory = {}
        if arm_config.get('include_user_memory', False) and user_id:
            memory_data = await self.clickhouse_memory.get_user_memory(user_id)
            user_memory = memory_data
            if memory_data:
                cache_hits += 1
                source_breakdown['clickhouse'] += sum(len(v) for v in memory_data.values())
            else:
                cache_misses += 1
        
        # 5. Calculate total tokens used
        total_tokens = self._calculate_total_context_tokens(
            recent_messages, conversation_summary, relevant_facts, user_memory
        )
        
        # 6. Create metadata
        metadata = {
            'strategy': arm_config.get('strategy', 'unknown'),
            'arm_id': arm_config.get('arm_id', 'unknown'),
            'budget_tokens': arm_config.get('memory_budget_tokens', 4000),
            'actual_tokens': total_tokens,
            'budget_utilization': total_tokens / max(1, arm_config.get('memory_budget_tokens', 4000)),
            'assembly_strategy': arm_config.get('assembly_strategy', 'standard'),
            'include_summary': arm_config.get('include_summary', False),
            'semantic_search_enabled': arm_config.get('semantic_search_enabled', False),
            'include_user_memory': arm_config.get('include_user_memory', False)
        }
        
        return AssembledContext(
            recent_messages=recent_messages,
            conversation_summary=conversation_summary,
            relevant_facts=relevant_facts,
            user_memory=user_memory,
            metadata=metadata,
            total_tokens_used=total_tokens,
            assembly_time_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            source_breakdown=source_breakdown
        )
    
    async def _infer_operation_context(self, session_id: str, user_id: Optional[str]) -> MemoryOperationContext:
        """Infer operation context from session data"""
        
        # Get conversation stats
        conversation_stats = await self.redis_memory.get_conversation_stats(session_id)
        conversation_length = conversation_stats.get('message_count', 0)
        
        # Simple heuristics for missing context
        conversation_complexity = min(1.0, conversation_length / 20)  # Complex after 20 messages
        user_tier = 'standard'  # Default tier
        cost_sensitivity = 0.5  # Medium sensitivity
        response_urgency = 'normal'
        memory_budget_tokens = 4000  # Default budget
        target_response_time_ms = 2500.0
        
        # Check for existing summary
        existing_summary = conversation_stats.get('has_summary', False)
        
        return MemoryOperationContext(
            session_id=session_id,
            user_id=user_id,
            operation_type=MemoryOperationType.CONTEXT_ASSEMBLY,
            conversation_length=conversation_length,
            conversation_complexity=conversation_complexity,
            user_tier=user_tier,
            cost_sensitivity=cost_sensitivity,
            response_urgency=response_urgency,
            memory_budget_tokens=memory_budget_tokens,
            target_response_time_ms=target_response_time_ms,
            existing_summary=existing_summary
        )
    
    async def _get_relevant_facts(
        self, 
        session_id: str, 
        user_id: str, 
        recent_messages: List[Dict], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get relevant facts via semantic search"""
        
        try:
            if not recent_messages:
                return []
            
            # Use the most recent user message for search
            user_messages = [msg for msg in recent_messages if msg.get('role') == 'user']
            if not user_messages:
                return []
            
            latest_message = user_messages[0]['content']
            
            # Generate embedding for search
            embedding_response = await self.model_manager.generate_embedding(
                model="sentence-transformers/all-MiniLM-L6-v2",
                text=latest_message
            )
            
            if not embedding_response or 'embedding' not in embedding_response:
                return []
            
            # Search for similar content
            similar_content = await self.clickhouse_memory.search_similar_content(
                query_embedding=embedding_response['embedding'],
                user_id=user_id,
                content_types=['preference', 'decision', 'fact'],
                min_importance=0.3,
                limit=limit
            )
            
            return similar_content
            
        except Exception as e:
            logger.error(
                "semantic_search_failed",
                session_id=session_id,
                user_id=user_id,
                error=str(e)
            )
            return []
    
    def _estimate_message_tokens(self, message: Dict[str, Any]) -> int:
        """Estimate token count for a message"""
        content = message.get('content', '')
        # Rough estimation: 1 token per 4 characters
        return max(1, len(content) // 4)
    
    def _calculate_total_context_tokens(
        self,
        messages: List[Dict],
        summary: Optional[str],
        facts: List[Dict],
        user_memory: Dict
    ) -> int:
        """Calculate total tokens used in assembled context"""
        total = 0
        
        # Messages
        for msg in messages:
            total += self._estimate_message_tokens(msg)
        
        # Summary
        if summary:
            total += len(summary) // 4
        
        # Facts
        for fact in facts:
            total += len(fact.get('content', '')) // 4
        
        # User memory
        for memory_type, entries in user_memory.items():
            for key, value in entries.items():
                total += len(str(value.get('value', ''))) // 4
        
        return total
    
    def _calculate_memory_efficiency(self, operation_data: Dict, performance_metrics: Dict) -> float:
        """Calculate memory efficiency score"""
        tokens_used = operation_data['tokens_used']
        tokens_allocated = operation_data['arm_config'].get('memory_budget_tokens', 4000)
        assembly_time = operation_data['assembly_time_ms']
        
        # Base efficiency: utilization vs time trade-off
        utilization = tokens_used / max(1, tokens_allocated)
        time_efficiency = min(1.0, 2000 / max(1, assembly_time))  # Optimal under 2s
        
        base_efficiency = (utilization * 0.6 + time_efficiency * 0.4)
        
        # Bonus for successful operation
        if performance_metrics.get('success', True):
            base_efficiency *= 1.1
        
        return min(1.0, max(0.0, base_efficiency))
    
    def _calculate_cost_per_quality(self, performance_metrics: Dict, quality_assessment: Optional[Dict]) -> float:
        """Calculate cost per quality unit"""
        cost = performance_metrics.get('cost_usd', 0.01)
        
        if quality_assessment:
            quality = quality_assessment.get('overall_quality', 0.5)
        else:
            # Use success as proxy for quality
            quality = 0.7 if performance_metrics.get('success', True) else 0.3
        
        return cost / max(0.1, quality)
    
    async def _should_trigger_summarization(self, session_id: str, message_count: int, token_count: int) -> bool:
        """Determine if summarization should be triggered"""
        # Trigger if we have enough messages and tokens
        return message_count >= 10 and token_count >= 2000
    
    def _determine_summarization_priority(self, session_id: str, user_id: Optional[str]) -> SummarizationPriority:
        """Determine summarization priority"""
        # Simple heuristic: recent sessions get higher priority
        session_context = self.session_contexts.get(session_id, {})
        last_updated = session_context.get('last_updated', 0)
        
        if time.time() - last_updated < 300:  # Last 5 minutes
            return SummarizationPriority.HIGH
        elif time.time() - last_updated < 1800:  # Last 30 minutes
            return SummarizationPriority.NORMAL
        else:
            return SummarizationPriority.LOW
    
    async def _update_conversation_metadata(self, session_id: str, updates: Dict[str, str], user_id: Optional[str]) -> None:
        """Update conversation metadata"""
        await self.redis_memory._update_conversation_metadata(session_id, updates)
    
    def _operation_to_context_dict(self, operation_data: Dict) -> Dict[str, Any]:
        """Convert operation data to context dict for bandit"""
        return {
            'conversation_length': 10,  # Default values - should be from operation_data
            'conversation_complexity': 0.5,
            'user_tier': 'standard',
            'cost_sensitivity': 0.5,
            'response_urgency': 'normal',
            'memory_budget_tokens': operation_data['arm_config'].get('memory_budget_tokens', 4000),
            'target_response_time_ms': 2500.0,
            'existing_summary': False,
            'cache_available': True
        }
    
    async def _get_redis_health_stats(self) -> Dict[str, Any]:
        """Get Redis health statistics"""
        try:
            # Simple health check
            test_key = "health_check"
            await self.redis_memory.redis.set(test_key, {"status": "ok"}, 60)
            result = await self.redis_memory.redis.get(test_key)
            return {
                'status': 'healthy' if result else 'degraded',
                'response_time_ms': 10.0  # Placeholder
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _get_clickhouse_health_stats(self) -> Dict[str, Any]:
        """Get ClickHouse health statistics"""
        try:
            if self.clickhouse_memory.connected:
                return {'status': 'healthy', 'connected': True}
            else:
                return {'status': 'disconnected', 'connected': False}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'avg_assembly_time_ms': 150.0,  # Placeholder
            'avg_cache_hit_rate': 0.75,
            'total_operations_24h': len(self.operation_metrics)
        }


# Factory functions
def create_bandit_integrated_orchestrator(
    model_manager: ModelManager,
    redis_memory: ConversationMemoryCache,
    clickhouse_memory: ConversationClickHouseManager,
    summarization_service: AsyncSummarizationService,
    **kwargs
) -> BanditIntegratedMemoryOrchestrator:
    """Create orchestrator with default configuration"""
    return BanditIntegratedMemoryOrchestrator(
        model_manager,
        redis_memory,
        clickhouse_memory,
        summarization_service,
        **kwargs
    )