"""
Web Search Audit Manager

Manages audit logging for web search operations with Redis storage and compliance features.
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import structlog

from app.core.config import get_settings
from app.cache.redis_client import CacheManager

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebSearchAuditManager:
    """
    Manages audit logging for web search operations.
    
    Features:
    - Structured audit event logging
    - Redis-based storage with TTL
    - Event correlation and tracking
    - Compliance-ready audit trails
    - Performance optimized for high-throughput
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.redis_key_prefix = "audit:web_search"
        self.default_retention_days = 2555  # 7 years for compliance
        
    async def log_event(self, event_data: Dict[str, Any]) -> str:
        """
        Log an audit event to Redis storage.
        
        Args:
            event_data: Audit event data (from AuditEvent model)
            
        Returns:
            str: Generated event ID
        """
        try:
            # Generate event ID if not provided
            event_id = event_data.get("event_id")
            if not event_id:
                timestamp = datetime.now().isoformat()
                event_type = event_data.get("event_type", "unknown")
                user_id = event_data.get("user_id", "anonymous")
                
                # Create deterministic but unique ID
                id_source = f"{timestamp}:{event_type}:{user_id}:{uuid.uuid4().hex[:8]}"
                event_id = hashlib.md5(id_source.encode()).hexdigest()[:16]
                event_data["event_id"] = event_id
            
            # Ensure timestamp is set
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.now().isoformat()
            
            # Add system metadata
            event_data.update({
                "logged_at": datetime.now().isoformat(),
                "system_component": event_data.get("system_component", "web_search"),
                "api_version": event_data.get("api_version", "v1"),
                "environment": event_data.get("environment", settings.environment)
            })
            
            # Store in Redis with multiple keys for different access patterns
            await self._store_event_multiple_keys(event_id, event_data)
            
            logger.info(
                "Audit event logged",
                event_id=event_id,
                event_type=event_data.get("event_type"),
                user_id=event_data.get("user_id")
            )
            
            return event_id
            
        except Exception as e:
            logger.error("Failed to log audit event", error=str(e), event_data=event_data)
            raise
    
    async def _store_event_multiple_keys(self, event_id: str, event_data: Dict[str, Any]) -> None:
        """Store event with multiple Redis keys for efficient querying."""
        
        retention_seconds = event_data.get("retention_period_days", self.default_retention_days) * 24 * 3600
        
        # Primary key: individual event
        primary_key = f"{self.redis_key_prefix}:event:{event_id}"
        await self.cache_manager.set_json(primary_key, event_data, ttl=retention_seconds)
        
        # Secondary keys for querying
        user_id = event_data.get("user_id")
        if user_id:
            user_key = f"{self.redis_key_prefix}:user:{user_id}:events"
            await self.cache_manager.redis.sadd(user_key, event_id)
            await self.cache_manager.redis.expire(user_key, retention_seconds)
        
        event_type = event_data.get("event_type")
        if event_type:
            type_key = f"{self.redis_key_prefix}:type:{event_type}:events"
            await self.cache_manager.redis.sadd(type_key, event_id)
            await self.cache_manager.redis.expire(type_key, retention_seconds)
        
        # Daily index for compliance reporting
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_key = f"{self.redis_key_prefix}:daily:{date_str}:events"
        await self.cache_manager.redis.sadd(daily_key, event_id)
        await self.cache_manager.redis.expire(daily_key, retention_seconds)
    
    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific audit event by ID."""
        try:
            key = f"{self.redis_key_prefix}:event:{event_id}"
            event_data = await self.cache_manager.get_json(key)
            return event_data
        except Exception as e:
            logger.error("Failed to retrieve audit event", event_id=event_id, error=str(e))
            return None
    
    async def search_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit events with various filters.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of results
            offset: Results offset for pagination
            
        Returns:
            List of matching audit events
        """
        try:
            event_ids = set()
            
            # Get event IDs based on filters
            if user_id:
                user_key = f"{self.redis_key_prefix}:user:{user_id}:events"
                user_event_ids = await self.cache_manager.redis.smembers(user_key)
                event_ids.update(id.decode() if isinstance(id, bytes) else id for id in user_event_ids)
            
            if event_type:
                type_key = f"{self.redis_key_prefix}:type:{event_type}:events"
                type_event_ids = await self.cache_manager.redis.smembers(type_key)
                type_event_ids_str = {id.decode() if isinstance(id, bytes) else id for id in type_event_ids}
                
                if event_ids:
                    event_ids = event_ids.intersection(type_event_ids_str)
                else:
                    event_ids = type_event_ids_str
            
            # If no specific filters, get recent events
            if not event_ids and not user_id and not event_type:
                # Get events from recent days
                recent_ids = set()
                for days_back in range(7):  # Last 7 days
                    date = datetime.now() - timedelta(days=days_back)
                    date_str = date.strftime("%Y-%m-%d")
                    daily_key = f"{self.redis_key_prefix}:daily:{date_str}:events"
                    daily_event_ids = await self.cache_manager.redis.smembers(daily_key)
                    recent_ids.update(id.decode() if isinstance(id, bytes) else id for id in daily_event_ids)
                event_ids = recent_ids
            
            # Retrieve actual events
            events = []
            event_ids_list = list(event_ids)[offset:offset + limit]
            
            for event_id in event_ids_list:
                event_data = await self.get_event(event_id)
                if event_data:
                    # Apply date filters if specified
                    if start_date or end_date:
                        event_timestamp = datetime.fromisoformat(event_data.get("timestamp", ""))
                        if start_date and event_timestamp < start_date:
                            continue
                        if end_date and event_timestamp > end_date:
                            continue
                    
                    events.append(event_data)
            
            # Sort by timestamp (most recent first)
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return events
            
        except Exception as e:
            logger.error("Failed to search audit events", error=str(e))
            return []
    
    async def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        compliance_level: str = "basic"
    ) -> Dict[str, Any]:
        """
        Generate compliance report for specified date range.
        
        Args:
            start_date: Report period start
            end_date: Report period end
            compliance_level: Compliance level requirement
            
        Returns:
            Compliance report with metrics and summaries
        """
        try:
            events = await self.search_events(start_date=start_date, end_date=end_date, limit=10000)
            
            # Calculate compliance metrics
            total_events = len(events)
            events_by_type = {}
            events_by_severity = {}
            events_by_user = {}
            consent_events = 0
            successful_consents = 0
            budget_events = 0
            budget_violations = 0
            
            for event in events:
                # Count by type
                event_type = event.get("event_type", "unknown")
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                
                # Count by severity
                severity = event.get("severity", "info")
                events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
                
                # Count by user
                user_id = event.get("user_id", "anonymous")
                events_by_user[user_id] = events_by_user.get(user_id, 0) + 1
                
                # Compliance-specific metrics
                if event_type in ["consent_requested", "consent_granted", "consent_denied"]:
                    consent_events += 1
                    if event_type == "consent_granted":
                        successful_consents += 1
                
                if event_type == "budget_exceeded":
                    budget_events += 1
                    budget_violations += 1
            
            # Calculate rates
            consent_compliance_rate = (successful_consents / consent_events * 100) if consent_events > 0 else 100
            budget_compliance_rate = ((budget_events - budget_violations) / budget_events * 100) if budget_events > 0 else 100
            
            report = {
                "report_id": f"compliance_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}",
                "generated_at": datetime.now().isoformat(),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "compliance_level": compliance_level,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "events_by_user": dict(list(events_by_user.items())[:10]),  # Top 10 users
                "consent_compliance_rate": consent_compliance_rate,
                "budget_compliance_rate": budget_compliance_rate,
                "access_violations": events_by_severity.get("error", 0) + events_by_severity.get("critical", 0),
                "summary": {
                    "status": "compliant" if consent_compliance_rate >= 95 and budget_compliance_rate >= 95 else "attention_required",
                    "key_metrics": {
                        "total_audit_events": total_events,
                        "consent_success_rate": f"{consent_compliance_rate:.1f}%",
                        "budget_compliance": f"{budget_compliance_rate:.1f}%",
                        "violations": budget_violations
                    }
                }
            }
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate compliance report", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check audit manager health and connectivity."""
        try:
            # Test Redis connectivity
            test_key = f"{self.redis_key_prefix}:health_check"
            await self.cache_manager.set_json(test_key, {"test": "ok"}, ttl=60)
            result = await self.cache_manager.get_json(test_key)
            
            redis_healthy = result is not None and result.get("test") == "ok"
            
            # Get storage statistics
            pattern = f"{self.redis_key_prefix}:event:*"
            event_keys = []
            async for key in self.cache_manager.redis.scan_iter(match=pattern):
                event_keys.append(key)
            
            return {
                "status": "healthy" if redis_healthy else "unhealthy",
                "redis_connection": "connected" if redis_healthy else "failed",
                "total_events_stored": len(event_keys),
                "storage_prefix": self.redis_key_prefix,
                "retention_days": self.default_retention_days,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Audit manager health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }