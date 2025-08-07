"""
AI Engineer Knowledge Base Service
Provides intelligent search and retrieval from AI engineering knowledge sources
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class KnowledgeResult:
    """Result from knowledge base search"""
    content: str
    source: str
    relevance_score: float
    section: str
    knowledge_type: str  # rag, transcript, analysis, dataset
    metadata: Dict[str, Any] = None


class AIKnowledgeBase:
    """
    Comprehensive AI Engineer Knowledge Base integrating:
    - RAG fundamentals and advanced techniques
    - 498 YouTube video analysis
    - 756 transcript deep analysis  
    - Raw transcript dataset
    """
    
    def __init__(self, knowledge_base_path: str = "/home/ews/unified-ai-system-clean"):
        self.base_path = Path(knowledge_base_path)
        self.knowledge_sources = {}
        self.indexed_content = {}
        self.logger = logger
        
        # Knowledge source mapping
        self.source_files = {
            "rag_knowledge": "AI_RAG_Knowledge_Base.md",
            "video_analysis": "AI_Engineer_Complete_Analysis.md", 
            "transcript_analysis": "AI_Engineer_Transcripts_Analysis.md",
            "transcript_dataset": "dataset_youtube-full-channel-transcripts-extractor_2025-07-30_11-08-56-062.json"
        }
        
        # Initialize knowledge base
        self._load_knowledge_sources()
        self._create_search_index()
    
    def _load_knowledge_sources(self):
        """Load all knowledge source files"""
        try:
            for source_key, filename in self.source_files.items():
                file_path = self.base_path / filename
                
                if file_path.exists():
                    if filename.endswith('.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.knowledge_sources[source_key] = json.load(f)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.knowledge_sources[source_key] = f.read()
                    
                    self.logger.info(f"Loaded knowledge source: {source_key}")
                else:
                    self.logger.warning(f"Knowledge source not found: {filename}")
                    
        except Exception as e:
            self.logger.error(f"Error loading knowledge sources: {e}")
    
    def _create_search_index(self):
        """Create searchable index from knowledge sources"""
        try:
            # Index markdown content by sections
            for source_key in ["rag_knowledge", "video_analysis", "transcript_analysis"]:
                if source_key in self.knowledge_sources:
                    content = self.knowledge_sources[source_key]
                    sections = self._extract_sections(content)
                    self.indexed_content[source_key] = sections
            
            # Index transcript dataset
            if "transcript_dataset" in self.knowledge_sources:
                transcripts = self.knowledge_sources["transcript_dataset"]
                self.indexed_content["transcript_dataset"] = self._index_transcripts(transcripts)
                
            self.logger.info(f"Created search index with {len(self.indexed_content)} sources")
            
        except Exception as e:
            self.logger.error(f"Error creating search index: {e}")
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from markdown content"""
        sections = {}
        current_section = "introduction"
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#'):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = re.sub(r'[^\w\s]', '', line.strip('#').strip()).lower().replace(' ', '_')
                current_content = []
            else:
                current_content.append(line)
        
        # Save final section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
            
        return sections
    
    def _index_transcripts(self, transcripts: List[Dict]) -> Dict[str, Any]:
        """Index transcript dataset for search"""
        indexed = {
            "videos": {},
            "topics": {},
            "speakers": {}
        }
        
        for video in transcripts[:100]:  # Limit for performance
            video_id = video.get("videoId", "")
            title = video.get("title", "")
            transcript = video.get("transcript", "")
            
            if video_id and transcript:
                indexed["videos"][video_id] = {
                    "title": title,
                    "transcript": transcript,
                    "content_length": len(transcript)
                }
        
        return indexed
    
    def search_knowledge(self, query: str, max_results: int = 5) -> List[KnowledgeResult]:
        """
        Search across all knowledge sources for relevant information
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of KnowledgeResult objects
        """
        results = []
        query_lower = query.lower()
        
        # Search markdown sources
        for source_key in ["rag_knowledge", "video_analysis", "transcript_analysis"]:
            if source_key in self.indexed_content:
                sections = self.indexed_content[source_key]
                
                for section_name, content in sections.items():
                    if self._is_relevant(query_lower, content.lower()):
                        score = self._calculate_relevance_score(query_lower, content.lower())
                        
                        result = KnowledgeResult(
                            content=content[:2000],  # Limit content length
                            source=self.source_files[source_key],
                            relevance_score=score,
                            section=section_name,
                            knowledge_type=source_key,
                            metadata={"section_length": len(content)}
                        )
                        results.append(result)
        
        # Search transcript dataset
        if "transcript_dataset" in self.indexed_content:
            transcript_results = self._search_transcripts(query_lower)
            results.extend(transcript_results)
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:max_results]
    
    def _search_transcripts(self, query: str) -> List[KnowledgeResult]:
        """Search transcript dataset"""
        results = []
        transcripts = self.indexed_content["transcript_dataset"]
        
        for video_id, video_data in transcripts["videos"].items():
            transcript = video_data["transcript"].lower()
            title = video_data["title"]
            
            if self._is_relevant(query, transcript):
                score = self._calculate_relevance_score(query, transcript)
                
                # Extract relevant excerpt
                excerpt = self._extract_relevant_excerpt(query, transcript, title)
                
                result = KnowledgeResult(
                    content=excerpt,
                    source="AI Engineer Video Transcript",
                    relevance_score=score,
                    section=title,
                    knowledge_type="transcript_dataset",
                    metadata={
                        "video_id": video_id,
                        "transcript_length": len(transcript)
                    }
                )
                results.append(result)
        
        return results
    
    def _is_relevant(self, query: str, content: str) -> bool:
        """Check if content is relevant to query"""
        query_terms = query.split()
        content_lower = content.lower()
        
        # Must have at least 50% of query terms
        matches = sum(1 for term in query_terms if term in content_lower)
        return matches >= len(query_terms) * 0.3
    
    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        query_terms = query.split()
        content_lower = content.lower()
        
        # Count term matches
        term_matches = sum(1 for term in query_terms if term in content_lower)
        term_score = term_matches / len(query_terms) if query_terms else 0
        
        # Boost score for exact phrase matches
        phrase_match = 1.2 if query in content_lower else 1.0
        
        # Consider content length (prefer focused content)
        length_penalty = min(1.0, 1000 / len(content)) if content else 0
        
        return term_score * phrase_match * (0.7 + 0.3 * length_penalty)
    
    def _extract_relevant_excerpt(self, query: str, content: str, title: str) -> str:
        """Extract most relevant excerpt from content"""
        sentences = content.split('.')
        query_terms = query.split()
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences[:20]:  # Check first 20 sentences
            sentence = sentence.strip()
            if len(sentence) < 50:  # Skip very short sentences
                continue
                
            score = sum(1 for term in query_terms if term in sentence.lower())
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        if best_sentence:
            return f"**{title}**\n\n{best_sentence}..."
        else:
            return f"**{title}**\n\n{content[:500]}..."
    
    def get_ai_engineering_recommendations(self, query: str) -> Dict[str, Any]:
        """
        Get comprehensive AI engineering recommendations for a query
        
        Returns structured recommendations including:
        - Technical implementation patterns
        - Tool recommendations  
        - Best practices
        - Industry insights
        """
        search_results = self.search_knowledge(query)
        
        recommendations = {
            "query": query,
            "technical_patterns": [],
            "tool_recommendations": [],
            "best_practices": [],
            "industry_insights": [],
            "references": []
        }
        
        # Categorize results
        for result in search_results:
            if "rag" in result.knowledge_type or "RAG" in result.content:
                recommendations["technical_patterns"].append({
                    "pattern": "RAG Implementation",
                    "description": result.content[:300],
                    "source": result.source
                })
            
            if "vector" in result.content.lower() or "embedding" in result.content.lower():
                recommendations["tool_recommendations"].append({
                    "category": "Vector Databases",
                    "recommendation": result.content[:300],
                    "source": result.source
                })
            
            if "best practice" in result.content.lower() or "production" in result.content.lower():
                recommendations["best_practices"].append({
                    "practice": result.section,
                    "description": result.content[:300],
                    "source": result.source
                })
            
            recommendations["references"].append({
                "title": result.section,
                "source": result.source,
                "relevance": result.relevance_score
            })
        
        return recommendations
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        stats = {
            "sources_loaded": len(self.knowledge_sources),
            "indexed_sections": sum(len(sections) if isinstance(sections, dict) else 1 
                                  for sections in self.indexed_content.values()),
            "total_content_size": sum(len(str(content)) for content in self.knowledge_sources.values()),
            "available_sources": list(self.source_files.keys())
        }
        
        # Add transcript dataset stats
        if "transcript_dataset" in self.indexed_content:
            transcripts = self.indexed_content["transcript_dataset"]
            stats["transcript_videos"] = len(transcripts.get("videos", {}))
            
        return stats