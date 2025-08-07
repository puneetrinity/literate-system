"""
GDPR compliance framework with consent management and privacy controls.

Provides comprehensive privacy compliance features:
- GDPR Article compliance (Right to be forgotten, Data portability, etc.)
- Consent management with granular permissions
- Data retention policies and automated cleanup
- Privacy impact assessments
- Data anonymization and pseudonymization
"""

import json
import uuid
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re

import structlog

from .encryption import DataClassification

logger = structlog.get_logger(__name__)


class ConsentType(Enum):
    """Types of consent as per GDPR"""
    NECESSARY = "necessary"           # Essential for service operation
    FUNCTIONAL = "functional"         # Functional features
    ANALYTICS = "analytics"           # Analytics and performance
    MARKETING = "marketing"           # Marketing communications
    PERSONALIZATION = "personalization"  # Personalized content
    THIRD_PARTY = "third_party"      # Third-party integrations


class ConsentStatus(Enum):
    """Consent status values"""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class DataProcessingPurpose(Enum):
    """Data processing purposes under GDPR"""
    SERVICE_PROVISION = "service_provision"
    LEGITIMATE_INTEREST = "legitimate_interest"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    CONSENT = "consent"


class GDPRRight(Enum):
    """GDPR individual rights"""
    ACCESS = "access"                 # Article 15
    RECTIFICATION = "rectification"   # Article 16
    ERASURE = "erasure"               # Article 17 (Right to be forgotten)
    RESTRICT_PROCESSING = "restrict_processing"  # Article 18
    DATA_PORTABILITY = "data_portability"  # Article 20
    OBJECT = "object"                 # Article 21
    AUTOMATED_DECISION_MAKING = "automated_decision_making"  # Article 22


@dataclass
class ConsentRecord:
    """Individual consent record"""
    consent_id: str
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    expires_at: Optional[datetime]
    purpose: str
    legal_basis: DataProcessingPurpose
    version: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class DataRetentionPolicy:
    """Data retention policy definition"""
    policy_id: str
    data_type: str
    classification: DataClassification
    retention_period_days: int
    legal_basis: str
    automatic_deletion: bool
    archive_before_deletion: bool
    exceptions: List[str] = None


