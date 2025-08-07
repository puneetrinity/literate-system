"""
Key management system with rotation, versioning, and secure storage.

Provides comprehensive key management capabilities:
- Automatic key rotation based on policies
- Key versioning and migration
- Secure key storage and retrieval
- Key lifecycle management
- Integration with encryption manager
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

import structlog

from .encryption import DataClassification

logger = structlog.get_logger(__name__)


class KeyStatus(Enum):
    """Key status enumeration"""
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class KeyType(Enum):
    """Key type enumeration"""
    MASTER = "master"
    DATA = "data"
    SESSION = "session"
    ENCRYPTION = "encryption"
    SIGNING = "signing"


@dataclass
class KeyMetadata:
    """Key metadata structure"""
    key_id: str
    key_type: KeyType
    classification: DataClassification
    status: KeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_rotated: Optional[datetime]
    rotation_interval_days: int
    version: int
    usage_count: int = 0
    max_usage: Optional[int] = None
    associated_data: Dict[str, Any] = None


class KeyManager:
    """
    Comprehensive key management system.
    
    Features:
    - Hierarchical key structure (master -> data keys)
    - Automatic key rotation based on time and usage
    - Key versioning and migration
    - Secure key derivation and storage
    - Audit logging for all key operations
    """
    
    def __init__(self, storage_backend: Optional[Dict] = None):
        """
        Initialize key manager.
        
        Args:
            storage_backend: Storage configuration (Redis, ClickHouse, etc.)
        """
        self.backend = default_backend()
        self.storage = storage_backend or {}
        
        # Key storage (in production, use secure key store)
        self.keys: Dict[str, KeyMetadata] = {}
        self.encrypted_keys: Dict[str, bytes] = {}
        
        # Rotation policies by classification
        self.rotation_policies = {
            DataClassification.INTERNAL: {"days": 90, "usage_limit": 100000},
            DataClassification.CONFIDENTIAL: {"days": 30, "usage_limit": 50000},
            DataClassification.RESTRICTED: {"days": 7, "usage_limit": 10000}
        }
        
        # Initialize master key
        self.master_key = self._initialize_master_key()
        self.master_fernet = Fernet(self.master_key)
        
        logger.info("key_manager_initialized")
    
    def _initialize_master_key(self) -> bytes:
        """Initialize or load master key"""
        # Try to load from environment
        env_key = os.getenv("KEY_MANAGER_MASTER_KEY")
        if env_key:
            return env_key.encode('utf-8')[:32].ljust(32, b'\0')
        
        # Generate new master key
        master_key = Fernet.generate_key()
        
        # In production, store this securely (HSM, key vault, etc.)
        logger.warning(
            "new_master_key_generated",
            message="Store this key securely for production use"
        )
        
        return master_key
    
    async def create_key(
        self,
        key_type: KeyType,
        classification: DataClassification,
        key_id: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        max_usage: Optional[int] = None,
        associated_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new encryption key.
        
        Args:
            key_type: Type of key to create
            classification: Data classification level
            key_id: Optional specific key ID
            expires_in_days: Optional expiration in days
            max_usage: Optional maximum usage count
            associated_data: Optional associated metadata
            
        Returns:
            Generated key ID
        """
        try:
            # Generate key ID if not provided
            if not key_id:
                timestamp = str(int(time.time()))
                random_suffix = secrets.token_hex(8)
                key_id = f"{key_type.value}_{classification.value}_{timestamp}_{random_suffix}"
            
            # Get rotation policy
            policy = self.rotation_policies.get(classification, {"days": 90, "usage_limit": 100000})
            
            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            elif policy["days"]:
                expires_at = datetime.now(timezone.utc) + timedelta(days=policy["days"])
            
            # Create key metadata
            metadata = KeyMetadata(
                key_id=key_id,
                key_type=key_type,
                classification=classification,
                status=KeyStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                last_rotated=None,
                rotation_interval_days=policy["days"],
                version=1,
                usage_count=0,
                max_usage=max_usage or policy["usage_limit"],
                associated_data=associated_data or {}
            )
            
            # Generate actual key material
            key_material = os.urandom(32)  # 256-bit key
            
            # Encrypt key material with master key
            encrypted_key = self.master_fernet.encrypt(key_material)
            
            # Store key and metadata
            self.keys[key_id] = metadata
            self.encrypted_keys[key_id] = encrypted_key
            
            # Audit log
            logger.info(
                "key_created",
                key_id=key_id,
                key_type=key_type.value,
                classification=classification.value,
                expires_at=expires_at.isoformat() if expires_at else None
            )
            
            return key_id
            
        except Exception as e:
            logger.error(
                "key_creation_failed",
                error=str(e),
                key_type=key_type.value,
                classification=classification.value
            )
            raise
    
    async def get_key(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve decrypted key material.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Decrypted key material or None if not found
        """
        try:
            # Check if key exists
            if key_id not in self.keys:
                logger.warning("key_not_found", key_id=key_id)
                return None
            
            metadata = self.keys[key_id]
            
            # Check key status
            if metadata.status not in [KeyStatus.ACTIVE, KeyStatus.ROTATING]:
                logger.warning(
                    "key_not_active",
                    key_id=key_id,
                    status=metadata.status.value
                )
                return None
            
            # Check expiration
            if metadata.expires_at and datetime.now(timezone.utc) > metadata.expires_at:
                logger.warning("key_expired", key_id=key_id)
                await self._mark_key_expired(key_id)
                return None
            
            # Check usage limit
            if metadata.max_usage and metadata.usage_count >= metadata.max_usage:
                logger.warning("key_usage_limit_exceeded", key_id=key_id)
                await self._mark_key_expired(key_id)
                return None
            
            # Decrypt key material
            encrypted_key = self.encrypted_keys[key_id]
            key_material = self.master_fernet.decrypt(encrypted_key)
            
            # Update usage count
            metadata.usage_count += 1
            
            # Audit log for restricted data
            if metadata.classification == DataClassification.RESTRICTED:
                logger.info(
                    "restricted_key_accessed",
                    key_id=key_id,
                    usage_count=metadata.usage_count
                )
            
            return key_material
            
        except Exception as e:
            logger.error(
                "key_retrieval_failed",
                error=str(e),
                key_id=key_id
            )
            return None
    
    async def rotate_key(self, key_id: str) -> Optional[str]:
        """
        Rotate existing key to new version.
        
        Args:
            key_id: Key identifier to rotate
            
        Returns:
            New key ID or None if rotation failed
        """
        try:
            # Get current key metadata
            if key_id not in self.keys:
                logger.error("cannot_rotate_nonexistent_key", key_id=key_id)
                return None
            
            current_metadata = self.keys[key_id]
            
            # Mark current key as rotating
            current_metadata.status = KeyStatus.ROTATING
            current_metadata.last_rotated = datetime.now(timezone.utc)
            
            # Create new key with incremented version
            new_key_id = f"{key_id}_v{current_metadata.version + 1}"
            
            new_metadata = KeyMetadata(
                key_id=new_key_id,
                key_type=current_metadata.key_type,
                classification=current_metadata.classification,
                status=KeyStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=current_metadata.rotation_interval_days),
                last_rotated=None,
                rotation_interval_days=current_metadata.rotation_interval_days,
                version=current_metadata.version + 1,
                usage_count=0,
                max_usage=current_metadata.max_usage,
                associated_data=current_metadata.associated_data
            )
            
            # Generate new key material
            new_key_material = os.urandom(32)
            encrypted_new_key = self.master_fernet.encrypt(new_key_material)
            
            # Store new key
            self.keys[new_key_id] = new_metadata
            self.encrypted_keys[new_key_id] = encrypted_new_key
            
            # Mark old key as deprecated after grace period
            await asyncio.sleep(0.1)  # Small delay to ensure ordering
            current_metadata.status = KeyStatus.DEPRECATED
            
            logger.info(
                "key_rotated",
                old_key_id=key_id,
                new_key_id=new_key_id,
                classification=current_metadata.classification.value,
                old_version=current_metadata.version,
                new_version=new_metadata.version
            )
            
            return new_key_id
            
        except Exception as e:
            logger.error(
                "key_rotation_failed",
                error=str(e),
                key_id=key_id
            )
            return None
    
    async def revoke_key(self, key_id: str, reason: str = "manual_revocation") -> bool:
        """
        Revoke key immediately.
        
        Args:
            key_id: Key identifier to revoke
            reason: Reason for revocation
            
        Returns:
            Success boolean
        """
        try:
            if key_id not in self.keys:
                logger.warning("cannot_revoke_nonexistent_key", key_id=key_id)
                return False
            
            metadata = self.keys[key_id]
            metadata.status = KeyStatus.REVOKED
            
            # Clear key material for security
            if key_id in self.encrypted_keys:
                del self.encrypted_keys[key_id]
            
            logger.info(
                "key_revoked",
                key_id=key_id,
                reason=reason,
                classification=metadata.classification.value
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "key_revocation_failed",
                error=str(e),
                key_id=key_id
            )
            return False
    
    async def check_rotation_needed(self) -> List[str]:
        """
        Check which keys need rotation.
        
        Returns:
            List of key IDs that need rotation
        """
        rotation_needed = []
        current_time = datetime.now(timezone.utc)
        
        for key_id, metadata in self.keys.items():
            if metadata.status != KeyStatus.ACTIVE:
                continue
            
            needs_rotation = False
            
            # Check time-based rotation
            if metadata.expires_at and current_time >= metadata.expires_at:
                needs_rotation = True
            
            # Check usage-based rotation
            if metadata.max_usage and metadata.usage_count >= metadata.max_usage * 0.9:  # 90% threshold
                needs_rotation = True
            
            if needs_rotation:
                rotation_needed.append(key_id)
        
        if rotation_needed:
            logger.info(
                "keys_need_rotation",
                count=len(rotation_needed),
                key_ids=rotation_needed
            )
        
        return rotation_needed
    
    async def _mark_key_expired(self, key_id: str):
        """Mark key as expired"""
        if key_id in self.keys:
            self.keys[key_id].status = KeyStatus.DEPRECATED
            logger.info("key_marked_expired", key_id=key_id)
    
    def get_key_metadata(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get key metadata as dictionary"""
        if key_id not in self.keys:
            return None
        
        metadata = self.keys[key_id]
        return {
            "key_id": metadata.key_id,
            "key_type": metadata.key_type.value,
            "classification": metadata.classification.value,
            "status": metadata.status.value,
            "created_at": metadata.created_at.isoformat(),
            "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
            "last_rotated": metadata.last_rotated.isoformat() if metadata.last_rotated else None,
            "rotation_interval_days": metadata.rotation_interval_days,
            "version": metadata.version,
            "usage_count": metadata.usage_count,
            "max_usage": metadata.max_usage,
            "associated_data": metadata.associated_data
        }
    
    def list_keys(self, key_type: Optional[KeyType] = None, status: Optional[KeyStatus] = None) -> List[Dict[str, Any]]:
        """List keys with optional filtering"""
        results = []
        
        for key_id, metadata in self.keys.items():
            if key_type and metadata.key_type != key_type:
                continue
            if status and metadata.status != status:
                continue
            
            results.append(self.get_key_metadata(key_id))
        
        return results


class KeyRotationService:
    """
    Automated key rotation service.
    
    Runs periodic checks and performs automatic key rotation
    based on policies and usage patterns.
    """
    
    def __init__(self, key_manager: KeyManager, check_interval_minutes: int = 60):
        """
        Initialize key rotation service.
        
        Args:
            key_manager: KeyManager instance
            check_interval_minutes: How often to check for rotation needs
        """
        self.key_manager = key_manager
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.running = False
        self.rotation_task = None
        
        logger.info(
            "key_rotation_service_initialized",
            check_interval_minutes=check_interval_minutes
        )
    
    async def start(self):
        """Start automated key rotation service"""
        if self.running:
            logger.warning("key_rotation_service_already_running")
            return
        
        self.running = True
        self.rotation_task = asyncio.create_task(self._rotation_loop())
        logger.info("key_rotation_service_started")
    
    async def stop(self):
        """Stop automated key rotation service"""
        self.running = False
        if self.rotation_task:
            self.rotation_task.cancel()
            try:
                await self.rotation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("key_rotation_service_stopped")
    
    async def _rotation_loop(self):
        """Main rotation loop"""
        while self.running:
            try:
                await self._check_and_rotate()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "rotation_loop_error",
                    error=str(e)
                )
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _check_and_rotate(self):
        """Check for keys that need rotation and rotate them"""
        try:
            keys_needing_rotation = await self.key_manager.check_rotation_needed()
            
            for key_id in keys_needing_rotation:
                try:
                    new_key_id = await self.key_manager.rotate_key(key_id)
                    if new_key_id:
                        logger.info(
                            "automatic_key_rotation_completed",
                            old_key_id=key_id,
                            new_key_id=new_key_id
                        )
                    else:
                        logger.error(
                            "automatic_key_rotation_failed",
                            key_id=key_id
                        )
                
                except Exception as e:
                    logger.error(
                        "key_rotation_error",
                        key_id=key_id,
                        error=str(e)
                    )
        
        except Exception as e:
            logger.error(
                "rotation_check_failed",
                error=str(e)
            )
    
    async def force_rotation(self, key_id: str) -> Optional[str]:
        """Force immediate rotation of specific key"""
        logger.info("forcing_key_rotation", key_id=key_id)
        return await self.key_manager.rotate_key(key_id)


# Factory functions
def create_key_manager(storage_config: Optional[Dict] = None) -> KeyManager:
    """Create KeyManager instance"""
    return KeyManager(storage_backend=storage_config)


def create_rotation_service(key_manager: KeyManager, check_interval_minutes: int = 60) -> KeyRotationService:
    """Create KeyRotationService instance"""
    return KeyRotationService(key_manager, check_interval_minutes)