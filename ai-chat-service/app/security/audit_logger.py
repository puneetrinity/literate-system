"""
Security audit logging system for compliance and monitoring.

Provides comprehensive audit logging capabilities:
- Structured audit events with tamper-proofing
- Data access tracking and compliance logging
- Real-time security monitoring
- Audit trail integrity verification
- Integration with SIEM systems
"""

import json
import time
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import socket
import os

import structlog

from .encryption import DataClassification

logger = structlog.get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    KEY_OPERATION = "key_operation"
    CONSENT_CHANGE = "consent_change"
    PRIVACY_REQUEST = "privacy_request"
    SYSTEM_ACCESS = "system_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_INCIDENT = "security_incident"


class RiskLevel(Enum):
    """Risk levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"


@dataclass
class AuditEvent:
    """Structured audit event"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    risk_level: RiskLevel
    user_id: Optional[str]
    session_id: Optional[str]
    resource: str
    action: str
    outcome: str  # success, failure, partial
    details: Dict[str, Any]
    
    # Context information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    source_system: Optional[str] = None
    
    # Compliance and classification
    data_classification: Optional[DataClassification] = None
    compliance_frameworks: List[ComplianceFramework] = None
    
    # Security context
    authentication_method: Optional[str] = None
    authorization_context: Dict[str, Any] = None
    
    # Integrity and verification
    checksum: Optional[str] = None
    signature: Optional[str] = None


