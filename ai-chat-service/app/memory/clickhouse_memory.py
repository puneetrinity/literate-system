"""
ClickHouse-based conversation memory for cold storage.

Extends the existing ClickHouse client with conversation-specific tables:
- Conversation summaries with quality metrics
- Long-term memory embeddings with HNSW indexing
- User memory preferences and learning
- Conversation quality and performance metrics
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

import structlog

from app.storage.clickhouse_client import ClickHouseManager

logger = structlog.get_logger(__name__)


class ConversationClickHouseManager(ClickHouseManager):
    """
    Extended ClickHouse manager for conversation memory cold storage.
    
    Manages:
    - Conversation summaries with versioning
    - Embeddings for semantic search with HNSW indexing
    - User memory preferences and patterns
    - Quality metrics and performance analytics
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Memory-specific settings
        self.embedding_dimension = 384  # sentence-transformers/all-MiniLM-L6-v2
        self.max_embedding_batch_size = 100
        
        logger.info(
            "conversation_clickhouse_manager_initialized",
            embedding_dimension=self.embedding_dimension
        )
    
    async def _create_conversation_tables(self):
        """Create conversation-specific tables in ClickHouse"""
        
        tables = {
            'conversation_summaries': """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id UUID DEFAULT generateUUIDv4(),
                session_id String,
                user_id Nullable(String),
                summary String,
                version UInt32,
                created_at DateTime64(3) DEFAULT now64(),
                
                -- Summary metadata
                token_count UInt32,
                message_count UInt32,
                compression_ratio Float32,
                summary_quality_score Float32,
                
                -- Context information
                conversation_length_at_summary UInt32,
                topics_covered Array(String),
                user_expertise_level LowCardinality(String) DEFAULT 'intermediate',
                
                -- Performance metrics
                generation_time_ms Float32,
                model_used LowCardinality(String),
                
                date Date DEFAULT toDate(created_at)
            ) ENGINE = MergeTree()
            PARTITION BY date
            ORDER BY (session_id, version, created_at)
            TTL created_at + INTERVAL 365 DAY
            SETTINGS index_granularity = 8192
            """,
            
            'conversation_embeddings': """
            CREATE TABLE IF NOT EXISTS conversation_embeddings (
                id UUID DEFAULT generateUUIDv4(),
                session_id String,
                user_id Nullable(String),
                content String,
                embedding Array(Float32),
                
                -- Content metadata
                content_type LowCardinality(String) DEFAULT 'fact', -- fact, preference, decision, topic
                importance_score Float32 DEFAULT 0.5,
                confidence_score Float32 DEFAULT 0.5,
                
                -- Context information
                message_index Nullable(UInt32),
                conversation_turn Nullable(UInt32),
                timestamp_in_conversation Nullable(UInt64),
                
                -- Extraction metadata
                extraction_method LowCardinality(String) DEFAULT 'rule_based',
                extracted_at DateTime64(3) DEFAULT now64(),
                model_used Nullable(String),
                
                date Date DEFAULT toDate(extracted_at),
                
                -- Vector similarity index
                INDEX embedding_idx embedding TYPE vector_similarity('hnsw', 'cosineDistance') GRANULARITY 1000
            ) ENGINE = MergeTree()
            PARTITION BY date
            ORDER BY (session_id, importance_score DESC, extracted_at)
            TTL extracted_at + INTERVAL 365 DAY
            SETTINGS index_granularity = 4096
            """,
            
            'user_memory': """
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id String,
                memory_key String,
                memory_value String,
                memory_type LowCardinality(String) DEFAULT 'preference', -- preference, fact, pattern, goal
                
                -- Confidence and learning
                confidence Float32 DEFAULT 0.5,
                update_count UInt32 DEFAULT 1,
                last_updated DateTime64(3) DEFAULT now64(),
                first_observed DateTime64(3) DEFAULT now64(),
                
                -- Source information
                learned_from_sessions Array(String),
                extraction_confidence Float32 DEFAULT 0.5,
                
                -- Metadata
                metadata String DEFAULT '{}', -- JSON
                
                date Date DEFAULT toDate(last_updated)
            ) ENGINE = ReplacingMergeTree(last_updated)
            PARTITION BY date
            ORDER BY (user_id, memory_type, memory_key)
            TTL last_updated + INTERVAL 730 DAY -- 2 years
            SETTINGS index_granularity = 8192
            """,
            
            'conversation_quality_metrics': """
            CREATE TABLE IF NOT EXISTS conversation_quality_metrics (
                session_id String,
                user_id Nullable(String),
                
                -- Quality scores
                coherence_score Float32,
                coherence_maintained UInt8,
                context_relevance_score Float32,
                user_satisfaction_inferred Float32,
                topic_continuity_score Float32,
                
                -- Memory effectiveness
                memory_efficiency Float32,
                context_utilization_rate Float32,
                memory_tokens_used UInt32,
                memory_budget_allocated UInt32,
                
                -- Performance metrics
                response_time_ms Float32,
                memory_retrieval_time_ms Float32,
                cache_hit_rate Float32,
                
                -- Cost metrics
                estimated_cost_cents Float32,
                cost_per_quality_unit Float32,
                memory_cost_ratio Float32,
                
                -- Routing information
                routing_arm_used LowCardinality(String),
                bandit_confidence Float32,
                
                -- Timestamp
                measured_at DateTime64(3) DEFAULT now64(),
                date Date DEFAULT toDate(measured_at)
            ) ENGINE = MergeTree()
            PARTITION BY date
            ORDER BY (session_id, measured_at)
            TTL measured_at + INTERVAL 90 DAY
            SETTINGS index_granularity = 8192
            """,
            
            'conversation_analytics': """
            CREATE TABLE IF NOT EXISTS conversation_analytics (
                date Date,
                hour UInt8,
                
                -- Aggregated metrics
                total_conversations UInt64,
                avg_conversation_length Float32,
                avg_coherence_score Float32,
                avg_memory_efficiency Float32,
                avg_response_time_ms Float32,
                
                -- Quality distribution
                high_quality_conversations UInt64, -- coherence > 0.7
                medium_quality_conversations UInt64, -- 0.4 <= coherence <= 0.7
                low_quality_conversations UInt64, -- coherence < 0.4
                
                -- Memory usage
                avg_memory_tokens_used Float32,
                avg_cache_hit_rate Float32,
                total_summaries_generated UInt64,
                total_embeddings_stored UInt64,
                
                -- Cost analytics
                total_cost_cents Float32,
                avg_cost_per_conversation Float32,
                cost_efficiency_score Float32,
                
                -- Routing arm performance
                routing_arm_distribution Map(String, UInt64),
                arm_success_rates Map(String, Float32)
            ) ENGINE = SummingMergeTree()
            PARTITION BY date
            ORDER BY (date, hour)
            TTL date + INTERVAL 365 DAY
            """
        }
        
        try:
            for table_name, create_sql in tables.items():
                self.client.command(create_sql)
                logger.info(f"conversation_table_created", table=table_name)
                
            logger.info("all_conversation_tables_created")
            return True
            
        except Exception as e:
            logger.error("conversation_table_creation_failed", error=str(e))
            return False
    
    async def initialize_conversation_storage(self) -> bool:
        """Initialize conversation-specific storage"""
        
        # First initialize base ClickHouse
        base_success = await self.initialize()
        if not base_success:
            return False
        
        # Create conversation tables
        return await self._create_conversation_tables()
    
    async def store_conversation_summary(
        self, 
        session_id: str, 
        summary: str, 
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store conversation summary with metadata.
        
        Args:
            session_id: Conversation session identifier
            summary: Summary text content
            metadata: Summary metadata (token_count, quality_score, etc.)
            user_id: Optional user identifier
            
        Returns:
            Success boolean
        """
        
        try:
            record = {
                'session_id': session_id,
                'user_id': user_id,
                'summary': summary,
                'version': metadata.get('version', 1),
                'token_count': metadata.get('token_count', 0),
                'message_count': metadata.get('message_count', 0),
                'compression_ratio': metadata.get('compression_ratio', 0.0),
                'summary_quality_score': metadata.get('quality_score', 0.5),
                'conversation_length_at_summary': metadata.get('conversation_length', 0),
                'topics_covered': metadata.get('topics', []),
                'user_expertise_level': metadata.get('expertise_level', 'intermediate'),
                'generation_time_ms': metadata.get('generation_time_ms', 0.0),
                'model_used': metadata.get('model_used', 'unknown')
            }
            
            if not self.connected:
                logger.warning("clickhouse_not_connected_skipping_summary_storage")
                return False
            
            self.client.insert('conversation_summaries', [record])
            
            logger.debug(
                "conversation_summary_stored",
                session_id=session_id,
                version=record['version'],
                quality_score=record['summary_quality_score']
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_store_conversation_summary",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def store_conversation_embeddings(
        self, 
        session_id: str, 
        embeddings_data: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store conversation embeddings for semantic search.
        
        Args:
            session_id: Conversation session identifier
            embeddings_data: List of embedding records with content and vectors
            user_id: Optional user identifier
            
        Returns:
            Success boolean
        """
        
        try:
            if not embeddings_data:
                return True
            
            records = []
            for emb_data in embeddings_data:
                record = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'content': emb_data['content'],
                    'embedding': emb_data['embedding'],
                    'content_type': emb_data.get('content_type', 'fact'),
                    'importance_score': emb_data.get('importance_score', 0.5),
                    'confidence_score': emb_data.get('confidence_score', 0.5),
                    'message_index': emb_data.get('message_index'),
                    'conversation_turn': emb_data.get('conversation_turn'),
                    'timestamp_in_conversation': emb_data.get('timestamp_in_conversation'),
                    'extraction_method': emb_data.get('extraction_method', 'rule_based'),
                    'model_used': emb_data.get('model_used')
                }
                records.append(record)
            
            if not self.connected:
                logger.warning("clickhouse_not_connected_skipping_embeddings_storage")
                return False
            
            # Batch insert for efficiency
            batch_size = min(self.max_embedding_batch_size, len(records))
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                self.client.insert('conversation_embeddings', batch)
            
            logger.debug(
                "conversation_embeddings_stored",
                session_id=session_id,
                count=len(records),
                user_id=user_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_store_conversation_embeddings",
                session_id=session_id,
                count=len(embeddings_data) if embeddings_data else 0,
                error=str(e)
            )
            return False
    
    async def search_similar_content(
        self, 
        query_embedding: List[float], 
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        min_importance: float = 0.3,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity.
        
        Args:
            query_embedding: Query vector for similarity search
            session_id: Optional session filter
            user_id: Optional user filter
            content_types: Optional content type filters
            min_importance: Minimum importance score threshold
            limit: Maximum number of results
            
        Returns:
            List of similar content with metadata
        """
        
        try:
            if not self.connected:
                logger.warning("clickhouse_not_connected_returning_empty_results")
                return []
            
            # Build WHERE clause
            where_conditions = [f"importance_score >= {min_importance}"]
            
            if session_id:
                where_conditions.append(f"session_id = '{session_id}'")
            
            if user_id:
                where_conditions.append(f"user_id = '{user_id}'")
            
            if content_types:
                types_str = "', '".join(content_types)
                where_conditions.append(f"content_type IN ('{types_str}')")
            
            where_clause = " AND ".join(where_conditions)
            
            # Vector similarity query
            sql = f"""
            SELECT 
                content,
                content_type,
                importance_score,
                confidence_score,
                session_id,
                user_id,
                message_index,
                conversation_turn,
                extracted_at,
                cosineDistance(embedding, {query_embedding}) as similarity_distance
            FROM conversation_embeddings
            WHERE {where_clause}
            ORDER BY similarity_distance ASC
            LIMIT {limit}
            """
            
            results = self.client.query(sql).result_rows
            
            # Convert to structured format
            similar_content = []
            for row in results:
                similar_content.append({
                    'content': row[0],
                    'content_type': row[1],
                    'importance_score': float(row[2]),
                    'confidence_score': float(row[3]),
                    'session_id': row[4],
                    'user_id': row[5],
                    'message_index': row[6],
                    'conversation_turn': row[7],
                    'extracted_at': str(row[8]),
                    'similarity_score': max(0.0, 1.0 - float(row[9]))  # Convert distance to similarity
                })
            
            logger.debug(
                "similar_content_search_completed",
                results_count=len(similar_content),
                session_id=session_id,
                user_id=user_id,
                min_importance=min_importance
            )
            
            return similar_content
            
        except Exception as e:
            logger.error(
                "similar_content_search_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            return []
    
    async def store_user_memory(
        self, 
        user_id: str, 
        memory_entries: List[Dict[str, Any]]
    ) -> bool:
        """
        Store or update user memory entries.
        
        Args:
            user_id: User identifier
            memory_entries: List of memory records
            
        Returns:
            Success boolean
        """
        
        try:
            if not memory_entries:
                return True
            
            records = []
            for entry in memory_entries:
                record = {
                    'user_id': user_id,
                    'memory_key': entry['key'],
                    'memory_value': entry['value'],
                    'memory_type': entry.get('type', 'preference'),
                    'confidence': entry.get('confidence', 0.5),
                    'update_count': entry.get('update_count', 1),
                    'learned_from_sessions': entry.get('sessions', []),
                    'extraction_confidence': entry.get('extraction_confidence', 0.5),
                    'metadata': json.dumps(entry.get('metadata', {}))
                }
                records.append(record)
            
            if not self.connected:
                logger.warning("clickhouse_not_connected_skipping_user_memory_storage")
                return False
            
            self.client.insert('user_memory', records)
            
            logger.debug(
                "user_memory_stored",
                user_id=user_id,
                entries_count=len(records)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_store_user_memory",
                user_id=user_id,
                error=str(e)
            )
            return False
    
    async def get_user_memory(
        self, 
        user_id: str, 
        memory_types: Optional[List[str]] = None,
        min_confidence: float = 0.3
    ) -> Dict[str, Any]:
        """
        Retrieve user memory entries.
        
        Args:
            user_id: User identifier
            memory_types: Optional filter by memory types
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dictionary of memory entries by type
        """
        
        try:
            if not self.connected:
                return {}
            
            # Build WHERE clause
            where_conditions = [
                f"user_id = '{user_id}'",
                f"confidence >= {min_confidence}"
            ]
            
            if memory_types:
                types_str = "', '".join(memory_types)
                where_conditions.append(f"memory_type IN ('{types_str}')")
            
            where_clause = " AND ".join(where_conditions)
            
            sql = f"""
            SELECT 
                memory_key,
                memory_value,
                memory_type,
                confidence,
                update_count,
                last_updated,
                metadata
            FROM user_memory
            WHERE {where_clause}
            ORDER BY memory_type, confidence DESC, last_updated DESC
            """
            
            results = self.client.query(sql).result_rows
            
            # Organize by memory type
            memory_by_type = {}
            for row in results:
                memory_type = row[2]
                if memory_type not in memory_by_type:
                    memory_by_type[memory_type] = {}
                
                memory_by_type[memory_type][row[0]] = {
                    'value': row[1],
                    'confidence': float(row[3]),
                    'update_count': int(row[4]),
                    'last_updated': str(row[5]),
                    'metadata': json.loads(row[6]) if row[6] else {}
                }
            
            logger.debug(
                "user_memory_retrieved",
                user_id=user_id,
                types_count=len(memory_by_type),
                total_entries=len(results)
            )
            
            return memory_by_type
            
        except Exception as e:
            logger.error(
                "failed_to_get_user_memory",
                user_id=user_id,
                error=str(e)
            )
            return {}
    
    async def store_conversation_quality_metrics(
        self, 
        session_id: str, 
        metrics: Dict[str, Any],
        user_id: Optional[str] = None,
        routing_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store conversation quality and performance metrics.
        
        Args:
            session_id: Conversation session identifier
            metrics: Quality and performance metrics
            user_id: Optional user identifier
            routing_info: Optional routing/bandit information
            
        Returns:
            Success boolean
        """
        
        try:
            record = {
                'session_id': session_id,
                'user_id': user_id,
                
                # Quality scores
                'coherence_score': metrics.get('coherence_score', 0.5),
                'coherence_maintained': 1 if metrics.get('coherence_maintained', False) else 0,
                'context_relevance_score': metrics.get('context_relevance_score', 0.5),
                'user_satisfaction_inferred': metrics.get('user_satisfaction_inferred', 0.5),
                'topic_continuity_score': metrics.get('topic_continuity_score', 0.5),
                
                # Memory effectiveness
                'memory_efficiency': metrics.get('memory_efficiency', 0.5),
                'context_utilization_rate': metrics.get('context_utilization_rate', 0.5),
                'memory_tokens_used': metrics.get('memory_tokens_used', 0),
                'memory_budget_allocated': metrics.get('memory_budget_allocated', 0),
                
                # Performance metrics
                'response_time_ms': metrics.get('response_time_ms', 0.0),
                'memory_retrieval_time_ms': metrics.get('memory_retrieval_time_ms', 0.0),
                'cache_hit_rate': metrics.get('cache_hit_rate', 0.0),
                
                # Cost metrics
                'estimated_cost_cents': metrics.get('estimated_cost_cents', 0.0),
                'cost_per_quality_unit': metrics.get('cost_per_quality_unit', 0.0),
                'memory_cost_ratio': metrics.get('memory_cost_ratio', 0.0),
                
                # Routing information
                'routing_arm_used': routing_info.get('arm_id', 'unknown') if routing_info else 'unknown',
                'bandit_confidence': routing_info.get('confidence', 0.0) if routing_info else 0.0
            }
            
            if not self.connected:
                logger.warning("clickhouse_not_connected_skipping_metrics_storage")
                return False
            
            self.client.insert('conversation_quality_metrics', [record])
            
            logger.debug(
                "conversation_quality_metrics_stored",
                session_id=session_id,
                coherence_score=record['coherence_score'],
                memory_efficiency=record['memory_efficiency']
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_store_quality_metrics",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def get_conversation_analytics(
        self, 
        days: int = 7,
        user_id: Optional[str] = None,
        routing_arm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get conversation analytics and performance insights.
        
        Args:
            days: Number of days to analyze
            user_id: Optional user filter
            routing_arm: Optional routing arm filter
            
        Returns:
            Analytics data dictionary
        """
        
        try:
            if not self.connected:
                return {"error": "ClickHouse not connected"}
            
            # Build base WHERE clause
            where_conditions = [f"measured_at >= now() - INTERVAL {days} DAY"]
            
            if user_id:
                where_conditions.append(f"user_id = '{user_id}'")
            
            if routing_arm:
                where_conditions.append(f"routing_arm_used = '{routing_arm}'")
            
            where_clause = " AND ".join(where_conditions)
            
            # Overall metrics
            overall_sql = f"""
            SELECT 
                count() as total_conversations,
                avg(coherence_score) as avg_coherence,
                avg(memory_efficiency) as avg_memory_efficiency,
                avg(response_time_ms) as avg_response_time,
                avg(cache_hit_rate) as avg_cache_hit_rate,
                sum(coherence_maintained) / count() as coherence_maintenance_rate,
                avg(cost_per_quality_unit) as avg_cost_per_quality
            FROM conversation_quality_metrics
            WHERE {where_clause}
            """
            
            # Quality distribution
            quality_sql = f"""
            SELECT 
                countIf(coherence_score >= 0.7) as high_quality,
                countIf(coherence_score >= 0.4 AND coherence_score < 0.7) as medium_quality,
                countIf(coherence_score < 0.4) as low_quality
            FROM conversation_quality_metrics
            WHERE {where_clause}
            """
            
            # Routing arm performance
            routing_sql = f"""
            SELECT 
                routing_arm_used,
                count() as usage_count,
                avg(coherence_score) as avg_coherence,
                avg(memory_efficiency) as avg_efficiency,
                avg(response_time_ms) as avg_response_time,
                avg(bandit_confidence) as avg_confidence
            FROM conversation_quality_metrics
            WHERE {where_clause}
            GROUP BY routing_arm_used
            ORDER BY usage_count DESC
            """
            
            # Time trends
            trends_sql = f"""
            SELECT 
                toDate(measured_at) as date,
                avg(coherence_score) as daily_coherence,
                avg(memory_efficiency) as daily_efficiency,
                count() as daily_conversations
            FROM conversation_quality_metrics
            WHERE {where_clause}
            GROUP BY date
            ORDER BY date DESC
            LIMIT {days}
            """
            
            # Execute queries
            overall_result = self.client.query(overall_sql).result_rows[0]
            quality_result = self.client.query(quality_sql).result_rows[0]
            routing_results = self.client.query(routing_sql).result_rows
            trends_results = self.client.query(trends_sql).result_rows
            
            # Format results
            analytics = {
                'period_days': days,
                'overall_metrics': {
                    'total_conversations': int(overall_result[0]),
                    'avg_coherence_score': round(float(overall_result[1]), 3),
                    'avg_memory_efficiency': round(float(overall_result[2]), 3),
                    'avg_response_time_ms': round(float(overall_result[3]), 1),
                    'avg_cache_hit_rate': round(float(overall_result[4]), 3),
                    'coherence_maintenance_rate': round(float(overall_result[5]), 3),
                    'avg_cost_per_quality': round(float(overall_result[6]), 2)
                },
                'quality_distribution': {
                    'high_quality': int(quality_result[0]),
                    'medium_quality': int(quality_result[1]),
                    'low_quality': int(quality_result[2])
                },
                'routing_performance': [
                    {
                        'arm': row[0],
                        'usage_count': int(row[1]),
                        'avg_coherence': round(float(row[2]), 3),
                        'avg_efficiency': round(float(row[3]), 3),
                        'avg_response_time_ms': round(float(row[4]), 1),
                        'avg_confidence': round(float(row[5]), 3)
                    }
                    for row in routing_results
                ],
                'daily_trends': [
                    {
                        'date': str(row[0]),
                        'coherence_score': round(float(row[1]), 3),
                        'memory_efficiency': round(float(row[2]), 3),
                        'conversation_count': int(row[3])
                    }
                    for row in trends_results
                ]
            }
            
            return analytics
            
        except Exception as e:
            logger.error(
                "failed_to_get_conversation_analytics",
                error=str(e),
                days=days,
                user_id=user_id
            )
            return {"error": str(e)}


# Global instance factory
def create_conversation_clickhouse_manager(**kwargs) -> ConversationClickHouseManager:
    """Create conversation ClickHouse manager with default settings"""
    # Remove mock parameter if present (for testing)
    filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'mock'}
    return ConversationClickHouseManager(**filtered_kwargs)