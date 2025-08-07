"""
Web Search Billing Isolation API

Provides complete billing separation for web search functionality:
- Cost center allocation and tracking
- Real-time budget monitoring and enforcement
- Detailed cost breakdowns by provider and service
- Enterprise billing reports and analytics
- API cost isolation from document search
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.dependencies import get_cache_manager

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["Web Search Billing"])


class BillingPeriod(Enum):
    """Billing period options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class CostComponent(Enum):
    """Web search cost components"""
    BRAVE_SEARCH = "brave_search"
    SCRAPINGBEE = "scrapingbee"
    CONTENT_ENHANCEMENT = "content_enhancement"
    FACT_VERIFICATION = "fact_verification"
    QUALITY_ASSURANCE = "quality_assurance"


class BillingRecord(BaseModel):
    """Individual billing record for a web search"""
    
    # Request identification
    request_id: str = Field(description="Unique request ID")
    consent_token: str = Field(description="Associated consent token")
    audit_id: str = Field(description="Audit trail ID")
    
    # User and account information
    user_id: str = Field(description="User who initiated the search")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    cost_center: Optional[str] = Field(default=None, description="Cost center")
    enterprise_account: bool = Field(default=False, description="Is enterprise account")
    
    # Search details
    search_query: str = Field(description="Search query")
    search_mode: str = Field(description="Search mode used")
    timestamp: datetime = Field(description="When the search was executed")
    
    # Cost breakdown
    total_cost: float = Field(description="Total cost for this search")
    cost_breakdown: Dict[str, float] = Field(description="Cost breakdown by component")
    
    # Performance metrics
    search_time_ms: float = Field(description="Search execution time")
    results_count: int = Field(description="Number of results returned")
    quality_score: float = Field(description="Quality score (0-1)")
    
    # Provider usage
    providers_used: List[str] = Field(description="List of providers used")
    primary_provider: str = Field(description="Primary provider")
    enhancement_used: bool = Field(default=False, description="Content enhancement used")


class BudgetAlert(BaseModel):
    """Budget alert configuration and status"""
    
    alert_id: str = Field(description="Alert ID")
    user_id: str = Field(description="User ID")
    cost_center: Optional[str] = Field(default=None, description="Cost center")
    
    # Thresholds
    budget_limit: float = Field(description="Budget limit")
    warning_threshold: float = Field(description="Warning threshold (percentage)")
    critical_threshold: float = Field(description="Critical threshold (percentage)")
    
    # Current status
    current_spend: float = Field(description="Current spend in period")
    remaining_budget: float = Field(description="Remaining budget")
    percentage_used: float = Field(description="Percentage of budget used")
    
    # Alert status
    warning_triggered: bool = Field(default=False, description="Warning alert triggered")
    critical_triggered: bool = Field(default=False, description="Critical alert triggered")
    budget_exceeded: bool = Field(default=False, description="Budget exceeded")
    
    # Timing
    period_start: datetime = Field(description="Budget period start")
    period_end: datetime = Field(description="Budget period end")
    last_updated: datetime = Field(description="Last update timestamp")


class BillingReport(BaseModel):
    """Comprehensive billing report"""
    
    # Report metadata
    report_id: str = Field(description="Report ID")
    period: BillingPeriod = Field(description="Billing period")
    start_date: datetime = Field(description="Report start date")
    end_date: datetime = Field(description="Report end date")
    generated_at: datetime = Field(description="When report was generated")
    
    # Summary statistics
    total_searches: int = Field(description="Total number of searches")
    total_cost: float = Field(description="Total cost for period")
    average_cost_per_search: float = Field(description="Average cost per search")
    
    # Cost breakdown
    cost_by_component: Dict[str, float] = Field(description="Cost breakdown by component")
    cost_by_provider: Dict[str, float] = Field(description="Cost breakdown by provider")
    cost_by_user: Dict[str, float] = Field(description="Cost breakdown by user")
    cost_by_cost_center: Dict[str, float] = Field(description="Cost breakdown by cost center")
    
    # Usage patterns
    searches_by_mode: Dict[str, int] = Field(description="Searches by mode")
    searches_by_hour: Dict[str, int] = Field(description="Searches by hour of day")
    searches_by_day: Dict[str, int] = Field(description="Searches by day")
    
    # Quality metrics
    average_quality_score: float = Field(description="Average quality score")
    average_response_time: float = Field(description="Average response time")
    success_rate: float = Field(description="Success rate percentage")
    
    # Top consumers
    top_users_by_cost: List[Dict[str, Any]] = Field(description="Top users by cost")
    top_cost_centers_by_cost: List[Dict[str, Any]] = Field(description="Top cost centers by cost")
    
    # Billing records (summary)
    total_records: int = Field(description="Total billing records in period")
    sample_records: List[BillingRecord] = Field(description="Sample billing records")