class SecurityAuditLogger:
    """
    Comprehensive security audit logging system.
    
    Features:
    - Structured audit events with tamper detection
    - Real-time security monitoring
    - Compliance-focused logging
    - Integrity verification with checksums
    - Integration with external SIEM systems
    """
    
    def __init__(self, 
                 secret_key: Optional[str] = None,
                 storage_backend: Optional[Dict] = None):
        """
        Initialize security audit logger.
        
        Args:
            secret_key: Secret key for HMAC signatures
            storage_backend: Storage configuration
        """
        self.secret_key = secret_key or os.getenv("AUDIT_SECRET_KEY", "default_audit_key")
        self.storage = storage_backend or {}
        
        # Audit event storage
        self.audit_events: List[AuditEvent] = []
        
        # System context
        self.hostname = socket.gethostname()
        self.source_system = "unified-ai-system"
        
        # Compliance requirements
        self.compliance_requirements = {
            ComplianceFramework.GDPR: {
                "required_events": [
                    AuditEventType.DATA_ACCESS,
                    AuditEventType.CONSENT_CHANGE,
                    AuditEventType.PRIVACY_REQUEST,
                    AuditEventType.DATA_DELETION
                ],
                "retention_days": 2555  # 7 years
            },
            ComplianceFramework.SOC2: {
                "required_events": [
                    AuditEventType.AUTHENTICATION,
                    AuditEventType.AUTHORIZATION,
                    AuditEventType.DATA_ACCESS,
                    AuditEventType.CONFIGURATION_CHANGE
                ],
                "retention_days": 365
            }
        }
        
        logger.info("security_audit_logger_initialized", hostname=self.hostname)
    
    async def log_event(self,
                       event_type: AuditEventType,
                       resource: str,
                       action: str,
                       outcome: str = "success",
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       risk_level: RiskLevel = RiskLevel.LOW,
                       data_classification: Optional[DataClassification] = None,
                       compliance_frameworks: Optional[List[ComplianceFramework]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> str:
        """
        Log security audit event.
        
        Args:
            event_type: Type of audit event
            resource: Resource being accessed/modified
            action: Action being performed
            outcome: Outcome of the action
            user_id: User identifier
            session_id: Session identifier
            details: Additional event details
            risk_level: Risk level of the event
            data_classification: Data classification if applicable
            compliance_frameworks: Applicable compliance frameworks
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Event ID
        """
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)
            
            # Create audit event
            event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_type,
                risk_level=risk_level,
                user_id=user_id,
                session_id=session_id,
                resource=resource,
                action=action,
                outcome=outcome,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                source_system=self.source_system,
                data_classification=data_classification,
                compliance_frameworks=compliance_frameworks or [],
                authentication_method=None,  # Could be extracted from context
                authorization_context={}
            )
            
            # Generate integrity checksum
            event.checksum = self._generate_checksum(event)
            
            # Generate HMAC signature for tamper detection
            event.signature = self._generate_signature(event)
            
            # Store event
            self.audit_events.append(event)
            
            # Log structured event
            logger.info(
                "security_audit_event",
                event_id=event_id,
                event_type=event_type.value,
                resource=resource,
                action=action,
                outcome=outcome,
                user_id=user_id,
                session_id=session_id,
                risk_level=risk_level.value,
                data_classification=data_classification.value if data_classification else None,
                compliance_frameworks=[f.value for f in (compliance_frameworks or [])],
                ip_address=ip_address,
                timestamp=timestamp.isoformat()
            )
            
            # Handle high-risk events
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._handle_high_risk_event(event)
            
            # Send to external SIEM if configured
            await self._send_to_siem(event)
            
            return event_id
            
        except Exception as e:
            logger.error(
                "audit_logging_failed",
                error=str(e),
                event_type=event_type.value,
                resource=resource,
                action=action
            )
            raise
    
    async def log_data_access(self,
                             resource: str,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             data_classification: Optional[DataClassification] = None,
                             query_details: Optional[Dict[str, Any]] = None,
                             ip_address: Optional[str] = None) -> str:
        """Log data access event"""
        
        details = {
            "access_type": "read",
            "query_details": query_details or {},
            "hostname": self.hostname
        }
        
        # Determine risk level based on classification
        risk_level = RiskLevel.LOW
        if data_classification == DataClassification.CONFIDENTIAL:
            risk_level = RiskLevel.MEDIUM
        elif data_classification == DataClassification.RESTRICTED:
            risk_level = RiskLevel.HIGH
        
        return await self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            resource=resource,
            action="read",
            user_id=user_id,
            session_id=session_id,
            details=details,
            risk_level=risk_level,
            data_classification=data_classification,
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2],
            ip_address=ip_address
        )
    
    async def log_data_modification(self,
                                   resource: str,
                                   modification_type: str,
                                   user_id: Optional[str] = None,
                                   session_id: Optional[str] = None,
                                   data_classification: Optional[DataClassification] = None,
                                   changes: Optional[Dict[str, Any]] = None,
                                   ip_address: Optional[str] = None) -> str:
        """Log data modification event"""
        
        details = {
            "modification_type": modification_type,
            "changes": changes or {},
            "hostname": self.hostname
        }
        
        risk_level = RiskLevel.MEDIUM
        if data_classification == DataClassification.RESTRICTED:
            risk_level = RiskLevel.HIGH
        
        return await self.log_event(
            event_type=AuditEventType.DATA_MODIFICATION,
            resource=resource,
            action=modification_type,
            user_id=user_id,
            session_id=session_id,
            details=details,
            risk_level=risk_level,
            data_classification=data_classification,
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2],
            ip_address=ip_address
        )
    
    async def log_privacy_request(self,
                                 request_type: str,
                                 user_id: str,
                                 details: Optional[Dict[str, Any]] = None,
                                 outcome: str = "success",
                                 ip_address: Optional[str] = None) -> str:
        """Log GDPR privacy request event"""
        
        request_details = {
            "request_type": request_type,
            "gdpr_article": details.get("gdpr_article") if details else None,
            "processing_time_ms": details.get("processing_time_ms") if details else None,
            "hostname": self.hostname
        }
        
        return await self.log_event(
            event_type=AuditEventType.PRIVACY_REQUEST,
            resource=f"user_data:{user_id}",
            action=request_type,
            outcome=outcome,
            user_id=user_id,
            details=request_details,
            risk_level=RiskLevel.MEDIUM,
            compliance_frameworks=[ComplianceFramework.GDPR],
            ip_address=ip_address
        )
    
    async def log_encryption_event(self,
                                  operation: str,
                                  key_id: Optional[str] = None,
                                  user_id: Optional[str] = None,
                                  data_classification: Optional[DataClassification] = None,
                                  details: Optional[Dict[str, Any]] = None) -> str:
        """Log encryption/decryption event"""
        
        encryption_details = {
            "operation": operation,
            "key_id": key_id,
            "algorithm": details.get("algorithm") if details else None,
            "hostname": self.hostname
        }
        
        risk_level = RiskLevel.LOW
        if operation in ["key_rotation", "key_revocation"]:
            risk_level = RiskLevel.MEDIUM
        
        return await self.log_event(
            event_type=AuditEventType.ENCRYPTION,
            resource=f"encryption_key:{key_id}" if key_id else "encryption_operation",
            action=operation,
            user_id=user_id,
            details=encryption_details,
            risk_level=risk_level,
            data_classification=data_classification,
            compliance_frameworks=[ComplianceFramework.SOC2]
        )
    
    async def log_security_incident(self,
                                   incident_type: str,
                                   severity: str,
                                   description: str,
                                   affected_resources: List[str],
                                   user_id: Optional[str] = None,
                                   ip_address: Optional[str] = None,
                                   details: Optional[Dict[str, Any]] = None) -> str:
        """Log security incident"""
        
        incident_details = {
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
            "affected_resources": affected_resources,
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "hostname": self.hostname
        }
        
        if details:
            incident_details.update(details)
        
        # Map severity to risk level
        risk_mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL
        }
        risk_level = risk_mapping.get(severity.lower(), RiskLevel.MEDIUM)
        
        return await self.log_event(
            event_type=AuditEventType.SECURITY_INCIDENT,
            resource=",".join(affected_resources[:3]),  # Limit resource list
            action=f"incident_{incident_type}",
            outcome="detected",
            user_id=user_id,
            details=incident_details,
            risk_level=risk_level,
            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
            ip_address=ip_address
        )
    
    def _generate_checksum(self, event: AuditEvent) -> str:
        """Generate integrity checksum for event"""
        # Create deterministic string representation
        event_data = {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "resource": event.resource,
            "action": event.action,
            "outcome": event.outcome,
            "user_id": event.user_id,
            "details": event.details
        }
        
        event_str = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    def _generate_signature(self, event: AuditEvent) -> str:
        """Generate HMAC signature for tamper detection"""
        event_str = f"{event.event_id}{event.timestamp.isoformat()}{event.checksum}"
        return hmac.new(
            self.secret_key.encode(),
            event_str.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_event_integrity(self, event: AuditEvent) -> bool:
        """Verify event integrity using checksum and signature"""
        try:
            # Verify checksum
            expected_checksum = self._generate_checksum(event)
            if event.checksum != expected_checksum:
                logger.warning(
                    "audit_event_checksum_mismatch",
                    event_id=event.event_id,
                    expected=expected_checksum,
                    actual=event.checksum
                )
                return False
            
            # Verify signature
            expected_signature = self._generate_signature(event)
            if event.signature != expected_signature:
                logger.warning(
                    "audit_event_signature_mismatch",
                    event_id=event.event_id,
                    expected=expected_signature,
                    actual=event.signature
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(
                "audit_event_verification_failed",
                event_id=event.event_id,
                error=str(e)
            )
            return False
    
    async def _handle_high_risk_event(self, event: AuditEvent):
        """Handle high-risk security events"""
        try:
            logger.warning(
                "high_risk_security_event",
                event_id=event.event_id,
                event_type=event.event_type.value,
                risk_level=event.risk_level.value,
                resource=event.resource,
                user_id=event.user_id,
                ip_address=event.ip_address
            )
            
            # Could trigger alerts, notifications, or automated responses
            
        except Exception as e:
            logger.error(
                "high_risk_event_handling_failed",
                event_id=event.event_id,
                error=str(e)
            )
    
    async def _send_to_siem(self, event: AuditEvent):
        """Send event to external SIEM system"""
        try:
            # Implementation would send to configured SIEM
            # (e.g., Splunk, ELK Stack, Azure Sentinel)
            pass
            
        except Exception as e:
            logger.error(
                "siem_transmission_failed",
                event_id=event.event_id,
                error=str(e)
            )
    
    def get_audit_events(self,
                        event_type: Optional[AuditEventType] = None,
                        user_id: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        risk_level: Optional[RiskLevel] = None) -> List[Dict[str, Any]]:
        """Retrieve audit events with filtering"""
        
        filtered_events = self.audit_events
        
        # Apply filters
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        if risk_level:
            filtered_events = [e for e in filtered_events if e.risk_level == risk_level]
        
        # Convert to dictionary format
        return [
            {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "risk_level": event.risk_level.value,
                "resource": event.resource,
                "action": event.action,
                "outcome": event.outcome,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "ip_address": event.ip_address,
                "data_classification": event.data_classification.value if event.data_classification else None,
                "details": event.details,
                "checksum": event.checksum,
                "signature": event.signature
            }
            for event in filtered_events
        ]
    
    def generate_compliance_report(self,
                                  framework: ComplianceFramework,
                                  start_date: datetime,
                                  end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for specific framework"""
        
        requirements = self.compliance_requirements.get(framework, {})
        required_events = requirements.get("required_events", [])
        
        # Filter events by framework and date range
        relevant_events = [
            event for event in self.audit_events
            if (framework in (event.compliance_frameworks or []) and
                start_date <= event.timestamp <= end_date)
        ]
        
        # Group events by type
        events_by_type = {}
        for event in relevant_events:
            event_type = event.event_type
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        
        # Generate compliance report
        report = {
            "framework": framework.value,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_events": len(relevant_events),
            "events_by_type": {
                event_type.value: len(events)
                for event_type, events in events_by_type.items()
            },
            "compliance_status": {
                "required_events_present": all(
                    req_type in events_by_type for req_type in required_events
                ),
                "missing_event_types": [
                    req_type.value for req_type in required_events
                    if req_type not in events_by_type
                ]
            },
            "risk_distribution": {},
            "integrity_verification": {
                "total_events_verified": 0,
                "verification_failures": 0
            }
        }
        
        # Calculate risk distribution
        for event in relevant_events:
            risk_level = event.risk_level.value
            report["risk_distribution"][risk_level] = report["risk_distribution"].get(risk_level, 0) + 1
        
        # Verify event integrity
        verified_count = 0
        failed_count = 0
        for event in relevant_events:
            if self.verify_event_integrity(event):
                verified_count += 1
            else:
                failed_count += 1
        
        report["integrity_verification"]["total_events_verified"] = verified_count
        report["integrity_verification"]["verification_failures"] = failed_count
        
        return report


# Factory function
def create_security_audit_logger(secret_key: Optional[str] = None,
                                storage_config: Optional[Dict] = None) -> SecurityAuditLogger:
    """Create SecurityAuditLogger instance"""
    return SecurityAuditLogger(secret_key=secret_key, storage_backend=storage_config)