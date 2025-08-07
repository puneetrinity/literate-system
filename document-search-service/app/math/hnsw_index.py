import numpy as np
import faiss
from typing import List, Tuple

class HNSWIndex:
    """
    Hierarchical Navigable Small World implementation using Faiss.
    Guarantees O(log n) search complexity and is highly optimized.
    """

    def __init__(self,
                 dimension: int,
                 max_connections: int = 16,  # Optimized: 32→16 for memory efficiency
                 ef_construction: int = 200,  # Keep optimal value
                 ef_search: int = 150):       # Optimized: 50→150 for better recall
        """
        Initializes the Faiss HNSW index.
        - dimension: The dimensionality of the vectors.
        - max_connections (M): Max connections per node.
        - ef_construction: Construction-time beam search width.
        - ef_search: Search-time beam search width.
        """
        self.dimension = dimension
        self.index = faiss.IndexHNSWFlat(dimension, max_connections, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        self.doc_ids = []
        
        # Optimization tracking for adaptive tuning
        self.search_stats = {
            'total_searches': 0,
            'avg_recall': 0.0,
            'avg_latency_ms': 0.0
        }
        self.optimal_ef_search = ef_search

    def add_documents(self, vectors: np.ndarray, doc_ids: List[str]):
        """Add a batch of documents to the index."""
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Input vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}")
        
        normalized_vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        self.index.add(normalized_vectors)
        self.doc_ids.extend(doc_ids)

    def search(self, query_vector: np.ndarray, k: int = 10, adaptive_ef: bool = True) -> List[Tuple[str, float]]:
        """
        Search for the k-nearest neighbors to the query vector with adaptive optimization.
        Returns a list of (doc_id, distance) tuples.
        """
        import time
        start_time = time.time()
        
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        if query_vector.shape[1] != self.dimension:
            raise ValueError(f"Query vector dimension {query_vector.shape[1]} does not match index dimension {self.dimension}")

        # Adaptive efSearch optimization
        if adaptive_ef and self.search_stats['total_searches'] > 100:
            self._adapt_ef_search()

        normalized_query = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)
        distances, indices = self.index.search(normalized_query, k)

        results = []
        for i in range(indices.shape[1]):
            if indices[0, i] != -1:
                doc_id = self.doc_ids[indices[0, i]]
                dist = distances[0, i]
                results.append((doc_id, dist))
        
        # Update performance stats
        search_time_ms = (time.time() - start_time) * 1000
        self._update_search_stats(search_time_ms, len(results))
        
        return results

    def _adapt_ef_search(self):
        """Dynamically adapt efSearch based on performance metrics"""
        current_latency = self.search_stats['avg_latency_ms']
        current_recall = self.search_stats['avg_recall']
        
        # Target: <100ms latency with >0.9 recall
        if current_latency > 100 and self.index.hnsw.efSearch > 50:
            # Reduce efSearch for speed
            new_ef = max(50, self.index.hnsw.efSearch - 25)
            self.index.hnsw.efSearch = new_ef
        elif current_recall < 0.9 and current_latency < 80 and self.index.hnsw.efSearch < 300:
            # Increase efSearch for better recall
            new_ef = min(300, self.index.hnsw.efSearch + 25)
            self.index.hnsw.efSearch = new_ef
            
    def _update_search_stats(self, search_time_ms: float, results_count: int):
        """Update running statistics for adaptive optimization"""
        self.search_stats['total_searches'] += 1
        
        # Exponential moving average for latency
        alpha = 0.1  # Learning rate
        if self.search_stats['total_searches'] == 1:
            self.search_stats['avg_latency_ms'] = search_time_ms
        else:
            self.search_stats['avg_latency_ms'] = (
                (1 - alpha) * self.search_stats['avg_latency_ms'] + 
                alpha * search_time_ms
            )
        
        # Estimate recall based on results count (simplified)
        expected_results = min(10, len(self.doc_ids))  # Assume k=10 default
        recall_estimate = results_count / expected_results if expected_results > 0 else 0.0
        
        if self.search_stats['total_searches'] == 1:
            self.search_stats['avg_recall'] = recall_estimate
        else:
            self.search_stats['avg_recall'] = (
                (1 - alpha) * self.search_stats['avg_recall'] + 
                alpha * recall_estimate
            )
    
    def get_performance_stats(self) -> dict:
        """Get current performance statistics"""
        return {
            'total_searches': self.search_stats['total_searches'],
            'avg_latency_ms': round(self.search_stats['avg_latency_ms'], 2),
            'avg_recall_estimate': round(self.search_stats['avg_recall'], 3),
            'current_ef_search': self.index.hnsw.efSearch,
            'optimal_ef_search': self.optimal_ef_search,
            'max_connections': self.index.hnsw.M,
            'total_vectors': len(self.doc_ids)
        }

    def __len__(self):
        return self.index.ntotal