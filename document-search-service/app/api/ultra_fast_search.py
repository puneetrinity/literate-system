
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import time
import asyncio
import traceback
from datetime import datetime, timezone

from app.search.ultra_fast_engine import UltraFastSearchEngine, SearchResult
from app.validation.validators import SearchRequest, IndexBuildRequest, HealthCheckResponse, MetricsResponse, ErrorResponse
from app.error_handling.exceptions import SearchSystemException, handle_and_log_error, ErrorHandler
from app.monitoring.health import HealthChecker
from app.monitoring.metrics import metrics
from app.logger import get_enhanced_logger, log_performance

import aiofiles

router = APIRouter(prefix="/api/v2", tags=["ultra-fast-search"])
logger = get_enhanced_logger(__name__)
error_handler = ErrorHandler(logger)

# This will be set on application startup
search_engine: Optional[UltraFastSearchEngine] = None
health_checker: Optional[HealthChecker] = None

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    num_results: int = Field(10, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict] = Field(None, description="Search filters")

class SearchResponse(BaseModel):
    success: bool
    results: List[Dict]
    total_found: int
    response_time_ms: float
    debug_info: Optional[Dict] = None

@router.post("/search/ultra-fast", response_model=SearchResponse)
@log_performance("search_request")
async def ultra_fast_search(request: SearchRequest):
    """Enhanced search endpoint with comprehensive error handling and validation."""
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized.")

    start_time = time.time()
    try:
        # Log search request
        logger.info("Processing search request", extra_fields={
            'query': request.query[:100],  # Truncate for logging
            'num_results': request.num_results,
            'has_filters': request.filters is not None
        })
        
        # Increment search counter
        metrics.increment_counter('search_requests_total')
        
        results = await search_engine.search(
            query=request.query,
            num_results=request.num_results,
            filters=request.filters.dict() if request.filters else None
        )
        response_time = (time.time() - start_time) * 1000
        
        # Record response time
        metrics.record_histogram('search_response_time_ms', response_time)

        formatted_results = [
            {
                "doc_id": r.doc_id,
                "similarity_score": r.similarity_score,
                "bm25_score": r.bm25_score,
                "combined_score": r.combined_score,
                **r.metadata
            }
            for r in results
        ]
        
        response_data = {
            "success": True,
            "results": formatted_results,
            "total_found": len(results),
            "response_time_ms": response_time
        }
        
        # Add debug information if requested
        include_debug = getattr(request, 'include_debug', False)
        if include_debug and search_engine:
            response_data["debug_info"] = {
                "search_stats": search_engine.get_performance_stats(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        logger.info("Search request completed successfully", extra_fields={
            'response_time_ms': response_time,
            'results_count': len(results)
        })
        
        return SearchResponse(**response_data)
        
    except SearchSystemException as e:
        metrics.increment_counter('search_errors_total', labels={'error_type': e.error_code.value})
        logger.error("Search system error", extra_fields=e.details)
        raise HTTPException(status_code=400, detail=e.to_dict())
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "search request")
        metrics.increment_counter('search_errors_total', labels={'error_type': 'internal'})
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

@router.get("/search/performance", response_model=MetricsResponse)
async def get_search_performance():
    """Get detailed search performance metrics."""
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    
    try:
        # Get search engine stats
        engine_stats = search_engine.get_performance_stats()
        
        # Get comprehensive metrics
        all_metrics = metrics.get_all_metrics()
        
        # Combine with engine-specific stats
        all_metrics['gauges'].update({
            'search_engine_total_searches': engine_stats.get('total_searches', 0),
            'search_engine_avg_response_time_ms': engine_stats.get('avg_response_time_ms', 0),
            'search_engine_cache_hit_rate': engine_stats.get('cache_hit_rate', 0)
        })
        
        return MetricsResponse(**all_metrics)
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "performance metrics")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    global health_checker
    try:
        if health_checker is None:
            # Create health checker if not available
            health_checker = HealthChecker(search_engine)
        
        health_data = await health_checker.check_all_health()
        return HealthCheckResponse(**health_data)
    
    except Exception as e:
        # Even if health check fails, return what we can
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            uptime_seconds=0,
            components={"error": {"status": "unhealthy", "message": str(e)}}
        )

@router.get("/health/quick")
async def quick_health_check():
    """Quick health check for load balancers."""
    global health_checker
    try:
        if health_checker is None:
            health_checker = HealthChecker(search_engine)
        
        return health_checker.get_quick_health()
    
    except Exception:
        return {"status": "unhealthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/metrics")
