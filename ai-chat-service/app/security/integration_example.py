"""
Example integration of the data protection system with the existing unified-ai-system.

This file demonstrates how to integrate the comprehensive security system
with the existing FastAPI application, Redis memory, and ClickHouse storage.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

import structlog

# Import security components
from .data_protection import DataProtectionService, create_data_protection_service
from .memory_integration import SecureConversationMemoryCache, SecureClickHouseManager
from .tls_config import SecureTLSManager, create_tls_manager
from .retention_scheduler import DataRetentionScheduler, create_retention_scheduler
from .privacy_compliance import ConsentType, ConsentStatus, DataProcessingPurpose
from .audit_logger import AuditEventType, RiskLevel, ComplianceFramework

# Import existing components
from ..cache.redis_client import CacheManager
from ..memory.clickhouse_memory import ConversationClickHouseManager
from ..core.config import get_settings

logger = structlog.get_logger(__name__)

# Global security services
data_protection_service: Optional[DataProtectionService] = None
retention_scheduler: Optional[DataRetentionScheduler] = None
tls_manager: Optional[SecureTLSManager] = None
secure_redis_cache: Optional[SecureConversationMemoryCache] = None
secure_clickhouse: Optional[SecureClickHouseManager] = None

# Security middleware
security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with security service initialization"""
    global data_protection_service, retention_scheduler, tls_manager
    global secure_redis_cache, secure_clickhouse
    
    try:
        # Initialize security services
        logger.info("initializing_security_services")
        
        # Create data protection service
        data_protection_service = create_data_protection_service()
        await data_protection_service.start_services()
        
        # Create TLS manager
        tls_manager = create_tls_manager()
        
        # Create retention scheduler
        retention_scheduler = create_retention_scheduler(data_protection_service)
        await retention_scheduler.start()
        
        # Initialize secure memory wrappers
        # Note: You would get these from your existing dependency injection
        redis_cache = CacheManager()  # Your existing Redis cache
        clickhouse_manager = ConversationClickHouseManager()  # Your existing ClickHouse
        
        secure_redis_cache = SecureConversationMemoryCache(
            redis_cache, 
            data_protection_service
        )
        
        secure_clickhouse = SecureClickHouseManager(
            clickhouse_manager,
            data_protection_service
        )
        
        logger.info("security_services_initialized")
        
        yield
        
    finally:
        # Cleanup security services
        logger.info("shutting_down_security_services")
        
        if retention_scheduler:
            await retention_scheduler.stop()
        
        if data_protection_service:
            await data_protection_service.stop_services()
        
        logger.info("security_services_shutdown_complete")


def create_secure_app() -> FastAPI:
    """Create FastAPI application with integrated security"""
    
    app = FastAPI(
        title="Unified AI System - Secure",
        description="AI Search System with comprehensive data protection",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        if tls_manager:
            security_headers = tls_manager.get_security_headers()
            for header, value in security_headers.items():
                response.headers[header] = value
        
        return response
    
    # Add CORS with secure settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().allowed_origins,
        allow_credentials=False,  # Security: Don't allow credentials
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        max_age=86400
    )
    
    return app