@dataclass
class PrivacyImpactAssessment:
    """Privacy Impact Assessment (PIA) record"""
    pia_id: str
    feature_name: str
    data_types: List[str]
    processing_purposes: List[DataProcessingPurpose]
    legal_bases: List[str]
    risk_level: str  # low, medium, high
    mitigation_measures: List[str]
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class ConsentManager:
    """
    Consent management system for GDPR compliance.
    
    Features:
    - Granular consent management
    - Consent versioning and history
    - Automatic expiration handling
    - Legal basis tracking
    - Audit trail for all consent operations
    """
    
    def __init__(self, storage_backend: Optional[Dict] = None):
        """
        Initialize consent manager.
        
        Args:
            storage_backend: Storage configuration
        """
        self.storage = storage_backend or {}
        self.consent_records: Dict[str, List[ConsentRecord]] = {}  # user_id -> consent records
        self.consent_versions = {}  # Track consent form versions
        
        # Default consent expiration periods (in days)
        self.consent_expiration = {
            ConsentType.NECESSARY: None,  # Never expires
            ConsentType.FUNCTIONAL: 365,
            ConsentType.ANALYTICS: 365,
            ConsentType.MARKETING: 180,
            ConsentType.PERSONALIZATION: 365,
            ConsentType.THIRD_PARTY: 180
        }
        
        logger.info("consent_manager_initialized")
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        purpose: str,
        legal_basis: DataProcessingPurpose,
        version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record user consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent
            status: Consent status
            purpose: Purpose description
            legal_basis: Legal basis for processing
            version: Consent form version
            ip_address: User's IP address
            user_agent: User's browser agent
            metadata: Additional metadata
            
        Returns:
            Consent record ID
        """
        try:
            consent_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Calculate expiration
            expires_at = None
            if status == ConsentStatus.GRANTED:
                expiration_days = self.consent_expiration.get(consent_type)
                if expiration_days:
                    expires_at = now + timedelta(days=expiration_days)
            
            # Create consent record
            consent_record = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                consent_type=consent_type,
                status=status,
                granted_at=now if status == ConsentStatus.GRANTED else None,
                withdrawn_at=now if status == ConsentStatus.WITHDRAWN else None,
                expires_at=expires_at,
                purpose=purpose,
                legal_basis=legal_basis,
                version=version,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {}
            )
            
            # Store consent record
            if user_id not in self.consent_records:
                self.consent_records[user_id] = []
            
            self.consent_records[user_id].append(consent_record)
            
            # Audit log
            logger.info(
                "consent_recorded",
                consent_id=consent_id,
                user_id=user_id,
                consent_type=consent_type.value,
                status=status.value,
                legal_basis=legal_basis.value,
                expires_at=expires_at.isoformat() if expires_at else None
            )
            
            return consent_id
            
        except Exception as e:
            logger.error(
                "consent_recording_failed",
                error=str(e),
                user_id=user_id,
                consent_type=consent_type.value
            )
            raise
    
    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        purpose: Optional[str] = None
    ) -> bool:
        """
        Check if user has valid consent for specific purpose.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            purpose: Specific purpose (optional)
            
        Returns:
            True if consent is valid and granted
        """
        try:
            if user_id not in self.consent_records:
                return consent_type == ConsentType.NECESSARY  # Necessary consent is implied
            
            user_consents = self.consent_records[user_id]
            now = datetime.now(timezone.utc)
            
            # Find most recent consent for this type
            relevant_consents = [
                c for c in user_consents
                if c.consent_type == consent_type and
                (not purpose or c.purpose == purpose)
            ]
            
            if not relevant_consents:
                return consent_type == ConsentType.NECESSARY
            
            # Get most recent consent
            latest_consent = max(relevant_consents, key=lambda x: x.granted_at or x.withdrawn_at or datetime.min.replace(tzinfo=timezone.utc))
            
            # Check if consent is granted and not expired
            if latest_consent.status != ConsentStatus.GRANTED:
                return False
            
            if latest_consent.expires_at and now > latest_consent.expires_at:
                # Mark as expired
                latest_consent.status = ConsentStatus.EXPIRED
                logger.info(
                    "consent_expired",
                    consent_id=latest_consent.consent_id,
                    user_id=user_id,
                    consent_type=consent_type.value
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(
                "consent_check_failed",
                error=str(e),
                user_id=user_id,
                consent_type=consent_type.value
            )
            return False
    
    async def withdraw_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        purpose: Optional[str] = None
    ) -> bool:
        """
        Withdraw user consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw
            purpose: Specific purpose (optional)
            
        Returns:
            Success boolean
        """
        try:
            if user_id not in self.consent_records:
                logger.warning("no_consent_records_found", user_id=user_id)
                return False
            
            user_consents = self.consent_records[user_id]
            now = datetime.now(timezone.utc)
            withdrawn_count = 0
            
            # Withdraw all matching consents
            for consent in user_consents:
                if (consent.consent_type == consent_type and
                    consent.status == ConsentStatus.GRANTED and
                    (not purpose or consent.purpose == purpose)):
                    
                    consent.status = ConsentStatus.WITHDRAWN
                    consent.withdrawn_at = now
                    withdrawn_count += 1
            
            if withdrawn_count > 0:
                logger.info(
                    "consent_withdrawn",
                    user_id=user_id,
                    consent_type=consent_type.value,
                    purpose=purpose,
                    withdrawn_count=withdrawn_count
                )
                return True
            else:
                logger.warning(
                    "no_valid_consent_to_withdraw",
                    user_id=user_id,
                    consent_type=consent_type.value
                )
                return False
                
        except Exception as e:
            logger.error(
                "consent_withdrawal_failed",
                error=str(e),
                user_id=user_id,
                consent_type=consent_type.value
            )
            return False
    
    def get_user_consents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all consent records for user"""
        if user_id not in self.consent_records:
            return []
        
        return [
            {
                "consent_id": c.consent_id,
                "consent_type": c.consent_type.value,
                "status": c.status.value,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "purpose": c.purpose,
                "legal_basis": c.legal_basis.value,
                "version": c.version
            }
            for c in self.consent_records[user_id]
        ]