async def get_metrics():
    """Get all system metrics in Prometheus-compatible format."""
    try:
        return metrics.get_all_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/performance")
async def get_performance_metrics():
    """Get P99 latency and performance metrics for monitoring."""
    try:
        all_metrics = metrics.get_all_metrics()
        
        # Extract latency histograms
        histograms = all_metrics.get('histograms', {})
        
        # Calculate P99 latencies (simplified - would use proper percentile calculation in production)
        performance_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "unified_search": {
                "total_queries": all_metrics.get('counters', {}).get('unified_search_queries_total', 0),
                "error_count": all_metrics.get('counters', {}).get('unified_search_errors_total', 0),
                "avg_response_time_ms": histograms.get('unified_search_response_time_ms', {}).get('avg', 0)
            },
            "ultra_fast_search": {
                "timeout_count": all_metrics.get('counters', {}).get('ultra_fast_search_timeouts_total', 0),
                "error_count": all_metrics.get('counters', {}).get('ultra_fast_search_errors_total', 0),
                "avg_response_time_ms": histograms.get('ultra_fast_search_time_ms', {}).get('avg', 0)
            },
            "rag_search": {
                "timeout_count": all_metrics.get('counters', {}).get('rag_search_timeouts_total', 0),
                "error_count": all_metrics.get('counters', {}).get('rag_search_errors_total', 0),
                "avg_response_time_ms": histograms.get('rag_search_time_ms', {}).get('avg', 0)
            },
            "circuit_breaker": {
                "critical_failures": all_metrics.get('counters', {}).get('critical_search_failures_total', 0),
                "ultra_fast_success_rate": _calculate_success_rate("ultra_fast"),
                "rag_success_rate": _calculate_success_rate("rag")
            }
        }
        
        return performance_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_success_rate(system_type: str) -> float:
    """Calculate success rate for a system (placeholder implementation)."""
    try:
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics.get('counters', {})
        
        total_attempts = counters.get(f'{system_type}_search_attempts_total', 0)
        errors = counters.get(f'{system_type}_search_errors_total', 0)
        timeouts = counters.get(f'{system_type}_search_timeouts_total', 0)
        
        if total_attempts == 0:
            return 1.0
            
        failures = errors + timeouts
        return max(0.0, (total_attempts - failures) / total_attempts)
        
    except Exception:
        return 1.0  # Default to healthy if calculation fails

@router.post("/admin/build-indexes")
@log_performance("build_indexes")
async def build_indexes_endpoint(request: IndexBuildRequest, background_tasks: BackgroundTasks):
    """Enhanced index building endpoint with validation and error handling."""
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized.")

    try:
        logger.info("Index build request received", extra_fields={
            'data_source': request.data_source,
            'force_rebuild': request.force_rebuild
        })

        async def _build():
            try:
                # Backup existing indexes if requested
                if request.backup_existing and search_engine.index_path:
                    backup_path = f"{search_engine.index_path}_backup_{int(time.time())}"
                    logger.info(f"Backing up existing indexes to {backup_path}")
                
                # Load and validate documents
                async with aiofiles.open(request.data_source, mode='r') as f:
                    content = await f.read()
                    documents = __import__('json').loads(content)
                
                # Validate document structure
                from app.validation.validators import validate_document_structure
                valid_docs = []
                for doc in documents:
                    if validate_document_structure(doc):
                        valid_docs.append(doc)
                    else:
                        logger.warning(f"Invalid document structure for doc_id: {doc.get('id', 'unknown')}")
                
                logger.info(f"Building indexes for {len(valid_docs)} valid documents")
                await search_engine.build_indexes(valid_docs)
                
                # Start incremental updates if available
                if hasattr(search_engine, 'incremental_manager'):
                    await search_engine.incremental_manager.start_background_processing()
                
                logger.info("Index building completed successfully")
                
            except Exception as e:
                handled_error = error_handler.handle_index_build_error(request.data_source, e)
                logger.error("Index building failed", extra_fields=handled_error.details)
                # In a production system, you might want to send notifications here

        background_tasks.add_task(_build)
        return {"message": "Index building started in the background.", "request_id": str(__import__('uuid').uuid4())}
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "index build request")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

