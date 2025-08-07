"""
Secure configuration management with secrets encryption and rotation.

Provides comprehensive configuration security features:
- Environment variable encryption
- Secrets management with automatic rotation
- Secure default configurations
- Configuration validation and integrity checking
- Integration with external secret stores
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets
import re

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

import structlog

logger = structlog.get_logger(__name__)


class SecretType(Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    ENCRYPTION_KEY = "encryption_key"
    JWT_SECRET = "jwt_secret"
    OAUTH_SECRET = "oauth_secret"
    WEBHOOK_SECRET = "webhook_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"


class SecurityLevel(Enum):
    """Security levels for configuration"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class SecretMetadata:
    """Metadata for managed secrets"""
    secret_id: str
    secret_type: SecretType
    security_level: SecurityLevel
    created_at: datetime
    last_rotated: Optional[datetime]
    rotation_interval_days: int
    max_age_days: int
    usage_count: int = 0
    is_active: bool = True
    tags: Dict[str, str] = None


class SecureConfigManager:
    """
    Secure configuration management system.
    
    Features:
    - Encrypted storage of sensitive configuration values
    - Automatic secrets rotation
    - Configuration validation and type checking
    - Secure defaults enforcement
    - Audit logging for configuration access
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize secure configuration manager.
        
        Args:
            master_key: Master key for encryption (auto-generated if not provided)
        """
        self.backend = default_backend()
        
        # Initialize encryption
        if master_key:
            self.master_key = master_key
        else:
            self.master_key = self._get_or_create_master_key()
        
        self.fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        
        # Configuration storage
        self.encrypted_config: Dict[str, bytes] = {}
        self.config_metadata: Dict[str, Dict[str, Any]] = {}
        self.secret_metadata: Dict[str, SecretMetadata] = {}
        
        # Security policies
        self.security_policies = {
            SecurityLevel.PUBLIC: {
                "encrypt": False,
                "rotation_days": None,
                "validation_required": False
            },
            SecurityLevel.INTERNAL: {
                "encrypt": True,
                "rotation_days": 180,
                "validation_required": True
            },
            SecurityLevel.CONFIDENTIAL: {
                "encrypt": True,
                "rotation_days": 90,
                "validation_required": True
            },
            SecurityLevel.RESTRICTED: {
                "encrypt": True,
                "rotation_days": 30,
                "validation_required": True
            }
        }
        
        # Initialize with secure defaults
        self._initialize_secure_defaults()
        
        logger.info("secure_config_manager_initialized")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get master key from environment or create new one"""
        env_key = os.getenv("CONFIG_MASTER_KEY")
        if env_key:
            try:
                return base64.b64decode(env_key)
            except Exception:
                pass
        
        # Generate new master key
        new_key = Fernet.generate_key()
        logger.warning(
            "new_config_master_key_generated",
            message="Set CONFIG_MASTER_KEY environment variable to persist this key"
        )
        return new_key
    
    def _initialize_secure_defaults(self):
        """Initialize secure default configurations"""
        secure_defaults = {
            # Security headers
            "SECURITY_HEADERS": {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            },
            
            # Rate limiting
            "RATE_LIMIT_DEFAULT": "100/hour",
            "RATE_LIMIT_STRICT": "10/minute",
            
            # Session security
            "SESSION_COOKIE_SECURE": True,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Strict",
            "SESSION_TIMEOUT_MINUTES": 30,
            
            # CORS settings
            "CORS_ALLOW_CREDENTIALS": False,
            "CORS_MAX_AGE": 86400,
            
            # TLS/SSL settings
            "TLS_MIN_VERSION": "1.2",
            "SSL_VERIFY": True,
            "SSL_CERT_REQUIRED": True,
            
            # Logging
            "LOG_LEVEL": "INFO",
            "LOG_SECURITY_EVENTS": True,
            "LOG_SENSITIVE_DATA": False,
            
            # File upload security
            "MAX_FILE_SIZE_MB": 10,
            "ALLOWED_FILE_TYPES": [".txt", ".pdf", ".docx", ".md"],
            "SCAN_UPLOADS": True,
            
            # Database security
            "DB_SSL_MODE": "require",
            "DB_CONNECTION_TIMEOUT": 30,
            "DB_MAX_CONNECTIONS": 20
        }
        
        for key, value in secure_defaults.items():
            self.set_config(key, value, SecurityLevel.INTERNAL, encrypt=False)
    
    def set_config(self,
                   key: str,
                   value: Any,
                   security_level: SecurityLevel = SecurityLevel.INTERNAL,
                   encrypt: Optional[bool] = None,
                   validation_rules: Optional[Dict[str, Any]] = None,
                   tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Set configuration value with security controls.
        
        Args:
            key: Configuration key
            value: Configuration value
            security_level: Security classification
            encrypt: Override encryption policy
            validation_rules: Validation rules for the value
            tags: Additional metadata tags
            
        Returns:
            Success boolean
        """
        try:
            # Get security policy
            policy = self.security_policies[security_level]
            should_encrypt = encrypt if encrypt is not None else policy["encrypt"]
            
            # Validate configuration if required
            if policy["validation_required"] and validation_rules:
                if not self._validate_config_value(key, value, validation_rules):
                    logger.error("config_validation_failed", key=key)
                    return False
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value).encode('utf-8')
            elif isinstance(value, str):
                serialized_value = value.encode('utf-8')
            elif isinstance(value, (int, float, bool)):
                serialized_value = str(value).encode('utf-8')
            else:
                serialized_value = str(value).encode('utf-8')
            
            # Encrypt if required
            if should_encrypt:
                encrypted_value = self.fernet.encrypt(serialized_value)
                self.encrypted_config[key] = encrypted_value
            else:
                self.encrypted_config[key] = serialized_value
            
            # Store metadata
            self.config_metadata[key] = {
                "security_level": security_level.value,
                "encrypted": should_encrypt,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "validation_rules": validation_rules or {},
                "tags": tags or {},
                "access_count": 0
            }
            
            logger.debug(
                "config_value_set",
                key=key,
                security_level=security_level.value,
                encrypted=should_encrypt
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "config_set_failed",
                error=str(e),
                key=key,
                security_level=security_level.value
            )
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with decryption if needed.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            if key not in self.encrypted_config:
                return default
            
            # Get encrypted/plain value
            stored_value = self.encrypted_config[key]
            metadata = self.config_metadata.get(key, {})
            
            # Decrypt if encrypted
            if metadata.get("encrypted", False):
                try:
                    decrypted_bytes = self.fernet.decrypt(stored_value)
                    decrypted_str = decrypted_bytes.decode('utf-8')
                except Exception as e:
                    logger.error("config_decryption_failed", key=key, error=str(e))
                    return default
            else:
                decrypted_str = stored_value.decode('utf-8')
            
            # Deserialize value
            try:
                # Try JSON first
                value = json.loads(decrypted_str)
            except json.JSONDecodeError:
                # Fallback to string
                value = decrypted_str
            
            # Update access count
            metadata["access_count"] = metadata.get("access_count", 0) + 1
            metadata["last_accessed"] = datetime.now(timezone.utc).isoformat()
            
            return value
            
        except Exception as e:
            logger.error(
                "config_get_failed",
                error=str(e),
                key=key
            )
            return default
    
    def set_secret(self,
                   secret_id: str,
                   secret_value: str,
                   secret_type: SecretType,
                   security_level: SecurityLevel = SecurityLevel.CONFIDENTIAL,
                   rotation_interval_days: int = 90,
                   tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Set managed secret with metadata.
        
        Args:
            secret_id: Secret identifier
            secret_value: Secret value
            secret_type: Type of secret
            security_level: Security classification
            rotation_interval_days: Days between rotations
            tags: Additional metadata tags
            
        Returns:
            Success boolean
        """
        try:
            # Validate secret format
            if not self._validate_secret_format(secret_value, secret_type):
                logger.error("invalid_secret_format", secret_id=secret_id, secret_type=secret_type.value)
                return False
            
            # Set the configuration value (always encrypted for secrets)
            success = self.set_config(
                secret_id,
                secret_value,
                security_level,
                encrypt=True,
                tags=tags
            )
            
            if success:
                # Create secret metadata
                metadata = SecretMetadata(
                    secret_id=secret_id,
                    secret_type=secret_type,
                    security_level=security_level,
                    created_at=datetime.now(timezone.utc),
                    last_rotated=None,
                    rotation_interval_days=rotation_interval_days,
                    max_age_days=rotation_interval_days * 2,  # Allow some grace period
                    usage_count=0,
                    is_active=True,
                    tags=tags or {}
                )
                
                self.secret_metadata[secret_id] = metadata
                
                logger.info(
                    "secret_stored",
                    secret_id=secret_id,
                    secret_type=secret_type.value,
                    security_level=security_level.value
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "secret_set_failed",
                error=str(e),
                secret_id=secret_id,
                secret_type=secret_type.value
            )
            return False
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """
        Get managed secret value.
        
        Args:
            secret_id: Secret identifier
            
        Returns:
            Secret value or None if not found
        """
        try:
            # Check if secret exists
            if secret_id not in self.secret_metadata:
                logger.warning("secret_not_found", secret_id=secret_id)
                return None
            
            metadata = self.secret_metadata[secret_id]
            
            # Check if secret is active
            if not metadata.is_active:
                logger.warning("secret_inactive", secret_id=secret_id)
                return None
            
            # Check if secret has expired
            if self._is_secret_expired(metadata):
                logger.warning("secret_expired", secret_id=secret_id)
                return None
            
            # Get the secret value
            secret_value = self.get_config(secret_id)
            
            if secret_value:
                # Update usage statistics
                metadata.usage_count += 1
                
                # Log secret access for audit
                logger.debug(
                    "secret_accessed",
                    secret_id=secret_id,
                    secret_type=metadata.secret_type.value,
                    usage_count=metadata.usage_count
                )
            
            return secret_value
            
        except Exception as e:
            logger.error(
                "secret_get_failed",
                error=str(e),
                secret_id=secret_id
            )
            return None
    
    def rotate_secret(self, secret_id: str, new_value: Optional[str] = None) -> bool:
        """
        Rotate secret to new value.
        
        Args:
            secret_id: Secret identifier
            new_value: New secret value (auto-generated if not provided)
            
        Returns:
            Success boolean
        """
        try:
            if secret_id not in self.secret_metadata:
                logger.error("cannot_rotate_nonexistent_secret", secret_id=secret_id)
                return False
            
            metadata = self.secret_metadata[secret_id]
            
            # Generate new value if not provided
            if new_value is None:
                new_value = self._generate_secret_value(metadata.secret_type)
            
            # Validate new secret
            if not self._validate_secret_format(new_value, metadata.secret_type):
                logger.error("invalid_new_secret_format", secret_id=secret_id)
                return False
            
            # Update the secret value
            success = self.set_config(
                secret_id,
                new_value,
                metadata.security_level,
                encrypt=True
            )
            
            if success:
                # Update metadata
                metadata.last_rotated = datetime.now(timezone.utc)
                metadata.usage_count = 0  # Reset usage count
                
                logger.info(
                    "secret_rotated",
                    secret_id=secret_id,
                    secret_type=metadata.secret_type.value
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "secret_rotation_failed",
                error=str(e),
                secret_id=secret_id
            )
            return False
    
    def check_secrets_needing_rotation(self) -> List[str]:
        """
        Check which secrets need rotation.
        
        Returns:
            List of secret IDs that need rotation
        """
        rotation_needed = []
        current_time = datetime.now(timezone.utc)
        
        for secret_id, metadata in self.secret_metadata.items():
            if not metadata.is_active:
                continue
            
            # Check if rotation interval has passed
            if metadata.last_rotated:
                time_since_rotation = current_time - metadata.last_rotated
            else:
                time_since_rotation = current_time - metadata.created_at
            
            if time_since_rotation.days >= metadata.rotation_interval_days:
                rotation_needed.append(secret_id)
        
        if rotation_needed:
            logger.info(
                "secrets_need_rotation",
                count=len(rotation_needed),
                secret_ids=rotation_needed
            )
        
        return rotation_needed
    
    def _validate_config_value(self, key: str, value: Any, rules: Dict[str, Any]) -> bool:
        """Validate configuration value against rules"""
        try:
            # Type validation
            if "type" in rules:
                expected_type = rules["type"]
                if expected_type == "string" and not isinstance(value, str):
                    return False
                elif expected_type == "integer" and not isinstance(value, int):
                    return False
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False
                elif expected_type == "list" and not isinstance(value, list):
                    return False
                elif expected_type == "dict" and not isinstance(value, dict):
                    return False
            
            # Range validation for numbers
            if isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    return False
                if "max" in rules and value > rules["max"]:
                    return False
            
            # Length validation for strings and lists
            if isinstance(value, (str, list)):
                if "min_length" in rules and len(value) < rules["min_length"]:
                    return False
                if "max_length" in rules and len(value) > rules["max_length"]:
                    return False
            
            # Pattern validation for strings
            if isinstance(value, str) and "pattern" in rules:
                pattern = rules["pattern"]
                if not re.match(pattern, value):
                    return False
            
            # Allowed values validation
            if "allowed_values" in rules:
                if value not in rules["allowed_values"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("config_validation_error", key=key, error=str(e))
            return False
    
    def _validate_secret_format(self, secret_value: str, secret_type: SecretType) -> bool:
        """Validate secret format based on type"""
        if not secret_value:
            return False
        
        validation_patterns = {
            SecretType.API_KEY: r"^[A-Za-z0-9\-_]{16,128}$",
            SecretType.DATABASE_PASSWORD: r"^.{8,128}$",  # At least 8 characters
            SecretType.ENCRYPTION_KEY: r"^[A-Za-z0-9+/]{32,}={0,2}$",  # Base64 pattern
            SecretType.JWT_SECRET: r"^.{32,}$",  # At least 32 characters
            SecretType.OAUTH_SECRET: r"^[A-Za-z0-9\-_]{20,128}$",
            SecretType.WEBHOOK_SECRET: r"^.{16,}$"  # At least 16 characters
        }
        
        pattern = validation_patterns.get(secret_type)
        if pattern:
            return bool(re.match(pattern, secret_value))
        
        # Default validation - just check it's not empty
        return len(secret_value) >= 8
    
    def _generate_secret_value(self, secret_type: SecretType) -> str:
        """Generate new secret value based on type"""
        generators = {
            SecretType.API_KEY: lambda: secrets.token_urlsafe(32),
            SecretType.DATABASE_PASSWORD: lambda: self._generate_strong_password(),
            SecretType.ENCRYPTION_KEY: lambda: base64.b64encode(secrets.token_bytes(32)).decode(),
            SecretType.JWT_SECRET: lambda: secrets.token_urlsafe(64),
            SecretType.OAUTH_SECRET: lambda: secrets.token_urlsafe(32),
            SecretType.WEBHOOK_SECRET: lambda: secrets.token_hex(32)
        }
        
        generator = generators.get(secret_type, lambda: secrets.token_urlsafe(32))
        return generator()
    
    def _generate_strong_password(self) -> str:
        """Generate strong password with mixed character types"""
        import string
        
        # Ensure we have at least one of each character type
        chars = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*")
        ]
        
        # Fill the rest randomly
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        for _ in range(12):  # Total length 16
            chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable pattern
        secrets.SystemRandom().shuffle(chars)
        return ''.join(chars)
    
    def _is_secret_expired(self, metadata: SecretMetadata) -> bool:
        """Check if secret has expired"""
        current_time = datetime.now(timezone.utc)
        
        if metadata.last_rotated:
            age = current_time - metadata.last_rotated
        else:
            age = current_time - metadata.created_at
        
        return age.days > metadata.max_age_days
    
    def get_security_configuration(self) -> Dict[str, Any]:
        """Get current security configuration summary"""
        config_summary = {
            "total_configs": len(self.encrypted_config),
            "encrypted_configs": sum(
                1 for metadata in self.config_metadata.values()
                if metadata.get("encrypted", False)
            ),
            "security_levels": {},
            "secrets_summary": {
                "total_secrets": len(self.secret_metadata),
                "active_secrets": sum(
                    1 for metadata in self.secret_metadata.values()
                    if metadata.is_active
                ),
                "secrets_needing_rotation": len(self.check_secrets_needing_rotation()),
                "secrets_by_type": {}
            }
        }
        
        # Count by security level
        for metadata in self.config_metadata.values():
            level = metadata.get("security_level", "unknown")
            config_summary["security_levels"][level] = config_summary["security_levels"].get(level, 0) + 1
        
        # Count secrets by type
        for metadata in self.secret_metadata.values():
            secret_type = metadata.secret_type.value
            config_summary["secrets_summary"]["secrets_by_type"][secret_type] = \
                config_summary["secrets_summary"]["secrets_by_type"].get(secret_type, 0) + 1
        
        return config_summary
    
    def export_configuration(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration for backup/migration"""
        export_data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "configuration": {},
            "metadata": self.config_metadata
        }
        
        for key in self.encrypted_config:
            metadata = self.config_metadata.get(key, {})
            
            # Skip secrets unless explicitly requested
            if key in self.secret_metadata and not include_secrets:
                continue
            
            # Get decrypted value
            value = self.get_config(key)
            export_data["configuration"][key] = value
        
        return export_data


# Factory function
def create_secure_config_manager(master_key: Optional[str] = None) -> SecureConfigManager:
    """
    Create SecureConfigManager instance.
    
    Args:
        master_key: Optional master key (hex string)
        
    Returns:
        SecureConfigManager instance
    """
    if master_key:
        key_bytes = bytes.fromhex(master_key)
    else:
        key_bytes = None
    
    return SecureConfigManager(master_key=key_bytes)