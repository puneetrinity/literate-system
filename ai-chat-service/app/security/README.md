# Comprehensive Data Protection System

This security package provides enterprise-grade data protection with encryption, privacy compliance, and audit logging for the Unified AI System.

## Features

### 🔐 Data Encryption
- **AES-256-GCM encryption** for sensitive data at rest
- **Classification-based encryption policies** (Public, Internal, Confidential, Restricted)
- **Field-level encryption** for database storage
- **Automatic key derivation** with PBKDF2
- **Encryption metadata tracking** and integrity verification

### 🔑 Key Management
- **Hierarchical key structure** with master and data keys
- **Automatic key rotation** based on time and usage policies
- **Key versioning and migration** support
- **Secure key storage** with HMAC signatures
- **Audit logging** for all key operations

### 📋 GDPR Compliance
- **Comprehensive consent management** with granular permissions
- **Right to be forgotten** implementation with secure deletion
- **Data portability** with structured export
- **Data anonymization and pseudonymization**
- **Privacy impact assessments**
- **Automated retention policies**

### 📊 Audit Logging
- **Structured security events** with tamper-proofing
- **Real-time monitoring** and alerting
- **Compliance-focused logging** (GDPR, SOC2, HIPAA, etc.)
- **Integrity verification** with checksums and HMAC signatures
- **SIEM integration** capabilities

### 🔒 Secure Configuration
- **Environment variable encryption**
- **Secrets management** with automatic rotation
- **Secure default configurations**
- **Configuration validation** and integrity checking

### 🌐 TLS/SSL Security
- **TLS 1.2+ enforcement** with secure cipher suites
- **Certificate management** and validation
- **Security headers** (HSTS, CSP, etc.)
- **Self-signed certificate generation** for development

## Quick Start

### 1. Basic Setup

```python
from app.security import DataProtectionService, create_data_protection_service

# Initialize data protection service
data_protection = create_data_protection_service()
await data_protection.start_services()
```

### 2. Protect Data

```python
from app.security import DataClassification

# Protect sensitive conversation data
protected_data = await data_protection.protect_data(
    data={"message": "Hello, world!", "user": "john@example.com"},
    data_type="conversation",
    user_id="user_123",
    session_id="session_456"
)

# Access protected data
decrypted_data = await data_protection.access_protected_data(
    protected_data=protected_data,
    user_id="user_123",
    purpose="chat_response"
)
```

### 3. Handle GDPR Requests

```python
# Handle data access request
access_result = await data_protection.handle_privacy_request(
    request_type="access",
    user_id="user_123"
)

# Handle data erasure request  
erasure_result = await data_protection.handle_privacy_request(
    request_type="erasure",
    user_id="user_123"
)
```

### 4. Manage Consent

```python
# Record user consent
success = await data_protection.process_consent_change(
    user_id="user_123",
    consent_type="analytics",
    granted=True,
    purpose="conversation_analytics"
)
```

## Configuration

### Environment Variables

```bash
# Encryption
ENCRYPTION_MASTER_KEY=your_hex_encoded_master_key
CONFIG_MASTER_KEY=your_base64_encoded_config_key
AUDIT_SECRET_KEY=your_audit_signing_key

# TLS/SSL Certificates
SERVER_SSL_CERT=/path/to/server.crt
SERVER_SSL_KEY=/path/to/server.key
SERVER_CA_CERT=/path/to/ca.crt

# Redis TLS
REDIS_CA_CERT=/path/to/redis-ca.crt
REDIS_CLIENT_CERT=/path/to/redis-client.crt
REDIS_CLIENT_KEY=/path/to/redis-client.key

# ClickHouse TLS
CLICKHOUSE_CA_CERT=/path/to/clickhouse-ca.crt
CLICKHOUSE_CLIENT_CERT=/path/to/clickhouse-client.crt
CLICKHOUSE_CLIENT_KEY=/path/to/clickhouse-client.key
```

### Data Classification Policies

```python
from app.security import DataClassification, EncryptionContext

# Configure encryption policies
encryption_context = EncryptionContext(
    classification=DataClassification.CONFIDENTIAL,
    user_id="user_123",
    purpose="conversation_storage",
    requires_audit=True
)
```

## Integration Examples

### Secure Redis Memory

```python
from app.security.memory_integration import SecureConversationMemoryCache

# Wrap existing Redis cache with security
secure_cache = SecureConversationMemoryCache(
    redis_cache=your_redis_cache,
    data_protection_service=data_protection
)

# Add message with automatic encryption and audit logging
result = await secure_cache.add_message_secure(
    session_id="session_123",
    message={"content": "Hello!", "timestamp": "2024-01-01T00:00:00Z"},
    tokens=50,
    user_id="user_123",
    ip_address="192.168.1.1"
)
```

### Secure ClickHouse Analytics

```python
from app.security.memory_integration import SecureClickHouseManager

# Wrap existing ClickHouse manager with security
secure_clickhouse = SecureClickHouseManager(
    clickhouse_manager=your_clickhouse_manager,
    data_protection_service=data_protection
)

# Store analytics with consent checking and encryption
success = await secure_clickhouse.store_conversation_summary_secure(
    session_id="session_123",
    summary="User discussed AI capabilities",
    metadata={"quality_score": 0.8, "topics": ["AI", "technology"]},
    user_id="user_123"
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, Request
from app.security.integration_example import create_secure_app, get_user_id_from_token

app = create_secure_app()

@app.post("/api/chat/message")
async def add_message(
    request: Request,
    message_data: dict,
    user_id: str = Depends(get_user_id_from_token)
):
    # Message is automatically encrypted and audit logged
    result = await secure_cache.add_message_secure(
        session_id=message_data["session_id"],
        message=message_data["message"],
        tokens=message_data["tokens"],
        user_id=user_id,
        ip_address=request.client.host
    )
    return {"success": result["success"]}
```

