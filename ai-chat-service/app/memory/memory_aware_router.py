"""
Memory-Aware Enhanced Adaptive Router.

Extends the existing EnhancedAdaptiveRouter with conversation memory integration:
- BanditIntegratedMemoryOrchestrator for context assembly
- Memory-aware routing decisions based on conversation history
- Conversation coherence tracking and optimization
- Memory budget management and cost optimization
- Real-time memory performance monitoring

This creates a unified system where routing decisions consider both
traditional factors (query complexity, user context) and conversation
memory factors (history length, coherence needs, user preferences).
"""

import time
import uuid
from typing import Any, Dict, Optional, Tuple
from dataclasses import asdict

import structlog

from app.adaptive.enhanced_router import EnhancedAdaptiveRouter
from app.cache.redis_client import CacheManager
from app.graphs.base import GraphState
from app.models.manager import ModelManager
from app.memory.bandit_orchestrator import (
    BanditIntegratedMemoryOrchestrator,
    MemoryOperationContext,
    MemoryOperationType
)
from app.memory.contextual_bandit import MemoryAwareThompsonBandit
from app.memory.reward_calculator import MemoryAwareRewardCalculator, MemoryAwareRouteMetrics
from app.memory.redis_memory import ConversationMemoryCache
from app.memory.clickhouse_memory import ConversationClickHouseManager
from app.memory.summarization_service import AsyncSummarizationService

logger = structlog.get_logger(__name__)


