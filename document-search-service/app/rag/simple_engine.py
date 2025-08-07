"""
Simple RAG Engine that bypasses complex dependencies
"""
import asyncio
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.rag.models import DocumentChunk, Document, DocumentStore
from app.logger import get_enhanced_logger

logger = get_enhanced_logger(__name__)

@dataclass
class RAGSearchResult:
    """Simple search result"""
    chunk_id: str
    content: str
    relevance_score: float
    source_document_id: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0

class SimpleRAGEngine:
    """Simple RAG engine with keyword-based search"""
    
    def __init__(self, *args, **kwargs):
        self.document_store = DocumentStore()
        self.logger = logger
    
    async def similarity_search(self, query: str, 
                               top_k: int = 10,
                               similarity_threshold: float = 0.1) -> List[RAGSearchResult]:
        """Simple keyword-based similarity search"""
        try:
            # Get all documents
            documents = self.document_store.list_documents(limit=1000)
            all_chunks = []
            
            for doc_info in documents:
                try:
                    document = self.document_store.retrieve_document(doc_info['id'])
                    if document and hasattr(document, 'chunks') and document.chunks:
                        all_chunks.extend(document.chunks)
                except Exception as e:
                    self.logger.warning(f"Failed to load document {doc_info['id']}: {e}")
            
            # Simple keyword matching
            query_words = set(query.lower().split())
            matching_chunks = []
            
            for chunk in all_chunks:
                chunk_words = set(chunk.content.lower().split())
                common_words = query_words.intersection(chunk_words)
                
                if common_words:
                    score = len(common_words) / len(query_words)
                    if score >= similarity_threshold:
                        result = RAGSearchResult(
                            chunk_id=chunk.chunk_id,
                            content=chunk.content,
                            relevance_score=score,
                            source_document_id=chunk.source_document_id,
                            chunk_index=chunk.chunk_index,
                            metadata=chunk.metadata or {},
                            keyword_score=score,
                            combined_score=score
                        )
                        matching_chunks.append(result)
            
            # Sort by relevance score
            matching_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
            
            self.logger.info(f"Found {len(matching_chunks)} chunks for query: {query[:50]}...")
            return matching_chunks[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error in similarity search: {e}")
            return []

    async def retrieve_for_rag(self, query: str, 
                              top_k: int = 5,
                              include_documents: bool = True) -> List[RAGSearchResult]:
        """Retrieve chunks for RAG"""
        return await self.similarity_search(query, top_k, 0.1)
    
    async def index_document_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Index chunks (no-op for simple engine)"""
        self.logger.info(f"Indexed {len(chunks)} chunks")
        return True
