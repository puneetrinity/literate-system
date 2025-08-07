"""
Asynchronous conversation summarization service.

Uses phi3:mini for cost-effective, fast summarization of conversation history.
Integrates with Redis queue for background processing and ClickHouse for storage.
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog

from app.models.manager import ModelManager
from app.memory.redis_memory import ConversationMemoryCache
from app.memory.clickhouse_memory import ConversationClickHouseManager

logger = structlog.get_logger(__name__)


class SummarizationPriority(Enum):
    """Summarization task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SummarizationTask:
    """Summarization task data structure"""
    session_id: str
    user_id: Optional[str]
    priority: SummarizationPriority
    queued_at: float
    max_retries: int = 3
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'priority': self.priority.value,
            'queued_at': self.queued_at,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SummarizationTask':
        return cls(
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            priority=SummarizationPriority(data['priority']),
            queued_at=data['queued_at'],
            max_retries=data.get('max_retries', 3),
            retry_count=data.get('retry_count', 0),
            metadata=data.get('metadata', {})
        )


class AsyncSummarizationService:
    """
    Background service for conversation summarization using phi3:mini.
    
    Features:
    - Redis-based task queue with priority handling
    - Intelligent fact extraction and embedding generation
    - Quality assessment and metadata tracking
    - Retry logic with exponential backoff
    - Performance monitoring and metrics
    """
    
    def __init__(
        self,
        model_manager: ModelManager,
        redis_memory: ConversationMemoryCache,
        clickhouse_memory: ConversationClickHouseManager,
        summarization_model: str = "phi3:mini",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.model_manager = model_manager
        self.redis_memory = redis_memory
        self.clickhouse_memory = clickhouse_memory
        
        # Model configuration
        self.summarization_model = summarization_model
        self.embedding_model = embedding_model
        
        # Queue configuration
        self.queue_name = "conversation_summary_queue"
        self.error_queue_name = "conversation_summary_errors"
        self.max_queue_size = 1000
        self.batch_processing_size = 5
        
        # Processing configuration
        self.min_messages_for_summary = 5
        self.max_summary_tokens = 500
        self.summary_overlap_tokens = 100  # Overlap between old and new content
        
        # Quality thresholds
        self.min_summary_quality = 0.3
        self.min_fact_confidence = 0.4
        
        # Worker control
        self.workers_running = False
        self.worker_tasks = []
        self.processing_stats = {
            'total_processed': 0,
            'successful_summaries': 0,
            'failed_summaries': 0,
            'average_processing_time': 0.0,
            'queue_size': 0
        }
        
        logger.info(
            "async_summarization_service_initialized",
            summarization_model=summarization_model,
            embedding_model=embedding_model,
            min_messages=self.min_messages_for_summary
        )
    
    async def queue_summarization(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        priority: SummarizationPriority = SummarizationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Queue conversation for summarization.
        
        Args:
            session_id: Conversation session identifier
            user_id: Optional user identifier
            priority: Task priority level
            metadata: Optional task metadata
            
        Returns:
            Success boolean
        """
        
        try:
            # Check if queue is full
            queue_size = await self._get_queue_size()
            if queue_size >= self.max_queue_size:
                logger.warning(
                    "summarization_queue_full",
                    queue_size=queue_size,
                    max_size=self.max_queue_size,
                    session_id=session_id
                )
                return False
            
            # Create task
            task = SummarizationTask(
                session_id=session_id,
                user_id=user_id,
                priority=priority,
                queued_at=time.time(),
                metadata=metadata or {}
            )
            
            # Determine queue key based on priority
            queue_key = self._get_priority_queue_key(priority)
            
            # Add to queue
            if hasattr(self.redis_memory.redis, 'redis') and self.redis_memory.redis.redis:
                await self.redis_memory.redis.redis.lpush(
                    queue_key,
                    json.dumps(task.to_dict())
                )
            else:
                # Fallback for testing
                await self.redis_memory.redis.set(
                    f"fallback_queue:{session_id}",
                    task.to_dict(),
                    3600  # 1 hour TTL
                )
            
            logger.debug(
                "summarization_task_queued",
                session_id=session_id,
                priority=priority.value,
                queue_size=queue_size + 1
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_queue_summarization",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def start_workers(self, num_workers: int = 2) -> None:
        """Start background worker tasks"""
        
        if self.workers_running:
            logger.warning("workers_already_running")
            return
        
        self.workers_running = True
        
        # Start worker tasks
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self.worker_tasks.append(task)
        
        # Start metrics collection task
        metrics_task = asyncio.create_task(self._metrics_collection_loop())
        self.worker_tasks.append(metrics_task)
        
        logger.info(
            "summarization_workers_started",
            worker_count=num_workers
        )
    
    async def stop_workers(self) -> None:
        """Stop background worker tasks"""
        
        self.workers_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for cancellation
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        
        logger.info("summarization_workers_stopped")
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop for processing summarization tasks"""
        
        logger.info("summarization_worker_started", worker_id=worker_id)
        
        while self.workers_running:
            try:
                # Get next task (priority order: urgent, high, normal, low)
                task = await self._get_next_task()
                
                if task:
                    start_time = time.time()
                    success = await self._process_summarization_task(task)
                    processing_time = time.time() - start_time
                    
                    # Update statistics
                    self.processing_stats['total_processed'] += 1
                    if success:
                        self.processing_stats['successful_summaries'] += 1
                    else:
                        self.processing_stats['failed_summaries'] += 1
                    
                    # Update average processing time
                    total_processed = self.processing_stats['total_processed']
                    current_avg = self.processing_stats['average_processing_time']
                    self.processing_stats['average_processing_time'] = (
                        (current_avg * (total_processed - 1) + processing_time) / total_processed
                    )
                    
                    logger.debug(
                        "summarization_task_completed",
                        worker_id=worker_id,
                        session_id=task.session_id,
                        success=success,
                        processing_time_ms=round(processing_time * 1000, 1)
                    )
                
                else:
                    # No tasks available, wait before checking again
                    await asyncio.sleep(5)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "worker_loop_error",
                    worker_id=worker_id,
                    error=str(e)
                )
                await asyncio.sleep(10)  # Back off on error
        
        logger.info("summarization_worker_stopped", worker_id=worker_id)
    
    async def _get_next_task(self) -> Optional[SummarizationTask]:
        """Get next task from priority queues"""
        
        # Priority order
        priorities = [
            SummarizationPriority.URGENT,
            SummarizationPriority.HIGH,
            SummarizationPriority.NORMAL,
            SummarizationPriority.LOW
        ]
        
        try:
            for priority in priorities:
                queue_key = self._get_priority_queue_key(priority)
                
                if hasattr(self.redis_memory.redis, 'redis') and self.redis_memory.redis.redis:
                    # Blocking pop with timeout
                    result = await self.redis_memory.redis.redis.brpop(queue_key, timeout=1)
                    
                    if result:
                        _, task_json = result
                        task_data = json.loads(task_json)
                        return SummarizationTask.from_dict(task_data)
                
            return None
            
        except Exception as e:
            logger.error("failed_to_get_next_task", error=str(e))
            return None
    
    async def _process_summarization_task(self, task: SummarizationTask) -> bool:
        """Process a single summarization task"""
        
        try:
            # Get conversation messages
            conversation_data = await self.redis_memory.get_recent_messages(task.session_id)
            
            if not conversation_data['success']:
                logger.error(
                    "failed_to_get_conversation_for_summary",
                    session_id=task.session_id,
                    error=conversation_data.get('error')
                )
                return False
            
            messages = conversation_data['messages']
            
            # Check if we have enough messages
            if len(messages) < self.min_messages_for_summary:
                logger.debug(
                    "insufficient_messages_for_summary",
                    session_id=task.session_id,
                    message_count=len(messages),
                    min_required=self.min_messages_for_summary
                )
                return True  # Not an error, just skip
            
            # Generate summary
            summary_result = await self._generate_summary(messages, task)
            
            if not summary_result['success']:
                logger.error(
                    "summary_generation_failed",
                    session_id=task.session_id,
                    error=summary_result.get('error')
                )
                await self._handle_failed_task(task, summary_result.get('error', 'Unknown error'))
                return False
            
            # Store summary in Redis (hot cache)
            redis_success = await self.redis_memory.store_summary(
                task.session_id,
                summary_result['summary'],
                summary_result['metadata']
            )
            
            # Store summary in ClickHouse (cold storage)
            clickhouse_success = await self.clickhouse_memory.store_conversation_summary(
                task.session_id,
                summary_result['summary'],
                summary_result['metadata'],
                task.user_id
            )
            
            # Extract and store facts as embeddings
            if summary_result.get('facts'):
                embeddings_success = await self._store_conversation_facts(
                    task.session_id,
                    summary_result['facts'],
                    task.user_id
                )
            else:
                embeddings_success = True
            
            success = redis_success and clickhouse_success and embeddings_success
            
            logger.info(
                "summarization_completed",
                session_id=task.session_id,
                summary_length=len(summary_result['summary']),
                quality_score=summary_result['metadata'].get('quality_score', 0.0),
                facts_extracted=len(summary_result.get('facts', [])),
                redis_stored=redis_success,
                clickhouse_stored=clickhouse_success,
                embeddings_stored=embeddings_success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "summarization_task_processing_error",
                session_id=task.session_id,
                error=str(e)
            )
            await self._handle_failed_task(task, str(e))
            return False
    
    async def _generate_summary(
        self, 
        messages: List[Dict[str, Any]], 
        task: SummarizationTask
    ) -> Dict[str, Any]:
        """Generate conversation summary using phi3:mini"""
        
        try:
            # Prepare conversation text
            conversation_text = self._format_conversation_for_summary(messages)
            
            # Create summarization prompt
            prompt = self._create_summarization_prompt(
                conversation_text,
                task.metadata.get('context', {})
            )
            
            # Generate summary using phi3:mini
            start_time = time.time()
            
            summary_response = await self.model_manager.generate(
                model=self.summarization_model,
                prompt=prompt,
                max_tokens=self.max_summary_tokens,
                temperature=0.3,  # Low temperature for consistency
                stop_sequences=["</summary>", "\n\n---"]
            )
            
            generation_time = time.time() - start_time
            
            if not summary_response or 'content' not in summary_response:
                return {
                    'success': False,
                    'error': 'No summary generated'
                }
            
            summary_text = summary_response['content'].strip()
            
            # Assess summary quality
            quality_score = self._assess_summary_quality(summary_text, messages)
            
            if quality_score < self.min_summary_quality:
                return {
                    'success': False,
                    'error': f'Summary quality too low: {quality_score}'
                }
            
            # Extract facts from conversation
            facts = await self._extract_conversation_facts(messages)
            
            # Calculate compression ratio
            input_tokens = sum(msg.get('tokens', 100) for msg in messages)
            summary_tokens = len(summary_text.split()) * 1.3  # Rough estimate
            compression_ratio = input_tokens / summary_tokens if summary_tokens > 0 else 0
            
            # Prepare metadata
            metadata = {
                'version': 1,
                'token_count': int(summary_tokens),
                'message_count': len(messages),
                'compression_ratio': compression_ratio,
                'quality_score': quality_score,
                'conversation_length': len(messages),
                'topics': self._extract_topics(summary_text),
                'expertise_level': self._infer_expertise_level(messages),
                'generation_time_ms': generation_time * 1000,
                'model_used': self.summarization_model,
                'created_at': time.time()
            }
            
            return {
                'success': True,
                'summary': summary_text,
                'metadata': metadata,
                'facts': facts
            }
            
        except Exception as e:
            logger.error(
                "summary_generation_error",
                session_id=task.session_id,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_conversation_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation messages for summarization"""
        
        formatted_parts = []
        
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # Simple formatting
            if role == 'user':
                formatted_parts.append(f"User: {content}")
            elif role == 'assistant':
                formatted_parts.append(f"Assistant: {content}")
            else:
                formatted_parts.append(f"{role.title()}: {content}")
        
        return "\n".join(formatted_parts)
    
    def _create_summarization_prompt(
        self, 
        conversation_text: str, 
        context: Dict[str, Any]
    ) -> str:
        """Create prompt for conversation summarization"""
        
        return f"""
You are an expert conversation analyst. Summarize the following conversation focusing on:

1. Key decisions and preferences mentioned by the user
2. Important facts and topics discussed
3. Current conversation context and direction
4. User's expertise level and communication style
5. Any goals or objectives identified

Requirements:
- Keep the summary under 400 words
- Focus on actionable information and user preferences
- Maintain chronological flow where relevant
- Include specific details that would be useful for continuing the conversation
- Use clear, concise language

<conversation>
{conversation_text}
</conversation>

<summary>
""".strip()
    
    def _assess_summary_quality(self, summary: str, messages: List[Dict[str, Any]]) -> float:
        """Assess quality of generated summary"""
        
        score = 0.5  # Base score
        
        # Length check (should be substantial but not too long)
        word_count = len(summary.split())
        if 50 <= word_count <= 300:
            score += 0.2
        elif word_count < 20:
            score -= 0.3
        elif word_count > 500:
            score -= 0.2
        
        # Content quality indicators
        quality_indicators = [
            'discussed', 'decided', 'mentioned', 'prefers', 'wants',
            'needs', 'explained', 'asked', 'suggested', 'concluded'
        ]
        
        indicator_count = sum(1 for indicator in quality_indicators if indicator in summary.lower())
        score += min(0.2, indicator_count * 0.05)
        
        # Structure check (multiple sentences)
        sentence_count = summary.count('.') + summary.count('!') + summary.count('?')
        if sentence_count >= 3:
            score += 0.1
        elif sentence_count < 2:
            score -= 0.1
        
        # Coherence check (basic)
        if any(phrase in summary.lower() for phrase in ['in summary', 'overall', 'the conversation', 'the user']):
            score += 0.1
        
        # Avoid repetition penalty
        words = summary.lower().split()
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.7:  # High repetition
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _extract_conversation_facts(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract important facts from conversation for embedding storage"""
        
        facts = []
        
        try:
            for i, msg in enumerate(messages):
                content = msg.get('content', '').lower()
                
                # Look for preference indicators
                if any(phrase in content for phrase in [
                    'i prefer', 'i like', 'i want', 'i need', 'i usually',
                    'my favorite', 'i always', 'i never', 'i tend to'
                ]):
                    facts.append({
                        'content': msg.get('content', ''),
                        'content_type': 'preference',
                        'importance_score': 0.8,
                        'confidence_score': 0.7,
                        'message_index': i,
                        'extraction_method': 'preference_pattern'
                    })
                
                # Look for decision indicators
                elif any(phrase in content for phrase in [
                    'decided', 'will use', 'going with', 'chose', 'selected',
                    'final decision', 'concluded', 'determined'
                ]):
                    facts.append({
                        'content': msg.get('content', ''),
                        'content_type': 'decision',
                        'importance_score': 0.9,
                        'confidence_score': 0.8,
                        'message_index': i,
                        'extraction_method': 'decision_pattern'
                    })
                
                # Look for factual statements
                elif any(phrase in content for phrase in [
                    'is located', 'works at', 'studies', 'specializes in',
                    'has experience', 'graduated from', 'lives in'
                ]):
                    facts.append({
                        'content': msg.get('content', ''),
                        'content_type': 'fact',
                        'importance_score': 0.6,
                        'confidence_score': 0.6,
                        'message_index': i,
                        'extraction_method': 'fact_pattern'
                    })
            
            # Limit facts to avoid noise
            facts = sorted(facts, key=lambda x: x['importance_score'], reverse=True)[:10]
            
            return facts
            
        except Exception as e:
            logger.error("fact_extraction_error", error=str(e))
            return []
    
    async def _store_conversation_facts(
        self, 
        session_id: str, 
        facts: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> bool:
        """Store extracted facts as embeddings"""
        
        try:
            if not facts:
                return True
            
            # Generate embeddings for facts
            embeddings_data = []
            
            for fact in facts:
                # Generate embedding
                embedding_response = await self.model_manager.generate_embedding(
                    model=self.embedding_model,
                    text=fact['content']
                )
                
                if embedding_response and 'embedding' in embedding_response:
                    fact['embedding'] = embedding_response['embedding']
                    fact['model_used'] = self.embedding_model
                    embeddings_data.append(fact)
            
            # Store in ClickHouse
            if embeddings_data:
                success = await self.clickhouse_memory.store_conversation_embeddings(
                    session_id,
                    embeddings_data,
                    user_id
                )
                
                logger.debug(
                    "conversation_facts_stored",
                    session_id=session_id,
                    facts_count=len(embeddings_data),
                    success=success
                )
                
                return success
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_store_conversation_facts",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    def _extract_topics(self, summary: str) -> List[str]:
        """Extract main topics from summary"""
        
        # Simple topic extraction (could be enhanced with NLP)
        topics = []
        
        # Look for topic indicators
        topic_patterns = [
            r'discuss(?:ed|ing)?\s+([a-zA-Z\s]{3,20})',
            r'talk(?:ed|ing)?\s+about\s+([a-zA-Z\s]{3,20})',
            r'focus(?:ed|ing)?\s+on\s+([a-zA-Z\s]{3,20})',
            r'regarding\s+([a-zA-Z\s]{3,20})',
            r'about\s+([a-zA-Z\s]{3,20})'
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, summary, re.IGNORECASE)
            for match in matches:
                topic = match.strip().lower()
                if len(topic) > 3 and topic not in topics:
                    topics.append(topic)
        
        return topics[:5]  # Limit to 5 topics
    
    def _infer_expertise_level(self, messages: List[Dict[str, Any]]) -> str:
        """Infer user expertise level from conversation"""
        
        technical_terms = 0
        total_words = 0
        
        for msg in messages[-10:]:  # Look at recent messages
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                words = content.split()
                total_words += len(words)
                
                # Count technical indicators
                for word in words:
                    if (len(word) > 8 or 
                        word in ['algorithm', 'implementation', 'architecture', 'framework',
                               'methodology', 'optimization', 'configuration', 'integration',
                               'api', 'database', 'server', 'deployment', 'scalability']):
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
    
    async def _handle_failed_task(self, task: SummarizationTask, error: str) -> None:
        """Handle failed summarization task with retry logic"""
        
        task.retry_count += 1
        
        if task.retry_count < task.max_retries:
            # Exponential backoff
            delay = 2 ** task.retry_count
            
            # Re-queue with delay
            await asyncio.sleep(delay)
            
            # Add back to appropriate queue
            queue_key = self._get_priority_queue_key(task.priority)
            
            if hasattr(self.redis_memory.redis, 'redis') and self.redis_memory.redis.redis:
                await self.redis_memory.redis.redis.lpush(
                    queue_key,
                    json.dumps(task.to_dict())
                )
            
            logger.info(
                "summarization_task_retried",
                session_id=task.session_id,
                retry_count=task.retry_count,
                delay=delay,
                error=error
            )
        
        else:
            # Max retries exceeded, move to error queue
            error_task = {
                **task.to_dict(),
                'final_error': error,
                'failed_at': time.time()
            }
            
            if hasattr(self.redis_memory.redis, 'redis') and self.redis_memory.redis.redis:
                await self.redis_memory.redis.redis.lpush(
                    self.error_queue_name,
                    json.dumps(error_task)
                )
            
            logger.error(
                "summarization_task_failed_permanently",
                session_id=task.session_id,
                retry_count=task.retry_count,
                error=error
            )
    
    def _get_priority_queue_key(self, priority: SummarizationPriority) -> str:
        """Get Redis queue key for priority level"""
        return f"{self.queue_name}:{priority.value}"
    
    async def _get_queue_size(self) -> int:
        """Get total queue size across all priority levels"""
        
        try:
            total_size = 0
            
            for priority in SummarizationPriority:
                queue_key = self._get_priority_queue_key(priority)
                
                if hasattr(self.redis_memory.redis, 'redis') and self.redis_memory.redis.redis:
                    size = await self.redis_memory.redis.redis.llen(queue_key)
                    total_size += size
            
            return total_size
            
        except Exception as e:
            logger.error("failed_to_get_queue_size", error=str(e))
            return 0
    
    async def _metrics_collection_loop(self) -> None:
        """Background task to collect and update processing metrics"""
        
        while self.workers_running:
            try:
                # Update queue size
                self.processing_stats['queue_size'] = await self._get_queue_size()
                
                # Log metrics periodically
                if self.processing_stats['total_processed'] % 10 == 0 and self.processing_stats['total_processed'] > 0:
                    logger.info(
                        "summarization_service_metrics",
                        **self.processing_stats
                    )
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("metrics_collection_error", error=str(e))
                await asyncio.sleep(60)  # Back off on error
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        
        return {
            'processing_stats': self.processing_stats.copy(),
            'configuration': {
                'summarization_model': self.summarization_model,
                'embedding_model': self.embedding_model,
                'min_messages_for_summary': self.min_messages_for_summary,
                'max_summary_tokens': self.max_summary_tokens,
                'workers_running': self.workers_running,
                'active_workers': len(self.worker_tasks)
            },
            'queue_configuration': {
                'queue_name': self.queue_name,
                'max_queue_size': self.max_queue_size,
                'batch_processing_size': self.batch_processing_size
            },
            'quality_thresholds': {
                'min_summary_quality': self.min_summary_quality,
                'min_fact_confidence': self.min_fact_confidence
            }
        }


# Factory function
def create_async_summarization_service(
    model_manager: ModelManager,
    redis_memory: ConversationMemoryCache,
    clickhouse_memory: ConversationClickHouseManager,
    **kwargs
) -> AsyncSummarizationService:
    """Create async summarization service with default configuration"""
    return AsyncSummarizationService(
        model_manager,
        redis_memory,
        clickhouse_memory,
        **kwargs
    )