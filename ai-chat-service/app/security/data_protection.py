"""
Comprehensive data protection service integrating all security components.

Provides unified data protection capabilities:
- Integration of encryption, key management, privacy compliance, and audit logging
- Data lifecycle management with automated retention policies
- Privacy-by-design implementation
- Compliance reporting and monitoring
- Unified interface for all data protection operations
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

import structlog

from .encryption import EncryptionManager, DataClassification, EncryptionContext
from .key_management import KeyManager, KeyRotationService, KeyType
from .privacy_compliance import GDPRComplianceManager, ConsentManager, ConsentType, GDPRRight
from .audit_logger import SecurityAuditLogger, AuditEventType, RiskLevel, ComplianceFramework
from .config_security import SecureConfigManager, SecretType, SecurityLevel

logger = structlog.get_logger(__name__)


class DataLifecycleStage(Enum):
    """Data lifecycle stages"""
    CREATION = "creation"
    ACTIVE_USE = "active_use"
    ARCHIVAL = "archival"
    DISPOSAL = "disposal"


class RetentionAction(Enum):
    """Actions for data retention"""
    RETAIN = "retain"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    DELETE = "delete"


@dataclass
class DataProtectionPolicy:
    """Data protection policy definition"""
    policy_id: str
    data_type: str
    classification: DataClassification
    retention_days: int
    lifecycle_actions: Dict[DataLifecycleStage, RetentionAction]
    encryption_required: bool
    anonymization_level: str
    compliance_frameworks: List[ComplianceFramework]
    audit_required: bool


class DataProtectionService:
    """
    Unified data protection service.
    
    Integrates all security components to provide comprehensive
    data protection capabilities with privacy-by-design principles.
    """
    
    def __init__(self):
        """Initialize data protection service with all components"""
        
        # Initialize core security components
        self.encryption_manager = EncryptionManager()
        self.key_manager = KeyManager()
        self.consent_manager = ConsentManager()
        self.gdpr_manager = GDPRComplianceManager(self.consent_manager)
        self.audit_logger = SecurityAuditLogger()
        self.config_manager = SecureConfigManager()
        
        # Initialize key rotation service
        self.key_rotation_service = KeyRotationService(self.key_manager)
        
        # Data protection policies
        self.protection_policies: Dict[str, DataProtectionPolicy] = {}
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info("data_protection_service_initialized")
    
    async def start_services(self):
        """Start background services"""
        try:
            await self.key_rotation_service.start()
            logger.info("data_protection_services_started")
        except Exception as e:
            logger.error("failed_to_start_data_protection_services", error=str(e))
            raise
    
    async def stop_services(self):
        """Stop background services"""
        try:
            await self.key_rotation_service.stop()
            logger.info("data_protection_services_stopped")
        except Exception as e:
            logger.error("failed_to_stop_data_protection_services", error=str(e))
    
    def _initialize_default_policies(self):
        """Initialize default data protection policies"""
        default_policies = [
            DataProtectionPolicy(
                policy_id="conversation_data",
                data_type="conversation",
                classification=DataClassification.CONFIDENTIAL,
                retention_days=365,
                lifecycle_actions={
                    DataLifecycleStage.CREATION: RetentionAction.RETAIN,
                    DataLifecycleStage.ACTIVE_USE: RetentionAction.RETAIN,
                    DataLifecycleStage.ARCHIVAL: RetentionAction.ARCHIVE,
                    DataLifecycleStage.DISPOSAL: RetentionAction.ANONYMIZE
                },
                encryption_required=True,
                anonymization_level="standard",
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2],
                audit_required=True
            ),
            DataProtectionPolicy(
                policy_id="user_profile",
                data_type="user_profile",
                classification=DataClassification.RESTRICTED,
                retention_days=2555,  # 7 years
                lifecycle_actions={
                    DataLifecycleStage.CREATION: RetentionAction.RETAIN,
                    DataLifecycleStage.ACTIVE_USE: RetentionAction.RETAIN,
                    DataLifecycleStage.ARCHIVAL: RetentionAction.ARCHIVE,
                    DataLifecycleStage.DISPOSAL: RetentionAction.DELETE
                },
                encryption_required=True,
                anonymization_level="strong",
                compliance_frameworks=[ComplianceFramework.GDPR],
                audit_required=True
            ),
            DataProtectionPolicy(
                policy_id="analytics_data",
                data_type="analytics",
                classification=DataClassification.INTERNAL,
                retention_days=730,  # 2 years
                lifecycle_actions={
                    DataLifecycleStage.CREATION: RetentionAction.RETAIN,
                    DataLifecycleStage.ACTIVE_USE: RetentionAction.RETAIN,
                    DataLifecycleStage.ARCHIVAL: RetentionAction.ANONYMIZE,
                    DataLifecycleStage.DISPOSAL: RetentionAction.DELETE
                },
                encryption_required=True,
                anonymization_level="basic",
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2],
                audit_required=False
            )
        ]
        
        for policy in default_policies:
            self.protection_policies[policy.policy_id] = policy
    
    async def protect_data(self,
                          data: Union[str, Dict, List],
                          data_type: str,
                          user_id: Optional[str] = None,
                          session_id: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Apply comprehensive data protection to data.
        
        Args:
            data: Data to protect
            data_type: Type of data for policy lookup
            user_id: User identifier
            session_id: Session identifier
            context: Additional context information
            
        Returns:
            Protected data package with metadata
        """
        try:
            # Get protection policy
            policy = self.protection_policies.get(data_type)
            if not policy:
                logger.warning("no_protection_policy_found", data_type=data_type)
                # Use default confidential policy
                classification = DataClassification.CONFIDENTIAL
                audit_required = True
            else:
                classification = policy.classification
                audit_required = policy.audit_required
            
            # Create encryption context
            encryption_context = EncryptionContext(
                classification=classification,
                user_id=user_id,
                session_id=session_id,
                purpose=f"data_protection:{data_type}",
                requires_audit=audit_required
            )
            
            # Encrypt data
            protected_data = self.encryption_manager.encrypt_data(data, encryption_context)
            
            # Add protection metadata
            protection_metadata = {
                "data_type": data_type,
                "protection_policy": policy.policy_id if policy else "default_confidential",
                "protected_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "context": context or {}
            }
            
            protected_data["protection_metadata"] = protection_metadata
            
            # Audit log data protection
            if audit_required:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DATA_MODIFICATION,
                    resource=f"{data_type}_data",
                    action="data_protection_applied",
                    user_id=user_id,
                    session_id=session_id,
                    details={
                        "data_type": data_type,
                        "classification": classification.value,
                        "encrypted": protected_data.get("encrypted", False)
                    },
                    risk_level=RiskLevel.LOW,
                    data_classification=classification,
                    compliance_frameworks=policy.compliance_frameworks if policy else [ComplianceFramework.GDPR]
                )
            
            logger.debug(
                "data_protected",
                data_type=data_type,
                user_id=user_id,
                classification=classification.value,
                encrypted=protected_data.get("encrypted", False)
            )
            
            return protected_data
            
        except Exception as e:
            logger.error(
                "data_protection_failed",
                error=str(e),
                data_type=data_type,
                user_id=user_id
            )
            raise
    
    async def access_protected_data(self,
                                   protected_data: Dict[str, Any],
                                   user_id: Optional[str] = None,
                                   session_id: Optional[str] = None,
                                   purpose: Optional[str] = None) -> Any:
        """
        Access protected data with proper authorization and audit logging.
        
        Args:
            protected_data: Protected data package
            user_id: User requesting access
            session_id: Session identifier
            purpose: Purpose for data access
            
        Returns:
            Decrypted data
        """
        try:
            # Extract protection metadata
            protection_metadata = protected_data.get("protection_metadata", {})
            data_type = protection_metadata.get("data_type", "unknown")
            original_user_id = protection_metadata.get("user_id")
            
            # Get protection policy
            policy = self.protection_policies.get(data_type)
            
            # Check consent if required
            if policy and ComplianceFramework.GDPR in policy.compliance_frameworks:
                if original_user_id and not await self._check_data_access_consent(original_user_id, data_type):
                    logger.warning(
                        "data_access_denied_no_consent",
                        user_id=user_id,
                        original_user_id=original_user_id,
                        data_type=data_type
                    )
                    raise PermissionError("Data access denied: No valid consent")
            
            # Decrypt data
            decrypted_data = self.encryption_manager.decrypt_data(protected_data)
            
            # Audit log data access
            if policy and policy.audit_required:
                await self.audit_logger.log_data_access(
                    resource=f"{data_type}_data",
                    user_id=user_id,
                    session_id=session_id,
                    data_classification=policy.classification,
                    query_details={
                        "purpose": purpose,
                        "original_user_id": original_user_id,
                        "access_granted": True
                    }
                )
            
            logger.debug(
                "protected_data_accessed",
                data_type=data_type,
                user_id=user_id,
                original_user_id=original_user_id,
                purpose=purpose
            )
            
            return decrypted_data
            
        except Exception as e:
            logger.error(
                "protected_data_access_failed",
                error=str(e),
                user_id=user_id,
                session_id=session_id
            )
            
            # Audit failed access attempt
            await self.audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                resource="protected_data",
                action="access_attempt",
                outcome="failure",
                user_id=user_id,
                session_id=session_id,
                details={"error": str(e), "purpose": purpose},
                risk_level=RiskLevel.MEDIUM,
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2]
            )
            
            raise
    
    async def handle_privacy_request(self,
                                    request_type: str,
                                    user_id: str,
                                    details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle GDPR privacy requests.
        
        Args:
            request_type: Type of privacy request (access, erasure, etc.)
            user_id: User making the request
            details: Additional request details
            
        Returns:
            Request fulfillment results
        """
        try:
            start_time = datetime.now()
            
            # Map request types to GDPR rights
            gdpr_rights_map = {
                "access": GDPRRight.ACCESS,
                "erasure": GDPRRight.ERASURE,
                "rectification": GDPRRight.RECTIFICATION,
                "portability": GDPRRight.DATA_PORTABILITY,
                "restrict": GDPRRight.RESTRICT_PROCESSING,
                "object": GDPRRight.OBJECT
            }
            
            gdpr_right = gdpr_rights_map.get(request_type.lower())
            if not gdpr_right:
                raise ValueError(f"Unknown privacy request type: {request_type}")
            
            # Handle different request types
            if request_type.lower() == "access":
                result = await self.gdpr_manager.fulfill_access_request(user_id)
            elif request_type.lower() == "erasure":
                result = await self.gdpr_manager.fulfill_erasure_request(user_id, details.get("specific_data") if details else None)
            else:
                # Placeholder for other request types
                result = {
                    "request_type": request_type,
                    "user_id": user_id,
                    "status": "not_implemented",
                    "message": f"Request type '{request_type}' is not yet implemented"
                }
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Audit log the privacy request
            await self.audit_logger.log_privacy_request(
                request_type=request_type,
                user_id=user_id,
                details={
                    "gdpr_article": f"Article {gdpr_right.value}" if gdpr_right else None,
                    "processing_time_ms": processing_time,
                    "result_status": result.get("status", "completed")
                },
                outcome="success"
            )
            
            logger.info(
                "privacy_request_fulfilled",
                request_type=request_type,
                user_id=user_id,
                processing_time_ms=processing_time
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "privacy_request_failed",
                error=str(e),
                request_type=request_type,
                user_id=user_id
            )
            
            # Audit failed request
            await self.audit_logger.log_privacy_request(
                request_type=request_type,
                user_id=user_id,
                details={"error": str(e)},
                outcome="failure"
            )
            
            raise
    
    async def process_consent_change(self,
                                    user_id: str,
                                    consent_type: str,
                                    granted: bool,
                                    purpose: str,
                                    ip_address: Optional[str] = None,
                                    user_agent: Optional[str] = None) -> bool:
        """
        Process user consent changes with audit logging.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent
            granted: Whether consent is granted or withdrawn
            purpose: Purpose for consent
            ip_address: User's IP address
            user_agent: User's browser agent
            
        Returns:
            Success boolean
        """
        try:
            # Map consent type string to enum
            consent_type_map = {
                "necessary": ConsentType.NECESSARY,
                "functional": ConsentType.FUNCTIONAL,
                "analytics": ConsentType.ANALYTICS,
                "marketing": ConsentType.MARKETING,
                "personalization": ConsentType.PERSONALIZATION,
                "third_party": ConsentType.THIRD_PARTY
            }
            
            consent_enum = consent_type_map.get(consent_type.lower())
            if not consent_enum:
                raise ValueError(f"Unknown consent type: {consent_type}")
            
            # Process consent change
            if granted:
                from .privacy_compliance import ConsentStatus, DataProcessingPurpose
                
                consent_id = await self.consent_manager.record_consent(
                    user_id=user_id,
                    consent_type=consent_enum,
                    status=ConsentStatus.GRANTED,
                    purpose=purpose,
                    legal_basis=DataProcessingPurpose.CONSENT,
                    version="1.0",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:
                success = await self.consent_manager.withdraw_consent(
                    user_id=user_id,
                    consent_type=consent_enum,
                    purpose=purpose
                )
                consent_id = "withdrawn" if success else None
            
            # Audit log consent change
            await self.audit_logger.log_event(
                event_type=AuditEventType.CONSENT_CHANGE,
                resource=f"user_consent:{user_id}",
                action="consent_granted" if granted else "consent_withdrawn",
                user_id=user_id,
                details={
                    "consent_type": consent_type,
                    "purpose": purpose,
                    "consent_id": consent_id,
                    "granted": granted
                },
                risk_level=RiskLevel.LOW,
                compliance_frameworks=[ComplianceFramework.GDPR],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                "consent_change_processed",
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                consent_id=consent_id
            )
            
            return consent_id is not None
            
        except Exception as e:
            logger.error(
                "consent_change_failed",
                error=str(e),
                user_id=user_id,
                consent_type=consent_type,
                granted=granted
            )
            raise
    
    async def apply_retention_policy(self, data_type: str) -> Dict[str, Any]:
        """
        Apply data retention policy to all data of specified type.
        
        Args:
            data_type: Type of data to process
            
        Returns:
            Retention processing results
        """
        try:
            policy = self.protection_policies.get(data_type)
            if not policy:
                logger.warning("no_retention_policy_found", data_type=data_type)
                return {"status": "no_policy", "data_type": data_type}
            
            results = {
                "data_type": data_type,
                "policy_id": policy.policy_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "actions_taken": {},
                "total_records_processed": 0
            }
            
            # This would integrate with your actual data storage systems
            # For now, we'll simulate the process
            
            # Determine current lifecycle stage based on data age
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            
            # Archive old data
            if DataLifecycleStage.ARCHIVAL in policy.lifecycle_actions:
                action = policy.lifecycle_actions[DataLifecycleStage.ARCHIVAL]
                if action == RetentionAction.ARCHIVE:
                    archived_count = await self._archive_old_data(data_type, cutoff_date)
                    results["actions_taken"]["archived"] = archived_count
                elif action == RetentionAction.ANONYMIZE:
                    anonymized_count = await self._anonymize_old_data(data_type, cutoff_date, policy.anonymization_level)
                    results["actions_taken"]["anonymized"] = anonymized_count
                elif action == RetentionAction.DELETE:
                    deleted_count = await self._delete_old_data(data_type, cutoff_date)
                    results["actions_taken"]["deleted"] = deleted_count
            
            # Audit log retention policy application
            await self.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"{data_type}_retention",
                action="retention_policy_applied",
                details={
                    "policy_id": policy.policy_id,
                    "retention_days": policy.retention_days,
                    "actions_taken": results["actions_taken"]
                },
                risk_level=RiskLevel.LOW,
                data_classification=policy.classification,
                compliance_frameworks=policy.compliance_frameworks
            )
            
            logger.info(
                "retention_policy_applied",
                data_type=data_type,
                policy_id=policy.policy_id,
                actions_taken=results["actions_taken"]
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "retention_policy_failed",
                error=str(e),
                data_type=data_type
            )
            raise
    
    async def _check_data_access_consent(self, user_id: str, data_type: str) -> bool:
        """Check if user has valid consent for data access"""
        try:
            # Map data types to consent requirements
            consent_requirements = {
                "conversation": ConsentType.FUNCTIONAL,
                "analytics": ConsentType.ANALYTICS,
                "user_profile": ConsentType.NECESSARY  # Always allowed
            }
            
            required_consent = consent_requirements.get(data_type, ConsentType.FUNCTIONAL)
            
            # Necessary consent is always valid
            if required_consent == ConsentType.NECESSARY:
                return True
            
            # Check actual consent
            return await self.consent_manager.check_consent(user_id, required_consent)
            
        except Exception as e:
            logger.error(
                "consent_check_failed",
                error=str(e),
                user_id=user_id,
                data_type=data_type
            )
            return False
    
    async def _archive_old_data(self, data_type: str, cutoff_date: datetime) -> int:
        """Archive old data (placeholder implementation)"""
        # This would integrate with your actual storage systems
        logger.info("archiving_old_data", data_type=data_type, cutoff_date=cutoff_date.isoformat())
        return 0  # Placeholder
    
    async def _anonymize_old_data(self, data_type: str, cutoff_date: datetime, level: str) -> int:
        """Anonymize old data (placeholder implementation)"""
        # This would integrate with your actual storage systems and use the anonymization methods
        logger.info("anonymizing_old_data", data_type=data_type, cutoff_date=cutoff_date.isoformat(), level=level)
        return 0  # Placeholder
    
    async def _delete_old_data(self, data_type: str, cutoff_date: datetime) -> int:
        """Delete old data (placeholder implementation)"""
        # This would integrate with your actual storage systems
        logger.info("deleting_old_data", data_type=data_type, cutoff_date=cutoff_date.isoformat())
        return 0  # Placeholder
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Get comprehensive data protection status"""
        try:
            # Get key rotation status
            keys_needing_rotation = asyncio.run(self.key_manager.check_rotation_needed())
            
            # Get security configuration status
            security_config = self.config_manager.get_security_configuration()
            
            # Get secrets rotation status
            secrets_needing_rotation = self.config_manager.check_secrets_needing_rotation()
            
            status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "protection_policies": {
                    "total_policies": len(self.protection_policies),
                    "policies_by_classification": {}
                },
                "encryption_status": {
                    "encryption_manager_active": True,
                    "master_key_available": self.encryption_manager.master_key is not None
                },
                "key_management": {
                    "total_keys": len(self.key_manager.keys),
                    "keys_needing_rotation": len(keys_needing_rotation),
                    "rotation_service_running": self.key_rotation_service.running
                },
                "configuration_security": security_config,
                "secrets_management": {
                    "secrets_needing_rotation": len(secrets_needing_rotation)
                },
                "compliance_status": {
                    "gdpr_manager_active": True,
                    "consent_manager_active": True,
                    "audit_logger_active": True
                }
            }
            
            # Count policies by classification
            for policy in self.protection_policies.values():
                classification = policy.classification.value
                status["protection_policies"]["policies_by_classification"][classification] = \
                    status["protection_policies"]["policies_by_classification"].get(classification, 0) + 1
            
            return status
            
        except Exception as e:
            logger.error("failed_to_get_protection_status", error=str(e))
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
    
    def generate_compliance_report(self,
                                  framework: str,
                                  days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            # Map framework string to enum
            framework_map = {
                "gdpr": ComplianceFramework.GDPR,
                "soc2": ComplianceFramework.SOC2,
                "hipaa": ComplianceFramework.HIPAA,
                "pci_dss": ComplianceFramework.PCI_DSS,
                "iso27001": ComplianceFramework.ISO27001
            }
            
            framework_enum = framework_map.get(framework.lower())
            if not framework_enum:
                raise ValueError(f"Unknown compliance framework: {framework}")
            
            # Generate audit report
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            audit_report = self.audit_logger.generate_compliance_report(
                framework_enum,
                start_date,
                end_date
            )
            
            # Add data protection specific information
            report = {
                **audit_report,
                "data_protection_status": {
                    "policies_compliant": self._check_policy_compliance(framework_enum),
                    "encryption_status": "active",
                    "key_rotation_status": "active" if self.key_rotation_service.running else "inactive",
                    "retention_policies_active": len(self.protection_policies) > 0
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(
                "compliance_report_failed",
                error=str(e),
                framework=framework,
                days=days
            )
            return {"error": str(e), "framework": framework, "days": days}
    
    def _check_policy_compliance(self, framework: ComplianceFramework) -> bool:
        """Check if current policies are compliant with framework"""
        # Check if we have policies that cover the required framework
        for policy in self.protection_policies.values():
            if framework in policy.compliance_frameworks:
                return True
        return False


# Factory function
def create_data_protection_service() -> DataProtectionService:
    """Create DataProtectionService instance"""
    return DataProtectionService()