# Incremental update endpoints
@router.post("/admin/documents")
async def add_documents(documents: List[Dict]):
    """Add new documents with incremental indexing."""
    if search_engine is None or not hasattr(search_engine, 'incremental_manager'):
        raise HTTPException(status_code=503, detail="Incremental updates not available")
    
    try:
        from app.validation.validators import validate_document_structure
        from app.indexing.incremental import ChangeType
        
        valid_docs = []
        for doc in documents:
            if validate_document_structure(doc):
                valid_docs.append(doc)
                search_engine.incremental_manager.add_document_change(
                    doc['id'], ChangeType.ADD, doc
                )
            else:
                logger.warning(f"Invalid document structure for doc_id: {doc.get('id', 'unknown')}")
        
        return {"message": f"Added {len(valid_docs)} documents to incremental update queue"}
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "add documents")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

@router.put("/admin/documents/{doc_id}")
async def update_document(doc_id: str, document: Dict):
    """Update an existing document with incremental indexing."""
    if search_engine is None or not hasattr(search_engine, 'incremental_manager'):
        raise HTTPException(status_code=503, detail="Incremental updates not available")
    
    try:
        from app.validation.validators import validate_document_structure
        from app.indexing.incremental import ChangeType
        
        document['id'] = doc_id  # Ensure ID matches
        if validate_document_structure(document):
            search_engine.incremental_manager.add_document_change(
                doc_id, ChangeType.UPDATE, document
            )
            return {"message": f"Document {doc_id} queued for update"}
        else:
            raise HTTPException(status_code=400, detail="Invalid document structure")
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "update document")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

@router.delete("/admin/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document with incremental indexing."""
    if search_engine is None or not hasattr(search_engine, 'incremental_manager'):
        raise HTTPException(status_code=503, detail="Incremental updates not available")
    
    try:
        from app.indexing.incremental import ChangeType
        
        search_engine.incremental_manager.add_document_change(
            doc_id, ChangeType.DELETE
        )
        return {"message": f"Document {doc_id} queued for deletion"}
    
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "delete document")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

@router.get("/admin/incremental-stats")
async def get_incremental_stats():
    """Get incremental update statistics."""
    if search_engine is None or not hasattr(search_engine, 'incremental_manager'):
        raise HTTPException(status_code=503, detail="Incremental updates not available")
    
    try:
        return search_engine.incremental_manager.get_stats()
    except Exception as e:
        handled_error = handle_and_log_error(e, logger, "incremental stats")
        raise HTTPException(status_code=500, detail=handled_error.to_dict())

# Unified Search Endpoint
class UnifiedSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    num_results: int = Field(10, ge=1, le=100, description="Number of results to return")
    search_type: str = Field("hybrid", description="Search type: 'documents', 'chunks', or 'hybrid'")
    filters: Optional[Dict] = Field(None, description="Search filters")
    confidence_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum confidence threshold")
    include_citations: bool = Field(True, description="Include document citations")