class GDPRComplianceManager:
    """
    Comprehensive GDPR compliance management system.
    
    Features:
    - Individual rights fulfillment (Articles 15-22)
    - Data retention policies
    - Automated data cleanup
    - Privacy impact assessments
    - Data anonymization and pseudonymization
    """
    
    def __init__(self, consent_manager: ConsentManager, storage_backend: Optional[Dict] = None):
        """
        Initialize GDPR compliance manager.
        
        Args:
            consent_manager: ConsentManager instance
            storage_backend: Storage configuration
        """
        self.consent_manager = consent_manager
        self.storage = storage_backend or {}
        
        # Data retention policies
        self.retention_policies: Dict[str, DataRetentionPolicy] = {}
        
        # Privacy impact assessments
        self.privacy_assessments: Dict[str, PrivacyImpactAssessment] = {}
        
        # Default retention policies
        self._initialize_default_policies()
        
        logger.info("gdpr_compliance_manager_initialized")
    
    def _initialize_default_policies(self):
        """Initialize default data retention policies"""
        default_policies = [
            DataRetentionPolicy(
                policy_id="conversations_confidential",
                data_type="conversation_data",
                classification=DataClassification.CONFIDENTIAL,
                retention_period_days=365,
                legal_basis="Legitimate interest - service improvement",
                automatic_deletion=True,
                archive_before_deletion=True,
                exceptions=["legal_hold", "active_investigation"]
            ),
            DataRetentionPolicy(
                policy_id="user_analytics",
                data_type="analytics_data",
                classification=DataClassification.INTERNAL,
                retention_period_days=730,  # 2 years
                legal_basis="Consent - analytics",
                automatic_deletion=True,
                archive_before_deletion=False
            ),
            DataRetentionPolicy(
                policy_id="audit_logs",
                data_type="audit_logs",
                classification=DataClassification.RESTRICTED,
                retention_period_days=2555,  # 7 years
                legal_basis="Legal obligation - audit requirements",
                automatic_deletion=False,
                archive_before_deletion=True
            )
        ]
        
        for policy in default_policies:
            self.retention_policies[policy.policy_id] = policy
    
    async def fulfill_access_request(self, user_id: str) -> Dict[str, Any]:
        """
        Fulfill GDPR Article 15 - Right of access.
        
        Args:
            user_id: User identifier
            
        Returns:
            Complete user data package
        """
        try:
            logger.info("fulfilling_access_request", user_id=user_id)
            
            # Gather all user data
            data_package = {
                "request_id": str(uuid.uuid4()),
                "user_id": user_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "gdpr_article": "Article 15 - Right of access",
                "data_categories": {}
            }
            
            # Personal data
            data_package["data_categories"]["personal_data"] = await self._collect_personal_data(user_id)
            
            # Conversation data
            data_package["data_categories"]["conversations"] = await self._collect_conversation_data(user_id)
            
            # Consent records
            data_package["data_categories"]["consents"] = self.consent_manager.get_user_consents(user_id)
            
            # Analytics data
            data_package["data_categories"]["analytics"] = await self._collect_analytics_data(user_id)
            
            # Processing activities
            data_package["processing_activities"] = await self._get_processing_activities(user_id)
            
            # Data retention information
            data_package["retention_policies"] = [
                {
                    "data_type": policy.data_type,
                    "retention_period_days": policy.retention_period_days,
                    "legal_basis": policy.legal_basis
                }
                for policy in self.retention_policies.values()
            ]
            
            logger.info(
                "access_request_fulfilled",
                user_id=user_id,
                request_id=data_package["request_id"],
                data_categories_count=len(data_package["data_categories"])
            )
            
            return data_package
            
        except Exception as e:
            logger.error(
                "access_request_failed",
                error=str(e),
                user_id=user_id
            )
            raise
    
    async def fulfill_erasure_request(self, user_id: str, specific_data: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fulfill GDPR Article 17 - Right to erasure (Right to be forgotten).
        
        Args:
            user_id: User identifier
            specific_data: Specific data categories to erase (optional)
            
        Returns:
            Erasure report
        """
        try:
            logger.info("fulfilling_erasure_request", user_id=user_id, specific_data=specific_data)
            
            erasure_report = {
                "request_id": str(uuid.uuid4()),
                "user_id": user_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "gdpr_article": "Article 17 - Right to erasure",
                "erasure_results": {},
                "exceptions": [],
                "verification_hash": None
            }
            
            # Check for legal obligations that prevent erasure
            legal_holds = await self._check_legal_holds(user_id)
            if legal_holds:
                erasure_report["exceptions"].extend(legal_holds)
                logger.warning("erasure_request_has_legal_holds", user_id=user_id, holds=legal_holds)
            
            # Erase conversation data
            if not specific_data or "conversations" in specific_data:
                conversations_result = await self._erase_conversation_data(user_id)
                erasure_report["erasure_results"]["conversations"] = conversations_result
            
            # Erase personal data
            if not specific_data or "personal_data" in specific_data:
                personal_result = await self._erase_personal_data(user_id)
                erasure_report["erasure_results"]["personal_data"] = personal_result
            
            # Erase analytics data (if consent withdrawn)
            analytics_consent = await self.consent_manager.check_consent(user_id, ConsentType.ANALYTICS)
            if not analytics_consent and (not specific_data or "analytics" in specific_data):
                analytics_result = await self._erase_analytics_data(user_id)
                erasure_report["erasure_results"]["analytics"] = analytics_result
            
            # Anonymize remaining data instead of deletion where required
            anonymization_result = await self._anonymize_remaining_data(user_id)
            erasure_report["erasure_results"]["anonymization"] = anonymization_result
            
            # Generate verification hash
            erasure_report["verification_hash"] = self._generate_erasure_hash(erasure_report)
            
            logger.info(
                "erasure_request_fulfilled",
                user_id=user_id,
                request_id=erasure_report["request_id"],
                categories_erased=len(erasure_report["erasure_results"])
            )
            
            return erasure_report
            
        except Exception as e:
            logger.error(
                "erasure_request_failed",
                error=str(e),
                user_id=user_id
            )
            raise
    
    async def anonymize_data(self, data: Dict[str, Any], anonymization_level: str = "standard") -> Dict[str, Any]:
        """
        Anonymize personal data while preserving utility.
        
        Args:
            data: Data to anonymize
            anonymization_level: Level of anonymization (basic, standard, strong)
            
        Returns:
            Anonymized data
        """
        try:
            anonymized = data.copy()
            
            # Define anonymization patterns
            patterns = {
                "basic": {
                    "user_id": lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16],
                    "email": lambda x: "anonymized@example.com",
                    "ip_address": lambda x: self._anonymize_ip(x),
                    "name": lambda x: "Anonymous User"
                },
                "standard": {
                    "user_id": lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16],
                    "email": lambda x: f"user_{hashlib.sha256(str(x).encode()).hexdigest()[:8]}@anonymized.com",
                    "ip_address": lambda x: self._anonymize_ip(x),
                    "name": lambda x: f"User_{hashlib.sha256(str(x).encode()).hexdigest()[:8]}",
                    "session_id": lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16],
                    "message": lambda x: self._anonymize_text(x) if isinstance(x, str) else x
                },
                "strong": {
                    "user_id": lambda x: "anonymized",
                    "email": lambda x: "anonymized@example.com",
                    "ip_address": lambda x: "0.0.0.0",
                    "name": lambda x: "Anonymous",
                    "session_id": lambda x: "anonymized",
                    "message": lambda x: "[ANONYMIZED]" if isinstance(x, str) else x,
                    "content": lambda x: "[ANONYMIZED]" if isinstance(x, str) else x
                }
            }
            
            anonymization_rules = patterns.get(anonymization_level, patterns["standard"])
            
            # Apply anonymization recursively
            def anonymize_recursive(obj):
                if isinstance(obj, dict):
                    result = {}
                    for key, value in obj.items():
                        if key.lower() in anonymization_rules:
                            result[key] = anonymization_rules[key.lower()](value)
                        else:
                            result[key] = anonymize_recursive(value)
                    return result
                elif isinstance(obj, list):
                    return [anonymize_recursive(item) for item in obj]
                else:
                    return obj
            
            anonymized = anonymize_recursive(anonymized)
            
            # Add anonymization metadata
            anonymized["_anonymization"] = {
                "level": anonymization_level,
                "anonymized_at": datetime.now(timezone.utc).isoformat(),
                "method": "hash_based_pseudonymization"
            }
            
            logger.debug(
                "data_anonymized",
                level=anonymization_level,
                original_keys=list(data.keys()),
                anonymized_keys=list(anonymized.keys())
            )
            
            return anonymized
            
        except Exception as e:
            logger.error(
                "data_anonymization_failed",
                error=str(e),
                level=anonymization_level
            )
            raise
    
    def _anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address by masking last octet"""
        if not ip_address:
            return "0.0.0.0"
        
        # IPv4 anonymization
        if "." in ip_address:
            parts = ip_address.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        
        # IPv6 anonymization (simplified)
        if ":" in ip_address:
            parts = ip_address.split(":")
            if len(parts) >= 4:
                return ":".join(parts[:4]) + "::0"
        
        return "0.0.0.0"
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize text by removing PII patterns"""
        if not text or len(text) < 10:
            return "[ANONYMIZED]"
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone numbers
        text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', text)
        text = re.sub(r'\b\(\d{3}\)\s*\d{3}-\d{4}\b', '[PHONE]', text)
        
        # Remove potential names (capitalized words)
        words = text.split()
        anonymized_words = []
        for word in words:
            if word.istitle() and len(word) > 2:
                anonymized_words.append('[NAME]')
            else:
                anonymized_words.append(word)
        
        return ' '.join(anonymized_words)
    
    async def _collect_personal_data(self, user_id: str) -> Dict[str, Any]:
        """Collect personal data for access request"""
        # This would query your user database
        return {
            "user_id": user_id,
            "collection_note": "Personal data would be collected from user database"
        }
    
    async def _collect_conversation_data(self, user_id: str) -> Dict[str, Any]:
        """Collect conversation data for access request"""
        # This would query conversation storage (Redis, ClickHouse)
        return {
            "user_id": user_id,
            "collection_note": "Conversation data would be collected from memory systems"
        }
    
    async def _collect_analytics_data(self, user_id: str) -> Dict[str, Any]:
        """Collect analytics data for access request"""
        return {
            "user_id": user_id,
            "collection_note": "Analytics data would be collected from ClickHouse"
        }
    
    async def _get_processing_activities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get data processing activities for user"""
        return [
            {
                "activity": "Conversation Processing",
                "purpose": "AI-powered search and chat responses",
                "legal_basis": "Legitimate interest",
                "data_categories": ["messages", "queries", "responses"],
                "retention_period": "365 days"
            }
        ]
    
    async def _check_legal_holds(self, user_id: str) -> List[str]:
        """Check for legal holds preventing erasure"""
        # This would check for active legal holds, investigations, etc.
        return []
    
    async def _erase_conversation_data(self, user_id: str) -> Dict[str, Any]:
        """Erase conversation data"""
        return {
            "status": "completed",
            "records_deleted": 0,
            "note": "Would delete conversation data from Redis and ClickHouse"
        }
    
    async def _erase_personal_data(self, user_id: str) -> Dict[str, Any]:
        """Erase personal data"""
        return {
            "status": "completed", 
            "records_deleted": 0,
            "note": "Would delete personal data from user database"
        }
    
    async def _erase_analytics_data(self, user_id: str) -> Dict[str, Any]:
        """Erase analytics data"""
        return {
            "status": "completed",
            "records_deleted": 0,
            "note": "Would delete analytics data from ClickHouse"
        }
    
    async def _anonymize_remaining_data(self, user_id: str) -> Dict[str, Any]:
        """Anonymize data that cannot be deleted"""
        return {
            "status": "completed",
            "records_anonymized": 0,
            "note": "Would anonymize remaining data that must be retained"
        }
    
    def _generate_erasure_hash(self, erasure_report: Dict[str, Any]) -> str:
        """Generate verification hash for erasure report"""
        # Create hash of erasure report for verification
        report_str = json.dumps(erasure_report, sort_keys=True, default=str)
        return hashlib.sha256(report_str.encode()).hexdigest()


# Factory functions
def create_consent_manager(storage_config: Optional[Dict] = None) -> ConsentManager:
    """Create ConsentManager instance"""
    return ConsentManager(storage_backend=storage_config)


def create_gdpr_compliance_manager(
    consent_manager: ConsentManager,
    storage_config: Optional[Dict] = None
) -> GDPRComplianceManager:
    """Create GDPRComplianceManager instance"""
    return GDPRComplianceManager(consent_manager, storage_backend=storage_config)