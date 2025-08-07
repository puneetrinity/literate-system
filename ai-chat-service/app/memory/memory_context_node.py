"""
Memory-Enhanced ContextManagerNode.

Replaces the basic ContextManagerNode with a memory-aware version that:
- Integrates with BanditIntegratedMemoryOrchestrator for context assembly
- Provides rich conversation context from Redis and ClickHouse
- Tracks conversation coherence and memory effectiveness
- Supports dynamic memory strategy selection based on conversation characteristics

This node can be used as a drop-in replacement for the existing ContextManagerNode
in the chat graph while providing significantly enhanced memory capabilities.
"""

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import structlog

from app.graphs.base import BaseGraphNode, GraphState, NodeResult, NodeType
from app.memory.bandit_orchestrator import (
    BanditIntegratedMemoryOrchestrator,
    MemoryOperationContext,
    MemoryOperationType
)

logger = structlog.get_logger(__name__)


@dataclass
class EnhancedConversationContext:
    """
    Enhanced conversation context with memory-aware features.
    
    Extends the basic ConversationContext with rich memory information:
    - Recent conversation history with token management
    - Conversation summaries for long-term context
    - User preferences and learned patterns
    - Semantic search results for relevant facts
    - Memory performance metrics
    """
    
    # Basic context (compatible with existing ConversationContext)
    user_name: Optional[str] = None
    conversation_topic: Optional[str] = None
    user_expertise_level: str = "intermediate"
    preferred_response_style: str = "balanced"
    conversation_mood: str = "neutral"
    key_entities: List[str] = None
    previous_topics: List[str] = None
    
    # Memory-enhanced context
    recent_messages: List[Dict[str, Any]] = None
    conversation_summary: Optional[str] = None
    relevant_facts: List[Dict[str, Any]] = None
    user_memory: Dict[str, Any] = None
    
    # Memory metadata
    memory_strategy_used: str = "unknown"
    total_context_tokens: int = 0
    context_assembly_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    memory_budget_utilization: float = 0.0
    
    # Conversation analytics
    conversation_length: int = 0
    conversation_complexity: float = 0.5
    coherence_score: float = 0.5
    memory_arm_confidence: float = 0.5
    
    # Source breakdown
    context_sources: Dict[str, int] = None  # redis, clickhouse, embeddings counts
    
    def __post_init__(self):
        if self.key_entities is None:
            self.key_entities = []
        if self.previous_topics is None:
            self.previous_topics = []
        if self.recent_messages is None:
            self.recent_messages = []
        if self.relevant_facts is None:
            self.relevant_facts = []
        if self.user_memory is None:
            self.user_memory = {}
        if self.context_sources is None:
            self.context_sources = {}
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy ConversationContext format for backward compatibility"""
        return {
            'user_name': self.user_name,
            'conversation_topic': self.conversation_topic,
            'user_expertise_level': self.user_expertise_level,
            'preferred_response_style': self.preferred_response_style,
            'conversation_mood': self.conversation_mood,
            'key_entities': self.key_entities,
            'previous_topics': self.previous_topics
        }


class MemoryEnhancedContextManagerNode(BaseGraphNode):
    """
    Memory-enhanced context manager node for conversation graphs.
    
    Provides intelligent conversation context assembly using the memory orchestrator:
    - Adaptive memory strategy selection via multi-armed bandit
    - Token-aware context window management
    - Conversation coherence tracking
    - User preference learning
    - Real-time performance optimization
    
    Can be used as a drop-in replacement for the basic ContextManagerNode.
    """
    
    def __init__(
        self,
        memory_orchestrator: BanditIntegratedMemoryOrchestrator,
        cache_manager=None,
        enable_memory_features: bool = True,
        fallback_to_basic: bool = True
    ):
        super().__init__("memory_context_manager", NodeType.PROCESSING)
        
        self.memory_orchestrator = memory_orchestrator
        self.cache_manager = cache_manager  # For backward compatibility
        self.enable_memory_features = enable_memory_features
        self.fallback_to_basic = fallback_to_basic
        
        # Performance tracking
        self.execution_stats = {
            'total_executions': 0,
            'memory_enabled_executions': 0,
            'fallback_executions': 0,
            'avg_execution_time_ms': 0.0,
            'avg_context_tokens': 0.0
        }
        
        logger.info(
            "memory_context_manager_initialized",
            enable_memory_features=enable_memory_features,
            fallback_to_basic=fallback_to_basic
        )
    
    async def execute(self, state: GraphState, **kwargs) -> NodeResult:
        """
        Execute memory-enhanced context management.
        
        Attempts to use memory orchestrator for rich context assembly,
        with fallback to basic context management if needed.
        """
        start_time = time.time()
        correlation_id = getattr(state, 'query_id', None)
        session_id = getattr(state, 'session_id', 'unknown')
        user_id = getattr(state, 'user_id', None)
        
        self.execution_stats['total_executions'] += 1
        
        logger.debug(
            "memory_context_manager_enter",
            correlation_id=correlation_id,
            session_id=session_id,
            enable_memory_features=self.enable_memory_features
        )
        
        try:
            # Try memory-enhanced context assembly
            if self.enable_memory_features:
                try:
                    enhanced_context = await self._execute_memory_enhanced(
                        state, session_id, user_id, correlation_id
                    )
                    
                    self.execution_stats['memory_enabled_executions'] += 1
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Update running averages
                    self._update_execution_stats(execution_time_ms, enhanced_context.total_context_tokens)
                    
                    # Store context in state (both enhanced and legacy formats)
                    state.processed_query = state.original_query
                    state.intermediate_results["conversation_context"] = enhanced_context.to_legacy_format()
                    state.intermediate_results["enhanced_conversation_context"] = asdict(enhanced_context)
                    
                    logger.info(
                        "memory_context_manager_success",
                        correlation_id=correlation_id,
                        session_id=session_id,
                        memory_strategy=enhanced_context.memory_strategy_used,
                        context_tokens=enhanced_context.total_context_tokens,
                        cache_hit_rate=round(enhanced_context.cache_hit_rate, 3),
                        execution_time_ms=round(execution_time_ms, 1)
                    )
                    
                    return NodeResult(
                        success=True,
                        data={
                            "context": enhanced_context.to_legacy_format(),
                            "enhanced_context": asdict(enhanced_context),
                            "memory_metadata": {
                                "strategy": enhanced_context.memory_strategy_used,
                                "tokens_used": enhanced_context.total_context_tokens,
                                "cache_hit_rate": enhanced_context.cache_hit_rate,
                                "coherence_score": enhanced_context.coherence_score
                            }
                        },
                        confidence=enhanced_context.memory_arm_confidence,
                        execution_time=execution_time_ms / 1000
                    )
                    
                except Exception as memory_error:
                    logger.error(
                        "memory_context_assembly_failed",
                        correlation_id=correlation_id,
                        session_id=session_id,
                        error=str(memory_error)
                    )
                    
                    # Fall back to basic context if enabled
                    if not self.fallback_to_basic:
                        raise memory_error
            
            # Basic context management (fallback or when memory features disabled)
            basic_context = await self._execute_basic_context(state, correlation_id)
            
            self.execution_stats['fallback_executions'] += 1
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update stats
            self._update_execution_stats(execution_time_ms, 0)
            
            # Store context in state
            state.processed_query = state.original_query
            state.intermediate_results["conversation_context"] = basic_context
            
            logger.debug(
                "memory_context_manager_fallback_success",
                correlation_id=correlation_id,
                session_id=session_id,
                execution_time_ms=round(execution_time_ms, 1)
            )
            
            return NodeResult(
                success=True,
                data={"context": basic_context},
                confidence=0.6,  # Lower confidence for basic context
                execution_time=execution_time_ms / 1000
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "memory_context_manager_failed",
                correlation_id=correlation_id,
                session_id=session_id,
                error=str(e),
                execution_time_ms=round(execution_time_ms, 1)
            )
            
            return NodeResult(
                success=False,
                error=f"Context management failed: {str(e)}",
                execution_time=execution_time_ms / 1000
            )
    
    async def _execute_memory_enhanced(
        self,
        state: GraphState,
        session_id: str,
        user_id: Optional[str],
        correlation_id: Optional[str]
    ) -> EnhancedConversationContext:
        """Execute memory-enhanced context assembly"""
        
        # Create memory operation context
        operation_context = await self._create_memory_operation_context(
            state, session_id, user_id
        )
        
        # Assemble conversation context using orchestrator
        assembled_context, memory_arm_used, memory_config = await self.memory_orchestrator.assemble_conversation_context(
            session_id=session_id,
            user_id=user_id,
            operation_context=operation_context
        )
        
        # Analyze conversation history for basic context inference
        basic_context = await self._analyze_conversation_history(assembled_context.recent_messages)
        
        # Extract key entities and topics from recent messages and facts
        key_entities, previous_topics = self._extract_entities_and_topics(
            assembled_context.recent_messages,
            assembled_context.relevant_facts,
            assembled_context.conversation_summary
        )
        
        # Calculate coherence score
        coherence_score = await self._calculate_coherence_score(
            assembled_context, state.original_query
        )
        
        # Build enhanced context
        enhanced_context = EnhancedConversationContext(
            # Basic context
            user_name=basic_context.get('user_name'),
            conversation_topic=basic_context.get('conversation_topic'),
            user_expertise_level=basic_context.get('user_expertise_level', 'intermediate'),
            preferred_response_style=basic_context.get('preferred_response_style', 'balanced'),
            conversation_mood=basic_context.get('conversation_mood', 'neutral'),
            key_entities=key_entities,
            previous_topics=previous_topics,
            
            # Memory-enhanced context
            recent_messages=assembled_context.recent_messages,
            conversation_summary=assembled_context.conversation_summary,
            relevant_facts=assembled_context.relevant_facts,
            user_memory=assembled_context.user_memory,
            
            # Memory metadata
            memory_strategy_used=memory_config.get('strategy', 'unknown'),
            total_context_tokens=assembled_context.total_tokens_used,
            context_assembly_time_ms=assembled_context.assembly_time_ms,
            cache_hit_rate=assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses),
            memory_budget_utilization=assembled_context.metadata.get('budget_utilization', 0.0),
            
            # Conversation analytics
            conversation_length=operation_context.conversation_length,
            conversation_complexity=operation_context.conversation_complexity,
            coherence_score=coherence_score,
            memory_arm_confidence=0.8,  # Would get from actual bandit selection
            
            # Source breakdown
            context_sources=assembled_context.source_breakdown
        )
        
        return enhanced_context
    
    async def _create_memory_operation_context(
        self,
        state: GraphState,
        session_id: str,
        user_id: Optional[str]
    ) -> MemoryOperationContext:
        """Create memory operation context from graph state"""
        
        # Get basic conversation stats
        conversation_stats = await self.memory_orchestrator.redis_memory.get_conversation_stats(session_id)
        conversation_length = conversation_stats.get('message_count', 0)
        
        # Calculate query complexity
        query = state.original_query
        query_complexity = self._calculate_query_complexity(query)
        conversation_complexity = min(1.0, query_complexity * 0.7 + (conversation_length / 20) * 0.3)
        
        # Extract context from state
        user_tier = getattr(state, 'user_tier', 'standard')
        cost_sensitivity = getattr(state, 'cost_sensitivity', 0.5)
        
        # Determine response urgency
        response_urgency = self._determine_response_urgency(query, conversation_length)
        
        # Calculate memory budget
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
    
    async def _analyze_conversation_history(self, recent_messages: List[Dict]) -> Dict[str, Any]:
        """Analyze recent messages for basic context inference"""
        
        basic_context = {
            'user_expertise_level': 'intermediate',
            'preferred_response_style': 'balanced',
            'conversation_mood': 'neutral',
            'conversation_topic': None,
            'user_name': None
        }
        
        if not recent_messages:
            return basic_context
        
        # Analyze expertise level
        basic_context['user_expertise_level'] = self._infer_expertise_level(recent_messages)
        
        # Analyze response style preference
        basic_context['preferred_response_style'] = self._infer_response_style(recent_messages)
        
        # Analyze conversation mood
        basic_context['conversation_mood'] = self._infer_conversation_mood(recent_messages)
        
        # Extract topic if possible
        basic_context['conversation_topic'] = self._extract_conversation_topic(recent_messages)
        
        return basic_context
    
    def _infer_expertise_level(self, messages: List[Dict]) -> str:
        """Infer user expertise level from messages"""
        technical_terms = 0
        total_words = 0
        
        for msg in messages[-5:]:  # Last 5 messages
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                words = content.split()
                total_words += len(words)
                
                # Count technical indicators
                for word in words:
                    if (len(word) > 8 or 
                        word in ['algorithm', 'implementation', 'architecture', 'methodology',
                               'optimization', 'configuration', 'integration', 'deployment']):
                        technical_terms += 1
        
        if total_words == 0:
            return 'intermediate'
        
        ratio = technical_terms / total_words
        if ratio > 0.1:
            return 'expert'
        elif ratio > 0.05:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _infer_response_style(self, messages: List[Dict]) -> str:
        """Infer preferred response style"""
        # Look for style indicators in recent messages
        for msg in messages[-3:]:
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                
                if any(word in content for word in ['detailed', 'comprehensive', 'thorough']):
                    return 'detailed'
                elif any(word in content for word in ['brief', 'short', 'quick', 'concise']):
                    return 'concise'
        
        return 'balanced'
    
    def _infer_conversation_mood(self, messages: List[Dict]) -> str:
        """Infer conversation mood"""
        # Simple mood detection
        for msg in messages[-2:]:
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                
                if any(word in content for word in ['please', 'thank', 'appreciate']):
                    return 'professional'
                elif any(word in content for word in ['hey', 'hi', 'cool', 'awesome']):
                    return 'casual'
        
        return 'neutral'
    
    def _extract_conversation_topic(self, messages: List[Dict]) -> Optional[str]:
        """Extract main conversation topic"""
        # Simple topic extraction from recent messages
        topics = []
        
        for msg in messages[-3:]:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Very simple topic extraction - could be enhanced with NLP
                if len(content) > 20:
                    topics.append(content[:50] + "..." if len(content) > 50 else content)
        
        return topics[0] if topics else None
    
    def _extract_entities_and_topics(
        self,
        recent_messages: List[Dict],
        relevant_facts: List[Dict],
        conversation_summary: Optional[str]
    ) -> tuple[List[str], List[str]]:
        """Extract key entities and topics from conversation content"""
        
        entities = set()
        topics = set()
        
        # Extract from recent messages
        for msg in recent_messages[-5:]:
            content = msg.get('content', '').lower()
            words = content.split()
            
            # Simple entity extraction (capitalized words, proper nouns)
            for word in words:
                if len(word) > 3 and word.istitle():
                    entities.add(word)
        
        # Extract from relevant facts
        for fact in relevant_facts[:3]:
            content = fact.get('content', '').lower()
            # Extract content type as topic
            content_type = fact.get('content_type', '')
            if content_type:
                topics.add(content_type)
        
        # Extract from summary
        if conversation_summary:
            # Simple topic extraction from summary
            summary_topics = ['discussion', 'conversation', 'topic']  # Placeholder
            topics.update(summary_topics)
        
        return list(entities)[:10], list(topics)[:5]  # Limit sizes
    
    async def _calculate_coherence_score(
        self,
        assembled_context,
        current_query: str
    ) -> float:
        """Calculate conversation coherence score"""
        
        coherence_score = 0.5  # Base score
        
        # Bonus for having recent context
        if assembled_context.recent_messages:
            coherence_score += 0.1
        
        # Bonus for having summary
        if assembled_context.conversation_summary:
            coherence_score += 0.15
        
        # Bonus for relevant facts
        if assembled_context.relevant_facts:
            coherence_score += 0.1
        
        # Bonus for good cache performance
        cache_hit_rate = assembled_context.cache_hits / max(1, assembled_context.cache_hits + assembled_context.cache_misses)
        if cache_hit_rate > 0.7:
            coherence_score += 0.05
        
        # Bonus for context utilization
        if assembled_context.total_tokens_used > 1000:
            coherence_score += 0.1
        
        # Simple content relevance check
        query_words = set(current_query.lower().split())
        context_words = set()
        
        for msg in assembled_context.recent_messages[-2:]:
            context_words.update(msg.get('content', '').lower().split())
        
        if query_words & context_words:  # Common words
            coherence_score += 0.05
        
        return max(0.0, min(1.0, coherence_score))
    
    async def _execute_basic_context(
        self,
        state: GraphState,
        correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute basic context management (fallback)"""
        
        basic_context = {
            'user_name': None,
            'conversation_topic': None,
            'user_expertise_level': 'intermediate',
            'preferred_response_style': 'balanced',
            'conversation_mood': 'neutral',
            'key_entities': [],
            'previous_topics': []
        }
        
        # Analyze conversation history if available
        if hasattr(state, 'conversation_history') and state.conversation_history:
            # Basic analysis using existing methods
            basic_context['user_expertise_level'] = self._infer_expertise_level(state.conversation_history)
            basic_context['preferred_response_style'] = self._infer_response_style(state.conversation_history)
            basic_context['conversation_mood'] = self._infer_conversation_mood(state.conversation_history)
        
        return basic_context
    
    def _calculate_query_complexity(self, query: str) -> float:
        """Calculate query complexity score"""
        factors = []
        
        # Length factor
        factors.append(min(1.0, len(query) / 200))
        
        # Word count factor
        factors.append(min(1.0, len(query.split()) / 30))
        
        # Question words factor
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
        question_count = sum(1 for word in question_words if word in query.lower())
        factors.append(min(1.0, question_count / 3))
        
        # Technical complexity
        technical_words = ['implement', 'configure', 'optimize', 'analyze', 'debug']
        tech_count = sum(1 for word in technical_words if word in query.lower())
        factors.append(min(1.0, tech_count / 2))
        
        return sum(factors) / len(factors)
    
    def _determine_response_urgency(self, query: str, conversation_length: int) -> str:
        """Determine response urgency level"""
        urgent_keywords = ['urgent', 'emergency', 'asap', 'quickly', 'fast']
        
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in urgent_keywords):
            return 'urgent'
        elif conversation_length > 15:  # Long conversations may need quick responses
            return 'high'
        else:
            return 'normal'
    
    def _calculate_memory_budget(self, complexity: float, user_tier: str, conversation_length: int) -> int:
        """Calculate memory budget based on context"""
        base_budgets = {
            'free': 2000,
            'standard': 4000,
            'pro': 8000,
            'enterprise': 12000
        }
        
        base_budget = base_budgets.get(user_tier, 4000)
        
        # Adjust based on complexity and length
        complexity_multiplier = 1.0 + (complexity * 0.5)
        length_multiplier = 1.0 + min(0.5, conversation_length / 30)
        
        final_budget = base_budget * complexity_multiplier * length_multiplier
        return int(min(16000, final_budget))
    
    def _update_execution_stats(self, execution_time_ms: float, context_tokens: int) -> None:
        """Update running execution statistics"""
        total_executions = self.execution_stats['total_executions']
        
        # Update average execution time
        current_avg_time = self.execution_stats['avg_execution_time_ms']
        self.execution_stats['avg_execution_time_ms'] = (
            (current_avg_time * (total_executions - 1) + execution_time_ms) / total_executions
        )
        
        # Update average context tokens (only for memory-enabled executions)
        if context_tokens > 0:
            memory_executions = self.execution_stats['memory_enabled_executions']
            current_avg_tokens = self.execution_stats['avg_context_tokens']
            if memory_executions > 0:
                self.execution_stats['avg_context_tokens'] = (
                    (current_avg_tokens * (memory_executions - 1) + context_tokens) / memory_executions
                )
    
    def get_node_stats(self) -> Dict[str, Any]:
        """Get comprehensive node statistics"""
        return {
            'node_config': {
                'enable_memory_features': self.enable_memory_features,
                'fallback_to_basic': self.fallback_to_basic
            },
            'execution_stats': self.execution_stats.copy(),
            'memory_effectiveness': {
                'memory_usage_rate': (
                    self.execution_stats['memory_enabled_executions'] / 
                    max(1, self.execution_stats['total_executions'])
                ),
                'fallback_rate': (
                    self.execution_stats['fallback_executions'] / 
                    max(1, self.execution_stats['total_executions'])
                )
            }
        }


# Factory function
def create_memory_enhanced_context_node(
    memory_orchestrator: BanditIntegratedMemoryOrchestrator,
    cache_manager=None,
    enable_memory_features: bool = True,
    fallback_to_basic: bool = True
) -> MemoryEnhancedContextManagerNode:
    """Create memory-enhanced context manager node"""
    return MemoryEnhancedContextManagerNode(
        memory_orchestrator=memory_orchestrator,
        cache_manager=cache_manager,
        enable_memory_features=enable_memory_features,
        fallback_to_basic=fallback_to_basic
    )