class MemoryAwareEnhancedRouter(EnhancedAdaptiveRouter):
    """
    Enhanced Adaptive Router with integrated conversation memory management.
    
    Combines traditional routing optimization with memory-aware features:
    - Context assembly using bandit-selected memory strategies
    - Conversation coherence maintenance across interactions
    - Memory budget optimization and cost tracking
    - User preference learning through conversation history
    - Dynamic memory strategy adaptation based on conversation characteristics
    """
    
    def __init__(
        self,
        model_manager: ModelManager,
        cache_manager: CacheManager,
        memory_orchestrator: BanditIntegratedMemoryOrchestrator,
        enable_memory_routing: bool = True,
        memory_weight_in_routing: float = 0.3,
        coherence_threshold: float = 0.6,
        **kwargs
    ):
        # Initialize base router
        super().__init__(
            model_manager=model_manager,
            cache_manager=cache_manager,
            **kwargs
        )
        
        # Memory integration components
        self.memory_orchestrator = memory_orchestrator
        self.enable_memory_routing = enable_memory_routing
        self.memory_weight_in_routing = memory_weight_in_routing
        self.coherence_threshold = coherence_threshold
        
        # Replace base bandit with memory-aware bandit if adaptive is enabled
        if self.enable_adaptive and enable_memory_routing:
            # Use memory orchestrator's bandit instead of base bandit
            self.bandit = self.memory_orchestrator.bandit
            self.reward_calculator = self.memory_orchestrator.reward_calculator
        
        # Memory-specific tracking
        self.memory_operations = {}  # request_id -> memory_operation_data
        self.conversation_coherence_scores = {}  # session_id -> coherence_score
        self.memory_cost_tracking = {
            'total_memory_operations': 0,
            'total_memory_cost_usd': 0.0,
            'avg_context_assembly_time_ms': 0.0,
        }
        
        logger.info(
            "memory_aware_router_initialized",
            enable_memory_routing=enable_memory_routing,
            memory_weight=memory_weight_in_routing,
            coherence_threshold=coherence_threshold
        )
    
    async def initialize(self):
        """Initialize the memory-aware router system"""
        # Initialize base router
        await super().initialize()
        
        # Initialize memory orchestrator's ClickHouse tables
        if hasattr(self.memory_orchestrator, 'clickhouse_memory'):
            await self.memory_orchestrator.clickhouse_memory.initialize_conversation_storage()
        
        # Start summarization workers
        if hasattr(self.memory_orchestrator, 'summarization_service'):
            await self.memory_orchestrator.summarization_service.start_workers(num_workers=2)
        
        logger.info("memory_aware_router_fully_initialized")
    
    async def route_query(self, query: str, state: GraphState) -> Any:
        """
        Memory-aware query routing that considers conversation history and context.
        
        Enhanced routing process:
        1. Assemble conversation context using memory orchestrator
        2. Determine routing strategy considering memory factors
        3. Execute routing with memory-enhanced state
        4. Update memory systems and track coherence
        """
        request_start_time = time.time()
        request_id = str(uuid.uuid4())
        session_id = getattr(state, "session_id", "unknown")
        user_id = getattr(state, "user_id", "anonymous")
        
        self.request_count += 1
        
        try:
            # 1. Assemble conversation context if memory routing is enabled
            assembled_context = None
            memory_arm_used = None
            memory_config = {}
            
            if self.enable_memory_routing:
                assembled_context, memory_arm_used, memory_config = await self._assemble_conversation_context(
                    session_id, user_id, query, state, request_id
                )
                
                # Enhance state with memory context
                state = await self._enhance_state_with_memory(state, assembled_context)
            
            # 2. Determine routing strategy (enhanced with memory factors)
            routing_strategy = await self._determine_memory_aware_routing_strategy(
                user_id, query, state, assembled_context
            )
            
            # 3. Execute routing based on strategy
            if routing_strategy == "baseline":
                result = await self._execute_baseline_route(query, state, request_id)
                routing_arm = "baseline"
            elif routing_strategy == "bandit":
                result = await self._execute_memory_aware_bandit_route(query, state, request_id, assembled_context)
                routing_arm = "bandit"
            elif routing_strategy == "control":
                result = await self._execute_control_route(query, state, request_id)
                routing_arm = "control"
            else:
                result = await self._execute_baseline_route(query, state, request_id)
                routing_arm = "baseline"
            
            # 4. Store conversation message and trigger memory updates
            if self.enable_memory_routing:
                await self._store_conversation_turn(
                    session_id, user_id, query, str(result), request_id
                )
            
            # 5. Assess conversation coherence
            coherence_score = await self._assess_conversation_coherence(
                session_id, query, str(result), assembled_context
            )
            
            # 6. Record successful completion with memory metrics
            response_time = time.time() - request_start_time
            await self._record_memory_aware_completion(
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                query=query,
                routing_arm=routing_arm,
                memory_arm_used=memory_arm_used,
                response_time=response_time,
                success=True,
                result=result,
                coherence_score=coherence_score,
                assembled_context=assembled_context
            )
            
            return result
            
        except Exception as e:
            # Record failure with memory context
            response_time = time.time() - request_start_time
            await self._record_memory_aware_completion(
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                query=query,
                routing_arm=routing_strategy,
                memory_arm_used=memory_arm_used,
                response_time=response_time,
                success=False,
                error=str(e),
                assembled_context=assembled_context
            )
            raise
    
    async def _assemble_conversation_context(
        self,
        session_id: str,
        user_id: Optional[str],
        query: str,
        state: GraphState,
        request_id: str
    ) -> Tuple[Any, str, Dict]:
        """Assemble conversation context using memory orchestrator"""
        
        # Create operation context
        operation_context = await self._create_memory_operation_context(
            session_id, user_id, query, state
        )
        
        # Use orchestrator to assemble context
        assembled_context, memory_arm_used, memory_config = await self.memory_orchestrator.assemble_conversation_context(
            session_id=session_id,
            user_id=user_id,
            operation_context=operation_context
        )
        
        # Track memory operation
        self.memory_operations[request_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'memory_arm_used': memory_arm_used,
            'memory_config': memory_config,
            'assembled_context': assembled_context,
            'operation_context': operation_context,
            'start_time': time.time()
        }
        
        # Update memory cost tracking
        self.memory_cost_tracking['total_memory_operations'] += 1
        assembly_time_ms = assembled_context.assembly_time_ms
        
        # Update running average
        total_ops = self.memory_cost_tracking['total_memory_operations']
        current_avg = self.memory_cost_tracking['avg_context_assembly_time_ms']
        self.memory_cost_tracking['avg_context_assembly_time_ms'] = (
            (current_avg * (total_ops - 1) + assembly_time_ms) / total_ops
        )
        
        logger.debug(
            "conversation_context_assembled",
            request_id=request_id,
            session_id=session_id,
            memory_arm=memory_arm_used,
            assembly_time_ms=round(assembly_time_ms, 1),
            tokens_used=assembled_context.total_tokens_used,
            cache_hit_rate=round(
                assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses), 3
            )
        )
        
        return assembled_context, memory_arm_used, memory_config
    
    async def _create_memory_operation_context(
        self,
        session_id: str,
        user_id: Optional[str],
        query: str,
        state: GraphState
    ) -> MemoryOperationContext:
        """Create memory operation context from current request"""
        
        # Get conversation stats
        conversation_stats = await self.memory_orchestrator.redis_memory.get_conversation_stats(session_id)
        conversation_length = conversation_stats.get('message_count', 0)
        
        # Calculate conversation complexity
        conversation_complexity = self._calculate_conversation_complexity(query, conversation_length)
        
        # Determine user tier and preferences (simplified)
        user_tier = getattr(state, 'user_tier', 'standard')
        cost_sensitivity = getattr(state, 'cost_sensitivity', 0.5)
        
        # Determine response urgency
        response_urgency = self._determine_response_urgency(query, conversation_length)
        
        # Set memory budget based on complexity and user tier
        memory_budget_tokens = self._calculate_memory_budget(
            conversation_complexity, user_tier, conversation_length
        )
        
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
            target_response_time_ms=2500.0,
            existing_summary=conversation_stats.get('has_summary', False)
        )
    
    def _calculate_conversation_complexity(self, query: str, conversation_length: int) -> float:
        """Calculate conversation complexity score"""
        base_complexity = self._calculate_query_complexity(query)
        
        # Adjust based on conversation length
        length_factor = min(1.0, conversation_length / 20)  # Complex after 20 messages
        
        # Combined complexity
        return min(1.0, base_complexity * 0.7 + length_factor * 0.3)
    
    def _determine_response_urgency(self, query: str, conversation_length: int) -> str:
        """Determine response urgency level"""
        urgent_keywords = ['urgent', 'emergency', 'asap', 'quickly', 'fast']
        normal_keywords = ['please', 'when you can', 'help']
        
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in urgent_keywords):
            return 'urgent'
        elif conversation_length > 15:  # Long conversations may need quick responses
            return 'high'
        elif any(keyword in query_lower for keyword in normal_keywords):
            return 'normal'
        else:
            return 'low'
    
    def _calculate_memory_budget(self, complexity: float, user_tier: str, conversation_length: int) -> int:
        """Calculate memory budget based on context"""
        base_budgets = {
            'free': 2000,
            'standard': 4000,
            'pro': 8000,
            'enterprise': 12000
        }
        
        base_budget = base_budgets.get(user_tier, 4000)
        
        # Adjust based on complexity
        complexity_multiplier = 1.0 + (complexity * 0.5)
        
        # Adjust based on conversation length
        length_multiplier = 1.0 + min(0.5, conversation_length / 30)
        
        final_budget = base_budget * complexity_multiplier * length_multiplier
        return int(min(16000, final_budget))  # Cap at 16k tokens
    
    async def _enhance_state_with_memory(self, state: GraphState, assembled_context) -> GraphState:
        """Enhance GraphState with assembled memory context"""
        if not assembled_context:
            return state
        
        # Add memory context to state
        state.conversation_context = {
            'recent_messages': assembled_context.recent_messages,
            'conversation_summary': assembled_context.conversation_summary,
            'relevant_facts': assembled_context.relevant_facts,
            'user_memory': assembled_context.user_memory,
            'metadata': assembled_context.metadata
        }
        
        # Add memory statistics for routing decisions
        state.memory_stats = {
            'total_tokens_used': assembled_context.total_tokens_used,
            'cache_hit_rate': assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses),
            'assembly_time_ms': assembled_context.assembly_time_ms,
            'memory_strategy': assembled_context.metadata.get('strategy', 'unknown')
        }
        
        return state
    
    async def _determine_memory_aware_routing_strategy(
        self,
        user_id: str,
        query: str,
        state: GraphState,
        assembled_context
    ) -> str:
        """Determine routing strategy considering memory factors"""
        
        # Start with base routing strategy
        base_strategy = await super()._determine_routing_strategy(user_id, state)
        
        # If memory routing is disabled, return base strategy
        if not self.enable_memory_routing:
            return base_strategy
        
        # Memory-specific routing adjustments
        memory_factors = self._calculate_memory_routing_factors(assembled_context, state)
        
        # Apply memory weight to routing decision
        if memory_factors['should_prefer_bandit']:
            # Override to bandit if memory factors strongly suggest it
            if memory_factors['memory_confidence'] > 0.8:
                return "bandit"
        
        # Return base strategy with memory considerations logged
        logger.debug(
            "memory_aware_routing_decision",
            base_strategy=base_strategy,
            memory_factors=memory_factors,
            final_strategy=base_strategy
        )
        
        return base_strategy
    
    def _calculate_memory_routing_factors(self, assembled_context, state: GraphState) -> Dict[str, Any]:
        """Calculate memory-specific routing factors"""
        factors = {
            'should_prefer_bandit': False,
            'memory_confidence': 0.5,
            'coherence_importance': 0.5,
            'context_richness': 0.5
        }
        
        if not assembled_context:
            return factors
        
        # Context richness
        total_tokens = assembled_context.total_tokens_used
        if total_tokens > 2000:  # Rich context available
            factors['context_richness'] = 0.8
            factors['should_prefer_bandit'] = True
        elif total_tokens > 1000:
            factors['context_richness'] = 0.6
        
        # Cache performance
        cache_hit_rate = assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses)
        if cache_hit_rate > 0.7:  # Good cache performance
            factors['memory_confidence'] = 0.8
        
        # Assembly performance
        if assembled_context.assembly_time_ms < 500:  # Fast assembly
            factors['memory_confidence'] += 0.1
        
        # Strategy-specific confidence
        strategy = assembled_context.metadata.get('strategy', 'unknown')
        if strategy in ['deep_context', 'enterprise_comprehensive']:
            factors['coherence_importance'] = 0.9
            factors['should_prefer_bandit'] = True
        
        return factors
    
    async def _execute_memory_aware_bandit_route(
        self,
        query: str,
        state: GraphState,
        request_id: str,
        assembled_context
    ) -> Any:
        """Execute bandit routing with memory awareness"""
        
        if not self.enable_adaptive:
            return await self._execute_baseline_route(query, state, request_id)
        
        # Enhanced context extraction with memory factors
        context = self._extract_memory_aware_routing_context(query, state, assembled_context)
        
        # Use memory-aware bandit for arm selection
        if hasattr(self.bandit, 'select_arm_with_memory_context'):
            selected_arm, confidence = self.bandit.select_arm_with_memory_context(context)
        else:
            # Fallback to standard bandit
            selected_arm, confidence = self.bandit.select_arm(context)
        
        # Record bandit decision with memory context
        if hasattr(self, 'monitor'):
            self.monitor.record_bandit_decision(selected_arm, confidence, context)
        
        # Execute selected route
        route_function = self._get_route_function(selected_arm)
        result = await route_function(state)
        
        logger.debug(
            "memory_aware_bandit_route_executed",
            request_id=request_id,
            selected_arm=selected_arm,
            confidence=round(confidence, 3),
            memory_strategy=assembled_context.metadata.get('strategy', 'unknown') if assembled_context else 'none',
            context_tokens=assembled_context.total_tokens_used if assembled_context else 0
        )
        
        return result
    
    def _extract_memory_aware_routing_context(self, query: str, state: GraphState, assembled_context) -> Dict[str, Any]:
        """Extract routing context enhanced with memory information"""
        
        # Start with base context
        context = super()._extract_routing_context(query, state)
        
        # Add memory-specific context
        if assembled_context and self.enable_memory_routing:
            context.update({
                # Memory context factors
                'conversation_length': len(assembled_context.recent_messages),
                'has_summary': assembled_context.conversation_summary is not None,
                'relevant_facts_count': len(assembled_context.relevant_facts),
                'user_memory_entries': sum(len(entries) for entries in assembled_context.user_memory.values()),
                'total_context_tokens': assembled_context.total_tokens_used,
                
                # Memory performance factors
                'cache_hit_rate': assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses),
                'assembly_time_ms': assembled_context.assembly_time_ms,
                'memory_strategy': assembled_context.metadata.get('strategy', 'unknown'),
                
                # Budget utilization
                'memory_budget_utilization': assembled_context.metadata.get('budget_utilization', 0.0),
                
                # Context richness indicators
                'has_rich_context': assembled_context.total_tokens_used > 2000,
                'context_diversity_score': len(assembled_context.source_breakdown),
            })
            
            # Add coherence context if available
            session_id = getattr(state, 'session_id', 'unknown')
            if session_id in self.conversation_coherence_scores:
                context['previous_coherence_score'] = self.conversation_coherence_scores[session_id]
        
        return context
    
    async def _store_conversation_turn(
        self,
        session_id: str,
        user_id: Optional[str],
        user_message: str,
        assistant_response: str,
        request_id: str
    ) -> None:
        """Store conversation turn in memory systems"""
        
        try:
            # Store user message
            user_msg = {
                'role': 'user',
                'content': user_message,
                'timestamp': time.time(),
                'request_id': request_id
            }
            
            await self.memory_orchestrator.store_conversation_message(
                session_id=session_id,
                message=user_msg,
                user_id=user_id,
                trigger_summarization=True
            )
            
            # Store assistant response
            assistant_msg = {
                'role': 'assistant',
                'content': assistant_response,
                'timestamp': time.time(),
                'request_id': request_id
            }
            
            await self.memory_orchestrator.store_conversation_message(
                session_id=session_id,
                message=assistant_msg,
                user_id=user_id,
                trigger_summarization=False  # Don't trigger twice
            )
            
        except Exception as e:
            logger.error(
                "failed_to_store_conversation_turn",
                session_id=session_id,
                request_id=request_id,
                error=str(e)
            )
    
    async def _assess_conversation_coherence(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        assembled_context
    ) -> float:
        """Assess conversation coherence for this turn"""
        
        try:
            # Simple coherence assessment based on context utilization
            coherence_score = 0.5  # Base score
            
            if assembled_context:
                # Bonus for using recent context
                if assembled_context.recent_messages and len(assembled_context.recent_messages) > 0:
                    coherence_score += 0.2
                
                # Bonus for using summary
                if assembled_context.conversation_summary:
                    coherence_score += 0.15
                
                # Bonus for using relevant facts
                if assembled_context.relevant_facts:
                    coherence_score += 0.1
                
                # Bonus for good cache performance
                cache_hit_rate = assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses)
                if cache_hit_rate > 0.7:
                    coherence_score += 0.05
            
            # Simple content coherence check
            if any(word in assistant_response.lower() for word in ['however', 'but', 'although', 'nevertheless']):
                coherence_score += 0.05  # Bonus for transition words
            
            # Store coherence score for session
            coherence_score = max(0.0, min(1.0, coherence_score))
            self.conversation_coherence_scores[session_id] = coherence_score
            
            return coherence_score
            
        except Exception as e:
            logger.error(
                "coherence_assessment_failed",
                session_id=session_id,
                error=str(e)
            )
            return 0.5  # Default moderate coherence
    
    async def _record_memory_aware_completion(
        self,
        request_id: str,
        session_id: str,
        user_id: str,
        query: str,
        routing_arm: str,
        memory_arm_used: Optional[str],
        response_time: float,
        success: bool,
        result: Any = None,
        error: str = None,
        coherence_score: float = 0.5,
        assembled_context = None
    ) -> None:
        """Record completion with comprehensive memory metrics"""
        
        # Call parent method for base recording
        await super()._record_request_completion(
            request_id=request_id,
            user_id=user_id,
            query=query,
            routing_arm=routing_arm,
            response_time=response_time,
            success=success,
            result=result,
            error=error
        )
        
        # Additional memory-specific recording
        if self.enable_memory_routing and request_id in self.memory_operations:
            memory_operation = self.memory_operations[request_id]
            
            # Build comprehensive memory metrics
            memory_metrics = self._build_memory_metrics(
                memory_operation, response_time, success, coherence_score, assembled_context
            )
            
            # Update memory orchestrator's bandit
            operation_id = f"{session_id}_{int(memory_operation['start_time'] * 1000)}"
            
            performance_metrics = {
                'response_time_ms': response_time * 1000,
                'success': success,
                'cost_usd': self._estimate_request_cost(routing_arm, query, success)
            }
            
            quality_assessment = {
                'coherence_score': coherence_score,
                'coherence_maintained': coherence_score >= self.coherence_threshold,
                'context_relevance': 0.7,  # Would need more sophisticated assessment
                'context_utilization': self._calculate_context_utilization(assembled_context),
                'user_satisfaction': 0.75 if success else 0.25,
                'overall_quality': coherence_score * 0.4 + (0.75 if success else 0.25) * 0.6
            }
            
            await self.memory_orchestrator.update_bandit_performance(
                operation_id, performance_metrics, quality_assessment
            )
            
            # Update memory cost tracking
            memory_cost = self._estimate_memory_cost(memory_operation, response_time)
            self.memory_cost_tracking['total_memory_cost_usd'] += memory_cost
            
            # Clean up operation tracking
            del self.memory_operations[request_id]
            
            logger.info(
                "memory_aware_completion_recorded",
                request_id=request_id,
                session_id=session_id,
                routing_arm=routing_arm,
                memory_arm=memory_arm_used,
                coherence_score=round(coherence_score, 3),
                coherence_maintained=coherence_score >= self.coherence_threshold,
                memory_cost_usd=round(memory_cost, 4),
                success=success
            )
    
    def _build_memory_metrics(
        self, 
        memory_operation: Dict, 
        response_time: float, 
        success: bool, 
        coherence_score: float,
        assembled_context
    ) -> Dict[str, Any]:
        """Build comprehensive memory metrics"""
        
        base_metrics = {
            'memory_arm_used': memory_operation['memory_arm_used'],
            'memory_strategy': memory_operation['memory_config'].get('strategy', 'unknown'),
            'response_time_ms': response_time * 1000,
            'success': success,
            'coherence_score': coherence_score,
            'coherence_maintained': coherence_score >= self.coherence_threshold
        }
        
        if assembled_context:
            base_metrics.update({
                'context_assembly_time_ms': assembled_context.assembly_time_ms,
                'total_tokens_used': assembled_context.total_tokens_used,
                'cache_hit_rate': assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses),
                'memory_efficiency': self._calculate_memory_efficiency(assembled_context, memory_operation),
                'context_utilization_rate': self._calculate_context_utilization(assembled_context)
            })
        
        return base_metrics
    
    def _calculate_memory_efficiency(self, assembled_context, memory_operation: Dict) -> float:
        """Calculate memory efficiency score"""
        if not assembled_context:
            return 0.5
        
        # Token efficiency
        tokens_used = assembled_context.total_tokens_used
        tokens_allocated = memory_operation['memory_config'].get('memory_budget_tokens', 4000)
        token_efficiency = min(1.0, tokens_used / max(1, tokens_allocated))
        
        # Time efficiency
        assembly_time = assembled_context.assembly_time_ms
        time_efficiency = min(1.0, 1000 / max(100, assembly_time))  # Optimal under 1s
        
        # Cache efficiency
        cache_hit_rate = assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses)
        
        # Combined efficiency
        efficiency = (token_efficiency * 0.4 + time_efficiency * 0.4 + cache_hit_rate * 0.2)
        return max(0.0, min(1.0, efficiency))
    
    def _calculate_context_utilization(self, assembled_context) -> float:
        """Calculate how well the assembled context was utilized"""
        if not assembled_context:
            return 0.0
        
        # Simple heuristic: assume good utilization if we have diverse sources
        source_count = len(assembled_context.source_breakdown)
        utilization = min(1.0, source_count / 3)  # Optimal with 3+ sources
        
        return utilization
    
    def _estimate_memory_cost(self, memory_operation: Dict, response_time: float) -> float:
        """Estimate cost of memory operations"""
        base_cost = 0.0005  # Base cost per memory operation
        
        # Add cost based on context assembly time
        assembly_time_ms = memory_operation.get('assembled_context', {}).get('assembly_time_ms', 0)
        time_cost = (assembly_time_ms / 1000) * 0.0001  # $0.0001 per second
        
        # Add cost based on tokens used
        tokens_used = memory_operation.get('assembled_context', {}).get('total_tokens_used', 0)
        token_cost = tokens_used * 0.000001  # $0.000001 per token
        
        return base_cost + time_cost + token_cost
    
    def get_memory_aware_status(self) -> Dict[str, Any]:
        """Get comprehensive status including memory metrics"""
        
        # Get base status
        base_status = super().get_comprehensive_status()
        
        # Add memory-specific status
        memory_status = {
            'memory_integration': {
                'enabled': self.enable_memory_routing,
                'memory_weight_in_routing': self.memory_weight_in_routing,
                'coherence_threshold': self.coherence_threshold,
                'active_memory_operations': len(self.memory_operations)
            },
            'memory_performance': self.memory_cost_tracking.copy(),
            'conversation_coherence': {
                'active_conversations': len(self.conversation_coherence_scores),
                'avg_coherence_score': sum(self.conversation_coherence_scores.values()) / max(1, len(self.conversation_coherence_scores)),
                'high_coherence_sessions': sum(1 for score in self.conversation_coherence_scores.values() if score >= self.coherence_threshold)
            }
        }
        
        # Add orchestrator status (non-async fallback)
        if hasattr(self.memory_orchestrator, 'get_orchestrator_stats'):
            try:
                # Try to get non-async version or create basic stats
                if hasattr(self.memory_orchestrator, 'get_basic_stats'):
                    memory_status['orchestrator'] = self.memory_orchestrator.get_basic_stats()
                else:
                    memory_status['orchestrator'] = {
                        'status': 'available',
                        'note': 'detailed stats require async call'
                    }
            except Exception as e:
                memory_status['orchestrator'] = {'error': str(e)}
        
        # Merge with base status
        base_status['memory_aware_features'] = memory_status
        
        return base_status


# Factory function
async def create_memory_aware_router(
    model_manager: ModelManager,
    cache_manager: CacheManager,
    memory_orchestrator: BanditIntegratedMemoryOrchestrator,
    enable_memory_routing: bool = True,
    memory_weight_in_routing: float = 0.3,
    coherence_threshold: float = 0.6,
    **kwargs
) -> MemoryAwareEnhancedRouter:
    """Create and initialize memory-aware enhanced router"""
    
    router = MemoryAwareEnhancedRouter(
        model_manager=model_manager,
        cache_manager=cache_manager,
        memory_orchestrator=memory_orchestrator,
        enable_memory_routing=enable_memory_routing,
        memory_weight_in_routing=memory_weight_in_routing,
        coherence_threshold=coherence_threshold,
        **kwargs
    )
    
    await router.initialize()
    return router