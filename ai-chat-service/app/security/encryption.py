"""
Data encryption at rest and in transit with classification-based protection.

Provides comprehensive encryption capabilities:
- AES-256-GCM encryption for sensitive data
- Data classification-based encryption policies
- Field-level encryption for databases
- Secure key derivation and management
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

import structlog

logger = structlog.get_logger(__name__)


class DataClassification(Enum):
    """Data classification levels with corresponding security requirements"""
    PUBLIC = "public"           # No encryption required
    INTERNAL = "internal"       # Basic encryption
    CONFIDENTIAL = "confidential"  # Strong encryption + key rotation
    RESTRICTED = "restricted"   # Maximum security + audit logging


@dataclass
class EncryptionContext:
    """Context information for encryption operations"""
    classification: DataClassification
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    purpose: Optional[str] = None
    retention_days: Optional[int] = None
    requires_audit: bool = False


class EncryptionManager:
    """
    Comprehensive encryption manager supporting multiple algorithms and data classifications.
    
    Features:
    - AES-256-GCM for symmetric encryption
    - RSA-4096 for asymmetric encryption  
    - Classification-based encryption policies
    - Key derivation with PBKDF2
    - Secure random generation
    - Encryption metadata tracking
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize encryption manager.
        
        Args:
            master_key: Master encryption key (auto-generated if not provided)
        """
        self.backend = default_backend()
        
        # Initialize master key
        if master_key:
            self.master_key = master_key
        else:
            self.master_key = self._generate_master_key()
        
        # Initialize Fernet for high-level encryption
        self.fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        
        # Classification-based policies
        self.encryption_policies = {
            DataClassification.PUBLIC: {"encrypt": False, "key_rotation_days": None},
            DataClassification.INTERNAL: {"encrypt": True, "key_rotation_days": 90},
            DataClassification.CONFIDENTIAL: {"encrypt": True, "key_rotation_days": 30},
            DataClassification.RESTRICTED: {"encrypt": True, "key_rotation_days": 7}
        }
        
        logger.info("encryption_manager_initialized")
    
    def _generate_master_key(self) -> bytes:
        """Generate secure master key"""
        return os.urandom(32)  # 256-bit key
    
    def encrypt_data(
        self, 
        data: Union[str, bytes, Dict, List], 
        context: EncryptionContext
    ) -> Dict[str, Any]:
        """
        Encrypt data based on classification level.
        
        Args:
            data: Data to encrypt (supports various types)
            context: Encryption context with classification
            
        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            # Check if encryption is required
            policy = self.encryption_policies[context.classification]
            if not policy["encrypt"]:
                return {
                    "encrypted": False,
                    "data": data,
                    "classification": context.classification.value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Serialize data if needed
            if isinstance(data, (dict, list)):
                plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, str):
                plaintext = data.encode('utf-8')
            else:
                plaintext = data
            
            # Generate encryption metadata
            salt = os.urandom(16)
            nonce = os.urandom(12)  # GCM nonce
            
            # Derive encryption key
            encryption_key = self._derive_key(salt, context)
            
            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(nonce),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # Add associated data for integrity
            associated_data = self._create_associated_data(context)
            encryptor.authenticate_additional_data(associated_data)
            
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Create encrypted package
            encrypted_package = {
                "encrypted": True,
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "salt": base64.b64encode(salt).decode('utf-8'),
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "tag": base64.b64encode(encryptor.tag).decode('utf-8'),
                "associated_data": base64.b64encode(associated_data).decode('utf-8'),
                "classification": context.classification.value,
                "algorithm": "AES-256-GCM",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "key_id": self._generate_key_id(salt, context),
                "user_id": context.user_id,
                "session_id": context.session_id,
                "purpose": context.purpose
            }
            
            # Log encryption event for audit
            if context.requires_audit or context.classification in [DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED]:
                logger.info(
                    "data_encrypted",
                    classification=context.classification.value,
                    user_id=context.user_id,
                    session_id=context.session_id,
                    purpose=context.purpose,
                    algorithm="AES-256-GCM",
                    key_id=encrypted_package["key_id"]
                )
            
            return encrypted_package
            
        except Exception as e:
            logger.error(
                "encryption_failed",
                error=str(e),
                classification=context.classification.value,
                user_id=context.user_id
            )
            raise
    
    def decrypt_data(self, encrypted_package: Dict[str, Any]) -> Any:
        """
        Decrypt data from encrypted package.
        
        Args:
            encrypted_package: Encrypted data package
            
        Returns:
            Decrypted data in original format
        """
        try:
            # Check if data is encrypted
            if not encrypted_package.get("encrypted", False):
                return encrypted_package.get("data")
            
            # Extract encryption components
            ciphertext = base64.b64decode(encrypted_package["ciphertext"])
            salt = base64.b64decode(encrypted_package["salt"])
            nonce = base64.b64decode(encrypted_package["nonce"])
            tag = base64.b64decode(encrypted_package["tag"])
            associated_data = base64.b64decode(encrypted_package["associated_data"])
            
            # Reconstruct context for key derivation
            context = EncryptionContext(
                classification=DataClassification(encrypted_package["classification"]),
                user_id=encrypted_package.get("user_id"),
                session_id=encrypted_package.get("session_id"),
                purpose=encrypted_package.get("purpose")
            )
            
            # Derive decryption key
            decryption_key = self._derive_key(salt, context)
            
            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(decryption_key),
                modes.GCM(nonce, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            decryptor.authenticate_additional_data(associated_data)
            
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Attempt to deserialize if JSON
            try:
                decrypted_data = json.loads(plaintext.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                decrypted_data = plaintext.decode('utf-8', errors='replace')
            
            # Log decryption event for audit
            if context.classification in [DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED]:
                logger.info(
                    "data_decrypted",
                    classification=context.classification.value,
                    user_id=context.user_id,
                    session_id=context.session_id,
                    key_id=encrypted_package.get("key_id")
                )
            
            return decrypted_data
            
        except Exception as e:
            logger.error(
                "decryption_failed",
                error=str(e),
                key_id=encrypted_package.get("key_id"),
                classification=encrypted_package.get("classification")
            )
            raise
    
    def encrypt_field(self, value: Any, field_name: str, context: EncryptionContext) -> str:
        """
        Encrypt individual field for database storage.
        
        Args:
            value: Field value to encrypt
            field_name: Name of the field
            context: Encryption context
            
        Returns:
            Base64-encoded encrypted field value
        """
        field_context = EncryptionContext(
            classification=context.classification,
            user_id=context.user_id,
            session_id=context.session_id,
            purpose=f"field:{field_name}",
            requires_audit=context.requires_audit
        )
        
        encrypted_package = self.encrypt_data(value, field_context)
        return base64.b64encode(json.dumps(encrypted_package).encode('utf-8')).decode('utf-8')
    
    def decrypt_field(self, encrypted_value: str) -> Any:
        """
        Decrypt individual field from database.
        
        Args:
            encrypted_value: Base64-encoded encrypted field value
            
        Returns:
            Decrypted field value
        """
        try:
            encrypted_package = json.loads(base64.b64decode(encrypted_value).decode('utf-8'))
            return self.decrypt_data(encrypted_package)
        except Exception as e:
            logger.error("field_decryption_failed", error=str(e))
            return None
    
    def _derive_key(self, salt: bytes, context: EncryptionContext) -> bytes:
        """
        Derive encryption key using PBKDF2.
        
        Args:
            salt: Cryptographic salt
            context: Encryption context
            
        Returns:
            Derived encryption key
        """
        # Create key derivation context
        kdf_input = self.master_key
        if context.user_id:
            kdf_input += context.user_id.encode('utf-8')
        if context.purpose:
            kdf_input += context.purpose.encode('utf-8')
        
        # Use different iteration counts based on classification
        iterations = {
            DataClassification.INTERNAL: 100000,
            DataClassification.CONFIDENTIAL: 200000,
            DataClassification.RESTRICTED: 400000
        }.get(context.classification, 100000)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key
            salt=salt,
            iterations=iterations,
            backend=self.backend
        )
        
        return kdf.derive(kdf_input)
    
    def _create_associated_data(self, context: EncryptionContext) -> bytes:
        """Create associated data for GCM authentication"""
        associated_data = {
            "classification": context.classification.value,
            "user_id": context.user_id,
            "purpose": context.purpose,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return json.dumps(associated_data, sort_keys=True).encode('utf-8')
    
    def _generate_key_id(self, salt: bytes, context: EncryptionContext) -> str:
        """Generate unique key identifier for tracking"""
        key_data = salt + self.master_key
        if context.user_id:
            key_data += context.user_id.encode('utf-8')
        
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def encrypt_for_storage(self, data: Dict[str, Any], classification: DataClassification) -> Dict[str, Any]:
        """
        Encrypt data for storage with automatic field classification.
        
        Args:
            data: Data dictionary to encrypt
            classification: Overall data classification
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        # Define sensitive field patterns
        sensitive_fields = {
            'user_id', 'email', 'phone', 'address', 'name', 'ip_address',
            'message', 'content', 'query', 'response', 'summary', 'notes'
        }
        
        result = {}
        context = EncryptionContext(classification=classification, requires_audit=True)
        
        for key, value in data.items():
            if any(pattern in key.lower() for pattern in sensitive_fields):
                # Encrypt sensitive fields
                result[f"{key}_encrypted"] = self.encrypt_field(value, key, context)
                result[f"{key}_is_encrypted"] = True
            else:
                # Keep non-sensitive fields as-is
                result[key] = value
        
        result['_encryption_classification'] = classification.value
        result['_encryption_timestamp'] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def decrypt_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt data retrieved from storage.
        
        Args:
            data: Data dictionary with encrypted fields
            
        Returns:
            Dictionary with decrypted fields
        """
        result = {}
        
        for key, value in data.items():
            if key.endswith('_encrypted'):
                # Decrypt encrypted field
                original_key = key[:-10]  # Remove '_encrypted' suffix
                if data.get(f"{original_key}_is_encrypted"):
                    result[original_key] = self.decrypt_field(value)
                else:
                    result[original_key] = value
            elif not key.endswith('_is_encrypted') and not key.startswith('_encryption_'):
                # Keep regular fields
                result[key] = value
        
        return result
    
    def generate_data_key(self, classification: DataClassification) -> Dict[str, str]:
        """
        Generate new data encryption key for key rotation.
        
        Args:
            classification: Data classification level
            
        Returns:
            Dictionary with new key information
        """
        new_key = os.urandom(32)
        key_id = hashlib.sha256(new_key + self.master_key).hexdigest()[:16]
        
        # Encrypt the data key with master key
        encrypted_key = self.fernet.encrypt(new_key)
        
        return {
            "key_id": key_id,
            "encrypted_key": base64.b64encode(encrypted_key).decode('utf-8'),
            "classification": classification.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rotation_interval_days": self.encryption_policies[classification]["key_rotation_days"]
        }
    
    def get_encryption_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get encryption status information for data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Encryption status information
        """
        status = {
            "is_encrypted": False,
            "encrypted_fields": [],
            "classification": None,
            "encryption_timestamp": None,
            "requires_key_rotation": False
        }
        
        if data.get("encrypted"):
            status["is_encrypted"] = True
            status["classification"] = data.get("classification")
            status["encryption_timestamp"] = data.get("timestamp")
        else:
            # Check for field-level encryption
            encrypted_fields = [k[:-10] for k in data.keys() if k.endswith('_encrypted')]
            if encrypted_fields:
                status["encrypted_fields"] = encrypted_fields
                status["classification"] = data.get("_encryption_classification")
                status["encryption_timestamp"] = data.get("_encryption_timestamp")
        
        # Check if key rotation is needed
        if status["encryption_timestamp"] and status["classification"]:
            classification = DataClassification(status["classification"])
            rotation_days = self.encryption_policies[classification]["key_rotation_days"]
            
            if rotation_days:
                encrypt_date = datetime.fromisoformat(status["encryption_timestamp"].replace('Z', '+00:00'))
                days_since_encryption = (datetime.now(timezone.utc) - encrypt_date).days
                status["requires_key_rotation"] = days_since_encryption > rotation_days
        
        return status


def create_encryption_manager(master_key: Optional[str] = None) -> EncryptionManager:
    """
    Factory function to create EncryptionManager instance.
    
    Args:
        master_key: Optional master key (hex string)
        
    Returns:
        EncryptionManager instance
    """
    if master_key:
        key_bytes = bytes.fromhex(master_key)
    else:
        # Try to get from environment
        env_key = os.getenv("ENCRYPTION_MASTER_KEY")
        if env_key:
            key_bytes = bytes.fromhex(env_key)
        else:
            key_bytes = None
    
    return EncryptionManager(master_key=key_bytes)