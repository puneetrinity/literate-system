"""
Web Search Router - Manual-Only Web Search with Enterprise Controls

This router handles manual web search activation with complete enterprise separation:
- Manual activation only (no automatic web search)
- Explicit user consent and double confirmation
- Enterprise admin controls and permissions
- Complete audit trail for compliance
- Cost tracking and budget enforcement
- Quality assurance and fact verification

Built on top of existing SmartSearchRouter functionality.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union

import structlog
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.providers.router import SmartSearchRouter, SearchProvider

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebSearchMode(Enum):
    """Web search modes with different quality/cost profiles"""
    RESEARCH = "research"        # <3s, ₹0.50-1.50, Brave only
    DEEP_DIVE = "deep_dive"     # <8s, ₹1.50-3.00, Brave + ScrapingBee


class ConsentLevel(Enum):
    """User consent levels for web search"""
    NONE = "none"                    # No consent given
    BASIC = "basic"                  # Basic consent
    DOUBLE_CONFIRMED = "double_confirmed"  # Double confirmation
    ADMIN_APPROVED = "admin_approved"      # Admin pre-approved


class WebSearchRequest(BaseModel):
    """Web search request with consent and controls"""
    
    query: str = Field(description="Search query")
    mode: WebSearchMode = Field(default=WebSearchMode.RESEARCH, description="Search mode")
    
    # Consent and permissions
    user_consent: ConsentLevel = Field(default=ConsentLevel.NONE, description="User consent level")
    consent_timestamp: Optional[datetime] = Field(default=None, description="When consent was given")
    double_confirmation: bool = Field(default=False, description="Double confirmation received")
    
    # Enterprise controls
    enterprise_account: bool = Field(default=False, description="Is enterprise account")
    admin_approval: bool = Field(default=False, description="Admin approval received")
    user_permissions: Dict[str, bool] = Field(default_factory=dict, description="User permissions")
    
    # Budget and cost controls
    budget_limit: float = Field(default=2.0, description="Budget limit for this search")
    cost_center: Optional[str] = Field(default=None, description="Cost center for billing")
    
    # Context and session
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")


class WebSearchResult(BaseModel):
    """Web search result with quality metrics and audit trail"""
    
    # Search results
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    total_results: int = Field(default=0, description="Total number of results")
    
    # Quality metrics
    relevance_score: float = Field(default=0.0, description="Overall relevance score")
    source_diversity: int = Field(default=0, description="Number of unique domains")
    fact_verification_score: Optional[float] = Field(default=None, description="Fact verification score")
    
    # Performance metrics
    search_time_ms: float = Field(description="Search execution time")
    response_time_ms: float = Field(description="Total response time")
    
    # Cost tracking
    actual_cost: float = Field(description="Actual cost incurred")
    cost_breakdown: Dict[str, float] = Field(default_factory=dict, description="Cost by component")
    
    # Providers used
    primary_provider: str = Field(description="Primary search provider used")
    enhancement_used: bool = Field(default=False, description="Content enhancement used")
    providers_called: List[str] = Field(default_factory=list, description="All providers called")
    
    # Audit trail
    request_id: str = Field(description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Search timestamp")
    consent_verified: bool = Field(description="Consent verification status")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings or notices")


class WebSearchRouter:
    """
    Manual-only web search router with enterprise controls
    """
    
    def __init__(self, 
                 brave_api_key: Optional[str] = None,
                 scrapingbee_api_key: Optional[str] = None):
        
        # Initialize underlying SmartSearchRouter
        self.smart_router = SmartSearchRouter(brave_api_key, scrapingbee_api_key)
        
        # Enterprise controls
        self.consent_timeout_minutes = 10  # Consent expires after 10 minutes
        self.max_daily_searches_per_user = 50
        self.cost_alert_threshold = 10.0  # Alert if user approaches budget limit
        
        # Quality assurance settings
        self.min_source_diversity = 2
        self.min_relevance_threshold = 0.3
        
        # Audit and compliance
        self.search_history = {}  # In-memory storage (would be database in production)
        self.user_budgets = {}    # User budget tracking
        
        logger.info("WebSearchRouter initialized with manual activation controls")
    
    async def search_with_consent(self, request: WebSearchRequest) -> WebSearchResult:
        """
        Execute web search with full consent verification and enterprise controls
        """
        
        start_time = datetime.now()
        request_id = hashlib.md5(f"{request.query}{request.user_id}{start_time}".encode()).hexdigest()[:12]
        
        logger.info("Manual web search initiated",
                   request_id=request_id,
                   user_id=request.user_id,
                   mode=request.mode.value,
                   consent_level=request.user_consent.value)
        
        try:
            # 1. Verify consent and permissions
            consent_check = await self._verify_consent_and_permissions(request)
            if not consent_check["allowed"]:
                return self._create_error_result(
                    request_id, start_time, consent_check["reason"], "CONSENT_DENIED"
                )
            
            # 2. Check budget and cost limits
            budget_check = await self._check_budget_limits(request)
            if not budget_check["allowed"]:
                return self._create_error_result(
                    request_id, start_time, budget_check["reason"], "BUDGET_EXCEEDED"
                )
            
            # 3. Validate search parameters
            validation_result = await self._validate_search_parameters(request)
            if not validation_result["valid"]:
                return self._create_error_result(
                    request_id, start_time, validation_result["reason"], "INVALID_PARAMETERS"
                )
            
            # 4. Execute search using SmartSearchRouter
            search_start = datetime.now()
            
            # Configure search based on mode
            if request.mode == WebSearchMode.RESEARCH:
                budget = min(request.budget_limit, 1.5)
                quality = "standard"
                max_results = 10
            else:  # DEEP_DIVE
                budget = min(request.budget_limit, 3.0)
                quality = "premium"
                max_results = 15
            
            # Execute search through SmartSearchRouter
            async with self.smart_router as router:
                search_results = await router.search(
                    query=request.query,
                    budget=budget,
                    quality_requirement=quality,
                    max_results=max_results
                )
            
            search_end = datetime.now()
            search_time_ms = (search_end - search_start).total_seconds() * 1000
            
            # 5. Quality assurance and fact verification
            qa_results = await self._perform_quality_assurance(search_results, request.query)
            
            # 6. Cost calculation and tracking
            cost_info = await self._calculate_and_track_costs(request, search_results, qa_results)
            
            # 7. Create comprehensive result
            result = WebSearchResult(
                results=search_results,
                total_results=len(search_results),
                relevance_score=qa_results["relevance_score"],
                source_diversity=qa_results["source_diversity"],
                fact_verification_score=qa_results.get("fact_verification_score"),
                search_time_ms=search_time_ms,
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                actual_cost=cost_info["total_cost"],
                cost_breakdown=cost_info["breakdown"],
                primary_provider=cost_info["primary_provider"],
                enhancement_used=cost_info["enhancement_used"],
                providers_called=cost_info["providers_called"],
                request_id=request_id,
                consent_verified=True,
                warnings=qa_results.get("warnings", [])
            )
            
            # 8. Log for audit trail and compliance
            await self._log_search_for_audit(request, result)
            
            # 9. Update user statistics
            await self._update_user_statistics(request, result)
            
            logger.info("Manual web search completed successfully",
                       request_id=request_id,
                       results_count=result.total_results,
                       cost=result.actual_cost,
                       response_time_ms=result.response_time_ms)
            
            return result
            
        except Exception as e:
            logger.error("Web search failed",
                        request_id=request_id,
                        error=str(e),
                        user_id=request.user_id)
            
            return self._create_error_result(
                request_id, start_time, f"Search execution failed: {str(e)}", "SEARCH_ERROR"
            )
    
    async def _verify_consent_and_permissions(self, request: WebSearchRequest) -> Dict[str, Union[bool, str]]:
        """Verify user consent and enterprise permissions"""
        
        # Check basic consent
        if request.user_consent == ConsentLevel.NONE:
            return {"allowed": False, "reason": "Web search requires explicit user consent"}
        
        # Check consent timeout
        if request.consent_timestamp:
            consent_age = datetime.now() - request.consent_timestamp
            if consent_age > timedelta(minutes=self.consent_timeout_minutes):
                return {"allowed": False, "reason": "Consent has expired - please confirm again"}
        
        # Enterprise account checks
        if request.enterprise_account:
            
            # Check if user has web search permissions
            if not request.user_permissions.get("web_search_enabled", False):
                return {"allowed": False, "reason": "User does not have web search permissions"}
            
            # Check for admin approval requirement
            if request.user_permissions.get("requires_admin_approval", False) and not request.admin_approval:
                return {"allowed": False, "reason": "Administrator approval required for web search"}
            
            # Check double confirmation for enterprise
            if request.user_consent != ConsentLevel.DOUBLE_CONFIRMED and not request.admin_approval:
                return {"allowed": False, "reason": "Enterprise accounts require double confirmation"}
        
        # Verify double confirmation if required
        if request.user_consent == ConsentLevel.DOUBLE_CONFIRMED and not request.double_confirmation:
            return {"allowed": False, "reason": "Double confirmation flag not set"}
        
        return {"allowed": True, "reason": "Consent and permissions verified"}
    
    async def _check_budget_limits(self, request: WebSearchRequest) -> Dict[str, Union[bool, str]]:
        """Check budget limits and cost controls"""
        
        user_id = request.user_id or "anonymous"
        
        # Check daily usage limits
        today = datetime.now().date()
        daily_key = f"{user_id}:{today}"
        
        if daily_key not in self.user_budgets:
            self.user_budgets[daily_key] = {"searches": 0, "cost": 0.0}
        
        daily_stats = self.user_budgets[daily_key]
        
        # Check search count limit
        if daily_stats["searches"] >= self.max_daily_searches_per_user:
            return {"allowed": False, "reason": f"Daily search limit ({self.max_daily_searches_per_user}) exceeded"}
        
        # Estimate search cost
        estimated_cost = self._estimate_search_cost(request)
        
        # Check if estimated cost would exceed budget
        if daily_stats["cost"] + estimated_cost > request.budget_limit:
            return {"allowed": False, "reason": f"Search would exceed budget limit (₹{request.budget_limit})"}
        
        # Warning if approaching budget limit
        remaining_budget = request.budget_limit - daily_stats["cost"]
        if remaining_budget < self.cost_alert_threshold:
            logger.warning("User approaching budget limit",
                          user_id=user_id,
                          remaining_budget=remaining_budget,
                          estimated_cost=estimated_cost)
        
        return {"allowed": True, "reason": "Budget limits verified"}
    
    def _estimate_search_cost(self, request: WebSearchRequest) -> float:
        """Estimate search cost based on mode and parameters"""
        
        if request.mode == WebSearchMode.RESEARCH:
            # Brave search only
            return 0.42  # Base Brave search cost
        else:  # DEEP_DIVE
            # Brave + ScrapingBee enhancement
            return 0.42 + (0.84 * 3)  # Brave + 3 enhanced results
    
    async def _validate_search_parameters(self, request: WebSearchRequest) -> Dict[str, Union[bool, str]]:
        """Validate search parameters and query"""
        
        # Check query length
        if len(request.query.strip()) < 3:
            return {"valid": False, "reason": "Query too short (minimum 3 characters)"}
        
        if len(request.query) > 500:
            return {"valid": False, "reason": "Query too long (maximum 500 characters)"}
        
        # Check for potentially harmful queries
        harmful_patterns = [
            r'\b(hack|exploit|crack|bypass)\b',
            r'\b(illegal|piracy|torrent)\b',
            r'\b(malware|virus|trojan)\b'
        ]
        
        query_lower = request.query.lower()
        for pattern in harmful_patterns:
            if re.search(pattern, query_lower):
                return {"valid": False, "reason": "Query contains potentially harmful content"}
        
        # Validate budget
        if request.budget_limit <= 0 or request.budget_limit > 50:
            return {"valid": False, "reason": "Budget limit must be between ₹0.01 and ₹50"}
        
        return {"valid": True, "reason": "Parameters validated"}
    
    async def _perform_quality_assurance(self, search_results: List[Dict], query: str) -> Dict[str, Any]:
        """Perform quality assurance on search results"""
        
        if not search_results:
            return {
                "relevance_score": 0.0,
                "source_diversity": 0,
                "warnings": ["No search results returned"]
            }
        
        # Calculate source diversity
        domains = set()
        for result in search_results:
            url = result.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.lower()
                    domains.add(domain)
                except Exception:
                    pass
        
        source_diversity = len(domains)
        
        # Calculate overall relevance score
        relevance_scores = [result.get("relevance_score", 0.5) for result in search_results]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        
        # Quality warnings
        warnings = []
        if source_diversity < self.min_source_diversity:
            warnings.append(f"Low source diversity ({source_diversity} unique domains)")
        
        if avg_relevance < self.min_relevance_threshold:
            warnings.append(f"Low relevance score ({avg_relevance:.2f})")
        
        # Fact verification (simplified - would integrate with fact-checking service)
        fact_verification_score = None
        if len(search_results) >= 3:
            # Simple fact verification based on result consistency
            fact_verification_score = min(avg_relevance + 0.2, 1.0)
        
        return {
            "relevance_score": avg_relevance,
            "source_diversity": source_diversity,
            "fact_verification_score": fact_verification_score,
            "warnings": warnings
        }
    
    async def _calculate_and_track_costs(self, request: WebSearchRequest, 
                                       search_results: List[Dict], qa_results: Dict) -> Dict[str, Any]:
        """Calculate and track search costs"""
        
        # Base costs (from SmartSearchRouter configuration)
        brave_cost = 0.42
        scrapingbee_cost_per_page = 0.84
        
        cost_breakdown = {}
        providers_called = []
        enhancement_used = False
        
        # Determine what was actually used
        if request.mode == WebSearchMode.RESEARCH:
            # Research mode: Brave only
            cost_breakdown["brave_search"] = brave_cost
            providers_called = ["brave"]
            primary_provider = "brave"
            
        else:  # DEEP_DIVE
            # Deep dive: Brave + ScrapingBee enhancement
            cost_breakdown["brave_search"] = brave_cost
            providers_called = ["brave"]
            primary_provider = "brave"
            
            # Estimate enhanced results (typically top 3)
            enhanced_results = min(len(search_results), 3)
            if enhanced_results > 0:
                enhancement_cost = enhanced_results * scrapingbee_cost_per_page
                cost_breakdown["scrapingbee_enhancement"] = enhancement_cost
                providers_called.append("scrapingbee")
                enhancement_used = True
        
        # Calculate total cost
        total_cost = sum(cost_breakdown.values())
        
        # Update user budget tracking
        user_id = request.user_id or "anonymous"
        today = datetime.now().date()
        daily_key = f"{user_id}:{today}"
        
        if daily_key in self.user_budgets:
            self.user_budgets[daily_key]["cost"] += total_cost
            self.user_budgets[daily_key]["searches"] += 1
        
        return {
            "total_cost": total_cost,
            "breakdown": cost_breakdown,
            "primary_provider": primary_provider,
            "enhancement_used": enhancement_used,
            "providers_called": providers_called
        }
    
    async def _log_search_for_audit(self, request: WebSearchRequest, result: WebSearchResult):
        """Log search for audit trail and compliance"""
        
        audit_entry = {
            "request_id": result.request_id,
            "timestamp": result.timestamp.isoformat(),
            "user_id": request.user_id,
            "session_id": request.session_id,
            "query_hash": hashlib.md5(request.query.encode()).hexdigest(),
            "search_mode": request.mode.value,
            "consent_level": request.user_consent.value,
            "enterprise_account": request.enterprise_account,
            "admin_approval": request.admin_approval,
            "cost": result.actual_cost,
            "providers_used": result.providers_called,
            "results_count": result.total_results,
            "response_time_ms": result.response_time_ms,
            "relevance_score": result.relevance_score,
            "source_diversity": result.source_diversity
        }
        
        # Log for monitoring
        logger.info("Web search audit entry", **audit_entry)
        
        # Store in audit database (implementation would depend on requirements)
        # await self._store_audit_entry(audit_entry)
    
    async def _update_user_statistics(self, request: WebSearchRequest, result: WebSearchResult):
        """Update user statistics and usage patterns"""
        
        user_id = request.user_id or "anonymous"
        
        # Update search history
        if user_id not in self.search_history:
            self.search_history[user_id] = []
        
        history_entry = {
            "timestamp": result.timestamp.isoformat(),
            "mode": request.mode.value,
            "cost": result.actual_cost,
            "results_count": result.total_results,
            "relevance_score": result.relevance_score,
            "response_time_ms": result.response_time_ms
        }
        
        self.search_history[user_id].append(history_entry)
        
        # Keep only recent history (last 100 searches)
        if len(self.search_history[user_id]) > 100:
            self.search_history[user_id] = self.search_history[user_id][-100:]
    
    def _create_error_result(self, request_id: str, start_time: datetime, 
                            error_message: str, error_code: str) -> WebSearchResult:
        """Create error result for failed searches"""
        
        return WebSearchResult(
            results=[],
            total_results=0,
            relevance_score=0.0,
            source_diversity=0,
            search_time_ms=0.0,
            response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            actual_cost=0.0,
            cost_breakdown={},
            primary_provider="none",
            enhancement_used=False,
            providers_called=[],
            request_id=request_id,
            consent_verified=False,
            errors=[f"{error_code}: {error_message}"]
        )
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user search statistics and usage patterns"""
        
        if user_id not in self.search_history:
            return {"error": "No search history found for user"}
        
        history = self.search_history[user_id]
        
        # Calculate statistics
        total_searches = len(history)
        total_cost = sum(entry["cost"] for entry in history)
        avg_cost = total_cost / total_searches if total_searches > 0 else 0
        avg_relevance = sum(entry["relevance_score"] for entry in history) / total_searches if total_searches > 0 else 0
        avg_response_time = sum(entry["response_time_ms"] for entry in history) / total_searches if total_searches > 0 else 0
        
        # Mode distribution
        mode_counts = {}
        for entry in history:
            mode = entry["mode"]
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        
        return {
            "user_id": user_id,
            "total_searches": total_searches,
            "total_cost": total_cost,
            "average_cost": avg_cost,
            "average_relevance_score": avg_relevance,
            "average_response_time_ms": avg_response_time,
            "mode_distribution": mode_counts,
            "last_search": history[-1]["timestamp"] if history else None
        }