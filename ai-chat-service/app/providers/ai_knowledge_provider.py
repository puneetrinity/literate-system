"""
AI Knowledge Base Search Provider
Integrates AI engineering knowledge base with the search provider ecosystem
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

from app.providers.base_provider import BaseProvider, ProviderConfig, SearchQuery, SearchResult
from app.services.ai_knowledge_base import AIKnowledgeBase, KnowledgeResult

logger = structlog.get_logger(__name__)


@dataclass
class AIKnowledgeConfig(ProviderConfig):
    """Configuration for AI Knowledge Base provider"""
    knowledge_base_path: str = "/home/ews/unified-ai-system-clean"
    max_results: int = 5
    min_relevance_score: float = 0.3
    include_transcripts: bool = True
    include_analysis: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.provider_name = "ai_knowledge_base"


@dataclass  
class AIKnowledgeQuery(SearchQuery):
    """Query for AI Knowledge Base search"""
    include_recommendations: bool = True
    focus_areas: Optional[List[str]] = None  # rag, agents, embeddings, etc.
    
    def __post_init__(self):
        super().__post_init__()


@dataclass
class AIKnowledgeSearchResult(SearchResult):
    """Enhanced search result with AI knowledge metadata"""
    knowledge_type: str = ""  # rag, transcript, analysis, dataset
    section: str = ""
    recommendations: Optional[Dict[str, Any]] = None
    expertise_level: str = "intermediate"  # beginner, intermediate, advanced
    
    def __post_init__(self):
        super().__post_init__()


class AIKnowledgeProvider(BaseProvider):
    """
    Provider for searching AI engineering knowledge base
    Integrates RAG fundamentals, video analysis, transcripts, and datasets
    """
    
    def __init__(self, config: AIKnowledgeConfig):
        super().__init__(config)
        self.config = config
        self.knowledge_base = AIKnowledgeBase(config.knowledge_base_path)
        self.ai_topics = {
            "rag", "retrieval", "augmented", "generation", "vector", "embedding",
            "llm", "language model", "ai agent", "agents", "langgraph", "langchain",
            "machine learning", "deep learning", "neural network", "transformer",
            "fine-tuning", "prompt engineering", "evaluation", "benchmarking",
            "production ai", "ai engineering", "mlops", "deployment"
        }
        
        logger.info(f"Initialized AI Knowledge Provider with {len(self.ai_topics)} AI topics")
    
    async def search(self, query: AIKnowledgeQuery) -> List[AIKnowledgeSearchResult]:
        """
        Search the AI engineering knowledge base
        
        Args:
            query: AIKnowledgeQuery with search parameters
            
        Returns:
            List of AIKnowledgeSearchResult objects
        """
        try:
            # Check if query is AI/ML related
            if not self._is_ai_related_query(query.text):
                logger.debug(f"Query not AI-related, skipping: {query.text}")
                return []
            
            # Search knowledge base
            knowledge_results = self.knowledge_base.search_knowledge(
                query.text, 
                max_results=self.config.max_results
            )
            
            # Convert to search results
            search_results = []
            for kr in knowledge_results:
                if kr.relevance_score >= self.config.min_relevance_score:
                    search_result = self._convert_to_search_result(kr, query)
                    search_results.append(search_result)
            
            # Add recommendations if requested
            if query.include_recommendations and search_results:
                recommendations = self.knowledge_base.get_ai_engineering_recommendations(query.text)
                # Add recommendations to the top result
                if search_results:
                    search_results[0].recommendations = recommendations
            
            logger.info(f"AI Knowledge search returned {len(search_results)} results for: {query.text}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error in AI Knowledge search: {e}")
            return []
    
    def _is_ai_related_query(self, query_text: str) -> bool:
        """Check if query is related to AI/ML topics"""
        query_lower = query_text.lower()
        
        # Direct topic matches
        for topic in self.ai_topics:
            if topic in query_lower:
                return True
        
        # Common AI patterns
        ai_patterns = [
            "how to implement",
            "best practices for",
            "production deployment",
            "architecture for",
            "comparison between",
            "performance optimization",
            "scalability of"
        ]
        
        for pattern in ai_patterns:
            if pattern in query_lower and any(topic in query_lower for topic in ["ai", "ml", "model", "data"]):
                return True
        
        return False
    
    def _convert_to_search_result(self, knowledge_result: KnowledgeResult, query: AIKnowledgeQuery) -> AIKnowledgeSearchResult:
        """Convert KnowledgeResult to AIKnowledgeSearchResult"""
        
        # Determine expertise level based on content
        expertise_level = self._determine_expertise_level(knowledge_result.content)
        
        # Create enhanced title
        title = f"AI Engineering: {knowledge_result.section.replace('_', ' ').title()}"
        
        # Create informative URL (knowledge base reference)
        url = f"knowledge://{knowledge_result.knowledge_type}/{knowledge_result.section}"
        
        # Enhanced snippet with context
        snippet = self._create_enhanced_snippet(knowledge_result, query.text)
        
        return AIKnowledgeSearchResult(
            title=title,
            url=url,
            snippet=snippet,
            source=f"AI Knowledge Base ({knowledge_result.source})",
            relevance_score=knowledge_result.relevance_score,
            knowledge_type=knowledge_result.knowledge_type,
            section=knowledge_result.section,
            expertise_level=expertise_level,
            metadata={
                "knowledge_source": knowledge_result.source,
                "section_name": knowledge_result.section,
                "content_length": len(knowledge_result.content),
                "original_metadata": knowledge_result.metadata
            }
        )
    
    def _determine_expertise_level(self, content: str) -> str:
        """Determine expertise level based on content complexity"""
        content_lower = content.lower()
        
        # Advanced indicators
        advanced_terms = [
            "architecture", "implementation", "production", "scalability", 
            "optimization", "performance", "enterprise", "deployment",
            "benchmarking", "evaluation metrics"
        ]
        
        # Beginner indicators  
        beginner_terms = [
            "introduction", "basics", "fundamentals", "overview",
            "getting started", "what is", "simple example"
        ]
        
        advanced_count = sum(1 for term in advanced_terms if term in content_lower)
        beginner_count = sum(1 for term in beginner_terms if term in content_lower)
        
        if advanced_count > beginner_count and advanced_count >= 2:
            return "advanced"
        elif beginner_count > advanced_count:
            return "beginner"
        else:
            return "intermediate"
    
    def _create_enhanced_snippet(self, knowledge_result: KnowledgeResult, query: str) -> str:
        """Create an enhanced snippet with AI engineering context"""
        content = knowledge_result.content
        
        # Try to find the most relevant sentence
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
        query_terms = query.lower().split()
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences[:10]:  # Check first 10 sentences
            sentence_lower = sentence.lower()
            score = sum(1 for term in query_terms if term in sentence_lower)
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        # Create contextual snippet
        if best_sentence:
            snippet = f"{best_sentence}..."
        else:
            snippet = content[:300] + "..." if len(content) > 300 else content
        
        # Add knowledge type context
        context_prefix = {
            "rag_knowledge": "🔍 RAG & Vector Search: ",
            "video_analysis": "📺 AI Engineering Insights: ",
            "transcript_analysis": "🎤 Expert Transcript: ",
            "transcript_dataset": "💬 Conference Talk: "
        }.get(knowledge_result.knowledge_type, "🤖 AI Knowledge: ")
        
        return context_prefix + snippet
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the AI Knowledge provider"""
        stats = self.knowledge_base.get_knowledge_stats()
        
        return {
            "provider_name": "AI Knowledge Base",
            "description": "Comprehensive AI engineering knowledge from expert sources",
            "knowledge_sources": stats["available_sources"],
            "total_sections": stats["indexed_sections"],
            "content_size_mb": round(stats["total_content_size"] / (1024 * 1024), 2),
            "specializes_in": [
                "RAG implementations and best practices",
                "Vector search and embeddings",
                "AI agent architectures", 
                "Production AI deployment",
                "Enterprise AI case studies",
                "Technical implementation patterns"
            ],
            "ai_topics_covered": len(self.ai_topics),
            "transcript_videos": stats.get("transcript_videos", 0)
        }
    
    async def test_connection(self) -> bool:
        """Test if the knowledge base is accessible"""
        try:
            test_query = AIKnowledgeQuery(text="RAG implementation")
            results = await self.search(test_query)
            return len(results) > 0
        except Exception as e:
            logger.error(f"AI Knowledge provider connection test failed: {e}")
            return False