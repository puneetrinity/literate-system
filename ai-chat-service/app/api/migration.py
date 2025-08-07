"""
Migration API - Router Consolidation Management

This API provides endpoints for managing the migration from 8-router to 3-router
architecture, including monitoring, control, and analytics.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.dependencies import get_model_manager, get_cache_manager
from app.routers.feature_flags import (
    get_feature_flag_manager,
    RouterArchitecture,
    UserSegment,
    FeatureFlagState
)
from app.routers.migration_manager import create_router_migration_manager

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["Migration"])

# Global migration manager instance
_migration_manager = None

async def get_migration_manager():
    """Get or create migration manager instance"""
    global _migration_manager
    if _migration_manager is None:
        from app.main import app_state
        model_manager = app_state.get("model_manager")
        cache_manager = app_state.get("cache_manager")
        if model_manager and cache_manager:
            _migration_manager = await create_router_migration_manager(
                model_manager, cache_manager
            )
        else:
            # Fallback: get existing migration_manager from app_state
            _migration_manager = app_state.get("migration_manager")
    return _migration_manager


class MigrationTestRequest(BaseModel):
    """Request for testing migration routing"""
    
    query: str = Field(description="Test query")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="User context")
    force_architecture: Optional[RouterArchitecture] = Field(default=None, description="Force specific architecture")


class FeatureFlagUpdateRequest(BaseModel):
    """Request for updating feature flag"""
    
    flag_name: str = Field(description="Feature flag name")
    state: Optional[FeatureFlagState] = Field(default=None, description="New flag state")
    rollout_percentage: Optional[float] = Field(default=None, description="New rollout percentage")
    admin_override: Optional[bool] = Field(default=None, description="Admin override")
    admin_user: str = Field(description="Admin user making the change")


class UserOverrideRequest(BaseModel):
    """Request for setting user override"""
    
    user_id: str = Field(description="User ID")
    flag_name: str = Field(description="Feature flag name")
    enabled: bool = Field(description="Whether feature should be enabled for user")


@router.get("/status")
async def get_migration_status(
    migration_manager = Depends(get_migration_manager)
):
    """Get comprehensive migration status"""
    
    try:
        migration_status = migration_manager.get_migration_status()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": migration_status,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error("Failed to get migration status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/test-routing")
async def test_migration_routing(
    request: MigrationTestRequest,
    migration_manager = Depends(get_migration_manager)
):
    """Test routing through migration system"""
    
    try:
        # Override architecture if requested
        if request.force_architecture:
            feature_flags = get_feature_flag_manager()
            
            # Temporarily override for this test
            if request.force_architecture == RouterArchitecture.CONSOLIDATED_3_ROUTER:
                feature_flags.set_user_override(
                    request.user_id or "test_user", 
                    "router_consolidation", 
                    True
                )
            else:
                feature_flags.set_user_override(
                    request.user_id or "test_user", 
                    "router_consolidation", 
                    False
                )
        
        # Route the test request
        result = await migration_manager.route_request(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id,
            user_context=request.user_context
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "result": result.dict(),
                    "test_metadata": {
                        "forced_architecture": request.force_architecture.value if request.force_architecture else None,
                        "query": request.query,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
        )
    
    except Exception as e:
        logger.error("Migration routing test failed", 
                    query=request.query, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration routing test failed: {str(e)}"
        )


@router.get("/feature-flags")
async def get_feature_flags():
    """Get all feature flag statuses"""
    
    try:
        feature_flags = get_feature_flag_manager()
        flags_status = feature_flags.get_all_flags_status()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": flags_status,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error("Failed to get feature flags", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature flags: {str(e)}"
        )


@router.get("/feature-flags/{flag_name}")
async def get_feature_flag(flag_name: str):
    """Get specific feature flag status"""
    
    try:
        feature_flags = get_feature_flag_manager()
        flag_status = feature_flags.get_flag_status(flag_name)
        
        if not flag_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{flag_name}' not found"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": flag_status,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get feature flag", flag_name=flag_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature flag: {str(e)}"
        )


@router.post("/feature-flags/update")
async def update_feature_flag(request: FeatureFlagUpdateRequest):
    """Update feature flag configuration"""
    
    try:
        feature_flags = get_feature_flag_manager()
        
        # Check if flag exists
        if request.flag_name not in feature_flags.flags:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{request.flag_name}' not found"
            )
        
        flag = feature_flags.flags[request.flag_name]
        
        # Update flag properties
        changes_made = []
        
        if request.state is not None:
            flag.state = request.state
            changes_made.append(f"state -> {request.state.value}")
        
        if request.rollout_percentage is not None:
            if 0.0 <= request.rollout_percentage <= 100.0:
                flag.rollout_percentage = request.rollout_percentage
                changes_made.append(f"rollout_percentage -> {request.rollout_percentage}%")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rollout percentage must be between 0 and 100"
                )
        
        if request.admin_override is not None:
            success = feature_flags.set_admin_override(
                request.flag_name, 
                request.admin_override, 
                request.admin_user
            )
            if success:
                changes_made.append(f"admin_override -> {request.admin_override}")
        
        flag.updated_at = datetime.now()
        
        logger.info("Feature flag updated",
                   flag_name=request.flag_name,
                   admin_user=request.admin_user,
                   changes=changes_made)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "flag_name": request.flag_name,
                    "changes_made": changes_made,
                    "updated_flag": feature_flags.get_flag_status(request.flag_name)
                },
                "message": f"Feature flag '{request.flag_name}' updated successfully"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update feature flag", 
                    flag_name=request.flag_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update feature flag: {str(e)}"
        )


@router.post("/user-override")
async def set_user_override(request: UserOverrideRequest):
    """Set user-specific feature flag override"""
    
    try:
        feature_flags = get_feature_flag_manager()
        
        # Check if flag exists
        if request.flag_name not in feature_flags.flags:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{request.flag_name}' not found"
            )
        
        feature_flags.set_user_override(
            request.user_id, 
            request.flag_name, 
            request.enabled
        )
        
        logger.info("User override set",
                   user_id=request.user_id,
                   flag_name=request.flag_name,
                   enabled=request.enabled)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "user_id": request.user_id,
                    "flag_name": request.flag_name,
                    "enabled": request.enabled
                },
                "message": f"User override set for '{request.flag_name}'"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set user override", 
                    user_id=request.user_id,
                    flag_name=request.flag_name, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set user override: {str(e)}"
        )


@router.post("/start")
async def start_migration(
    migration_manager = Depends(get_migration_manager)
):
    """Start the migration process"""
    
    try:
        await migration_manager.start_migration()
        
        logger.info("Migration started via API")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Migration started successfully",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error("Failed to start migration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start migration: {str(e)}"
        )


@router.post("/stop")
async def stop_migration(
    migration_manager = Depends(get_migration_manager)
):
    """Stop the migration process"""
    
    try:
        await migration_manager.stop_migration()
        
        logger.info("Migration stopped via API")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Migration stopped successfully",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error("Failed to stop migration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop migration: {str(e)}"
        )


@router.get("/analytics")
async def get_migration_analytics(
    migration_manager = Depends(get_migration_manager)
):
    """Get detailed migration analytics"""
    
    try:
        status = migration_manager.get_migration_status()
        analytics = status.get("analytics", {})
        
        # Add additional computed metrics
        if analytics.get("total_requests", 0) > 0:
            analytics["consolidation_adoption_rate"] = (
                analytics.get("consolidated_requests", 0) / analytics["total_requests"] * 100
            )
        else:
            analytics["consolidation_adoption_rate"] = 0.0
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": analytics,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error("Failed to get migration analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration analytics: {str(e)}"
        )


@router.post("/advance-rollout/{flag_name}")
async def advance_rollout(flag_name: str):
    """Manually advance gradual rollout for a specific flag"""
    
    try:
        feature_flags = get_feature_flag_manager()
        
        success = feature_flags.advance_gradual_rollout(flag_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot advance rollout for flag '{flag_name}' (flag not found or not in gradual rollout state)"
            )
        
        updated_flag = feature_flags.get_flag_status(flag_name)
        
        logger.info("Rollout advanced manually", flag_name=flag_name)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "flag_name": flag_name,
                    "updated_flag": updated_flag
                },
                "message": f"Rollout advanced for '{flag_name}'"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to advance rollout", flag_name=flag_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to advance rollout: {str(e)}"
        )


@router.get("/health")
async def migration_health_check():
    """Health check for migration system"""
    
    try:
        feature_flags = get_feature_flag_manager()
        
        # Check if key flags are responsive
        consolidation_flag = feature_flags.get_flag_status("router_consolidation")
        
        health_status = {
            "migration_system_healthy": True,
            "feature_flags_responsive": consolidation_flag is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": health_status
            }
        )
    
    except Exception as e:
        logger.error("Migration health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "data": {
                    "migration_system_healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )