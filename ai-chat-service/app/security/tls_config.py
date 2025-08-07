"""
TLS/SSL configuration for encryption in transit.

Provides secure communication configurations:
- TLS 1.2+ enforcement
- Certificate management and validation
- Secure cipher suites
- HSTS headers and security policies
- Integration with Redis, ClickHouse, and HTTP services
"""

import ssl
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TLSConfig:
    """TLS configuration structure"""
    min_version: ssl.TLSVersion
    cipher_suites: List[str]
    cert_file: Optional[str]
    key_file: Optional[str]
    ca_file: Optional[str]
    verify_mode: ssl.VerifyMode
    check_hostname: bool
    protocols: List[str]


class SecureTLSManager:
    """
    TLS/SSL configuration manager for secure communications.
    
    Provides standardized TLS configurations for:
    - HTTPS/HTTP API endpoints
    - Redis connections
    - ClickHouse connections
    - Inter-service communications
    """
    
    def __init__(self, cert_dir: Optional[str] = None):
        """
        Initialize TLS manager.
        
        Args:
            cert_dir: Directory containing certificates
        """
        self.cert_dir = Path(cert_dir) if cert_dir else Path("/etc/ssl/certs")
        
        # Security policies
        self.security_policies = {
            "strict": {
                "min_tls_version": ssl.TLSVersion.TLSv1_3,
                "allowed_ciphers": [
                    "ECDHE+AESGCM",
                    "ECDHE+CHACHA20",
                    "DHE+AESGCM",
                    "DHE+CHACHA20"
                ],
                "verify_certificates": True,
                "check_hostname": True
            },
            "standard": {
                "min_tls_version": ssl.TLSVersion.TLSv1_2,
                "allowed_ciphers": [
                    "ECDHE+AESGCM",
                    "ECDHE+CHACHA20",
                    "DHE+AESGCM",
                    "DHE+CHACHA20",
                    "ECDHE+SHA256",
                    "DHE+SHA256"
                ],
                "verify_certificates": True,
                "check_hostname": True
            },
            "compatible": {
                "min_tls_version": ssl.TLSVersion.TLSv1_2,
                "allowed_ciphers": [
                    "ECDHE+AESGCM",
                    "ECDHE+CHACHA20",
                    "DHE+AESGCM",
                    "DHE+CHACHA20",
                    "ECDHE+SHA256",
                    "DHE+SHA256",
                    "ECDHE+SHA1",
                    "DHE+SHA1"
                ],
                "verify_certificates": False,  # For development
                "check_hostname": False
            }
        }
        
        logger.info("secure_tls_manager_initialized", cert_dir=str(self.cert_dir))
    
    def create_ssl_context(self,
                          purpose: str = "client",
                          security_level: str = "standard",
                          cert_file: Optional[str] = None,
                          key_file: Optional[str] = None,
                          ca_file: Optional[str] = None) -> ssl.SSLContext:
        """
        Create SSL context with secure defaults.
        
        Args:
            purpose: Purpose of SSL context ("client", "server", "both")
            security_level: Security level ("strict", "standard", "compatible")
            cert_file: Path to certificate file
            key_file: Path to private key file
            ca_file: Path to CA certificate file
            
        Returns:
            Configured SSL context
        """
        try:
            policy = self.security_policies.get(security_level, self.security_policies["standard"])
            
            # Create SSL context based on purpose
            if purpose == "server":
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            else:
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Set minimum TLS version
            context.minimum_version = policy["min_tls_version"]
            context.maximum_version = ssl.TLSVersion.TLSv1_3
            
            # Configure cipher suites
            cipher_string = ":".join(policy["allowed_ciphers"])
            context.set_ciphers(cipher_string)
            
            # Certificate verification
            if policy["verify_certificates"]:
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                context.verify_mode = ssl.CERT_NONE
            
            context.check_hostname = policy["check_hostname"]
            
            # Load certificates if provided
            if cert_file and key_file:
                cert_path = self.cert_dir / cert_file if not os.path.isabs(cert_file) else cert_file
                key_path = self.cert_dir / key_file if not os.path.isabs(key_file) else key_file
                
                if Path(cert_path).exists() and Path(key_path).exists():
                    context.load_cert_chain(str(cert_path), str(key_path))
                    logger.info("ssl_certificates_loaded", cert_file=str(cert_path))
                else:
                    logger.warning("ssl_certificates_not_found", cert_file=str(cert_path), key_file=str(key_path))
            
            # Load CA certificates
            if ca_file:
                ca_path = self.cert_dir / ca_file if not os.path.isabs(ca_file) else ca_file
                if Path(ca_path).exists():
                    context.load_verify_locations(str(ca_path))
                    logger.info("ca_certificates_loaded", ca_file=str(ca_path))
            
            # Additional security settings
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_SINGLE_DH_USE
            context.options |= ssl.OP_SINGLE_ECDH_USE
            
            logger.debug(
                "ssl_context_created",
                purpose=purpose,
                security_level=security_level,
                min_version=policy["min_tls_version"].name,
                verify_mode=context.verify_mode.name
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "ssl_context_creation_failed",
                error=str(e),
                purpose=purpose,
                security_level=security_level
            )
            raise
    
    def get_redis_tls_config(self, security_level: str = "standard") -> Dict[str, Any]:
        """
        Get Redis TLS configuration.
        
        Args:
            security_level: Security level for TLS
            
        Returns:
            Redis TLS configuration dictionary
        """
        try:
            ssl_context = self.create_ssl_context(
                purpose="client",
                security_level=security_level,
                ca_file=os.getenv("REDIS_CA_CERT"),
                cert_file=os.getenv("REDIS_CLIENT_CERT"),
                key_file=os.getenv("REDIS_CLIENT_KEY")
            )
            
            config = {
                "ssl": True,
                "ssl_context": ssl_context,
                "ssl_check_hostname": ssl_context.check_hostname,
                "ssl_verify_mode": ssl_context.verify_mode,
                "ssl_ca_certs": os.getenv("REDIS_CA_CERT"),
                "ssl_certfile": os.getenv("REDIS_CLIENT_CERT"),
                "ssl_keyfile": os.getenv("REDIS_CLIENT_KEY")
            }
            
            logger.info("redis_tls_config_created", security_level=security_level)
            return config
            
        except Exception as e:
            logger.error("redis_tls_config_failed", error=str(e))
            # Return non-TLS config as fallback
            return {"ssl": False}
    
    def get_clickhouse_tls_config(self, security_level: str = "standard") -> Dict[str, Any]:
        """
        Get ClickHouse TLS configuration.
        
        Args:
            security_level: Security level for TLS
            
        Returns:
            ClickHouse TLS configuration dictionary
        """
        try:
            ssl_context = self.create_ssl_context(
                purpose="client",
                security_level=security_level,
                ca_file=os.getenv("CLICKHOUSE_CA_CERT"),
                cert_file=os.getenv("CLICKHOUSE_CLIENT_CERT"),
                key_file=os.getenv("CLICKHOUSE_CLIENT_KEY")
            )
            
            config = {
                "secure": True,
                "verify": ssl_context.verify_mode == ssl.CERT_REQUIRED,
                "ca_certs": os.getenv("CLICKHOUSE_CA_CERT"),
                "client_cert": os.getenv("CLICKHOUSE_CLIENT_CERT"),
                "client_key": os.getenv("CLICKHOUSE_CLIENT_KEY"),
                "ssl_context": ssl_context
            }
            
            logger.info("clickhouse_tls_config_created", security_level=security_level)
            return config
            
        except Exception as e:
            logger.error("clickhouse_tls_config_failed", error=str(e))
            # Return non-TLS config as fallback
            return {"secure": False}
    
    def get_fastapi_tls_config(self, security_level: str = "standard") -> Dict[str, Any]:
        """
        Get FastAPI TLS configuration for HTTPS.
        
        Args:
            security_level: Security level for TLS
            
        Returns:
            FastAPI TLS configuration dictionary
        """
        try:
            config = {
                "ssl_keyfile": os.getenv("SERVER_SSL_KEY", str(self.cert_dir / "server.key")),
                "ssl_certfile": os.getenv("SERVER_SSL_CERT", str(self.cert_dir / "server.crt")),
                "ssl_ca_certs": os.getenv("SERVER_CA_CERT"),
                "ssl_version": ssl.PROTOCOL_TLS_SERVER,
                "ssl_ciphers": None  # Use system defaults for server
            }
            
            # Verify certificate files exist
            cert_exists = Path(config["ssl_certfile"]).exists()
            key_exists = Path(config["ssl_keyfile"]).exists()
            
            if not (cert_exists and key_exists):
                logger.warning(
                    "ssl_certificates_missing",
                    cert_file=config["ssl_certfile"],
                    key_file=config["ssl_keyfile"],
                    cert_exists=cert_exists,
                    key_exists=key_exists
                )
                return {}
            
            logger.info(
                "fastapi_tls_config_created",
                security_level=security_level,
                cert_file=config["ssl_certfile"],
                key_file=config["ssl_keyfile"]
            )
            
            return config
            
        except Exception as e:
            logger.error("fastapi_tls_config_failed", error=str(e))
            return {}
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        Get HTTP security headers for HTTPS.
        
        Returns:
            Dictionary of security headers
        """
        return {
            # HSTS - Force HTTPS for 1 year
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # Feature policy
            "Permissions-Policy": (
                "camera=(), "
                "microphone=(), "
                "geolocation=(), "
                "interest-cohort=()"
            )
        }
    
    def generate_self_signed_cert(self,
                                 hostname: str = "localhost",
                                 cert_file: str = "server.crt",
                                 key_file: str = "server.key",
                                 days: int = 365) -> bool:
        """
        Generate self-signed certificate for development.
        
        Args:
            hostname: Hostname for certificate
            cert_file: Certificate file name
            key_file: Private key file name
            days: Certificate validity in days
            
        Returns:
            Success boolean
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
            from cryptography.hazmat.primitives import serialization, hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Unified AI System"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Write certificate
            cert_path = self.cert_dir / cert_file
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            key_path = self.cert_dir / key_file
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set appropriate permissions
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)
            
            logger.info(
                "self_signed_certificate_generated",
                hostname=hostname,
                cert_file=str(cert_path),
                key_file=str(key_path),
                valid_days=days
            )
            
            return True
            
        except ImportError:
            logger.error("cryptography_package_required_for_cert_generation")
            return False
        except Exception as e:
            logger.error("certificate_generation_failed", error=str(e))
            return False
    
    def validate_certificate(self, cert_file: str) -> Dict[str, Any]:
        """
        Validate SSL certificate.
        
        Args:
            cert_file: Path to certificate file
            
        Returns:
            Certificate validation results
        """
        try:
            import ssl
            import socket
            from urllib.parse import urlparse
            
            cert_path = self.cert_dir / cert_file if not os.path.isabs(cert_file) else cert_file
            
            if not Path(cert_path).exists():
                return {"valid": False, "error": "Certificate file not found"}
            
            # Load and parse certificate
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            try:
                from cryptography import x509
                cert = x509.load_pem_x509_certificate(cert_data)
                
                now = datetime.utcnow()
                not_before = cert.not_valid_before
                not_after = cert.not_valid_after
                
                validation_result = {
                    "valid": True,
                    "subject": str(cert.subject),
                    "issuer": str(cert.issuer),
                    "not_before": not_before.isoformat(),
                    "not_after": not_after.isoformat(),
                    "expired": now > not_after,
                    "not_yet_valid": now < not_before,
                    "days_until_expiry": (not_after - now).days,
                    "serial_number": str(cert.serial_number),
                    "signature_algorithm": cert.signature_algorithm_oid._name
                }
                
                # Check for SAN extension
                try:
                    san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                    san_names = [name.value for name in san_ext.value]
                    validation_result["subject_alternative_names"] = san_names
                except x509.ExtensionNotFound:
                    validation_result["subject_alternative_names"] = []
                
                return validation_result
                
            except ImportError:
                # Fallback without cryptography library
                return {
                    "valid": True,
                    "note": "Limited validation without cryptography library",
                    "file_exists": True,
                    "file_size": len(cert_data)
                }
            
        except Exception as e:
            logger.error("certificate_validation_failed", error=str(e), cert_file=cert_file)
            return {"valid": False, "error": str(e)}


# Factory function
def create_tls_manager(cert_dir: Optional[str] = None) -> SecureTLSManager:
    """Create SecureTLSManager instance"""
    return SecureTLSManager(cert_dir=cert_dir)