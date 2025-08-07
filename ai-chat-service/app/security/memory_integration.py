"""
Security integration for existing memory systems (Redis and ClickHouse).

Provides secure wrappers for memory operations:
- Encrypted Redis conversation storage
- Encrypted ClickHouse analytics storage
- Automated audit logging for all memory operations
- GDPR compliance for conversation data
- Data retention policy enforcement
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone

import structlog

from .data_protection import DataProtectionService
from .encryption import DataClassification
from .audit_logger import AuditEventType, RiskLevel, ComplianceFramework
from ..memory.redis_memory import ConversationMemoryCache
from ..memory.clickhouse_memory import ConversationClickHouseManager

logger = structlog.get_logger(__name__)


class SecureConversationMemoryCache:
    """
    Secure wrapper for Redis conversation memory with encryption and audit logging.
    
    Extends ConversationMemoryCache with:
    - Automatic data encryption for sensitive content
    - Audit logging for all memory operations
    - GDPR compliance checks
    - Data retention policy enforcement
    """
    
    def __init__(self, 
                 redis_cache,
                 data_protection_service: Optional[DataProtectionService] = None):
        """
        Initialize secure conversation memory cache.
        
        Args:
            redis_cache: Underlying Redis cache manager
            data_protection_service: Data protection service instance
        """
        self.base_cache = ConversationMemoryCache(redis_cache)
        self.data_protection = data_protection_service or DataProtectionService()
        
        logger.info("secure_conversation_memory_cache_initialized")
    
    async def add_message_secure(self,
                                session_id: str,
                                message: Dict,
                                tokens: int,
                                user_id: Optional[str] = None,
                                token_budget: Optional[int] = None,
                                ttl: Optional[int] = None,
                                ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Add message with security protection.
        
        Args:
            session_id: Session identifier
            message: Message data
            tokens: Token count
            user_id: User identifier for compliance
            token_budget: Token budget
            ttl: Time to live
            ip_address: Client IP for audit
            
        Returns:
            Operation result with security metadata
        """
        try:
            # Check consent for storing conversation data
            if user_id:
                consent_valid = await self._check_conversation_consent(user_id)
                if not consent_valid:
                    logger.warning(
                        "conversation_storage_denied_no_consent",
                        user_id=user_id,
                        session_id=session_id
                    )
                    return {
                        "success": False,
                        "error": "Storage denied: No valid consent for conversation data",
                        "requires_consent": True
                    }
            
            # Apply data protection to message
            protected_message = await self.data_protection.protect_data(
                data=message,
                data_type="conversation",
                user_id=user_id,
                session_id=session_id,
                context={"tokens": tokens, "ip_address": ip_address}
            )
            
            # Store protected message
            result = await self.base_cache.add_message(
                session_id=session_id,
                message=protected_message,
                tokens=tokens,
                token_budget=token_budget,
                ttl=ttl
            )
            
            # Audit log the operation
            await self.data_protection.audit_logger.log_data_access(
                resource=f"conversation:{session_id}",
                user_id=user_id,
                session_id=session_id,
                data_classification=DataClassification.CONFIDENTIAL,
                query_details={
                    "operation": "add_message",
                    "tokens": tokens,
                    "protected": protected_message.get("encrypted", False)
                },
                ip_address=ip_address
            )
            
            # Add security metadata to result
            if result.get("success"):
                result["security"] = {
                    "encrypted": protected_message.get("encrypted", False),
                    "classification": "confidential",
                    "audit_logged": True,
                    "consent_checked": user_id is not None
                }
            
            logger.debug(
                "secure_message_added",
                session_id=session_id,
                user_id=user_id,
                tokens=tokens,
                encrypted=protected_message.get("encrypted", False)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "secure_message_add_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"conversation:{session_id}",
                action="add_message",
                outcome="failure",
                user_id=user_id,
                session_id=session_id,
                details={"error": str(e), "tokens": tokens},
                risk_level=RiskLevel.MEDIUM,
                data_classification=DataClassification.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            return {
                "success": False,
                "error": str(e),
                "security": {"audit_logged": True}
            }
    
    async def get_recent_messages_secure(self,
                                        session_id: str,
                                        limit: Optional[int] = None,
                                        user_id: Optional[str] = None,
                                        purpose: str = "chat_response",
                                        ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recent messages with security checks and decryption.
        
        Args:
            session_id: Session identifier
            limit: Message limit
            user_id: User identifier for compliance
            purpose: Purpose for data access
            ip_address: Client IP for audit
            
        Returns:
            Messages with security metadata
        """
        try:
            # Check consent for accessing conversation data
            if user_id:
                consent_valid = await self._check_conversation_consent(user_id)
                if not consent_valid:
                    logger.warning(
                        "conversation_access_denied_no_consent",
                        user_id=user_id,
                        session_id=session_id
                    )
                    return {
                        "success": False,
                        "error": "Access denied: No valid consent for conversation data",
                        "messages": [],
                        "requires_consent": True
                    }
            
            # Get protected messages from base cache
            result = await self.base_cache.get_recent_messages(session_id, limit)
            
            if result.get("success") and result.get("messages"):
                # Decrypt messages
                decrypted_messages = []
                for protected_message in result["messages"]:
                    try:
                        if isinstance(protected_message, dict) and "protection_metadata" in protected_message:
                            # This is a protected message, decrypt it
                            decrypted_message = await self.data_protection.access_protected_data(
                                protected_data=protected_message,
                                user_id=user_id,
                                session_id=session_id,
                                purpose=purpose
                            )
                            decrypted_messages.append(decrypted_message)
                        else:
                            # Legacy unprotected message
                            decrypted_messages.append(protected_message)
                    except Exception as e:
                        logger.warning(
                            "message_decryption_failed",
                            error=str(e),
                            session_id=session_id,
                            message_index=len(decrypted_messages)
                        )
                        # Skip failed decryption but continue with other messages
                        continue
                
                result["messages"] = decrypted_messages
                result["security"] = {
                    "decrypted_count": len(decrypted_messages),
                    "total_count": len(result["messages"]),
                    "classification": "confidential",
                    "audit_logged": True,
                    "consent_checked": user_id is not None
                }
                
                # Audit log successful access
                await self.data_protection.audit_logger.log_data_access(
                    resource=f"conversation:{session_id}",
                    user_id=user_id,
                    session_id=session_id,
                    data_classification=DataClassification.CONFIDENTIAL,
                    query_details={
                        "operation": "get_messages",
                        "purpose": purpose,
                        "limit": limit,
                        "messages_returned": len(decrypted_messages)
                    },
                    ip_address=ip_address
                )
            
            logger.debug(
                "secure_messages_retrieved",
                session_id=session_id,
                user_id=user_id,
                message_count=len(result.get("messages", [])),
                purpose=purpose
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "secure_message_retrieval_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                resource=f"conversation:{session_id}",
                action="get_messages",
                outcome="failure",
                user_id=user_id,
                session_id=session_id,
                details={"error": str(e), "purpose": purpose, "limit": limit},
                risk_level=RiskLevel.MEDIUM,
                data_classification=DataClassification.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            return {
                "success": False,
                "error": str(e),
                "messages": [],
                "security": {"audit_logged": True}
            }
    
    async def delete_conversation_secure(self,
                                        session_id: str,
                                        user_id: Optional[str] = None,
                                        reason: str = "user_request",
                                        ip_address: Optional[str] = None) -> bool:
        """
        Delete conversation with audit logging and GDPR compliance.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            reason: Reason for deletion
            ip_address: Client IP for audit
            
        Returns:
            Success boolean
        """
        try:
            # Delete from base cache
            success = await self.base_cache.delete_conversation(session_id)
            
            # Audit log the deletion
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_DELETION,
                resource=f"conversation:{session_id}",
                action="delete_conversation",
                outcome="success" if success else "failure",
                user_id=user_id,
                session_id=session_id,
                details={
                    "reason": reason,
                    "deleted": success
                },
                risk_level=RiskLevel.MEDIUM,
                data_classification=DataClassification.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            logger.info(
                "secure_conversation_deleted",
                session_id=session_id,
                user_id=user_id,
                reason=reason,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "secure_conversation_deletion_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_DELETION,
                resource=f"conversation:{session_id}",
                action="delete_conversation",
                outcome="failure",
                user_id=user_id,
                session_id=session_id,
                details={"error": str(e), "reason": reason},
                risk_level=RiskLevel.HIGH,
                data_classification=DataClassification.CONFIDENTIAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            return False
    
    async def _check_conversation_consent(self, user_id: str) -> bool:
        """Check if user has valid consent for conversation storage/access"""
        try:
            from .privacy_compliance import ConsentType
            return await self.data_protection.consent_manager.check_consent(
                user_id=user_id,
                consent_type=ConsentType.FUNCTIONAL,
                purpose="conversation_storage"
            )
        except Exception as e:
            logger.error("consent_check_failed", error=str(e), user_id=user_id)
            return False


class SecureClickHouseManager:
    """
    Secure wrapper for ClickHouse conversation analytics with encryption and compliance.
    
    Extends ConversationClickHouseManager with:
    - Encrypted storage of sensitive analytics data
    - Audit logging for all analytics operations
    - Data retention policy enforcement
    - GDPR compliance for user analytics
    """
    
    def __init__(self,
                 clickhouse_manager: ConversationClickHouseManager,
                 data_protection_service: Optional[DataProtectionService] = None):
        """
        Initialize secure ClickHouse manager.
        
        Args:
            clickhouse_manager: Underlying ClickHouse manager
            data_protection_service: Data protection service instance
        """
        self.base_manager = clickhouse_manager
        self.data_protection = data_protection_service or DataProtectionService()
        
        logger.info("secure_clickhouse_manager_initialized")
    
    async def store_conversation_summary_secure(self,
                                               session_id: str,
                                               summary: str,
                                               metadata: Dict[str, Any],
                                               user_id: Optional[str] = None,
                                               ip_address: Optional[str] = None) -> bool:
        """
        Store conversation summary with encryption and audit logging.
        
        Args:
            session_id: Session identifier
            summary: Summary text
            metadata: Summary metadata
            user_id: User identifier
            ip_address: Client IP for audit
            
        Returns:
            Success boolean
        """
        try:
            # Check consent for analytics storage
            if user_id:
                consent_valid = await self._check_analytics_consent(user_id)
                if not consent_valid:
                    logger.warning(
                        "analytics_storage_denied_no_consent",
                        user_id=user_id,
                        session_id=session_id
                    )
                    return False
            
            # Apply data protection to summary
            protected_summary = await self.data_protection.protect_data(
                data=summary,
                data_type="analytics",
                user_id=user_id,
                session_id=session_id,
                context={"type": "conversation_summary", "ip_address": ip_address}
            )
            
            # Store protected summary
            success = await self.base_manager.store_conversation_summary(
                session_id=session_id,
                summary=json.dumps(protected_summary) if protected_summary.get("encrypted") else summary,
                metadata=metadata,
                user_id=user_id
            )
            
            # Audit log the operation
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"analytics:conversation_summary:{session_id}",
                action="store_summary",
                outcome="success" if success else "failure",
                user_id=user_id,
                session_id=session_id,
                details={
                    "summary_length": len(summary),
                    "metadata": metadata,
                    "encrypted": protected_summary.get("encrypted", False)
                },
                risk_level=RiskLevel.LOW,
                data_classification=DataClassification.INTERNAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            logger.debug(
                "secure_summary_stored",
                session_id=session_id,
                user_id=user_id,
                encrypted=protected_summary.get("encrypted", False),
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "secure_summary_storage_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"analytics:conversation_summary:{session_id}",
                action="store_summary",
                outcome="failure",
                user_id=user_id,
                session_id=session_id,
                details={"error": str(e)},
                risk_level=RiskLevel.MEDIUM,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            return False
    
    async def store_quality_metrics_secure(self,
                                          session_id: str,
                                          metrics: Dict[str, Any],
                                          user_id: Optional[str] = None,
                                          routing_info: Optional[Dict[str, Any]] = None,
                                          ip_address: Optional[str] = None) -> bool:
        """
        Store conversation quality metrics with security controls.
        
        Args:
            session_id: Session identifier
            metrics: Quality metrics
            user_id: User identifier
            routing_info: Routing configuration info
            ip_address: Client IP for audit
            
        Returns:
            Success boolean
        """
        try:
            # Check consent for analytics storage
            if user_id:
                consent_valid = await self._check_analytics_consent(user_id)
                if not consent_valid:
                    # Store anonymized metrics without user_id
                    metrics_copy = metrics.copy()
                    user_id = None
                    logger.info(
                        "storing_anonymized_metrics_no_consent",
                        session_id=session_id
                    )
            
            # Store quality metrics (metrics are generally not PII, so less protection needed)
            success = await self.base_manager.store_conversation_quality_metrics(
                session_id=session_id,
                metrics=metrics,
                user_id=user_id,
                routing_info=routing_info
            )
            
            # Audit log the operation
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"analytics:quality_metrics:{session_id}",
                action="store_metrics",
                outcome="success" if success else "failure",
                user_id=user_id,
                session_id=session_id,
                details={
                    "metrics_count": len(metrics),
                    "has_routing_info": routing_info is not None,
                    "anonymized": user_id is None
                },
                risk_level=RiskLevel.LOW,
                data_classification=DataClassification.INTERNAL,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            logger.debug(
                "secure_metrics_stored",
                session_id=session_id,
                user_id=user_id,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "secure_metrics_storage_failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id
            )
            return False
    
    async def get_analytics_secure(self,
                                  days: int = 7,
                                  user_id: Optional[str] = None,
                                  routing_arm: Optional[str] = None,
                                  requester_user_id: Optional[str] = None,
                                  ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics data with security controls and consent checks.
        
        Args:
            days: Number of days to analyze
            user_id: User filter (for user-specific analytics)
            routing_arm: Routing arm filter
            requester_user_id: User requesting the analytics
            ip_address: Client IP for audit
            
        Returns:
            Analytics data with security metadata
        """
        try:
            # If requesting user-specific analytics, check consent
            if user_id:
                consent_valid = await self._check_analytics_consent(user_id)
                if not consent_valid:
                    logger.warning(
                        "user_analytics_access_denied_no_consent",
                        user_id=user_id,
                        requester=requester_user_id
                    )
                    return {
                        "error": "Access denied: No valid consent for user analytics",
                        "requires_consent": True
                    }
            
            # Get analytics from base manager
            analytics = await self.base_manager.get_conversation_analytics(
                days=days,
                user_id=user_id,
                routing_arm=routing_arm
            )
            
            # Add security metadata
            analytics["security"] = {
                "user_specific": user_id is not None,
                "consent_checked": user_id is not None,
                "classification": "internal",
                "audit_logged": True
            }
            
            # Audit log the access
            await self.data_protection.audit_logger.log_data_access(
                resource="analytics:conversation_analytics",
                user_id=requester_user_id,
                data_classification=DataClassification.INTERNAL,
                query_details={
                    "days": days,
                    "user_filter": user_id,
                    "routing_arm": routing_arm,
                    "records_returned": analytics.get("overall_metrics", {}).get("total_conversations", 0)
                },
                ip_address=ip_address
            )
            
            logger.debug(
                "secure_analytics_retrieved",
                days=days,
                user_id=user_id,
                requester=requester_user_id,
                total_conversations=analytics.get("overall_metrics", {}).get("total_conversations", 0)
            )
            
            return analytics
            
        except Exception as e:
            logger.error(
                "secure_analytics_retrieval_failed",
                error=str(e),
                days=days,
                user_id=user_id,
                requester=requester_user_id
            )
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                resource="analytics:conversation_analytics",
                action="get_analytics",
                outcome="failure",
                user_id=requester_user_id,
                details={"error": str(e), "days": days, "user_filter": user_id},
                risk_level=RiskLevel.MEDIUM,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address
            )
            
            return {"error": str(e)}
    
    async def _check_analytics_consent(self, user_id: str) -> bool:
        """Check if user has valid consent for analytics storage/access"""
        try:
            from .privacy_compliance import ConsentType
            return await self.data_protection.consent_manager.check_consent(
                user_id=user_id,
                consent_type=ConsentType.ANALYTICS,
                purpose="conversation_analytics"
            )
        except Exception as e:
            logger.error("analytics_consent_check_failed", error=str(e), user_id=user_id)
            return False


# Factory functions
def create_secure_conversation_cache(redis_cache, data_protection_service: Optional[DataProtectionService] = None) -> SecureConversationMemoryCache:
    """Create secure conversation memory cache"""
    return SecureConversationMemoryCache(redis_cache, data_protection_service)


def create_secure_clickhouse_manager(clickhouse_manager: ConversationClickHouseManager, data_protection_service: Optional[DataProtectionService] = None) -> SecureClickHouseManager:
    """Create secure ClickHouse manager"""
    return SecureClickHouseManager(clickhouse_manager, data_protection_service)