def get_user_id_from_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Extract user ID from JWT token (simplified example)"""
    if not credentials:
        return None
    
    # In a real implementation, you would validate and decode the JWT
    # For this example, we'll just return a placeholder
    return "user_123"


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Example secure API endpoints

app = create_secure_app()


@app.post("/api/v1/chat/message")
async def add_chat_message(
    request: Request,
    message_data: Dict[str, Any],
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Add chat message with security protection"""
    try:
        session_id = message_data.get("session_id")
        message = message_data.get("message", {})
        tokens = message_data.get("tokens", 100)
        ip_address = get_client_ip(request)
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        if not secure_redis_cache:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Add message with security protection
        result = await secure_redis_cache.add_message_secure(
            session_id=session_id,
            message=message,
            tokens=tokens,
            user_id=user_id,
            ip_address=ip_address
        )
        
        if not result.get("success"):
            if result.get("requires_consent"):
                raise HTTPException(
                    status_code=403,
                    detail="Data storage requires user consent"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to store message")
                )
        
        return {
            "success": True,
            "message": "Message stored securely",
            "security": result.get("security", {}),
            "statistics": {
                "final_length": result.get("final_length"),
                "final_tokens": result.get("final_tokens"),
                "budget_utilization": result.get("budget_utilization")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_message_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    request: Request,
    limit: Optional[int] = None,
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Get chat history with security checks"""
    try:
        ip_address = get_client_ip(request)
        
        if not secure_redis_cache:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Get messages with security checks
        result = await secure_redis_cache.get_recent_messages_secure(
            session_id=session_id,
            limit=limit,
            user_id=user_id,
            purpose="chat_history_retrieval",
            ip_address=ip_address
        )
        
        if not result.get("success"):
            if result.get("requires_consent"):
                raise HTTPException(
                    status_code=403,
                    detail="Data access requires user consent"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to retrieve messages")
                )
        
        return {
            "success": True,
            "session_id": session_id,
            "messages": result.get("messages", []),
            "total_tokens": result.get("total_tokens", 0),
            "message_count": result.get("message_count", 0),
            "security": result.get("security", {}),
            "metadata": result.get("metadata", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_history_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/privacy/consent")
async def update_consent(
    request: Request,
    consent_data: Dict[str, Any],
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Update user consent preferences"""
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        consent_type = consent_data.get("consent_type")
        granted = consent_data.get("granted", False)
        purpose = consent_data.get("purpose", "general")
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        if not consent_type:
            raise HTTPException(status_code=400, detail="consent_type is required")
        
        if not data_protection_service:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Process consent change
        success = await data_protection_service.process_consent_change(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            purpose=purpose,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update consent")
        
        return {
            "success": True,
            "message": f"Consent {'granted' if granted else 'withdrawn'} successfully",
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "purpose": purpose,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("consent_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/privacy/request")
async def handle_privacy_request(
    request: Request,
    privacy_request: Dict[str, Any],
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Handle GDPR privacy requests"""
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        request_type = privacy_request.get("request_type")
        details = privacy_request.get("details", {})
        
        if not request_type:
            raise HTTPException(status_code=400, detail="request_type is required")
        
        if request_type not in ["access", "erasure", "rectification", "portability", "restrict", "object"]:
            raise HTTPException(status_code=400, detail="Invalid request_type")
        
        if not data_protection_service:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Handle privacy request
        result = await data_protection_service.handle_privacy_request(
            request_type=request_type,
            user_id=user_id,
            details=details
        )
        
        return {
            "success": True,
            "message": f"Privacy request '{request_type}' processed successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("privacy_request_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/admin/security/status")
async def get_security_status(
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Get comprehensive security status (admin only)"""
    try:
        # In a real implementation, you would check admin permissions
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not data_protection_service:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Get protection status
        status = data_protection_service.get_protection_status()
        
        # Add retention scheduler status
        if retention_scheduler:
            status["retention_scheduler"] = retention_scheduler.get_task_status()
        
        return {
            "success": True,
            "security_status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("security_status_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/admin/compliance/report")
async def get_compliance_report(
    request: Request,
    framework: str = "gdpr",
    days: int = 30,
    user_id: Optional[str] = Depends(get_user_id_from_token)
):
    """Generate compliance report (admin only)"""
    try:
        # In a real implementation, you would check admin permissions
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if framework not in ["gdpr", "soc2", "hipaa", "pci_dss", "iso27001"]:
            raise HTTPException(status_code=400, detail="Invalid compliance framework")
        
        if not data_protection_service:
            raise HTTPException(status_code=503, detail="Security services not available")
        
        # Generate compliance report
        report = data_protection_service.generate_compliance_report(
            framework=framework,
            days=days
        )
        
        return {
            "success": True,
            "compliance_report": report,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance_report_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with security audit logging"""
    
    # Log security incidents
    if data_protection_service:
        try:
            await data_protection_service.audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_ACCESS,
                resource="api_endpoint",
                action="exception_occurred",
                outcome="failure",
                details={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "endpoint": str(request.url),
                    "method": request.method
                },
                risk_level=RiskLevel.MEDIUM,
                ip_address=get_client_ip(request)
            )
        except Exception as audit_error:
            logger.error("audit_logging_failed", error=str(audit_error))
    
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        endpoint=str(request.url),
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime, timezone
    
    # Get TLS configuration
    settings = get_settings()
    tls_config = {}
    
    if tls_manager:
        tls_config = tls_manager.get_fastapi_tls_config()
    
    # Run with HTTPS if certificates are available
    if tls_config:
        logger.info("starting_secure_server_with_https")
        uvicorn.run(
            "security.integration_example:app",
            host=settings.api_host,
            port=settings.api_port,
            **tls_config
        )
    else:
        logger.warning("starting_server_without_https_certificates_not_found")
        uvicorn.run(
            "security.integration_example:app",
            host=settings.api_host,
            port=settings.api_port
        )