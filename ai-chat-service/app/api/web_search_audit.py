"""
Web Search Audit Logging API

Provides comprehensive audit logging for web search operations:
- Complete audit trail for compliance and governance
- User access logging and permission tracking
- Search query and result logging
- Cost and billing audit trails
- Admin action logging
- Compliance reporting and data export
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.dependencies import get_cache_manager

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["Web Search Audit"])


class AuditEventType(Enum):
    """Types of audit events"""
    CONSENT_REQUESTED = "consent_requested"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_DENIED = "consent_denied"
    CONSENT_EXPIRED = "consent_expired"
    SEARCH_EXECUTED = "search_executed"
    SEARCH_FAILED = "search_failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    ADMIN_OVERRIDE = "admin_override"
    PERMISSION_CHANGED = "permission_changed"
    COMPLIANCE_EXPORT = "compliance_export"
    USER_ACCESS = "user_access"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceLevel(Enum):
    """Compliance requirement levels"""
    BASIC = "basic"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    ENTERPRISE = "enterprise"


class AuditEvent(BaseModel):
    """Individual audit event record"""
    
    # Event identification
    event_id: Optional[str] = Field(default=None, description="Unique event ID (auto-generated if not provided)")
    event_type: AuditEventType = Field(description="Type of audit event")
    severity: AuditSeverity = Field(description="Event severity")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    
    # User and session context
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    
    # Request context
    request_id: Optional[str] = Field(default=None, description="Associated request ID")
    consent_token: Optional[str] = Field(default=None, description="Associated consent token")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID")
    
    # Event details
    event_description: str = Field(description="Human-readable event description")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Structured event data")
    
    # Cost and billing context
    cost_incurred: Optional[float] = Field(default=None, description="Cost incurred")
    cost_center: Optional[str] = Field(default=None, description="Cost center")
    
    # Compliance and governance
    compliance_tags: List[str] = Field(default_factory=list, description="Compliance requirement tags")
    retention_period_days: int = Field(default=2555, description="Retention period (7 years default)")
    
    # System context
    system_component: str = Field(default="web_search", description="System component")
    api_version: str = Field(default="v1", description="API version")
    environment: str = Field(default="production", description="Environment")


class AuditQuery(BaseModel):
    """Query parameters for audit log search"""
    
    # Time range
    start_date: Optional[datetime] = Field(default=None, description="Start date for search")
    end_date: Optional[datetime] = Field(default=None, description="End date for search")
    
    # Filters
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    event_type: Optional[AuditEventType] = Field(default=None, description="Filter by event type")
    severity: Optional[AuditSeverity] = Field(default=None, description="Filter by severity")
    request_id: Optional[str] = Field(default=None, description="Filter by request ID")
    cost_center: Optional[str] = Field(default=None, description="Filter by cost center")
    
    # Search
    search_term: Optional[str] = Field(default=None, description="Free text search")
    
    # Pagination
    limit: int = Field(default=100, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, description="Results offset")
    
    # Sorting
    sort_by: str = Field(default="timestamp", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class AuditReport(BaseModel):
    """Audit report summary"""
    
    # Report metadata
    report_id: str = Field(description="Report ID")
    generated_at: datetime = Field(description="Report generation time")
    period_start: datetime = Field(description="Report period start")
    period_end: datetime = Field(description="Report period end")
    compliance_level: ComplianceLevel = Field(description="Compliance level")
    
    # Summary statistics
    total_events: int = Field(description="Total events in period")
    events_by_type: Dict[str, int] = Field(description="Events by type")
    events_by_severity: Dict[str, int] = Field(description="Events by severity")
    events_by_user: Dict[str, int] = Field(description="Events by user")
    
    # Compliance metrics
    consent_compliance_rate: float = Field(description="Consent compliance rate (%)")
    budget_compliance_rate: float = Field(description="Budget compliance rate (%)")
    access_violations: int = Field(description="Number of access violations")
    
    # Cost and usage
    total_cost_audited: float = Field(description="Total cost in audit trail")
    searches_audited: int = Field(description="Total searches audited")
    unique_users: int = Field(description="Unique users in period")
    
    # Data integrity
    data_integrity_score: float = Field(description="Data integrity score (%)")
    missing_events: int = Field(description="Number of missing/corrupted events")
    retention_compliance: float = Field(description="Retention policy compliance (%)")


class WebSearchAuditManager:
    """Manages web search audit logging and compliance"""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
        
        # Audit configuration
        self.retention_policies = {
            ComplianceLevel.BASIC: 365,      # 1 year
            ComplianceLevel.GDPR: 2555,      # 7 years
            ComplianceLevel.HIPAA: 2190,     # 6 years
            ComplianceLevel.SOX: 2555,       # 7 years
            ComplianceLevel.ENTERPRISE: 3650  # 10 years
        }
        
        # Critical events that require immediate attention
        self.critical_events = {
            AuditEventType.BUDGET_EXCEEDED,
            AuditEventType.SEARCH_FAILED,
            AuditEventType.ADMIN_OVERRIDE,
            AuditEventType.SYSTEM_ERROR
        }
    
    async def log_event(self, event: AuditEvent) -> str:
        """Log an audit event"""
        
        try:
            # Generate event ID if not provided
            if not event.event_id:
                event.event_id = self._generate_event_id(event)
            
            # Add system context
            event.environment = settings.environment
            event.timestamp = datetime.now()
            
            # Determine compliance tags based on event type
            event.compliance_tags = self._determine_compliance_tags(event)
            
            # Set retention period based on compliance requirements
            max_compliance = self._get_max_compliance_level(event.compliance_tags)
            event.retention_period_days = self.retention_policies.get(max_compliance, 2555)
            
            # Store event with appropriate TTL
            event_key = f"audit_event:{event.event_id}"
            await self.cache.set(
                event_key,
                json.dumps(event.dict(), default=str),
                ttl=event.retention_period_days * 86400  # Convert days to seconds
            )
            
            # Create searchable indexes
            await self._create_audit_indexes(event)
            
            # Handle critical events
            if event.event_type in self.critical_events or event.severity == AuditSeverity.CRITICAL:
                await self._handle_critical_event(event)
            
            logger.info("Audit event logged",
                       event_id=event.event_id,
                       event_type=event.event_type.value,
                       severity=event.severity.value,
                       user_id=event.user_id)
            
            return event.event_id
            
        except Exception as e:
            logger.error("Failed to log audit event",
                        event_type=event.event_type.value if event.event_type else "unknown",
                        error=str(e))
            raise
    
    async def search_events(self, query: AuditQuery) -> Tuple[List[AuditEvent], int]:
        """Search audit events based on query parameters"""
        
        try:
            # Build search filters
            filters = self._build_search_filters(query)
            
            # Get matching event keys (in production, this would use a proper database)
            event_keys = await self._get_filtered_event_keys(filters, query)
            
            # Retrieve events
            events = []
            for key in event_keys[query.offset:query.offset + query.limit]:
                event_data = await self.cache.get(key)
                if event_data:
                    event_dict = json.loads(event_data)
                    # Convert string timestamps back to datetime objects
                    if 'timestamp' in event_dict:
                        event_dict['timestamp'] = datetime.fromisoformat(event_dict['timestamp'])
                    events.append(AuditEvent(**event_dict))
            
            total_count = len(event_keys)
            
            return events, total_count
            
        except Exception as e:
            logger.error("Audit search failed", error=str(e))
            raise
    
    async def generate_compliance_report(self, 
                                       start_date: datetime, 
                                       end_date: datetime,
                                       compliance_level: ComplianceLevel) -> AuditReport:
        """Generate comprehensive compliance report"""
        
        try:
            # Search for all events in period
            query = AuditQuery(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Get all events for reporting
            )
            
            events, total_count = await self.search_events(query)
            
            # Generate report statistics
            events_by_type = {}
            events_by_severity = {}
            events_by_user = {}
            consent_events = 0
            consent_compliant = 0
            budget_events = 0
            budget_compliant = 0
            total_cost = 0.0
            searches_count = 0
            unique_users = set()
            access_violations = 0
            
            for event in events:
                # Count by type
                event_type = event.event_type.value
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                
                # Count by severity
                severity = event.severity.value
                events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
                
                # Count by user
                if event.user_id:
                    unique_users.add(event.user_id)
                    events_by_user[event.user_id] = events_by_user.get(event.user_id, 0) + 1
                
                # Compliance metrics
                if event.event_type in [AuditEventType.CONSENT_REQUESTED, AuditEventType.CONSENT_GRANTED]:
                    consent_events += 1
                    if event.event_type == AuditEventType.CONSENT_GRANTED:
                        consent_compliant += 1
                
                if event.event_type == AuditEventType.BUDGET_EXCEEDED:
                    budget_events += 1
                else:
                    budget_compliant += 1
                
                # Cost tracking
                if event.cost_incurred:
                    total_cost += event.cost_incurred
                
                # Search counting
                if event.event_type == AuditEventType.SEARCH_EXECUTED:
                    searches_count += 1
                
                # Access violations
                if event.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
                    access_violations += 1
            
            # Calculate compliance rates
            consent_compliance_rate = (consent_compliant / consent_events * 100) if consent_events > 0 else 100.0
            budget_compliance_rate = (budget_compliant / (budget_compliant + budget_events) * 100) if (budget_compliant + budget_events) > 0 else 100.0
            
            report_id = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            report = AuditReport(
                report_id=report_id,
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                compliance_level=compliance_level,
                total_events=total_count,
                events_by_type=events_by_type,
                events_by_severity=events_by_severity,
                events_by_user=events_by_user,
                consent_compliance_rate=consent_compliance_rate,
                budget_compliance_rate=budget_compliance_rate,
                access_violations=access_violations,
                total_cost_audited=total_cost,
                searches_audited=searches_count,
                unique_users=len(unique_users),
                data_integrity_score=95.0,  # Placeholder - would be calculated based on data validation
                missing_events=0,  # Placeholder
                retention_compliance=100.0  # Placeholder
            )
            
            # Store report for future reference
            report_key = f"audit_report:{report_id}"
            await self.cache.set(
                report_key,
                json.dumps(report.dict(), default=str),
                ttl=86400 * 365  # Keep reports for 1 year
            )
            
            return report
            
        except Exception as e:
            logger.error("Compliance report generation failed", error=str(e))
            raise
    
    def _generate_event_id(self, event: AuditEvent) -> str:
        """Generate unique event ID"""
        content = f"{event.event_type.value}{event.user_id}{event.timestamp}{event.event_description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _determine_compliance_tags(self, event: AuditEvent) -> List[str]:
        """Determine compliance tags based on event type and data"""
        
        tags = ["basic"]
        
        # GDPR compliance for user data
        if event.user_id or event.ip_address:
            tags.append("gdpr")
        
        # Financial compliance for cost-related events
        if event.cost_incurred or event.cost_center:
            tags.append("sox")
        
        # Enterprise compliance for admin actions
        if event.event_type in [AuditEventType.ADMIN_OVERRIDE, AuditEventType.PERMISSION_CHANGED]:
            tags.append("enterprise")
        
        return tags
    
    def _get_max_compliance_level(self, tags: List[str]) -> ComplianceLevel:
        """Get the highest compliance level from tags"""
        
        if "enterprise" in tags:
            return ComplianceLevel.ENTERPRISE
        elif "sox" in tags:
            return ComplianceLevel.SOX
        elif "gdpr" in tags:
            return ComplianceLevel.GDPR
        else:
            return ComplianceLevel.BASIC
    
    async def _create_audit_indexes(self, event: AuditEvent):
        """Create searchable indexes for the event"""
        
        # Time-based indexes
        date_key = event.timestamp.strftime("%Y-%m-%d")
        hour_key = event.timestamp.strftime("%Y-%m-%d-%H")
        
        # Add event to date index
        date_index_key = f"audit_index:date:{date_key}"
        await self._add_to_index(date_index_key, event.event_id)
        
        # Add event to hour index
        hour_index_key = f"audit_index:hour:{hour_key}"
        await self._add_to_index(hour_index_key, event.event_id)
        
        # User index
        if event.user_id:
            user_index_key = f"audit_index:user:{event.user_id}"
            await self._add_to_index(user_index_key, event.event_id)
        
        # Event type index
        type_index_key = f"audit_index:type:{event.event_type.value}"
        await self._add_to_index(type_index_key, event.event_id)
        
        # Severity index
        severity_index_key = f"audit_index:severity:{event.severity.value}"
        await self._add_to_index(severity_index_key, event.event_id)
    
    async def _add_to_index(self, index_key: str, event_id: str):
        """Add event ID to an index"""
        
        # Get current index
        current_index = await self.cache.get(index_key)
        if current_index:
            event_ids = json.loads(current_index)
        else:
            event_ids = []
        
        # Add new event ID
        if event_id not in event_ids:
            event_ids.append(event_id)
            # Keep only last 10000 events per index
            if len(event_ids) > 10000:
                event_ids = event_ids[-10000:]
        
        # Update index
        await self.cache.set(index_key, json.dumps(event_ids), ttl=86400 * 365)
    
    def _build_search_filters(self, query: AuditQuery) -> Dict[str, Any]:
        """Build search filters from query"""
        
        filters = {}
        
        if query.user_id:
            filters["user_id"] = query.user_id
        if query.event_type:
            filters["event_type"] = query.event_type.value
        if query.severity:
            filters["severity"] = query.severity.value
        if query.request_id:
            filters["request_id"] = query.request_id
        if query.cost_center:
            filters["cost_center"] = query.cost_center
        
        return filters
    
    async def _get_filtered_event_keys(self, filters: Dict[str, Any], query: AuditQuery) -> List[str]:
        """Get event keys matching filters (simplified implementation)"""
        
        # In production, this would use proper database indexes
        # For now, return a simplified result
        
        if query.user_id:
            user_index_key = f"audit_index:user:{query.user_id}"
            user_events = await self.cache.get(user_index_key)
            if user_events:
                event_ids = json.loads(user_events)
                return [f"audit_event:{event_id}" for event_id in event_ids]
        
        # Fallback to date-based search
        if query.start_date:
            date_key = query.start_date.strftime("%Y-%m-%d")
            date_index_key = f"audit_index:date:{date_key}"
            date_events = await self.cache.get(date_index_key)
            if date_events:
                event_ids = json.loads(date_events)
                return [f"audit_event:{event_id}" for event_id in reversed(event_ids)]
        
        return []
    
    async def _handle_critical_event(self, event: AuditEvent):
        """Handle critical events requiring immediate attention"""
        
        logger.critical("Critical audit event",
                       event_id=event.event_id,
                       event_type=event.event_type.value,
                       description=event.event_description,
                       user_id=event.user_id)
        
        # In production, this would trigger alerts, notifications, etc.


# Global audit manager
_audit_manager = None

async def get_audit_manager(cache_manager = Depends(get_cache_manager)):
    """Get or create audit manager instance"""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = WebSearchAuditManager(cache_manager)
    return _audit_manager


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_audit_event(
    event: AuditEvent,
    audit_manager: WebSearchAuditManager = Depends(get_audit_manager)
):
    """Log an audit event"""
    
    try:
        event_id = await audit_manager.log_event(event)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "event_id": event_id,
                "message": "Audit event logged successfully",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Audit logging failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log audit event: {str(e)}"
        )


@router.post("/search")
async def search_audit_events(
    query: AuditQuery,
    audit_manager: WebSearchAuditManager = Depends(get_audit_manager)
):
    """Search audit events"""
    
    try:
        events, total_count = await audit_manager.search_events(query)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "events": [event.dict() for event in events],
                    "total_count": total_count,
                    "returned_count": len(events),
                    "offset": query.offset,
                    "limit": query.limit
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Audit search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search audit events: {str(e)}"
        )


@router.get("/report", response_model=AuditReport)
async def generate_audit_report(
    start_date: datetime = Query(description="Report start date"),
    end_date: datetime = Query(description="Report end date"),
    compliance_level: ComplianceLevel = Query(default=ComplianceLevel.BASIC, description="Compliance level"),
    audit_manager: WebSearchAuditManager = Depends(get_audit_manager)
):
    """Generate compliance audit report"""
    
    try:
        report = await audit_manager.generate_compliance_report(
            start_date, end_date, compliance_level
        )
        
        return report
        
    except Exception as e:
        logger.error("Audit report generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit report: {str(e)}"
        )


@router.get("/user/{user_id}/events")
async def get_user_audit_events(
    user_id: str,
    days: int = Query(default=30, le=365, description="Number of days to look back"),
    event_type: Optional[AuditEventType] = Query(default=None, description="Filter by event type"),
    audit_manager: WebSearchAuditManager = Depends(get_audit_manager)
):
    """Get audit events for a specific user"""
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = AuditQuery(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            limit=500
        )
        
        events, total_count = await audit_manager.search_events(query)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "user_id": user_id,
                    "period_days": days,
                    "events": [event.dict() for event in events],
                    "total_count": total_count,
                    "event_types": list(set(event.event_type.value for event in events))
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("User audit events retrieval failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user audit events: {str(e)}"
        )