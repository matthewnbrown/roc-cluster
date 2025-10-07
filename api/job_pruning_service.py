"""
Job Pruning Service

This service removes job steps from the 11th job and later to keep the database clean.
Runs on startup and every 8 hours.
"""

import logging
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text

from api.database import SessionLocal
from api.db_models import Job, JobStep, JobStatus, AccountLog
from api.async_logger import async_logger
from config import settings
import json

logger = logging.getLogger(__name__)


async def system_notification_handler(model_class, data: dict, timestamp):
    """Custom handler for system notifications that doesn't require account_id"""
    db = SessionLocal()
    try:
        # Create a system notification log entry
        log_entry = AccountLog(
            account_id=1,  # Use a dummy account_id for system notifications
            action=data.get("action", "system_notification"),
            details=json.dumps(data),
            success=data.get("success", True),
            timestamp=timestamp
        )
        
        db.add(log_entry)
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to write system notification to database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def job_pruning_handler(model_class, data: dict, timestamp):
    """Custom handler for job pruning logs"""
    db = SessionLocal()
    try:
        # Create a job pruning log entry
        log_entry = AccountLog(
            account_id=1,  # Use a dummy account_id for system operations
            action=data.get("action", "job_pruning"),
            details=json.dumps(data),
            success=data.get("success", True),
            timestamp=timestamp
        )
        
        db.add(log_entry)
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to write job pruning log to database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