class WebSearchBillingManager:
    """Manages web search billing isolation and cost tracking"""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
        
        # Default cost configuration (₹ Indian Rupees)
        self.cost_config = {
            CostComponent.BRAVE_SEARCH.value: {
                "per_request": 0.50,
                "per_result": 0.05
            },
            CostComponent.SCRAPINGBEE.value: {
                "per_request": 1.20,
                "per_page": 0.30
            },
            CostComponent.CONTENT_ENHANCEMENT.value: {
                "per_request": 0.25,
                "per_kb": 0.02
            },
            CostComponent.FACT_VERIFICATION.value: {
                "per_request": 0.40,
                "per_fact": 0.10
            },
            CostComponent.QUALITY_ASSURANCE.value: {
                "per_request": 0.15,
                "per_check": 0.05
            }
        }
        
        # Budget defaults
        self.default_daily_budget = 25.0
        self.default_warning_threshold = 80.0  # 80%
        self.default_critical_threshold = 95.0  # 95%
    
    async def record_billing(self, billing_record: BillingRecord) -> bool:
        """Record a billing transaction"""
        
        try:
            # Store individual billing record
            record_key = f"billing_record:{billing_record.request_id}"
            await self.cache.set(
                record_key,
                json.dumps(billing_record.dict()),
                ttl=86400 * 90  # 90 days retention
            )
            
            # Update user daily spending
            today = datetime.now().strftime("%Y-%m-%d")
            daily_key = f"daily_spend:{billing_record.user_id}:{today}"
            
            current_spend = await self.cache.get(daily_key)
            current_spend = float(current_spend) if current_spend else 0.0
            new_spend = current_spend + billing_record.total_cost
            
            await self.cache.set(daily_key, str(new_spend), ttl=86400 * 7)  # 7 days
            
            # Update cost center spending if applicable
            if billing_record.cost_center:
                cc_key = f"cost_center_spend:{billing_record.cost_center}:{today}"
                cc_current = await self.cache.get(cc_key)
                cc_current = float(cc_current) if cc_current else 0.0
                cc_new = cc_current + billing_record.total_cost
                await self.cache.set(cc_key, str(cc_new), ttl=86400 * 7)
            
            # Update component spending
            for component, cost in billing_record.cost_breakdown.items():
                comp_key = f"component_spend:{component}:{today}"
                comp_current = await self.cache.get(comp_key)
                comp_current = float(comp_current) if comp_current else 0.0
                comp_new = comp_current + cost
                await self.cache.set(comp_key, str(comp_new), ttl=86400 * 7)
            
            # Check for budget alerts
            await self._check_budget_alerts(billing_record.user_id, new_spend)
            
            logger.info("Billing record created",
                       request_id=billing_record.request_id,
                       user_id=billing_record.user_id,
                       cost=billing_record.total_cost,
                       cost_center=billing_record.cost_center)
            
            return True
            
        except Exception as e:
            logger.error("Failed to record billing", 
                        request_id=billing_record.request_id, 
                        error=str(e))
            return False
    
    async def get_user_spending(self, user_id: str, period: BillingPeriod = BillingPeriod.DAILY) -> Dict[str, Any]:
        """Get user spending for specified period"""
        
        now = datetime.now()
        
        if period == BillingPeriod.DAILY:
            date_key = now.strftime("%Y-%m-%d")
            spend_key = f"daily_spend:{user_id}:{date_key}"
        elif period == BillingPeriod.WEEKLY:
            # Get week start (Monday)
            week_start = now - timedelta(days=now.weekday())
            date_key = week_start.strftime("%Y-W%U")
            spend_key = f"weekly_spend:{user_id}:{date_key}"
        elif period == BillingPeriod.MONTHLY:
            date_key = now.strftime("%Y-%m")
            spend_key = f"monthly_spend:{user_id}:{date_key}"
        else:  # QUARTERLY
            quarter = (now.month - 1) // 3 + 1
            date_key = f"{now.year}-Q{quarter}"
            spend_key = f"quarterly_spend:{user_id}:{date_key}"
        
        current_spend = await self.cache.get(spend_key)
        current_spend = float(current_spend) if current_spend else 0.0
        
        return {
            "user_id": user_id,
            "period": period.value,
            "period_key": date_key,
            "current_spend": current_spend,
            "budget_limit": self.default_daily_budget,
            "remaining_budget": max(0, self.default_daily_budget - current_spend),
            "percentage_used": min(100, (current_spend / self.default_daily_budget) * 100),
            "last_updated": now.isoformat()
        }
    
    async def get_budget_alert(self, user_id: str) -> BudgetAlert:
        """Get current budget alert status for user"""
        
        spending_info = await self.get_user_spending(user_id, BillingPeriod.DAILY)
        
        warning_threshold = self.default_warning_threshold
        critical_threshold = self.default_critical_threshold
        
        percentage_used = spending_info["percentage_used"]
        warning_triggered = percentage_used >= warning_threshold
        critical_triggered = percentage_used >= critical_threshold
        budget_exceeded = spending_info["current_spend"] > self.default_daily_budget
        
        today = datetime.now()
        period_start = datetime.combine(today.date(), datetime.min.time())
        period_end = datetime.combine(today.date(), datetime.max.time())
        
        return BudgetAlert(
            alert_id=f"alert_{user_id}_{today.strftime('%Y%m%d')}",
            user_id=user_id,
            budget_limit=self.default_daily_budget,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            current_spend=spending_info["current_spend"],
            remaining_budget=spending_info["remaining_budget"],
            percentage_used=percentage_used,
            warning_triggered=warning_triggered,
            critical_triggered=critical_triggered,
            budget_exceeded=budget_exceeded,
            period_start=period_start,
            period_end=period_end,
            last_updated=today
        )
    
    async def _check_budget_alerts(self, user_id: str, current_spend: float):
        """Check and trigger budget alerts if needed"""
        
        percentage_used = (current_spend / self.default_daily_budget) * 100
        
        if percentage_used >= self.default_critical_threshold:
            logger.warning("Critical budget threshold exceeded",
                          user_id=user_id,
                          current_spend=current_spend,
                          percentage_used=percentage_used)
            # In production, this would trigger alerts/notifications
        elif percentage_used >= self.default_warning_threshold:
            logger.info("Budget warning threshold exceeded",
                       user_id=user_id,
                       current_spend=current_spend,
                       percentage_used=percentage_used)
    
    def calculate_search_cost(self, providers_used: List[str], results_count: int, 
                            pages_scraped: int = 0, content_size_kb: float = 0) -> Dict[str, float]:
        """Calculate cost breakdown for a search"""
        
        cost_breakdown = {}
        
        if "brave" in providers_used:
            brave_cost = (
                self.cost_config[CostComponent.BRAVE_SEARCH.value]["per_request"] +
                (results_count * self.cost_config[CostComponent.BRAVE_SEARCH.value]["per_result"])
            )
            cost_breakdown[CostComponent.BRAVE_SEARCH.value] = brave_cost
        
        if "scrapingbee" in providers_used:
            scrapingbee_cost = (
                self.cost_config[CostComponent.SCRAPINGBEE.value]["per_request"] +
                (pages_scraped * self.cost_config[CostComponent.SCRAPINGBEE.value]["per_page"])
            )
            cost_breakdown[CostComponent.SCRAPINGBEE.value] = scrapingbee_cost
        
        if content_size_kb > 0:
            enhancement_cost = (
                self.cost_config[CostComponent.CONTENT_ENHANCEMENT.value]["per_request"] +
                (content_size_kb * self.cost_config[CostComponent.CONTENT_ENHANCEMENT.value]["per_kb"])
            )
            cost_breakdown[CostComponent.CONTENT_ENHANCEMENT.value] = enhancement_cost
        
        # Quality assurance is always applied
        qa_cost = self.cost_config[CostComponent.QUALITY_ASSURANCE.value]["per_request"]
        cost_breakdown[CostComponent.QUALITY_ASSURANCE.value] = qa_cost
        
        return cost_breakdown


