"""
Automated data retention and cleanup scheduler.

Provides automated data lifecycle management:
- Scheduled data retention policy enforcement
- Automated data cleanup and archival
- Data aging and lifecycle transitions
- Compliance-driven retention schedules
- Integration with existing storage systems
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

import structlog

from .data_protection import DataProtectionService, RetentionAction, DataLifecycleStage
from .encryption import DataClassification
from .audit_logger import AuditEventType, RiskLevel, ComplianceFramework

logger = structlog.get_logger(__name__)


class ScheduleFrequency(Enum):
    """Schedule frequencies for retention tasks"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class RetentionTask:
    """Retention task definition"""
    task_id: str
    data_type: str
    action: RetentionAction
    schedule: ScheduleFrequency
    conditions: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class DataRetentionScheduler:
    """
    Automated data retention and cleanup scheduler.
    
    Features:
    - Configurable retention schedules
    - Automated data lifecycle management
    - Compliance-driven cleanup policies
    - Safe deletion with audit trails
    - Integration with existing storage systems
    """
    
    def __init__(self, data_protection_service: DataProtectionService):
        """
        Initialize retention scheduler.
        
        Args:
            data_protection_service: Data protection service instance
        """
        self.data_protection = data_protection_service
        self.retention_tasks: Dict[str, RetentionTask] = {}
        self.running = False
        self.scheduler_task = None
        
        # Schedule intervals in seconds
        self.schedule_intervals = {
            ScheduleFrequency.HOURLY: 3600,
            ScheduleFrequency.DAILY: 86400,
            ScheduleFrequency.WEEKLY: 604800,
            ScheduleFrequency.MONTHLY: 2592000  # 30 days
        }
        
        # Initialize default retention tasks
        self._initialize_default_tasks()
        
        logger.info("data_retention_scheduler_initialized")
    
    def _initialize_default_tasks(self):
        """Initialize default retention tasks"""
        default_tasks = [
            RetentionTask(
                task_id="conversation_cleanup",
                data_type="conversation",
                action=RetentionAction.ARCHIVE,
                schedule=ScheduleFrequency.DAILY,
                conditions={
                    "age_days": 365,
                    "min_activity_days": 30,
                    "preserve_high_quality": True
                }
            ),
            RetentionTask(
                task_id="analytics_anonymization",
                data_type="analytics",
                action=RetentionAction.ANONYMIZE,
                schedule=ScheduleFrequency.WEEKLY,
                conditions={
                    "age_days": 730,  # 2 years
                    "anonymization_level": "standard"
                }
            ),
            RetentionTask(
                task_id="expired_session_cleanup",
                data_type="session",
                action=RetentionAction.DELETE,
                schedule=ScheduleFrequency.HOURLY,
                conditions={
                    "age_hours": 24,
                    "inactive": True
                }
            ),
            RetentionTask(
                task_id="audit_log_archival",
                data_type="audit_logs",
                action=RetentionAction.ARCHIVE,
                schedule=ScheduleFrequency.MONTHLY,
                conditions={
                    "age_days": 2555,  # 7 years
                    "compress": True
                }
            ),
            RetentionTask(
                task_id="gdpr_expired_data",
                data_type="user_data",
                action=RetentionAction.DELETE,
                schedule=ScheduleFrequency.DAILY,
                conditions={
                    "consent_expired": True,
                    "grace_period_days": 30
                }
            )
        ]
        
        for task in default_tasks:
            self.retention_tasks[task.task_id] = task
            task.next_run = self._calculate_next_run(task)
    
    async def start(self):
        """Start the retention scheduler"""
        if self.running:
            logger.warning("retention_scheduler_already_running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("data_retention_scheduler_started")
    
    async def stop(self):
        """Stop the retention scheduler"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("data_retention_scheduler_stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check for tasks that need to run
                for task in self.retention_tasks.values():
                    if (task.enabled and 
                        task.next_run and 
                        current_time >= task.next_run):
                        
                        asyncio.create_task(self._execute_retention_task(task))
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("retention_scheduler_loop_error", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _execute_retention_task(self, task: RetentionTask):
        """Execute a retention task"""
        try:
            start_time = datetime.now(timezone.utc)
            
            logger.info(
                "executing_retention_task",
                task_id=task.task_id,
                data_type=task.data_type,
                action=task.action.value
            )
            
            # Execute based on data type and action
            result = await self._perform_retention_action(task)
            
            # Update task execution metadata
            task.last_run = start_time
            task.next_run = self._calculate_next_run(task)
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Audit log the retention task execution
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"retention:{task.data_type}",
                action=f"retention_{task.action.value}",
                outcome="success" if result.get("success", False) else "failure",
                details={
                    "task_id": task.task_id,
                    "conditions": task.conditions,
                    "execution_time_seconds": execution_time,
                    "result": result
                },
                risk_level=RiskLevel.LOW,
                data_classification=self._get_data_classification(task.data_type),
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2]
            )
            
            logger.info(
                "retention_task_completed",
                task_id=task.task_id,
                execution_time_seconds=execution_time,
                success=result.get("success", False),
                records_processed=result.get("records_processed", 0)
            )
            
        except Exception as e:
            logger.error(
                "retention_task_execution_failed",
                error=str(e),
                task_id=task.task_id,
                data_type=task.data_type
            )
            
            # Update next run even on failure to prevent infinite retries
            task.last_run = datetime.now(timezone.utc)
            task.next_run = self._calculate_next_run(task)
            
            # Audit log the failure
            await self.data_protection.audit_logger.log_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                resource=f"retention:{task.data_type}",
                action=f"retention_{task.action.value}",
                outcome="failure",
                details={"task_id": task.task_id, "error": str(e)},
                risk_level=RiskLevel.MEDIUM,
                compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2]
            )
    
    async def _perform_retention_action(self, task: RetentionTask) -> Dict[str, Any]:
        """Perform the actual retention action"""
        try:
            if task.data_type == "conversation":
                return await self._process_conversation_retention(task)
            elif task.data_type == "analytics":
                return await self._process_analytics_retention(task)
            elif task.data_type == "session":
                return await self._process_session_retention(task)
            elif task.data_type == "audit_logs":
                return await self._process_audit_log_retention(task)
            elif task.data_type == "user_data":
                return await self._process_user_data_retention(task)
            else:
                logger.warning("unknown_data_type_for_retention", data_type=task.data_type)
                return {"success": False, "error": f"Unknown data type: {task.data_type}"}
                
        except Exception as e:
            logger.error("retention_action_failed", error=str(e), task_id=task.task_id)
            return {"success": False, "error": str(e)}
    
    async def _process_conversation_retention(self, task: RetentionTask) -> Dict[str, Any]:
        """Process conversation data retention"""
        conditions = task.conditions
        age_days = conditions.get("age_days", 365)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=age_days)
        
        # This would integrate with your Redis/ClickHouse conversation storage
        # For now, we'll simulate the process
        
        if task.action == RetentionAction.ARCHIVE:
            # Archive old conversations
            archived_count = await self._archive_conversations(cutoff_date, conditions)
            return {
                "success": True,
                "action": "archive",
                "records_processed": archived_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        elif task.action == RetentionAction.DELETE:
            # Delete very old conversations
            deleted_count = await self._delete_conversations(cutoff_date, conditions)
            return {
                "success": True,
                "action": "delete",
                "records_processed": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        elif task.action == RetentionAction.ANONYMIZE:
            # Anonymize conversation data
            anonymized_count = await self._anonymize_conversations(cutoff_date, conditions)
            return {
                "success": True,
                "action": "anonymize",
                "records_processed": anonymized_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        return {"success": False, "error": f"Unsupported action: {task.action}"}
    
    async def _process_analytics_retention(self, task: RetentionTask) -> Dict[str, Any]:
        """Process analytics data retention"""
        conditions = task.conditions
        age_days = conditions.get("age_days", 730)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=age_days)
        
        if task.action == RetentionAction.ANONYMIZE:
            # Anonymize old analytics data
            anonymized_count = await self._anonymize_analytics(cutoff_date, conditions)
            return {
                "success": True,
                "action": "anonymize",
                "records_processed": anonymized_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        return {"success": False, "error": f"Unsupported action: {task.action}"}
    
    async def _process_session_retention(self, task: RetentionTask) -> Dict[str, Any]:
        """Process session data retention"""
        conditions = task.conditions
        age_hours = conditions.get("age_hours", 24)
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        
        if task.action == RetentionAction.DELETE:
            # Delete expired sessions
            deleted_count = await self._delete_expired_sessions(cutoff_date, conditions)
            return {
                "success": True,
                "action": "delete",
                "records_processed": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        return {"success": False, "error": f"Unsupported action: {task.action}"}
    
    async def _process_audit_log_retention(self, task: RetentionTask) -> Dict[str, Any]:
        """Process audit log retention"""
        conditions = task.conditions
        age_days = conditions.get("age_days", 2555)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=age_days)
        
        if task.action == RetentionAction.ARCHIVE:
            # Archive old audit logs
            archived_count = await self._archive_audit_logs(cutoff_date, conditions)
            return {
                "success": True,
                "action": "archive",
                "records_processed": archived_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        return {"success": False, "error": f"Unsupported action: {task.action}"}
    
    async def _process_user_data_retention(self, task: RetentionTask) -> Dict[str, Any]:
        """Process user data retention for GDPR compliance"""
        conditions = task.conditions
        
        if task.action == RetentionAction.DELETE:
            # Delete data for users without valid consent
            deleted_count = await self._delete_unconsented_user_data(conditions)
            return {
                "success": True,
                "action": "delete",
                "records_processed": deleted_count
            }
        
        return {"success": False, "error": f"Unsupported action: {task.action}"}
    
    # Placeholder implementations for actual data operations
    # These would integrate with your real storage systems
    
    async def _archive_conversations(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Archive old conversations (placeholder)"""
        logger.info("archiving_conversations", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would move conversations from active Redis to cold storage
        return 0  # Placeholder
    
    async def _delete_conversations(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Delete old conversations (placeholder)"""
        logger.info("deleting_conversations", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would permanently delete very old conversations
        return 0  # Placeholder
    
    async def _anonymize_conversations(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Anonymize old conversations (placeholder)"""
        logger.info("anonymizing_conversations", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would use the GDPR manager to anonymize conversation data
        return 0  # Placeholder
    
    async def _anonymize_analytics(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Anonymize old analytics data (placeholder)"""
        logger.info("anonymizing_analytics", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would anonymize user identifiers in ClickHouse analytics
        return 0  # Placeholder
    
    async def _delete_expired_sessions(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Delete expired sessions (placeholder)"""
        logger.info("deleting_expired_sessions", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would clean up expired session data from Redis
        return 0  # Placeholder
    
    async def _archive_audit_logs(self, cutoff_date: datetime, conditions: Dict[str, Any]) -> int:
        """Archive old audit logs (placeholder)"""
        logger.info("archiving_audit_logs", cutoff_date=cutoff_date.isoformat(), conditions=conditions)
        # This would move old audit logs to long-term storage
        return 0  # Placeholder
    
    async def _delete_unconsented_user_data(self, conditions: Dict[str, Any]) -> int:
        """Delete data for users without consent (placeholder)"""
        logger.info("deleting_unconsented_user_data", conditions=conditions)
        # This would identify and delete data for users who withdrew consent
        return 0  # Placeholder
    
    def _calculate_next_run(self, task: RetentionTask) -> datetime:
        """Calculate next run time for a task"""
        now = datetime.now(timezone.utc)
        interval_seconds = self.schedule_intervals[task.schedule]
        
        if task.last_run:
            next_run = task.last_run + timedelta(seconds=interval_seconds)
            # If the calculated next run is in the past, schedule for now + interval
            if next_run <= now:
                next_run = now + timedelta(seconds=interval_seconds)
        else:
            # First run - schedule based on frequency
            if task.schedule == ScheduleFrequency.HOURLY:
                next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            elif task.schedule == ScheduleFrequency.DAILY:
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif task.schedule == ScheduleFrequency.WEEKLY:
                days_until_sunday = (6 - now.weekday()) % 7
                next_run = (now + timedelta(days=days_until_sunday)).replace(hour=3, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(weeks=1)
            else:  # MONTHLY
                next_month = now.replace(day=1, hour=4, minute=0, second=0, microsecond=0) + timedelta(days=32)
                next_run = next_month.replace(day=1)
        
        return next_run
    
    def _get_data_classification(self, data_type: str) -> DataClassification:
        """Get data classification for data type"""
        classifications = {
            "conversation": DataClassification.CONFIDENTIAL,
            "analytics": DataClassification.INTERNAL,
            "session": DataClassification.INTERNAL,
            "audit_logs": DataClassification.RESTRICTED,
            "user_data": DataClassification.RESTRICTED
        }
        return classifications.get(data_type, DataClassification.INTERNAL)
    
    def add_retention_task(self, task: RetentionTask) -> bool:
        """Add a new retention task"""
        try:
            task.next_run = self._calculate_next_run(task)
            self.retention_tasks[task.task_id] = task
            
            logger.info(
                "retention_task_added",
                task_id=task.task_id,
                data_type=task.data_type,
                action=task.action.value,
                schedule=task.schedule.value,
                next_run=task.next_run.isoformat() if task.next_run else None
            )
            
            return True
            
        except Exception as e:
            logger.error("failed_to_add_retention_task", error=str(e), task_id=task.task_id)
            return False
    
    def remove_retention_task(self, task_id: str) -> bool:
        """Remove a retention task"""
        if task_id in self.retention_tasks:
            del self.retention_tasks[task_id]
            logger.info("retention_task_removed", task_id=task_id)
            return True
        else:
            logger.warning("retention_task_not_found", task_id=task_id)
            return False
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a retention task"""
        if task_id in self.retention_tasks:
            self.retention_tasks[task_id].enabled = True
            logger.info("retention_task_enabled", task_id=task_id)
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a retention task"""
        if task_id in self.retention_tasks:
            self.retention_tasks[task_id].enabled = False
            logger.info("retention_task_disabled", task_id=task_id)
            return True
        return False
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all retention tasks"""
        current_time = datetime.now(timezone.utc)
        
        status = {
            "scheduler_running": self.running,
            "total_tasks": len(self.retention_tasks),
            "enabled_tasks": sum(1 for task in self.retention_tasks.values() if task.enabled),
            "tasks": {}
        }
        
        for task_id, task in self.retention_tasks.items():
            status["tasks"][task_id] = {
                "data_type": task.data_type,
                "action": task.action.value,
                "schedule": task.schedule.value,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "overdue": task.next_run and current_time > task.next_run if task.enabled else False
            }
        
        return status


# Factory function
def create_retention_scheduler(data_protection_service: DataProtectionService) -> DataRetentionScheduler:
    """Create DataRetentionScheduler instance"""
    return DataRetentionScheduler(data_protection_service)