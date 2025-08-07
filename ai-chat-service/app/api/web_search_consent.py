"""
Web Search Consent Management API

Provides enterprise-grade consent management for web search functionality:
- Consent verification and double confirmation
- Admin approval workflows
- User permission management
- Audit trail for compliance
- Cost center and budget controls
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.dependencies import get_cache_manager
from app.routers.web_search_router import (
    WebSearchRouter, 
    WebSearchRequest, 
    WebSearchResult,
    ConsentLevel, 
    WebSearchMode
)

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["Web Search Consent"])


class ConsentRequest(BaseModel):
    """Request for web search consent"""
    
    user_id: str = Field(description="User ID requesting consent")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    search_query: str = Field(description="Intended search query")
    mode: WebSearchMode = Field(default=WebSearchMode.RESEARCH, description="Search mode")
    
    # Enterprise controls
    enterprise_account: bool = Field(default=False, description="Is enterprise account")
    cost_center: Optional[str] = Field(default=None, description="Cost center for billing")
    budget_limit: float = Field(default=2.0, description="Budget limit for search")
    
    # Context
    user_agent: Optional[str] = Field(default=None, description="User agent")
    ip_address: Optional[str] = Field(default=None, description="IP address")


class ConsentResponse(BaseModel):
    """Response for consent request"""
    
    consent_token: str = Field(description="Consent token for search execution")
    consent_level: ConsentLevel = Field(description="Granted consent level")
    expires_at: datetime = Field(description="When consent expires")
    
    # Cost information
    estimated_cost: float = Field(description="Estimated search cost")
    budget_remaining: float = Field(description="Remaining budget")
    
    # Compliance information
    audit_id: str = Field(description="Audit trail ID")
    compliance_notes: List[str] = Field(default_factory=list, description="Compliance notes")
    
    # Next steps
    requires_double_confirmation: bool = Field(default=False, description="Requires double confirmation")
    admin_approval_required: bool = Field(default=False, description="Admin approval required")


class DoubleConfirmationRequest(BaseModel):
    """Double confirmation request"""
    
    consent_token: str = Field(description="Original consent token")
    confirmation_text: str = Field(description="User confirmation text")
    understood_costs: bool = Field(description="User understands costs")
    understood_scope: bool = Field(description="User understands search scope")


class AdminApprovalRequest(BaseModel):
    """Admin approval request"""
    
    consent_token: str = Field(description="Consent token to approve")
    admin_user_id: str = Field(description="Admin user ID")
    approval_reason: str = Field(description="Reason for approval")
    budget_override: Optional[float] = Field(default=None, description="Budget override")


class ConsentStatus(BaseModel):
    """Consent status response"""
    
    consent_token: str = Field(description="Consent token")
    status: str = Field(description="Current status")
    consent_level: ConsentLevel = Field(description="Current consent level")
    
    # Validity
    is_valid: bool = Field(description="Is consent still valid")
    expires_at: datetime = Field(description="Expiration time")
    time_remaining_seconds: int = Field(description="Time remaining in seconds")
    
    # Usage tracking
    searches_used: int = Field(default=0, description="Searches used with this consent")
    budget_used: float = Field(default=0.0, description="Budget used")
    budget_remaining: float = Field(description="Budget remaining")


class ConsentManager:
    """Manages web search consent and enterprise controls"""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self.consent_timeout_minutes = 10
        self.max_searches_per_consent = 5
        self.enterprise_controls = {
            "require_double_confirmation": True,
            "admin_approval_threshold": 5.0,  # Budget threshold requiring admin approval
            "max_daily_budget_per_user": 25.0,
            "compliance_logging": True
        }
    
    async def request_consent(self, request: ConsentRequest, client_ip: str) -> ConsentResponse:
        """Process initial consent request"""
        
        # Generate consent token
        consent_token = hashlib.sha256(
            f"{request.user_id}{request.search_query}{datetime.now().isoformat()}{client_ip}".encode()
        ).hexdigest()[:16]
        
        # Generate audit ID
        audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{consent_token[:8]}"
        
        # Calculate estimated cost
        estimated_cost = self._estimate_search_cost(request.mode, request.search_query)
        
        # Check user budget
        daily_budget_used = await self._get_daily_budget_used(request.user_id)
        budget_remaining = self.enterprise_controls["max_daily_budget_per_user"] - daily_budget_used
        
        if estimated_cost > budget_remaining:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient budget remaining for this search"
            )
        
        # Determine consent level and requirements
        consent_level = ConsentLevel.BASIC
        requires_double_confirmation = False
        admin_approval_required = False
        compliance_notes = []
        
        if request.enterprise_account:
            requires_double_confirmation = self.enterprise_controls["require_double_confirmation"]
            if estimated_cost > self.enterprise_controls["admin_approval_threshold"]:
                admin_approval_required = True
                compliance_notes.append(f"Admin approval required for searches over ${self.enterprise_controls['admin_approval_threshold']}")
        
        # Store consent data
        consent_data = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "search_query": request.search_query,
            "mode": request.mode.value,
            "enterprise_account": request.enterprise_account,
            "cost_center": request.cost_center,
            "budget_limit": request.budget_limit,
            "estimated_cost": estimated_cost,
            "ip_address": client_ip,
            "user_agent": request.user_agent,
            "audit_id": audit_id,
            "consent_level": consent_level.value,
            "requires_double_confirmation": requires_double_confirmation,
            "admin_approval_required": admin_approval_required,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=self.consent_timeout_minutes)).isoformat(),
            "searches_used": 0,
            "budget_used": 0.0,
            "status": "pending_confirmation" if requires_double_confirmation else "active"
        }
        
        # Store in cache with expiration
        await self.cache.set(
            f"consent:{consent_token}",
            json.dumps(consent_data),
            ttl=self.consent_timeout_minutes * 60
        )
        
        # Log consent request for audit
        await self._log_consent_event(audit_id, "consent_requested", consent_data)
        
        logger.info("Web search consent requested",
                   consent_token=consent_token,
                   user_id=request.user_id,
                   audit_id=audit_id,
                   estimated_cost=estimated_cost)
        
        return ConsentResponse(
            consent_token=consent_token,
            consent_level=consent_level,
            expires_at=datetime.now() + timedelta(minutes=self.consent_timeout_minutes),
            estimated_cost=estimated_cost,
            budget_remaining=budget_remaining,
            audit_id=audit_id,
            compliance_notes=compliance_notes,
            requires_double_confirmation=requires_double_confirmation,
            admin_approval_required=admin_approval_required
        )
    
    async def confirm_consent(self, request: DoubleConfirmationRequest) -> ConsentStatus:
        """Process double confirmation"""
        
        # Retrieve consent data
        consent_data_str = await self.cache.get(f"consent:{request.consent_token}")
        if not consent_data_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent token not found or expired"
            )
        
        consent_data = json.loads(consent_data_str)
        
        # Validate confirmation
        if not request.understood_costs or not request.understood_scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must understand both costs and scope to proceed"
            )
        
        # Update consent data
        consent_data["consent_level"] = ConsentLevel.DOUBLE_CONFIRMED.value
        consent_data["status"] = "confirmed"
        consent_data["confirmed_at"] = datetime.now().isoformat()
        consent_data["confirmation_text"] = request.confirmation_text
        
        # Save updated consent
        await self.cache.set(
            f"consent:{request.consent_token}",
            json.dumps(consent_data),
            ttl=self.consent_timeout_minutes * 60
        )
        
        # Log confirmation
        await self._log_consent_event(consent_data["audit_id"], "consent_confirmed", {
            "confirmation_text": request.confirmation_text,
            "understood_costs": request.understood_costs,
            "understood_scope": request.understood_scope
        })
        
        logger.info("Web search consent confirmed",
                   consent_token=request.consent_token,
                   user_id=consent_data["user_id"])
        
        return await self._get_consent_status(request.consent_token, consent_data)
    
    async def get_consent_status(self, consent_token: str) -> ConsentStatus:
        """Get current consent status"""
        
        consent_data_str = await self.cache.get(f"consent:{consent_token}")
        if not consent_data_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent token not found or expired"
            )
        
        consent_data = json.loads(consent_data_str)
        return await self._get_consent_status(consent_token, consent_data)
    
    async def _get_consent_status(self, consent_token: str, consent_data: dict) -> ConsentStatus:
        """Build consent status response"""
        
        expires_at = datetime.fromisoformat(consent_data["expires_at"])
        now = datetime.now()
        time_remaining = max(0, int((expires_at - now).total_seconds()))
        is_valid = time_remaining > 0 and consent_data["status"] in ["active", "confirmed"]
        
        # Get current budget usage
        daily_budget_used = await self._get_daily_budget_used(consent_data["user_id"])
        budget_remaining = self.enterprise_controls["max_daily_budget_per_user"] - daily_budget_used
        
        return ConsentStatus(
            consent_token=consent_token,
            status=consent_data["status"],
            consent_level=ConsentLevel(consent_data["consent_level"]),
            is_valid=is_valid,
            expires_at=expires_at,
            time_remaining_seconds=time_remaining,
            searches_used=consent_data["searches_used"],
            budget_used=consent_data["budget_used"],
            budget_remaining=budget_remaining
        )
    
    def _estimate_search_cost(self, mode: WebSearchMode, query: str) -> float:
        """Estimate search cost based on mode and query complexity"""
        
        base_costs = {
            WebSearchMode.RESEARCH: 1.0,
            WebSearchMode.DEEP_DIVE: 2.5
        }
        
        base_cost = base_costs[mode]
        
        # Adjust for query complexity
        if len(query.split()) > 10:
            base_cost *= 1.2
        if any(term in query.lower() for term in ["complex", "detailed", "comprehensive"]):
            base_cost *= 1.3
            
        return round(base_cost, 2)
    
    async def _get_daily_budget_used(self, user_id: str) -> float:
        """Get daily budget used by user"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"daily_budget:{user_id}:{today}"
        
        budget_str = await self.cache.get(key)
        return float(budget_str) if budget_str else 0.0
    
    async def _log_consent_event(self, audit_id: str, event_type: str, data: dict):
        """Log consent event for audit trail"""
        
        event = {
            "audit_id": audit_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Store in cache (in production, this would go to a persistent audit log)
        log_key = f"audit_log:{audit_id}:{event_type}:{datetime.now().isoformat()}"
        await self.cache.set(log_key, json.dumps(event), ttl=86400 * 30)  # 30 days retention


# Global consent manager
_consent_manager = None

async def get_consent_manager(cache_manager = Depends(get_cache_manager)):
    """Get or create consent manager instance"""
    global _consent_manager
    if _consent_manager is None:
        _consent_manager = ConsentManager(cache_manager)
    return _consent_manager


@router.post("/request", response_model=ConsentResponse)
async def request_web_search_consent(
    request: ConsentRequest,
    http_request: Request,
    consent_manager: ConsentManager = Depends(get_consent_manager)
):
    """Request consent for web search"""
    
    client_ip = http_request.client.host
    
    try:
        response = await consent_manager.request_consent(request, client_ip)
        
        logger.info("Consent request processed",
                   user_id=request.user_id,
                   consent_token=response.consent_token,
                   estimated_cost=response.estimated_cost)
        
        return response
        
    except Exception as e:
        logger.error("Consent request failed", user_id=request.user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process consent request: {str(e)}"
        )


@router.post("/confirm", response_model=ConsentStatus)
async def confirm_web_search_consent(
    request: DoubleConfirmationRequest,
    consent_manager: ConsentManager = Depends(get_consent_manager)
):
    """Confirm web search consent (double confirmation)"""
    
    try:
        response = await consent_manager.confirm_consent(request)
        
        logger.info("Consent confirmed",
                   consent_token=request.consent_token)
        
        return response
        
    except Exception as e:
        logger.error("Consent confirmation failed", 
                    consent_token=request.consent_token, 
                    error=str(e))
        raise


@router.get("/status/{consent_token}", response_model=ConsentStatus)
async def get_consent_status(
    consent_token: str,
    consent_manager: ConsentManager = Depends(get_consent_manager)
):
    """Get current consent status"""
    
    try:
        response = await consent_manager.get_consent_status(consent_token)
        return response
        
    except Exception as e:
        logger.error("Failed to get consent status", 
                    consent_token=consent_token, 
                    error=str(e))
        raise


@router.get("/user/{user_id}/status")
async def get_user_consent_summary(
    user_id: str,
    consent_manager: ConsentManager = Depends(get_consent_manager)
):
    """Get user's consent summary and budget status"""
    
    try:
        daily_budget_used = await consent_manager._get_daily_budget_used(user_id)
        budget_remaining = consent_manager.enterprise_controls["max_daily_budget_per_user"] - daily_budget_used
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "user_id": user_id,
                    "daily_budget_used": daily_budget_used,
                    "budget_remaining": budget_remaining,
                    "max_daily_budget": consent_manager.enterprise_controls["max_daily_budget_per_user"],
                    "enterprise_controls": consent_manager.enterprise_controls
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to get user consent summary", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user consent summary: {str(e)}"
        )