## Security Components

### 1. EncryptionManager
- **Purpose**: Handles data encryption/decryption with classification-based policies
- **Key Features**: AES-256-GCM, field-level encryption, key derivation
- **Usage**: Automatic via DataProtectionService or direct API

### 2. KeyManager
- **Purpose**: Manages encryption keys with rotation and versioning
- **Key Features**: Hierarchical keys, automatic rotation, secure storage
- **Usage**: Background service with policy-driven rotation

### 3. GDPRComplianceManager
- **Purpose**: Implements GDPR requirements and privacy rights
- **Key Features**: Right to be forgotten, data portability, consent management
- **Usage**: Via DataProtectionService privacy request APIs

### 4. SecurityAuditLogger
- **Purpose**: Comprehensive security event logging with integrity protection
- **Key Features**: Structured events, tamper detection, compliance reporting
- **Usage**: Automatic logging for all security operations

### 5. SecureConfigManager
- **Purpose**: Secure configuration and secrets management
- **Key Features**: Encrypted config values, secrets rotation, validation
- **Usage**: Replace standard environment variable access

### 6. DataRetentionScheduler
- **Purpose**: Automated data lifecycle management and cleanup
- **Key Features**: Policy-driven retention, scheduled cleanup, compliance automation
- **Usage**: Background service with configurable schedules

## Data Classification Levels

### Public
- No encryption required
- Standard audit logging
- No special handling

### Internal
- Basic encryption (AES-256)
- Standard audit logging
- 180-day key rotation

### Confidential
- Strong encryption (AES-256-GCM)
- Enhanced audit logging
- 90-day key rotation
- Consent checking required

### Restricted
- Maximum security encryption
- Full audit logging
- 30-day key rotation
- Enhanced consent and authorization

## Compliance Frameworks

### GDPR (General Data Protection Regulation)
- ✅ Right to access (Article 15)
- ✅ Right to rectification (Article 16)
- ✅ Right to erasure (Article 17)
- ✅ Right to restrict processing (Article 18)
- ✅ Right to data portability (Article 20)
- ✅ Right to object (Article 21)
- ✅ Consent management
- ✅ Data protection by design

### SOC 2 (System and Organization Controls)
- ✅ Security controls
- ✅ Availability controls
- ✅ Processing integrity
- ✅ Confidentiality controls
- ✅ Privacy controls

### Additional Frameworks
- HIPAA (Healthcare)
- PCI DSS (Payment Card Industry)
- ISO 27001 (Information Security)

## Performance Considerations

### Encryption Performance
- **AES-256-GCM**: High-performance hardware acceleration
- **Key Caching**: Derived keys cached for performance
- **Batch Operations**: Support for bulk encryption/decryption

### Memory Usage
- **Streaming Encryption**: Large data processed in chunks
- **Key Rotation**: Non-blocking rotation with graceful transitions
- **Audit Logging**: Asynchronous logging to prevent blocking

### Storage Overhead
- **Encrypted Data**: ~15% overhead for metadata and padding
- **Audit Logs**: Configurable retention with compression
- **Key Storage**: Minimal overhead with hierarchical structure

## Security Best Practices

### Development
1. **Never commit secrets** to version control
2. **Use environment variables** for configuration
3. **Test with realistic data volumes** for performance
4. **Implement proper error handling** for security operations
5. **Use secure defaults** for all configurations

### Production
1. **Use proper certificate management** (Let's Encrypt, CA-signed)
2. **Enable all security headers** and CSP policies
3. **Monitor audit logs** for security incidents
4. **Implement backup and recovery** for encrypted data
5. **Regular security assessments** and compliance audits

### Compliance
1. **Document data flows** and processing activities
2. **Maintain consent records** with audit trails
3. **Implement data retention policies** with automated cleanup
4. **Regular compliance reporting** and gap analysis
5. **Staff training** on privacy and security requirements

## Troubleshooting

### Common Issues

#### Encryption Errors
```python
# Check encryption status
status = encryption_manager.get_encryption_status(data)
if status["requires_key_rotation"]:
    await key_manager.rotate_key(key_id)
```

#### Consent Issues
```python
# Check user consent
has_consent = await consent_manager.check_consent(
    user_id="user_123",
    consent_type=ConsentType.FUNCTIONAL
)
```

#### Audit Log Verification
```python
# Verify audit event integrity
is_valid = audit_logger.verify_event_integrity(event)
if not is_valid:
    logger.warning("audit_event_integrity_failure", event_id=event.event_id)
```

### Monitoring and Alerts

#### Key Metrics
- Encryption/decryption success rates
- Key rotation completion rates
- Consent compliance rates
- Audit log integrity rates
- Data retention policy execution

#### Alert Conditions
- Failed encryption operations
- Key rotation failures
- GDPR request processing failures
- Audit log integrity violations
- Compliance policy violations

## Support and Maintenance

### Updates
- **Security patches**: Applied automatically via key rotation
- **Compliance updates**: Policy configuration updates
- **Performance optimizations**: Regular performance monitoring

### Backup and Recovery
- **Key backup**: Secure key escrow for disaster recovery
- **Configuration backup**: Encrypted configuration snapshots
- **Audit log backup**: Tamper-proof audit trail preservation

### Monitoring
- **Real-time dashboards**: Security metrics and compliance status
- **Automated alerts**: Security incidents and policy violations
- **Regular reports**: Compliance and security posture reports

For more detailed information, see the individual component documentation in each module.