# Global billing manager
_billing_manager = None

async def get_billing_manager(cache_manager = Depends(get_cache_manager)):
    """Get or create billing manager instance"""
    global _billing_manager
    if _billing_manager is None:
        _billing_manager = WebSearchBillingManager(cache_manager)
    return _billing_manager


@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_billing_transaction(
    billing_record: BillingRecord,
    billing_manager: WebSearchBillingManager = Depends(get_billing_manager)
):
    """Record a web search billing transaction"""
    
    try:
        success = await billing_manager.record_billing(billing_record)
        
        if success:
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "success": True,
                    "message": "Billing record created successfully",
                    "request_id": billing_record.request_id,
                    "total_cost": billing_record.total_cost,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record billing transaction"
            )
            
    except Exception as e:
        logger.error("Billing record creation failed", 
                    request_id=billing_record.request_id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record billing: {str(e)}"
        )


@router.get("/user/{user_id}/spending")
async def get_user_spending_summary(
    user_id: str,
    period: BillingPeriod = Query(default=BillingPeriod.DAILY, description="Billing period"),
    billing_manager: WebSearchBillingManager = Depends(get_billing_manager)
):
    """Get user's spending summary for specified period"""
    
    try:
        spending_info = await billing_manager.get_user_spending(user_id, period)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": spending_info,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to get user spending", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user spending: {str(e)}"
        )


