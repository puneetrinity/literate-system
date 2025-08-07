"""
Unified Intelligent Router - Consolidation of 5 Routers

This router consolidates the functionality of:
1. IntelligentRouter - Pattern learning and intent classification  
2. EnhancedAdaptiveRouter - Thompson Sampling and A/B testing
3. MemoryAwareEnhancedRouter - Memory-aware routing decisions
4. ModelRouter - Query complexity and model selection
5. Shadow Router functionality - Safe parallel testing

Key Features:
- Unified decision-making process
- Multi-dimensional analysis (intent, complexity, memory, adaptivity)
- Thompson Sampling bandit optimization
- Memory-aware contextual routing
- Model selection integration
- Shadow testing capabilities
- Feature flag support for gradual rollout
"""

import asyncio
import json
import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.memory.bandit_orchestrator import BanditIntegratedMemoryOrchestrator
from app.memory.contextual_bandit import MemoryAwareThompsonBandit
from app.memory.routing_arms import MemoryRoutingArm, MemoryStrategy

logger = structlog.get_logger(__name__)
settings = get_settings()


class IntentType(Enum):
    """Enhanced intent classification"""
    SIMPLE_CHAT = "simple_chat"
    SEARCH_NEEDED = "search_needed" 
    CODE_ASSISTANCE = "code_assistance"
    ANALYSIS_NEEDED = "analysis_needed"
    RESEARCH_MODE = "research_mode"
    MULTILINGUAL = "multilingual"
    DOCUMENT_SEARCH = "document_search"  # New for document integration


class GraphType(Enum):
    """Graph execution types - consolidated"""
    CHAT = "chat"
    SEARCH = "search" 
    DOCUMENT = "document"  # New dedicated document graph type


class ModelTier(Enum):
    """Model tiers for intelligent selection"""
    LIGHTWEIGHT = "lightweight"  # phi3:mini
    STANDARD = "standard"        # llama2:7b  
    PREMIUM = "premium"          # llama2:13b


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class UnifiedRoutingDecision(BaseModel):
    """Comprehensive routing decision with all contexts"""
    
    # Core routing
    intent_type: IntentType = Field(description="Detected intent")
    graph_type: GraphType = Field(description="Target graph type")
    confidence: float = Field(description="Overall routing confidence")
    
    # Model selection
    selected_model: str = Field(description="Selected model name")
    model_tier: ModelTier = Field(description="Model tier")
    query_complexity: QueryComplexity = Field(description="Detected complexity")
    
    # Memory context
    memory_strategy: Optional[MemoryStrategy] = Field(default=None, description="Memory strategy")
    memory_context: Dict[str, Any] = Field(default_factory=dict, description="Memory context")
    
    # Adaptive learning
    bandit_arm: Optional[str] = Field(default=None, description="Selected bandit arm")
    exploration_factor: float = Field(default=0.0, description="Exploration vs exploitation")
    
    # Cost and performance
    estimated_cost: float = Field(default=0.0, description="Estimated processing cost")
    estimated_time: float = Field(default=0.0, description="Estimated processing time")
    
    # Reasoning and debugging
    reasoning: List[str] = Field(default_factory=list, description="Decision reasoning")
    feature_scores: Dict[str, float] = Field(default_factory=dict, description="Feature analysis scores")
    
    # Enterprise controls
    web_search_blocked: bool = Field(default=True, description="Web search blocked by policy")
    manual_override: Optional[str] = Field(default=None, description="Manual routing override")


