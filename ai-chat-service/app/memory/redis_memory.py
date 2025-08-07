"""
Redis-based conversation memory manager.

Extends the existing Redis cache with conversation-specific functionality:
- Token-aware sliding window management
- Atomic conversation operations via Lua scripts
- Conversation summaries and metadata storage
- Performance metrics tracking
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import structlog

from app.cache.redis_client import CacheManager, CacheKey

logger = structlog.get_logger(__name__)


class ConversationMemoryCache:
    """
    Redis-based conversation memory with token-aware sliding window.
    
    Features:
    - Atomic operations via Lua scripts
    - Token budget management
    - Conversation metadata tracking
    - Performance monitoring
    """
    
    def __init__(self, redis_cache: CacheManager):
        self.redis = redis_cache
        self.DEFAULT_TOKEN_BUDGET = 4000
        self.DEFAULT_CONVERSATION_TTL = 86400  # 24 hours
        self.DEFAULT_SUMMARY_TTL = 3600  # 1 hour
        
        # Lua scripts for atomic operations
        self._init_lua_scripts()
        
        logger.info("conversation_memory_cache_initialized")
    
    def _init_lua_scripts(self):
        """Initialize Lua scripts for atomic Redis operations"""
        
        # Script for adding message with token management
        self.add_message_script = """
        local conv_key = KEYS[1]
        local token_key = KEYS[2]
        local message = ARGV[1]
        local tokens = tonumber(ARGV[2])
        local max_tokens = tonumber(ARGV[3])
        local ttl = tonumber(ARGV[4])
        
        -- Add new message and token count
        redis.call('LPUSH', conv_key, message)
        redis.call('LPUSH', token_key, tokens)
        
        -- Calculate total tokens and trim if necessary
        local token_list = redis.call('LRANGE', token_key, 0, -1)
        local total_tokens = 0
        local messages_to_keep = 0
        
        for i, token_count in ipairs(token_list) do
            total_tokens = total_tokens + tonumber(token_count)
            messages_to_keep = i
            if total_tokens > max_tokens then
                break
            end
        end
        
        -- Trim both lists to stay within budget
        redis.call('LTRIM', conv_key, 0, messages_to_keep - 1)
        redis.call('LTRIM', token_key, 0, messages_to_keep - 1)
        
        -- Set TTL
        redis.call('EXPIRE', conv_key, ttl)
        redis.call('EXPIRE', token_key, ttl)
        
        -- Return stats
        local final_length = redis.call('LLEN', conv_key)
        local final_tokens = 0
        local final_token_list = redis.call('LRANGE', token_key, 0, -1)
        for _, token_count in ipairs(final_token_list) do
            final_tokens = final_tokens + tonumber(token_count)
        end
        
        return {final_length, final_tokens, messages_to_keep}
        """
        
        # Script for getting conversation with metadata
        self.get_conversation_script = """
        local conv_key = KEYS[1]
        local token_key = KEYS[2]
        local metadata_key = KEYS[3]
        
        -- Get messages and tokens
        local messages = redis.call('LRANGE', conv_key, 0, -1)
        local tokens = redis.call('LRANGE', token_key, 0, -1)
        local metadata = redis.call('HGETALL', metadata_key)
        
        -- Calculate total tokens
        local total_tokens = 0
        for _, token_count in ipairs(tokens) do
            total_tokens = total_tokens + tonumber(token_count)
        end
        
        -- Convert metadata to table
        local meta_table = {}
        for i = 1, #metadata, 2 do
            meta_table[metadata[i]] = metadata[i+1]
        end
        
        return {messages, tokens, total_tokens, meta_table}
        """
        
        # Script for updating conversation metadata
        self.update_metadata_script = """
        local metadata_key = KEYS[1]
        local ttl = tonumber(ARGV[1])
        
        -- Update metadata fields (ARGV[2], ARGV[3], ARGV[4], ARGV[5], ...)
        for i = 2, #ARGV, 2 do
            if ARGV[i+1] then
                redis.call('HSET', metadata_key, ARGV[i], ARGV[i+1])
            end
        end
        
        -- Update timestamp
        redis.call('HSET', metadata_key, 'last_updated', tostring(redis.call('TIME')[1]))
        
        -- Set TTL
        redis.call('EXPIRE', metadata_key, ttl)
        
        return redis.call('HGETALL', metadata_key)
        """
    
    async def add_message(
        self, 
        session_id: str, 
        message: Dict, 
        tokens: int,
        token_budget: Optional[int] = None,
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add message to conversation with token management.
        
        Args:
            session_id: Conversation session identifier
            message: Message data to store
            tokens: Token count for this message
            token_budget: Maximum tokens to keep (default: 4000)
            ttl: Time to live in seconds (default: 24h)
            
        Returns:
            Dict with operation results and statistics
        """
        
        token_budget = token_budget or self.DEFAULT_TOKEN_BUDGET
        ttl = ttl or self.DEFAULT_CONVERSATION_TTL
        
        conv_key = f"conv:{session_id}"
        token_key = f"conv:{session_id}:tokens"
        
        try:
            # Execute atomic add with token management
            if hasattr(self.redis, 'redis') and self.redis.redis:
                result = await self.redis.redis.eval(
                    self.add_message_script,
                    2,  # Number of keys
                    conv_key,
                    token_key,
                    json.dumps(message),
                    str(tokens),
                    str(token_budget),
                    str(ttl)
                )
                
                final_length, final_tokens, messages_kept = result
                
                # Update conversation metadata
                await self._update_conversation_metadata(
                    session_id,
                    {
                        'message_count': str(final_length),
                        'token_count': str(final_tokens),
                        'last_message_tokens': str(tokens),
                        'token_budget': str(token_budget)
                    }
                )
                
                logger.debug(
                    "message_added_to_conversation",
                    session_id=session_id,
                    message_tokens=tokens,
                    final_length=final_length,
                    final_tokens=final_tokens,
                    messages_kept=messages_kept,
                    token_budget=token_budget
                )
                
                return {
                    'success': True,
                    'final_length': final_length,
                    'final_tokens': final_tokens,
                    'messages_kept': messages_kept,
                    'token_budget': token_budget,
                    'budget_utilization': final_tokens / token_budget if token_budget > 0 else 0
                }
            
            else:
                # Fallback for testing/local development
                logger.warning("redis_not_available_using_fallback")
                return await self._add_message_fallback(session_id, message, tokens, token_budget, ttl)
                
        except Exception as e:
            logger.error(
                "failed_to_add_message",
                session_id=session_id,
                error=str(e),
                message_tokens=tokens
            )
            return {
                'success': False,
                'error': str(e),
                'token_budget': token_budget
            }
    
    async def get_recent_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get recent messages from conversation.
        
        Args:
            session_id: Conversation session identifier
            limit: Maximum number of messages to return
            
        Returns:
            Dict with messages, tokens, and metadata
        """
        
        conv_key = f"conv:{session_id}"
        token_key = f"conv:{session_id}:tokens"
        metadata_key = f"conv:{session_id}:meta"
        
        try:
            if hasattr(self.redis, 'redis') and self.redis.redis:
                # Get conversation data atomically
                result = await self.redis.redis.eval(
                    self.get_conversation_script,
                    3,  # Number of keys
                    conv_key,
                    token_key,
                    metadata_key
                )
                
                # Handle variable return lengths from Lua script
                if len(result) == 4:
                    messages_raw, tokens_raw, total_tokens, metadata = result
                elif len(result) == 3:
                    messages_raw, tokens_raw, total_tokens = result
                    metadata = {}
                else:
                    logger.warning("unexpected_redis_result_length", length=len(result))
                    messages_raw, tokens_raw = result[:2]
                    total_tokens = 0
                    metadata = {}
                
                # Parse messages
                messages = []
                for msg_json in messages_raw:
                    try:
                        messages.append(json.loads(msg_json))
                    except json.JSONDecodeError as e:
                        logger.warning("failed_to_parse_message", error=str(e))
                
                # Apply limit if specified
                if limit and len(messages) > limit:
                    messages = messages[:limit]
                    tokens_raw = tokens_raw[:limit]
                
                # Convert token counts
                tokens = [int(t) for t in tokens_raw]
                
                return {
                    'success': True,
                    'messages': messages,
                    'tokens': tokens,
                    'total_tokens': int(total_tokens),
                    'message_count': len(messages),
                    'metadata': metadata
                }
            
            else:
                # Fallback implementation
                return await self._get_messages_fallback(session_id, limit)
                
        except Exception as e:
            logger.error(
                "failed_to_get_messages",
                session_id=session_id,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    async def store_summary(
        self, 
        session_id: str, 
        summary: str, 
        metadata: Optional[Dict] = None,
        version: int = 1,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store conversation summary.
        
        Args:
            session_id: Conversation session identifier
            summary: Summary text
            metadata: Additional summary metadata
            version: Summary version number
            ttl: Time to live in seconds
            
        Returns:
            Success boolean
        """
        
        ttl = ttl or self.DEFAULT_SUMMARY_TTL
        summary_key = f"summary:{session_id}:v{version}"
        
        try:
            summary_data = {
                'content': summary,
                'version': version,
                'created_at': time.time(),
                'session_id': session_id
            }
            
            if metadata:
                summary_data.update(metadata)
            
            success = await self.redis.set(summary_key, summary_data, ttl)
            
            if success:
                # Update conversation metadata
                await self._update_conversation_metadata(
                    session_id,
                    {
                        'has_summary': 'true',
                        'latest_summary_version': str(version),
                        'summary_created_at': str(time.time())
                    }
                )
            
            logger.debug(
                "summary_stored",
                session_id=session_id,
                version=version,
                summary_length=len(summary),
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "failed_to_store_summary",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def get_summary(
        self, 
        session_id: str, 
        version: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Get conversation summary.
        
        Args:
            session_id: Conversation session identifier
            version: Specific version to retrieve (default: latest)
            
        Returns:
            Summary data or None if not found
        """
        
        try:
            if version is None:
                # Get latest version from metadata
                metadata = await self.get_conversation_metadata(session_id)
                if metadata and 'latest_summary_version' in metadata:
                    version = int(metadata['latest_summary_version'])
                else:
                    version = 1
            
            summary_key = f"summary:{session_id}:v{version}"
            summary_data = await self.redis.get(summary_key)
            
            if summary_data:
                logger.debug(
                    "summary_retrieved",
                    session_id=session_id,
                    version=version
                )
                return summary_data
            
            return None
            
        except Exception as e:
            logger.error(
                "failed_to_get_summary",
                session_id=session_id,
                version=version,
                error=str(e)
            )
            return None
    
    async def get_conversation_metadata(self, session_id: str) -> Optional[Dict]:
        """Get conversation metadata"""
        
        metadata_key = f"conv:{session_id}:meta"
        
        try:
            if hasattr(self.redis, 'redis') and self.redis.redis:
                metadata = await self.redis.redis.hgetall(metadata_key)
                return {k.decode(): v.decode() for k, v in metadata.items()} if metadata else None
            else:
                # Fallback
                return await self.redis.get(metadata_key)
                
        except Exception as e:
            logger.error(
                "failed_to_get_metadata",
                session_id=session_id,
                error=str(e)
            )
            return None
    
    async def _update_conversation_metadata(
        self, 
        session_id: str, 
        updates: Dict[str, str],
        ttl: Optional[int] = None
    ) -> bool:
        """Update conversation metadata atomically"""
        
        ttl = ttl or self.DEFAULT_CONVERSATION_TTL
        metadata_key = f"conv:{session_id}:meta"
        
        try:
            if hasattr(self.redis, 'redis') and self.redis.redis:
                # Prepare arguments for Lua script
                args = [str(ttl)]
                for key, value in updates.items():
                    args.extend([key, str(value)])
                
                await self.redis.redis.eval(
                    self.update_metadata_script,
                    1,  # Number of keys
                    metadata_key,
                    *args
                )
                
                return True
            
            else:
                # Fallback
                existing = await self.redis.get(metadata_key, {})
                existing.update(updates)
                existing['last_updated'] = str(time.time())
                return await self.redis.set(metadata_key, existing, ttl)
                
        except Exception as e:
            logger.error(
                "failed_to_update_metadata",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def get_conversation_stats(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation statistics"""
        
        try:
            # Get recent messages
            conversation_data = await self.get_recent_messages(session_id)
            
            # Get summary info
            summary = await self.get_summary(session_id)
            
            # Get metadata
            metadata = await self.get_conversation_metadata(session_id)
            
            stats = {
                'session_id': session_id,
                'message_count': conversation_data.get('message_count', 0),
                'total_tokens': conversation_data.get('total_tokens', 0),
                'has_summary': summary is not None,
                'summary_version': summary.get('version') if summary else None,
                'last_updated': metadata.get('last_updated') if metadata else None,
                'token_budget': int(metadata.get('token_budget', 0)) if metadata else 0,
                'budget_utilization': 0
            }
            
            if stats['token_budget'] > 0:
                stats['budget_utilization'] = stats['total_tokens'] / stats['token_budget']
            
            return stats
            
        except Exception as e:
            logger.error(
                "failed_to_get_conversation_stats",
                session_id=session_id,
                error=str(e)
            )
            return {'session_id': session_id, 'error': str(e)}
    
    async def delete_conversation(self, session_id: str) -> bool:
        """Delete entire conversation and associated data"""
        
        try:
            keys_to_delete = [
                f"conv:{session_id}",
                f"conv:{session_id}:tokens",
                f"conv:{session_id}:meta",
                f"summary:{session_id}:v1",
                f"summary:{session_id}:v2",
                f"summary:{session_id}:v3"  # Delete common versions
            ]
            
            deleted_count = 0
            for key in keys_to_delete:
                if hasattr(self.redis, 'redis') and self.redis.redis:
                    deleted = await self.redis.redis.delete(key)
                    deleted_count += deleted
            
            logger.info(
                "conversation_deleted",
                session_id=session_id,
                keys_deleted=deleted_count
            )
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(
                "failed_to_delete_conversation",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def _add_message_fallback(
        self, 
        session_id: str, 
        message: Dict, 
        tokens: int, 
        token_budget: int, 
        ttl: int
    ) -> Dict[str, Any]:
        """Fallback implementation for add_message when Redis is not available"""
        
        # Simple in-memory fallback (for testing)
        conv_key = f"conv:{session_id}"
        
        # Get existing messages
        existing = await self.redis.get(conv_key, [])
        
        # Add token count to message for consistency
        message_with_tokens = message.copy()
        message_with_tokens['tokens'] = tokens
        
        # Add new message
        existing.insert(0, message_with_tokens)  # Add to front (like LPUSH)
        
        # Simple token trimming
        total_tokens = tokens
        keep_messages = [message_with_tokens]
        
        for i, msg in enumerate(existing[1:], 1):
            msg_tokens = msg.get('tokens', 100)  # Estimate if not provided
            if total_tokens + msg_tokens <= token_budget:
                total_tokens += msg_tokens
                keep_messages.append(msg)
            else:
                break
        
        # Store trimmed conversation
        await self.redis.set(conv_key, keep_messages, ttl)
        
        return {
            'success': True,
            'final_length': len(keep_messages),
            'final_tokens': total_tokens,
            'messages_kept': len(keep_messages),
            'token_budget': token_budget,
            'budget_utilization': total_tokens / token_budget
        }
    
    async def _get_messages_fallback(
        self, 
        session_id: str, 
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """Fallback implementation for get_recent_messages"""
        
        conv_key = f"conv:{session_id}"
        messages = await self.redis.get(conv_key, [])
        
        if limit and len(messages) > limit:
            messages = messages[:limit]
        
        # Estimate tokens
        total_tokens = sum(msg.get('tokens', 100) for msg in messages)
        
        return {
            'success': True,
            'messages': messages,
            'tokens': [msg.get('tokens', 100) for msg in messages],
            'total_tokens': total_tokens,
            'message_count': len(messages),
            'metadata': {}
        }