@router.get("/user/{user_id}/budget-alert", response_model=BudgetAlert)
async def get_user_budget_alert(
    user_id: str,
    billing_manager: WebSearchBillingManager = Depends(get_billing_manager)
):
    """Get user's current budget alert status"""
    
    try:
        alert = await billing_manager.get_budget_alert(user_id)
        return alert
        
    except Exception as e:
        logger.error("Failed to get budget alert", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get budget alert: {str(e)}"
        )


@router.get("/cost-calculator")
async def calculate_search_cost(
    providers: str = Query(description="Comma-separated list of providers (brave,scrapingbee)"),
    results_count: int = Query(default=10, description="Number of results expected"),
    pages_scraped: int = Query(default=0, description="Number of pages to scrape"),
    content_size_kb: float = Query(default=0, description="Expected content size in KB"),
    billing_manager: WebSearchBillingManager = Depends(get_billing_manager)
):
    """Calculate estimated cost for a web search"""
    
    try:
        providers_list = [p.strip() for p in providers.split(",")]
        cost_breakdown = billing_manager.calculate_search_cost(
            providers_list, results_count, pages_scraped, content_size_kb
        )
        
        total_cost = sum(cost_breakdown.values())
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "providers_used": providers_list,
                    "results_count": results_count,
                    "pages_scraped": pages_scraped,
                    "content_size_kb": content_size_kb,
                    "cost_breakdown": cost_breakdown,
                    "total_estimated_cost": round(total_cost, 2),
                    "currency": "INR"
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Cost calculation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate cost: {str(e)}"
        )