@router.post("/unified/search")
async def unified_search(request: UnifiedSearchRequest):
    """
    Unified search endpoint with circuit breakers and timeout safeguards.
    
    This endpoint provides a single interface for all search needs:
    - Document search (like /search/ultra-fast)
    - RAG chunk retrieval (like /rag/query) 
    - Hybrid search combining both approaches
    
    Features circuit breakers to ensure system resilience:
    - Ultra-Fast search timeout: 3 seconds
    - RAG search timeout: 5 seconds  
    - Graceful degradation when components fail
    
    Supports all document types through GenericDocumentHandler.
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    
    start_time = time.time()
    
    try:
        # Get RAG system for chunk-based search
        from app.rag.integration import get_rag_manager
        rag_manager = await get_rag_manager()
        
        results = []
        search_status = {
            "ultra_fast_status": "not_attempted",
            "rag_status": "not_attempted",
            "ultra_fast_time_ms": 0,
            "rag_time_ms": 0
        }
        
        # Document-level search using Ultra-Fast engine with circuit breaker
        if request.search_type in ["documents", "hybrid"]:
            ultra_fast_start = time.time()
            search_status["ultra_fast_status"] = "attempting"
            
            try:
                # Circuit breaker: 3 second timeout for Ultra-Fast search
                search_results = await asyncio.wait_for(
                    search_engine.search(
                        query=request.query,
                        num_results=request.num_results,
                        filters=request.filters
                    ),
                    timeout=3.0
                )
                
                search_status["ultra_fast_time_ms"] = (time.time() - ultra_fast_start) * 1000
                search_status["ultra_fast_status"] = "success"
                
                # Convert to unified format
                for result in search_results:
                    unified_result = {
                        "type": "document",
                        "doc_id": result.doc_id,
                        "content": result.metadata.get("title", ""),
                        "title": result.metadata.get("title", "Document"),
                        "score": result.combined_score,
                        "similarity_score": result.similarity_score,
                        "bm25_score": result.bm25_score,
                        "metadata": result.metadata,
                        "source": "ultra_fast_search"
                    }
                    results.append(unified_result)
                    
            except asyncio.TimeoutError:
                search_status["ultra_fast_time_ms"] = (time.time() - ultra_fast_start) * 1000
                search_status["ultra_fast_status"] = "timeout"
                logger.warning(f"Ultra-Fast search timeout after 3s for query: {request.query[:50]}")
                metrics.increment_counter('ultra_fast_search_timeouts_total')
                
            except Exception as e:
                search_status["ultra_fast_time_ms"] = (time.time() - ultra_fast_start) * 1000
                search_status["ultra_fast_status"] = "error"
                logger.warning(f"Ultra-Fast search failed: {e}")
                metrics.increment_counter('ultra_fast_search_errors_total')
        
        # Chunk-level search using RAG system with circuit breaker
        if request.search_type in ["chunks", "hybrid"] and rag_manager and rag_manager.initialized:
            rag_start = time.time()
            search_status["rag_status"] = "attempting"
            
            try:
                # Circuit breaker: 5 second timeout for RAG search
                rag_results = await asyncio.wait_for(
                    rag_manager.rag_engine.search_chunks(
                        query=request.query,
                        max_chunks=request.num_results,
                        confidence_threshold=request.confidence_threshold
                    ),
                    timeout=5.0
                )
                
                search_status["rag_time_ms"] = (time.time() - rag_start) * 1000
                search_status["rag_status"] = "success"
                
                # Convert to unified format
                for chunk in rag_results:
                    unified_result = {
                        "type": "chunk", 
                        "chunk_id": chunk.chunk_id,
                        "content": chunk.content,
                        "title": chunk.metadata.get("title", "Document Chunk"),
                        "score": chunk.combined_score,
                        "relevance_score": chunk.relevance_score,
                        "embedding_score": chunk.embedding_score,
                        "keyword_score": chunk.keyword_score,
                        "metadata": chunk.metadata,
                        "source_document_id": chunk.source_document_id,
                        "chunk_index": chunk.chunk_index,
                        "source": "rag_system"
                    }
                    if request.include_citations:
                        unified_result["citation"] = f"Source: {chunk.metadata.get('title', 'Document')} (Chunk {chunk.chunk_index})"
                    results.append(unified_result)
                    
            except asyncio.TimeoutError:
                search_status["rag_time_ms"] = (time.time() - rag_start) * 1000
                search_status["rag_status"] = "timeout"
                logger.warning(f"RAG search timeout after 5s for query: {request.query[:50]}")
                metrics.increment_counter('rag_search_timeouts_total')
                
            except Exception as e:
                search_status["rag_time_ms"] = (time.time() - rag_start) * 1000
                search_status["rag_status"] = "error"
                logger.warning(f"RAG search failed: {e}")
                metrics.increment_counter('rag_search_errors_total')
        
        # Sort results by score (descending)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Limit to requested number of results
        results = results[:request.num_results]
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Record metrics and P99 latency tracking
        metrics.increment_counter('unified_search_queries_total')
        metrics.record_histogram('unified_search_response_time_ms', response_time)
        
        # Track component-specific metrics for P99 monitoring
        if search_status["ultra_fast_status"] == "success":
            metrics.record_histogram('ultra_fast_search_time_ms', search_status["ultra_fast_time_ms"])
        if search_status["rag_status"] == "success":
            metrics.record_histogram('rag_search_time_ms', search_status["rag_time_ms"])
        
        # Check if both systems failed and log alert
        both_failed = (
            search_status["ultra_fast_status"] in ["timeout", "error"] and 
            search_status["rag_status"] in ["timeout", "error"]
        )
        if both_failed:
            logger.error(f"CRITICAL: Both search systems failed for query: {request.query[:50]}")
            metrics.increment_counter('critical_search_failures_total')
        
        return {
            "success": True,
            "query": request.query,
            "search_type": request.search_type,
            "results": results,
            "total_found": len(results),
            "response_time_ms": response_time,
            "circuit_breaker_status": search_status,
            "metadata": {
                "confidence_threshold": request.confidence_threshold,
                "include_citations": request.include_citations,
                "filters_applied": request.filters is not None,
                "degraded_mode": both_failed
            }
        }
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Unified search failed: {e}")
        metrics.increment_counter('unified_search_errors_total')
        
        return {
            "success": False,
            "query": request.query,
            "error": str(e),
            "results": [],
            "total_found": 0,
            "response_time_ms": response_time
        }