class JobPruningService:
    """Service for pruning old job steps"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        
    async def start(self):
        """Start the job pruning scheduler"""
        if self.is_running:
            logger.warning("Job pruning service is already running")
            return
            
        try:
            self.scheduler = AsyncIOScheduler()
            
            # Schedule job to run immediately on startup
            self.scheduler.add_job(
                self._prune_job_steps,
                DateTrigger(run_date=datetime.now()),
                id='startup_prune',
                name='Startup Job Steps Prune',
                replace_existing=True
            )
            
            # Schedule job to run every 8 hours
            self.scheduler.add_job(
                self._prune_job_steps,
                CronTrigger(hour='*/8', minute=0),  # Every 8 hours at minute 0
                id='scheduled_prune',
                name='Scheduled Job Steps Prune',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Job pruning service started successfully")
            logger.info("Scheduled jobs: startup prune, then every 8 hours")
            
        except Exception as e:
            logger.error(f"Failed to start job pruning service: {e}")
            raise
    
    async def stop(self):
        """Stop the job pruning scheduler"""
        if not self.is_running or not self.scheduler:
            return
            
        try:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
            self.is_running = False
            logger.info("Job pruning service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping job pruning service: {e}")
    
    async def _prune_job_steps(self):
        """Remove all job steps from the oldest jobs, keeping the latest N jobs (configurable)"""
        keep_count = settings.JOB_PRUNE_KEEP_COUNT
        logger.info(f"Starting job steps pruning process (keeping latest {keep_count} jobs)")
        
        db = SessionLocal()
        try:
            # Find the oldest jobs that haven't been pruned yet (keep the latest N jobs, remove steps from the rest)
            # Order by created_at DESC to get newest first, then offset(N) to skip the N newest
            jobs_to_prune = db.query(Job).filter(
                Job.pruned == False
            ).order_by(Job.created_at.desc()).offset(keep_count).all()
            
            if not jobs_to_prune:
                logger.info(f"No unpruned jobs found beyond the latest {keep_count} jobs - nothing to prune")
                return
            
            total_steps_removed = 0
            jobs_affected = []
            
            for job in jobs_to_prune:
                # Count steps before deletion
                steps_count = db.query(JobStep).filter(JobStep.job_id == job.id).count()
                
                if steps_count > 0:
                    # Delete all steps for this job
                    db.query(JobStep).filter(JobStep.job_id == job.id).delete()
                    total_steps_removed += steps_count
                    
                    # Mark the job as pruned
                    job.pruned = True
                    
                    jobs_affected.append({
                        'job_id': job.id,
                        'job_name': job.name,
                        'steps_removed': steps_count,
                        'created_at': job.created_at.isoformat() if job.created_at else None
                    })
                    
                    logger.info(f"Removed {steps_count} steps from old job {job.id} ({job.name}) and marked as pruned")
                else:
                    # Even if no steps, mark as pruned to avoid reprocessing
                    job.pruned = True
                    logger.info(f"Marked job {job.id} ({job.name}) as pruned (no steps to remove)")
            
            # Commit the changes
            db.commit()
            
            # Perform incremental vacuum if we removed a significant number of steps
            if total_steps_removed > 100:  # Only vacuum if we removed more than 100 steps
                try:
                    logger.info("Performing incremental vacuum after large pruning operation...")
                    db.execute(text("PRAGMA incremental_vacuum"))
                    db.commit()
                    logger.info("Incremental vacuum completed")
                except Exception as e:
                    logger.warning(f"Incremental vacuum failed: {e}")
            
            # Log the pruning operation
            pruning_summary = {
                'timestamp': datetime.now().isoformat(),
                'total_jobs_affected': len(jobs_affected),
                'total_steps_removed': total_steps_removed,
                'jobs_affected': jobs_affected
            }
            
            logger.info(f"Job steps pruning completed: {total_steps_removed} steps removed from {len(jobs_affected)} old jobs (keeping latest {keep_count} jobs)")
            
            # Log to async logger for persistence
            await async_logger.log(
                "job_pruning",
                {
                    "action": "Job steps pruning completed",
                    "details": pruning_summary,
                    "success": True
                }
            )
            
            # Store pruning notification for frontend
            await self._store_pruning_notification(pruning_summary)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during job steps pruning: {e}")
            
            # Log error to async logger
            await async_logger.log(
                "job_pruning",
                {
                    "action": "Job steps pruning failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "success": False
                }
            )
            raise
            
        finally:
            db.close()
    
    async def _store_pruning_notification(self, pruning_summary: dict):
        """Store a notification about the pruning operation for frontend consumption"""
        try:
            # We'll create a simple notification table entry or use existing logging
            # For now, we'll log it as a special event that the frontend can query
            await async_logger.log(
                "system_notification",
                {
                    "action": "system_notification",
                    "type": "job_pruning",
                    "message": f"Removed {pruning_summary['total_steps_removed']} steps from {pruning_summary['total_jobs_affected']} old jobs (keeping latest 10 jobs)",
                    "details": pruning_summary,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store pruning notification: {e}")
    
    async def get_pruning_stats(self) -> dict:
        """Get statistics about job pruning"""
        db = SessionLocal()
        try:
            # Get total jobs count
            total_jobs = db.query(Job).count()
            
            # Get unpruned jobs beyond the latest 10 (oldest jobs that would be pruned)
            jobs_beyond_10th = db.query(Job).filter(
                Job.pruned == False
            ).order_by(Job.created_at.desc()).offset(10).count()
            
            # Get total steps in unpruned jobs beyond the latest 10
            total_steps_to_prune = 0
            if jobs_beyond_10th > 0:
                jobs_to_check = db.query(Job).filter(
                    Job.pruned == False
                ).order_by(Job.created_at.desc()).offset(10).all()
                for job in jobs_to_check:
                    steps_count = db.query(JobStep).filter(JobStep.job_id == job.id).count()
                    total_steps_to_prune += steps_count
            
            # Get count of pruned jobs
            pruned_jobs_count = db.query(Job).filter(Job.pruned == True).count()
            
            return {
                'total_jobs': total_jobs,
                'jobs_beyond_10th': jobs_beyond_10th,
                'total_steps_to_prune': total_steps_to_prune,
                'pruned_jobs_count': pruned_jobs_count,
                'service_running': self.is_running,
                'last_checked': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting pruning stats: {e}")
            return {'error': str(e)}
        finally:
            db.close()


# Global instance
job_pruning_service = JobPruningService()
