"""
Scheduler Service for handling scheduled job execution
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone, timedelta, time as dt_time
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

from api.database import SessionLocal
from api.db_models import ScheduledJob, ScheduledJobExecution, ScheduledJobStatus, ScheduledJobScheduleType, JobStatus
from api.job_manager import JobManager
from api.schemas import OnceScheduleConfig, CronScheduleConfig, DailyScheduleConfig

logger = logging.getLogger(__name__)


def _calculate_random_interval(base_interval_minutes: int, noise_minutes: int) -> int:
    """
    Calculate a random interval using Gaussian distribution.
    
    This function adds random variation to scheduled job intervals to avoid predictable patterns.
    For example, with a 10-minute base interval and 2-minute noise, the actual intervals will
    vary between approximately 8-12 minutes using a Gaussian distribution centered on 10 minutes.
    
    Args:
        base_interval_minutes: Base interval in minutes (the mean of the distribution)
        noise_minutes: Standard deviation for random variation in minutes
        
    Returns:
        Random interval in minutes, bounded by [1, base_interval_minutes * 2]
        
    Example:
        >>> _calculate_random_interval(10, 2)
        9  # Could be anywhere from ~6 to ~14 minutes
    """
    if noise_minutes <= 0:
        return base_interval_minutes
    
    # Use Gaussian distribution with base_interval as mean and noise as std dev
    random_interval = random.gauss(base_interval_minutes, noise_minutes)
    
    # Bound the result to reasonable values
    min_interval = max(1, base_interval_minutes // 2)  # At least 1 minute, or half the base interval
    max_interval = base_interval_minutes * 2  # At most double the base interval
    
    return max(min_interval, min(max_interval, int(random_interval)))


class SchedulerService:
    """Service for managing scheduled job execution"""
    
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self._running_scheduler = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._active_scheduled_jobs: Dict[int, ScheduledJob] = {}

    def _convert_datetime_for_json(self, obj):
        """Convert datetime objects to ISO format strings for JSON serialization"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._convert_datetime_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime_for_json(item) for item in obj]
        else:
            return obj
    
    async def start_scheduler(self):
        """Start the scheduler background task"""
        if self._running_scheduler:
            logger.warning("Scheduler is already running")
            return
        
        self._running_scheduler = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop_scheduler(self):
        """Stop the scheduler background task"""
        if not self._running_scheduler:
            logger.warning("Scheduler is not running")
            return
        
        self._running_scheduler = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that checks for jobs to execute"""
        logger.info("Scheduler loop started")
        
        while self._running_scheduler:
            try:
                await self._check_and_execute_jobs()
                # Check every 30 seconds
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(30)
        
        logger.info("Scheduler loop ended")
    
    async def _check_and_execute_jobs(self):
        """Check for scheduled jobs that need to be executed"""
        db = SessionLocal()
        try:
            # Find jobs that should be executed now
            now = datetime.now(timezone.utc)
            
            scheduled_jobs = db.query(ScheduledJob).filter(
                and_(
                    ScheduledJob.status == ScheduledJobStatus.ACTIVE,
                    ScheduledJob.next_execution_at <= now
                )
            ).all()
            
            logger.debug(f"Scheduler check at {now}: Found {len(scheduled_jobs)} jobs ready for execution")
            
            for scheduled_job in scheduled_jobs:
                try:
                    await self._execute_scheduled_job(scheduled_job, db)
                except Exception as e:
                    logger.error(f"Error executing scheduled job {scheduled_job.id}: {e}", exc_info=True)
                    # Update failure count
                    scheduled_job.failure_count += 1
                    db.commit()
            
        finally:
            db.close()
    
    async def _execute_scheduled_job(self, scheduled_job: ScheduledJob, db: Session):
        """Execute a scheduled job"""
        logger.info(f"Executing scheduled job: {scheduled_job.name} (ID: {scheduled_job.id})")
        
        # Create execution record
        execution = ScheduledJobExecution(
            scheduled_job_id=scheduled_job.id,
            scheduled_at=scheduled_job.next_execution_at,
            started_at=datetime.now(timezone.utc),
            status=JobStatus.PENDING
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        try:
            # Parse job configuration
            job_config = json.loads(scheduled_job.job_config)
            
            # Create and execute the job
            job_response = await self.job_manager.create_job(
                name=f"{scheduled_job.name} (Scheduled)",
                description=f"Scheduled execution of: {scheduled_job.description or scheduled_job.name}",
                steps=job_config.get("steps", []),
                parallel_execution=job_config.get("parallel_execution", False)
            )
            
            # Update execution record with job reference
            execution.job_id = job_response.id
            execution.status = JobStatus.RUNNING
            db.commit()
            
            # Update scheduled job tracking
            scheduled_job.last_executed_at = datetime.now(timezone.utc)
            scheduled_job.execution_count += 1
            
            # Calculate next execution time
            next_execution = self._calculate_next_execution(scheduled_job)
            if next_execution:
                scheduled_job.next_execution_at = next_execution
            else:
                # No more executions needed (e.g., one-time job completed)
                scheduled_job.status = ScheduledJobStatus.COMPLETED
                scheduled_job.next_execution_at = None
            
            db.commit()
            
            logger.info(f"Successfully executed scheduled job: {scheduled_job.name}")
            
        except Exception as e:
            logger.error(f"Error executing scheduled job {scheduled_job.id}: {e}", exc_info=True)
            
            # Update execution record with error
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            
            # Update scheduled job failure count
            scheduled_job.failure_count += 1
            
            db.commit()
            
            raise
    
    def _calculate_next_execution(self, scheduled_job: ScheduledJob) -> Optional[datetime]:
        """Calculate the next execution time for a scheduled job"""
        schedule_config = json.loads(scheduled_job.schedule_config)
        now = datetime.now(timezone.utc)
        
        if scheduled_job.schedule_type == ScheduledJobScheduleType.ONCE:
            # One-time jobs don't have a next execution
            return None
        
        elif scheduled_job.schedule_type == ScheduledJobScheduleType.CRON:
            return self._calculate_next_cron_execution(schedule_config, now)
        
        elif scheduled_job.schedule_type == ScheduledJobScheduleType.DAILY:
            return self._calculate_next_daily_execution(schedule_config, now)
        
        return None
    
    def _calculate_next_cron_execution(self, config: Dict[str, Any], now: datetime) -> Optional[datetime]:
        """Calculate next execution time for cron-based scheduling"""
        try:
            cron_expression = config.get("cron_expression", "")
            if not cron_expression:
                return None
            
            if CRONITER_AVAILABLE:
                # Use croniter library for robust cron parsing
                try:
                    cron = croniter(cron_expression, now)
                    next_execution = cron.get_next(datetime)
                    logger.debug(f"Cron expression '{cron_expression}' - next execution: {next_execution}")
                    return next_execution
                except Exception as e:
                    logger.error(f"Invalid cron expression '{cron_expression}': {e}")
                    return None
            else:
                # Fallback to simple implementation if croniter is not available
                logger.warning("croniter library not available, using basic cron parsing")
                return self._calculate_next_cron_execution_basic(config, now)
            
        except Exception as e:
            logger.error(f"Error calculating next cron execution: {e}")
            return None
    
    def _calculate_next_cron_execution_basic(self, config: Dict[str, Any], now: datetime) -> Optional[datetime]:
        """Basic cron parsing fallback when croniter is not available"""
        try:
            cron_expression = config.get("cron_expression", "")
            
            # Simple implementation for common patterns
            if cron_expression == "* * * * *":
                # Every minute
                return now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            elif cron_expression.startswith("*/") and " * * * *" in cron_expression:
                # Every N minutes
                try:
                    minutes = int(cron_expression.split("/")[1].split()[0])
                    next_minute = ((now.minute // minutes) + 1) * minutes
                    if next_minute >= 60:
                        return (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
                    else:
                        return now.replace(minute=next_minute, second=0, microsecond=0)
                except:
                    pass
            elif cron_expression.endswith(" * * * *"):
                # Specific minute every hour
                try:
                    minute = int(cron_expression.split()[0])
                    if minute == now.minute:
                        return now.replace(second=0, microsecond=0) + timedelta(hours=1)
                    elif minute > now.minute:
                        return now.replace(minute=minute, second=0, microsecond=0)
                    else:
                        return (now.replace(minute=minute, second=0, microsecond=0) + timedelta(hours=1))
                except:
                    pass
            
            # Default fallback - add 1 hour
            logger.warning(f"Unsupported cron expression '{cron_expression}', defaulting to 1 hour interval")
            return now + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Error in basic cron calculation: {e}")
            return now + timedelta(hours=1)
    
    def _calculate_next_daily_execution(self, config: Dict[str, Any], now: datetime) -> Optional[datetime]:
        """Calculate next execution time for daily scheduling"""
        try:
            ranges = config.get("ranges", [])
            if not ranges:
                return None
            
            # Get timezone from config, default to UTC if not specified
            timezone_str = config.get("timezone", "UTC")
            
            if PYTZ_AVAILABLE:
                try:
                    user_tz = pytz.timezone(timezone_str)
                except pytz.exceptions.UnknownTimeZoneError:
                    logger.warning(f"Unknown timezone '{timezone_str}', falling back to UTC")
                    user_tz = pytz.UTC
            else:
                logger.warning("pytz not available, treating times as UTC")
                user_tz = timezone.utc
            
            # Convert current UTC time to user's timezone
            current_user_time = now.astimezone(user_tz)
            current_time = current_user_time.time()
            current_date = current_user_time.date()
            
            # Find the next execution time today
            for range_config in ranges:
                start_time = datetime.strptime(range_config["start_time"], "%H:%M").time()
                end_time = datetime.strptime(range_config["end_time"], "%H:%M").time()
                interval_minutes = range_config["interval_minutes"]
                
                # Check if current time is within this range
                # Handle ranges that span midnight (e.g., 5pm-9am)
                is_in_range = False
                if start_time <= end_time:
                    # Normal range (doesn't span midnight)
                    is_in_range = start_time <= current_time <= end_time
                else:
                    # Range spans midnight (e.g., 5pm-9am)
                    is_in_range = current_time >= start_time or current_time <= end_time
                
                if is_in_range:
                    # Calculate next execution within this range with random interval
                    random_noise = range_config.get("random_noise_minutes", 0)
                    actual_interval = _calculate_random_interval(interval_minutes, random_noise)
                    next_execution_user = current_user_time + timedelta(minutes=actual_interval)
                    
                    # Check if it's still within the range
                    next_time = next_execution_user.time()
                    still_in_range = False
                    
                    if start_time <= end_time:
                        # Normal range
                        still_in_range = next_time <= end_time
                    else:
                        # Range spans midnight - check if we're still in the same day
                        # or if we've crossed midnight but are still within the end time
                        if next_execution_user.date() == current_date:
                            # Still same day - for midnight-spanning ranges, if we're in the early morning
                            # (before end_time), we're still in the range
                            if current_time <= end_time:
                                # We're in the early morning part of the range (e.g., 4 AM in 5pm-9am)
                                still_in_range = next_time <= end_time
                            else:
                                # We're in the evening part of the range (e.g., 6 PM in 5pm-9am)
                                still_in_range = next_time >= start_time
                        else:
                            # Crossed midnight, check if within end time
                            still_in_range = next_time <= end_time
                    
                    if still_in_range:
                        # Convert back to UTC
                        return next_execution_user.astimezone(timezone.utc)
                    else:
                        # Move to next range or tomorrow
                        continue
            
            # If no execution found today, find the first execution tomorrow
            tomorrow = current_date + timedelta(days=1)
            for range_config in ranges:
                start_time = datetime.strptime(range_config["start_time"], "%H:%M").time()
                # Create datetime in user's timezone, then convert to UTC
                next_execution_user = user_tz.localize(datetime.combine(tomorrow, start_time))
                return next_execution_user.astimezone(timezone.utc)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating next daily execution: {e}")
            return None
    
    def calculate_next_execution_time(self, schedule_type: str, schedule_config: Dict[str, Any]) -> Optional[datetime]:
        """Calculate the next execution time for a given schedule configuration"""
        now = datetime.now(timezone.utc)
        
        if schedule_type == "once":
            config = OnceScheduleConfig(**schedule_config)
            return config.execution_time
        
        elif schedule_type == "cron":
            return self._calculate_next_cron_execution(schedule_config, now)
        
        elif schedule_type == "daily":
            return self._calculate_next_daily_execution(schedule_config, now)
        
        return None
    
    async def create_scheduled_job(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new scheduled job"""
        db = SessionLocal()
        try:
            # Validate and prepare schedule configuration
            schedule_type = request_data["schedule_type"]
            schedule_config = {}
            next_execution = None
            
            if schedule_type == "once":
                once_config = request_data.get("once_config")
                if not once_config:
                    raise ValueError("once_config is required for once schedule type")
                schedule_config = self._convert_datetime_for_json(once_config)
                # Handle next_execution - convert to datetime if it's a string
                execution_time = once_config["execution_time"]
                if isinstance(execution_time, str):
                    next_execution = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
                elif hasattr(execution_time, 'isoformat'):
                    next_execution = execution_time
                else:
                    raise ValueError("Invalid execution_time format")
                
                # Validate that the execution time is in the future
                now = datetime.now(timezone.utc)
                if next_execution <= now:
                    raise ValueError("Scheduled execution time cannot be in the past. Please select a future date and time.")
            
            elif schedule_type == "cron":
                cron_config = request_data.get("cron_config")
                if not cron_config:
                    raise ValueError("cron_config is required for cron schedule type")
                schedule_config = self._convert_datetime_for_json(cron_config)
                next_execution = self._calculate_next_cron_execution(cron_config, datetime.now(timezone.utc))
                logger.info(f"Created cron job with expression '{cron_config.get('cron_expression')}' - next execution: {next_execution}")
            
            elif schedule_type == "daily":
                daily_config = request_data.get("daily_config")
                if not daily_config:
                    raise ValueError("daily_config is required for daily schedule type")
                schedule_config = self._convert_datetime_for_json(daily_config)
                next_execution = self._calculate_next_daily_execution(daily_config, datetime.now(timezone.utc))
            
            else:
                raise ValueError(f"Invalid schedule_type: {schedule_type}")
            
            # Create scheduled job
            scheduled_job = ScheduledJob(
                name=request_data["name"],
                description=request_data.get("description"),
                job_config=json.dumps(request_data["job_config"]),
                schedule_type=ScheduledJobScheduleType(schedule_type),
                schedule_config=json.dumps(schedule_config),
                next_execution_at=next_execution
            )
            
            db.add(scheduled_job)
            db.commit()
            db.refresh(scheduled_job)
            
            # Return response
            return {
                "id": scheduled_job.id,
                "name": scheduled_job.name,
                "description": scheduled_job.description,
                "job_config": json.loads(scheduled_job.job_config),
                "schedule_type": scheduled_job.schedule_type.value,
                "schedule_config": json.loads(scheduled_job.schedule_config),
                "status": scheduled_job.status.value,
                "created_at": scheduled_job.created_at,
                "updated_at": scheduled_job.updated_at,
                "last_executed_at": scheduled_job.last_executed_at,
                "next_execution_at": scheduled_job.next_execution_at,
                "execution_count": scheduled_job.execution_count,
                "failure_count": scheduled_job.failure_count
            }
            
        finally:
            db.close()
    
    async def list_scheduled_jobs(self, status: Optional[str] = None) -> Dict[str, Any]:
        """List scheduled jobs with optional status filtering"""
        db = SessionLocal()
        try:
            query = db.query(ScheduledJob)
            
            if status:
                query = query.filter(ScheduledJob.status == ScheduledJobStatus(status))
            
            scheduled_jobs = query.order_by(ScheduledJob.created_at.desc()).all()
            
            scheduled_job_responses = []
            for scheduled_job in scheduled_jobs:
                scheduled_job_responses.append({
                    "id": scheduled_job.id,
                    "name": scheduled_job.name,
                    "description": scheduled_job.description,
                    "job_config": json.loads(scheduled_job.job_config),
                    "schedule_type": scheduled_job.schedule_type.value,
                    "schedule_config": json.loads(scheduled_job.schedule_config),
                    "status": scheduled_job.status.value,
                    "created_at": scheduled_job.created_at,
                    "updated_at": scheduled_job.updated_at,
                    "last_executed_at": scheduled_job.last_executed_at,
                    "next_execution_at": scheduled_job.next_execution_at,
                    "execution_count": scheduled_job.execution_count,
                    "failure_count": scheduled_job.failure_count
                })
            
            return {
                "scheduled_jobs": scheduled_job_responses,
                "total": len(scheduled_job_responses)
            }
            
        finally:
            db.close()
    
    async def get_scheduled_job(self, scheduled_job_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific scheduled job"""
        db = SessionLocal()
        try:
            scheduled_job = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
            
            if not scheduled_job:
                return None
            
            return {
                "id": scheduled_job.id,
                "name": scheduled_job.name,
                "description": scheduled_job.description,
                "job_config": json.loads(scheduled_job.job_config),
                "schedule_type": scheduled_job.schedule_type.value,
                "schedule_config": json.loads(scheduled_job.schedule_config),
                "status": scheduled_job.status.value,
                "created_at": scheduled_job.created_at,
                "updated_at": scheduled_job.updated_at,
                "last_executed_at": scheduled_job.last_executed_at,
                "next_execution_at": scheduled_job.next_execution_at,
                "execution_count": scheduled_job.execution_count,
                "failure_count": scheduled_job.failure_count
            }
            
        finally:
            db.close()
    
    async def update_scheduled_job_status(self, scheduled_job_id: int, status: str) -> bool:
        """Update the status of a scheduled job"""
        db = SessionLocal()
        try:
            scheduled_job = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
            
            if not scheduled_job:
                return False
            
            scheduled_job.status = ScheduledJobStatus(status)
            scheduled_job.updated_at = datetime.now(timezone.utc)
            
            # If pausing, clear next execution
            if status == "paused":
                scheduled_job.next_execution_at = None
            
            # If reactivating, recalculate next execution
            elif status == "active" and not scheduled_job.next_execution_at:
                next_execution = self._calculate_next_execution(scheduled_job)
                scheduled_job.next_execution_at = next_execution
            
            db.commit()
            return True
            
        finally:
            db.close()
    
    async def update_scheduled_job(self, scheduled_job_id: int, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing scheduled job"""
        db = SessionLocal()
        try:
            scheduled_job = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
            
            if not scheduled_job:
                return None
            
            # Validate and prepare schedule configuration
            schedule_type = request_data["schedule_type"]
            schedule_config = {}
            next_execution = None
            
            if schedule_type == "once":
                once_config = request_data.get("once_config")
                if not once_config:
                    raise ValueError("once_config is required for once schedule type")
                schedule_config = self._convert_datetime_for_json(once_config)
                # Handle next_execution - convert to datetime if it's a string
                execution_time = once_config["execution_time"]
                if isinstance(execution_time, str):
                    next_execution = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
                elif hasattr(execution_time, 'isoformat'):
                    next_execution = execution_time
                else:
                    raise ValueError("Invalid execution_time format")
                
                # Validate that the execution time is in the future
                now = datetime.now(timezone.utc)
                if next_execution <= now:
                    raise ValueError("Scheduled execution time cannot be in the past. Please select a future date and time.")
            
            elif schedule_type == "cron":
                cron_config = request_data.get("cron_config")
                if not cron_config:
                    raise ValueError("cron_config is required for cron schedule type")
                schedule_config = self._convert_datetime_for_json(cron_config)
                next_execution = self._calculate_next_cron_execution(cron_config, datetime.now(timezone.utc))
                logger.info(f"Updated cron job with expression '{cron_config.get('cron_expression')}' - next execution: {next_execution}")
            
            elif schedule_type == "daily":
                daily_config = request_data.get("daily_config")
                if not daily_config:
                    raise ValueError("daily_config is required for daily schedule type")
                schedule_config = self._convert_datetime_for_json(daily_config)
                next_execution = self._calculate_next_daily_execution(daily_config, datetime.now(timezone.utc))
            
            else:
                raise ValueError(f"Invalid schedule_type: {schedule_type}")
            
            # Update the scheduled job
            scheduled_job.name = request_data["name"]
            scheduled_job.description = request_data.get("description")
            scheduled_job.job_config = json.dumps(request_data["job_config"])
            scheduled_job.schedule_type = ScheduledJobScheduleType(schedule_type)
            scheduled_job.schedule_config = json.dumps(schedule_config)
            scheduled_job.next_execution_at = next_execution
            scheduled_job.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(scheduled_job)
            
            # Return response
            return {
                "id": scheduled_job.id,
                "name": scheduled_job.name,
                "description": scheduled_job.description,
                "job_config": json.loads(scheduled_job.job_config),
                "schedule_type": scheduled_job.schedule_type.value,
                "schedule_config": json.loads(scheduled_job.schedule_config),
                "status": scheduled_job.status.value,
                "created_at": scheduled_job.created_at,
                "updated_at": scheduled_job.updated_at,
                "last_executed_at": scheduled_job.last_executed_at,
                "next_execution_at": scheduled_job.next_execution_at,
                "execution_count": scheduled_job.execution_count,
                "failure_count": scheduled_job.failure_count
            }
            
        finally:
            db.close()
    
    async def delete_scheduled_job(self, scheduled_job_id: int) -> bool:
        """Delete a scheduled job"""
        db = SessionLocal()
        try:
            scheduled_job = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
            
            if not scheduled_job:
                return False
            
            db.delete(scheduled_job)
            db.commit()
            return True
            
        finally:
            db.close()
    
    async def cleanup_expired_scheduled_jobs(self) -> int:
        """
        Clean up expired scheduled jobs based on their schedule type.
        
        - For "once" jobs: Mark as canceled if execution time has passed
        - For "cron" and "daily" jobs: Recalculate next execution time
        
        This function finds scheduled jobs that have a next_execution_at time in the past
        and handles them appropriately based on their schedule type.
        
        Returns:
            int: Number of jobs that were processed (canceled or recalculated)
        """
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            
            # Find active scheduled jobs that have expired
            expired_jobs = db.query(ScheduledJob).filter(
                and_(
                    ScheduledJob.status == ScheduledJobStatus.ACTIVE,
                    ScheduledJob.next_execution_at < now
                )
            ).all()
            
            processed_count = 0
            canceled_count = 0
            recalculated_count = 0
            
            for job in expired_jobs:
                try:
                    if job.schedule_type == ScheduledJobScheduleType.ONCE:
                        # For once jobs, mark as canceled
                        logger.info(f"Marking expired once job '{job.name}' (ID: {job.id}) as canceled. "
                                  f"Was scheduled for: {job.next_execution_at}")
                        job.status = ScheduledJobStatus.CANCELED
                        job.updated_at = now
                        canceled_count += 1
                        
                    elif job.schedule_type == ScheduledJobScheduleType.CRON:
                        # For cron jobs, recalculate next execution
                        try:
                            schedule_config = json.loads(job.schedule_config)
                            cron_config = CronScheduleConfig(**schedule_config)
                            next_execution = self._calculate_next_cron_execution(cron_config.dict(), now)
                            
                            logger.info(f"Recalculating next execution for cron job '{job.name}' (ID: {job.id}). "
                                      f"Was scheduled for: {job.next_execution_at}, "
                                      f"new execution: {next_execution}")
                            
                            job.next_execution_at = next_execution
                            job.updated_at = now
                            recalculated_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error recalculating cron job '{job.name}' (ID: {job.id}): {e}. Marking as failed.")
                            job.status = ScheduledJobStatus.FAILED
                            job.updated_at = now
                            canceled_count += 1
                            
                    elif job.schedule_type == ScheduledJobScheduleType.DAILY:
                        # For daily jobs, recalculate next execution
                        try:
                            schedule_config = json.loads(job.schedule_config)
                            daily_config = DailyScheduleConfig(**schedule_config)
                            next_execution = self._calculate_next_daily_execution(daily_config.dict(), now)
                            
                            logger.info(f"Recalculating next execution for daily job '{job.name}' (ID: {job.id}). "
                                      f"Was scheduled for: {job.next_execution_at}, "
                                      f"new execution: {next_execution}")
                            
                            job.next_execution_at = next_execution
                            job.updated_at = now
                            recalculated_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error recalculating daily job '{job.name}' (ID: {job.id}): {e}. Marking as failed.")
                            job.status = ScheduledJobStatus.FAILED
                            job.updated_at = now
                            canceled_count += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing expired job '{job.name}' (ID: {job.id}): {e}")
                    # Mark as failed if we can't process it
                    job.status = ScheduledJobStatus.FAILED
                    job.updated_at = now
                    processed_count += 1
            
            if processed_count > 0:
                db.commit()
                if canceled_count > 0:
                    logger.info(f"Marked {canceled_count} expired scheduled jobs as canceled/failed")
                if recalculated_count > 0:
                    logger.info(f"Recalculated next execution time for {recalculated_count} recurring scheduled jobs")
                logger.info(f"Processed {processed_count} expired scheduled jobs total")
            else:
                logger.info("No expired scheduled jobs found to process")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired scheduled jobs: {e}")
            db.rollback()
            raise
        finally:
            db.close()