class UnifiedIntelligentRouter:
    """
    Unified router consolidating 5 separate routers into one intelligent system
    """
    
    def __init__(self, 
                 memory_orchestrator: Optional[BanditIntegratedMemoryOrchestrator] = None,
                 enable_adaptive_learning: bool = True,
                 enable_shadow_testing: bool = False):
        
        self.memory_orchestrator = memory_orchestrator
        self.enable_adaptive_learning = enable_adaptive_learning
        self.enable_shadow_testing = enable_shadow_testing
        
        # Initialize consolidated components
        self._init_intent_classification()
        self._init_model_selection()
        self._init_adaptive_learning()
        self._init_feature_extraction()
        
        # Pattern learning storage
        self.routing_patterns = {}
        self.performance_history = {}
        
        logger.info("UnifiedIntelligentRouter initialized", 
                   adaptive_learning=enable_adaptive_learning,
                   shadow_testing=enable_shadow_testing)
    
    def _init_intent_classification(self):
        """Initialize intent classification patterns"""
        self.intent_patterns = {
            IntentType.SIMPLE_CHAT: [
                r'\b(hello|hi|hey|thanks|thank you|goodbye|bye)\b',
                r'\b(how are you|what\'s up|nice to meet)\b',
                r'^(yes|no|okay|ok|sure|maybe)\s*$'
            ],
            IntentType.SEARCH_NEEDED: [
                r'\b(search|find|lookup|latest|recent|news)\b',
                r'\b(what happened|current|today|now)\b',
                r'\b(price|stock|weather|forecast)\b'
            ],
            IntentType.DOCUMENT_SEARCH: [
                r'\b(document|file|pdf|doc|upload|my files)\b',
                r'\b(in my documents|from my files|search documents)\b',
                r'\b(what does.*document say|find in files)\b'
            ],
            IntentType.CODE_ASSISTANCE: [
                r'\b(code|programming|debug|error|function)\b',
                r'\b(python|javascript|java|sql|api)\b',
                r'\b(implement|create|write.*code)\b'
            ],
            IntentType.ANALYSIS_NEEDED: [
                r'\b(analyze|compare|evaluate|assess|review)\b',
                r'\b(pros and cons|advantages|disadvantages)\b',
                r'\b(recommend|suggest|best approach)\b'
            ],
            IntentType.RESEARCH_MODE: [
                r'\b(research|comprehensive|detailed|in-depth)\b',
                r'\b(study|investigate|explore|deep dive)\b',
                r'\b(tell me everything|complete analysis)\b'
            ]
        }
    
    def _init_model_selection(self):
        """Initialize model selection capabilities"""
        self.model_capabilities = {
            "phi3:mini": {
                "tier": ModelTier.LIGHTWEIGHT,
                "cost_per_token": 0.0001,
                "avg_tokens_per_second": 50,
                "max_context": 2048,
                "strengths": ["speed", "basic_chat", "simple_questions"]
            },
            "llama2:7b": {
                "tier": ModelTier.STANDARD,
                "cost_per_token": 0.0005,
                "avg_tokens_per_second": 25,
                "max_context": 4096,
                "strengths": ["reasoning", "analysis", "code_help"]
            },
            "llama2:13b": {
                "tier": ModelTier.PREMIUM,
                "cost_per_token": 0.001,
                "avg_tokens_per_second": 15,
                "max_context": 4096,
                "strengths": ["complex_reasoning", "research", "premium_quality"]
            }
        }
    
    def _init_adaptive_learning(self):
        """Initialize Thompson Sampling bandit for adaptive learning"""
        if self.enable_adaptive_learning:
            # Bandit arms for different routing strategies
            self.bandit_arms = {
                "intent_based": {"successes": 10, "failures": 2},
                "pattern_learned": {"successes": 8, "failures": 3}, 
                "memory_aware": {"successes": 6, "failures": 1},
                "complexity_based": {"successes": 7, "failures": 2}
            }
    
    def _init_feature_extraction(self):
        """Initialize feature extraction for multi-dimensional analysis"""
        self.feature_extractors = {
            "length": lambda q: len(q) / 100.0,
            "question_marks": lambda q: q.count('?') / 5.0,
            "technical_terms": lambda q: len(re.findall(r'\b(api|database|algorithm|implementation)\b', q.lower())) / 10.0,
            "urgency": lambda q: len(re.findall(r'\b(urgent|asap|quickly|immediately)\b', q.lower())) / 5.0,
            "complexity_words": lambda q: len(re.findall(r'\b(complex|detailed|comprehensive|thorough)\b', q.lower())) / 5.0
        }
    
    async def route_query(self, 
                         query: str,
                         user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         budget: float = 2.0,
                         quality_preference: str = "balanced",
                         context: Optional[Dict] = None,
                         manual_override: Optional[str] = None) -> UnifiedRoutingDecision:
        """
        Unified routing decision incorporating all consolidated router logic
        """
        
        start_time = datetime.now()
        reasoning = []
        
        # 1. Extract features (consolidated from all routers)
        features = self._extract_query_features(query, context)
        reasoning.append(f"Extracted {len(features)} features")
        
        # 2. Intent classification (from IntelligentRouter)
        intent_type, intent_confidence = self._classify_intent(query, features)
        reasoning.append(f"Intent: {intent_type.value} (confidence: {intent_confidence:.2f})")
        
        # 3. Query complexity analysis (from ModelRouter)
        complexity, complexity_confidence = self._analyze_complexity(query, features)
        reasoning.append(f"Complexity: {complexity.value} (confidence: {complexity_confidence:.2f})")
        
        # 4. Memory-aware analysis (from MemoryAwareRouter)
        memory_strategy, memory_context = await self._analyze_memory_context(
            query, user_id, session_id, intent_type
        )
        if memory_strategy:
            reasoning.append(f"Memory strategy: {memory_strategy.value}")
        
        # 5. Adaptive routing (from EnhancedAdaptiveRouter)
        bandit_arm, exploration_factor = None, 0.0
        if self.enable_adaptive_learning:
            bandit_arm, exploration_factor = self._select_bandit_arm(features, intent_type)
            reasoning.append(f"Bandit arm: {bandit_arm} (exploration: {exploration_factor:.2f})")
        
        # 6. Model selection (from ModelRouter)
        selected_model, model_tier = self._select_model(complexity, budget, quality_preference)
        reasoning.append(f"Model: {selected_model} ({model_tier.value})")
        
        # 7. Graph type determination (consolidated logic)
        graph_type = self._determine_graph_type(intent_type, manual_override)
        reasoning.append(f"Graph: {graph_type.value}")
        
        # 8. Enterprise controls (web search blocking)
        web_search_blocked = self._check_web_search_policy(intent_type, context)
        if web_search_blocked and graph_type == GraphType.SEARCH:
            graph_type = GraphType.DOCUMENT  # Redirect to document search
            reasoning.append("Web search blocked - redirected to document search")
        
        # 9. Cost and time estimation
        estimated_cost, estimated_time = self._estimate_cost_and_time(
            selected_model, query, graph_type
        )
        
        # 10. Overall confidence calculation
        overall_confidence = (intent_confidence + complexity_confidence) / 2.0
        if memory_strategy:
            overall_confidence = (overall_confidence + 0.8) / 2.0  # Memory context boosts confidence
        
        # Create unified decision
        decision = UnifiedRoutingDecision(
            intent_type=intent_type,
            graph_type=graph_type,
            confidence=overall_confidence,
            selected_model=selected_model,
            model_tier=model_tier,
            query_complexity=complexity,
            memory_strategy=memory_strategy,
            memory_context=memory_context,
            bandit_arm=bandit_arm,
            exploration_factor=exploration_factor,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            reasoning=reasoning,
            feature_scores=features,
            web_search_blocked=web_search_blocked,
            manual_override=manual_override
        )
        
        # Log the decision
        routing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info("Unified routing completed",
                   query_hash=hashlib.md5(query.encode()).hexdigest()[:8],
                   intent=intent_type.value,
                   graph=graph_type.value,
                   model=selected_model,
                   confidence=overall_confidence,
                   routing_time_ms=routing_time)
        
        # Shadow testing (if enabled)
        if self.enable_shadow_testing:
            asyncio.create_task(self._shadow_test_routing(query, decision, context))
        
        return decision
    
    def _extract_query_features(self, query: str, context: Optional[Dict] = None) -> Dict[str, float]:
        """Extract comprehensive features from query"""
        features = {}
        
        # Apply all feature extractors
        for name, extractor in self.feature_extractors.items():
            try:
                features[name] = min(extractor(query), 1.0)  # Normalize to 0-1
            except Exception as e:
                logger.warning(f"Feature extraction failed for {name}: {e}")
                features[name] = 0.0
        
        # Context-based features
        if context:
            features["has_context"] = 1.0
            features["context_relevance"] = context.get("relevance_score", 0.5)
        else:
            features["has_context"] = 0.0
            features["context_relevance"] = 0.0
        
        return features
    
    def _classify_intent(self, query: str, features: Dict[str, float]) -> Tuple[IntentType, float]:
        """Classify query intent using pattern matching and features"""
        query_lower = query.lower()
        intent_scores = {}
        
        # Pattern-based scoring
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1.0
            intent_scores[intent_type] = score
        
        # Feature-based adjustments
        if features["technical_terms"] > 0.3:
            intent_scores[IntentType.CODE_ASSISTANCE] += 0.5
        
        if features["complexity_words"] > 0.3:
            intent_scores[IntentType.RESEARCH_MODE] += 0.5
        
        if features["question_marks"] > 0.4:
            intent_scores[IntentType.SEARCH_NEEDED] += 0.3
        
        # Find best intent
        if not intent_scores or max(intent_scores.values()) == 0:
            return IntentType.SIMPLE_CHAT, 0.7  # Default
        
        best_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
        confidence = min(intent_scores[best_intent] / 2.0, 1.0)
        
        return best_intent, confidence
    
    def _analyze_complexity(self, query: str, features: Dict[str, float]) -> Tuple[QueryComplexity, float]:
        """Analyze query complexity using multiple signals"""
        
        # Length-based analysis
        if features["length"] > 0.8:
            base_complexity = QueryComplexity.COMPLEX
        elif features["length"] > 0.4:
            base_complexity = QueryComplexity.MODERATE
        else:
            base_complexity = QueryComplexity.SIMPLE
        
        # Feature-based adjustments
        complexity_score = 0.0
        if features["technical_terms"] > 0.2:
            complexity_score += 0.3
        if features["complexity_words"] > 0.2:
            complexity_score += 0.4
        if features["question_marks"] > 0.6:
            complexity_score += 0.2
        
        # Final complexity determination
        if complexity_score > 0.6:
            final_complexity = QueryComplexity.COMPLEX
            confidence = 0.8
        elif complexity_score > 0.3:
            final_complexity = QueryComplexity.MODERATE
            confidence = 0.7
        else:
            final_complexity = base_complexity
            confidence = 0.6
        
        return final_complexity, confidence
    
    async def _analyze_memory_context(self, query: str, user_id: Optional[str], 
                                    session_id: Optional[str], intent_type: IntentType) -> Tuple[Optional[MemoryStrategy], Dict[str, Any]]:
        """Analyze memory context and select strategy"""
        
        if not self.memory_orchestrator or not user_id:
            return None, {}
        
        try:
            # Get memory context from orchestrator
            memory_context = await self.memory_orchestrator.get_memory_context(
                user_id=user_id,
                session_id=session_id,
                query=query
            )
            
            # Select memory strategy based on intent and context
            if intent_type in [IntentType.RESEARCH_MODE, IntentType.ANALYSIS_NEEDED]:
                strategy = MemoryStrategy.DEEP
            elif intent_type == IntentType.CODE_ASSISTANCE:
                strategy = MemoryStrategy.STANDARD
            else:
                strategy = MemoryStrategy.MINIMAL
            
            return strategy, memory_context
            
        except Exception as e:
            logger.warning(f"Memory analysis failed: {e}")
            return None, {}
    
    def _select_bandit_arm(self, features: Dict[str, float], intent_type: IntentType) -> Tuple[str, float]:
        """Select bandit arm using Thompson Sampling"""
        
        if not self.enable_adaptive_learning:
            return "intent_based", 0.0
        
        # Thompson Sampling selection
        arm_samples = {}
        for arm_name, stats in self.bandit_arms.items():
            alpha = stats["successes"] + 1
            beta = stats["failures"] + 1
            arm_samples[arm_name] = np.random.beta(alpha, beta)
        
        # Select arm with highest sample
        selected_arm = max(arm_samples.keys(), key=lambda k: arm_samples[k])
        
        # Calculate exploration factor
        total_trials = sum(stats["successes"] + stats["failures"] for stats in self.bandit_arms.values())
        exploration_factor = min(10.0 / (total_trials + 10.0), 0.3)  # Decrease exploration over time
        
        return selected_arm, exploration_factor
    
    def _select_model(self, complexity: QueryComplexity, budget: float, quality_preference: str) -> Tuple[str, ModelTier]:
        """Select appropriate model based on complexity and constraints"""
        
        # Budget-based selection
        if budget < 0.5:
            return "phi3:mini", ModelTier.LIGHTWEIGHT
        
        # Quality preference handling
        if quality_preference == "premium" and budget >= 2.0:
            if complexity in [QueryComplexity.COMPLEX, QueryComplexity.MODERATE]:
                return "llama2:13b", ModelTier.PREMIUM
            else:
                return "llama2:7b", ModelTier.STANDARD
        
        # Complexity-based selection
        if complexity == QueryComplexity.COMPLEX and budget >= 1.0:
            return "llama2:7b", ModelTier.STANDARD
        elif complexity == QueryComplexity.MODERATE and budget >= 0.5:
            return "llama2:7b" if budget >= 1.0 else "phi3:mini", ModelTier.STANDARD if budget >= 1.0 else ModelTier.LIGHTWEIGHT
        else:
            return "phi3:mini", ModelTier.LIGHTWEIGHT
    
    def _determine_graph_type(self, intent_type: IntentType, manual_override: Optional[str] = None) -> GraphType:
        """Determine target graph type from intent and overrides"""
        
        # Manual override takes precedence
        if manual_override:
            if manual_override.lower() in ["search", "web"]:
                return GraphType.SEARCH
            elif manual_override.lower() in ["document", "docs"]:
                return GraphType.DOCUMENT
            elif manual_override.lower() in ["chat"]:
                return GraphType.CHAT
        
        # Intent-based routing
        intent_to_graph = {
            IntentType.SIMPLE_CHAT: GraphType.CHAT,
            IntentType.CODE_ASSISTANCE: GraphType.CHAT,
            IntentType.SEARCH_NEEDED: GraphType.SEARCH,
            IntentType.RESEARCH_MODE: GraphType.SEARCH,
            IntentType.ANALYSIS_NEEDED: GraphType.CHAT,
            IntentType.DOCUMENT_SEARCH: GraphType.DOCUMENT,
            IntentType.MULTILINGUAL: GraphType.CHAT
        }
        
        return intent_to_graph.get(intent_type, GraphType.CHAT)
    
    def _check_web_search_policy(self, intent_type: IntentType, context: Optional[Dict] = None) -> bool:
        """Check if web search should be blocked by enterprise policy"""
        
        # Default: block web search for enterprise accounts
        if context and context.get("enterprise_account", False):
            return True
        
        # Block web search by default - require manual activation
        if intent_type == IntentType.SEARCH_NEEDED:
            web_search_consent = context.get("web_search_consent", False) if context else False
            return not web_search_consent
        
        return False
    
    def _estimate_cost_and_time(self, model_name: str, query: str, graph_type: GraphType) -> Tuple[float, float]:
        """Estimate processing cost and time"""
        
        model_info = self.model_capabilities.get(model_name, self.model_capabilities["phi3:mini"])
        
        # Estimate tokens (rough calculation)
        estimated_tokens = len(query.split()) * 3
        
        # Graph type overhead
        graph_overhead = {
            GraphType.CHAT: 1.0,
            GraphType.SEARCH: 2.0,  # Search requires additional processing
            GraphType.DOCUMENT: 1.5  # Document search moderate overhead
        }
        
        overhead = graph_overhead.get(graph_type, 1.0)
        
        # Calculate cost and time
        cost = estimated_tokens * model_info["cost_per_token"] * overhead
        time = (estimated_tokens / model_info["avg_tokens_per_second"]) * overhead
        
        return cost, time
    
    async def _shadow_test_routing(self, query: str, primary_decision: UnifiedRoutingDecision, context: Optional[Dict] = None):
        """Run shadow test with alternative routing strategy"""
        
        try:
            # Create alternative routing decision for comparison
            # This would run in parallel without affecting the main response
            logger.info("Shadow test initiated", 
                       primary_intent=primary_decision.intent_type.value,
                       primary_graph=primary_decision.graph_type.value)
            
            # In a real implementation, this would execute the alternative path
            # and compare results for learning
            
        except Exception as e:
            logger.warning(f"Shadow test failed: {e}")
    
    async def update_performance(self, decision: UnifiedRoutingDecision, success: bool, response_time: float, user_feedback: Optional[float] = None):
        """Update routing performance for adaptive learning"""
        
        if not self.enable_adaptive_learning or not decision.bandit_arm:
            return
        
        # Update bandit arm statistics
        arm_stats = self.bandit_arms.get(decision.bandit_arm)
        if arm_stats:
            if success:
                arm_stats["successes"] += 1
            else:
                arm_stats["failures"] += 1
        
        # Store performance history
        performance_key = f"{decision.intent_type.value}_{decision.graph_type.value}"
        if performance_key not in self.performance_history:
            self.performance_history[performance_key] = []
        
        self.performance_history[performance_key].append({
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "response_time": response_time,
            "user_feedback": user_feedback,
            "confidence": decision.confidence
        })
        
        # Keep only recent history (last 100 entries)
        if len(self.performance_history[performance_key]) > 100:
            self.performance_history[performance_key] = self.performance_history[performance_key][-100:]
        
        logger.info("Performance updated",
                   bandit_arm=decision.bandit_arm,
                   success=success,
                   response_time=response_time)