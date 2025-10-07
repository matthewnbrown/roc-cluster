"""
Scheduled Jobs API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import json
import logging
from datetime import datetime, timezone

from api.database import get_db
from api.db_models import ScheduledJob
from api.schemas import (
    ScheduledJobCreateRequest,
    ScheduledJobResponse,
    ScheduledJobListResponse,
    ScheduledJobExecutionResponse,
    ScheduledJobExecutionListResponse,
    DailyScheduleConfig,
    OnceScheduleConfig,
    CronScheduleConfig
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()

# Global scheduler service instance
_scheduler_service = None

def set_scheduler_service(scheduler_service_instance):
    """Set the global scheduler service instance"""
    global _scheduler_service
    _scheduler_service = scheduler_service_instance

def get_scheduler_service():
    """Get the scheduler service instance"""
    if _scheduler_service is None:
        raise HTTPException(status_code=503, detail="Scheduler service not available")
    return _scheduler_service


@router.post("/", response_model=ScheduledJobResponse, status_code=201)
async def create_scheduled_job(
    request: ScheduledJobCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new scheduled job"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Use scheduler service to create the scheduled job
        response_data = await scheduler_service.create_scheduled_job(request.dict())
        
        return ScheduledJobResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scheduled job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=ScheduledJobListResponse)
async def list_scheduled_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all scheduled jobs with optional status filtering"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Use scheduler service to list scheduled jobs
        response_data = await scheduler_service.list_scheduled_jobs(status)
        
        return ScheduledJobListResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{scheduled_job_id}", response_model=ScheduledJobResponse)
async def get_scheduled_job(
    scheduled_job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific scheduled job"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Use scheduler service to get scheduled job
        response_data = await scheduler_service.get_scheduled_job(scheduled_job_id)
        
        if not response_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Scheduled job with ID {scheduled_job_id} not found"
            )
        
        return ScheduledJobResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scheduled job {scheduled_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{scheduled_job_id}", response_model=ScheduledJobResponse)
async def update_scheduled_job(
    scheduled_job_id: int,
    request: ScheduledJobCreateRequest,
    db: Session = Depends(get_db)
):
    """Update a scheduled job"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Use scheduler service to update the scheduled job
        response_data = await scheduler_service.update_scheduled_job(scheduled_job_id, request.dict())
        
        if not response_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Scheduled job with ID {scheduled_job_id} not found"
            )
        
        return ScheduledJobResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scheduled job {scheduled_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{scheduled_job_id}/status")
async def update_scheduled_job_status(
    scheduled_job_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Update the status of a scheduled job"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Extract status from request body
        status = request_data.get("status")
        if not status:
            raise HTTPException(
                status_code=400, 
                detail="Status is required in request body"
            )
        
        # Validate status
        valid_statuses = ["active", "paused", "completed", "cancelled", "failed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Use scheduler service to update status
        success = await scheduler_service.update_scheduled_job_status(scheduled_job_id, status)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Scheduled job with ID {scheduled_job_id} not found"
            )
        
        return {"message": f"Scheduled job status updated to '{status}'"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scheduled job status {scheduled_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{scheduled_job_id}")
async def delete_scheduled_job(
    scheduled_job_id: int,
    db: Session = Depends(get_db)
):
    """Delete a scheduled job"""
    try:
        scheduler_service = get_scheduler_service()
        
        # Use scheduler service to delete scheduled job
        success = await scheduler_service.delete_scheduled_job(scheduled_job_id)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Scheduled job with ID {scheduled_job_id} not found"
            )
        
        return {"message": f"Scheduled job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled job {scheduled_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{scheduled_job_id}/executions", response_model=ScheduledJobExecutionListResponse)
async def list_scheduled_job_executions(
    scheduled_job_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List executions for a specific scheduled job"""
    try:
        # Verify scheduled job exists
        scheduled_job = db.query(ScheduledJob).filter(
            ScheduledJob.id == scheduled_job_id
        ).first()
        
        if not scheduled_job:
            raise HTTPException(
                status_code=404, 
                detail=f"Scheduled job with ID {scheduled_job_id} not found"
            )
        
        # Get executions
        from api.db_models import ScheduledJobExecution
        executions = db.query(ScheduledJobExecution).filter(
            ScheduledJobExecution.scheduled_job_id == scheduled_job_id
        ).order_by(ScheduledJobExecution.scheduled_at.desc()).limit(limit).all()
        
        execution_responses = []
        for execution in executions:
            execution_responses.append(ScheduledJobExecutionResponse(
                id=execution.id,
                scheduled_job_id=execution.scheduled_job_id,
                job_id=execution.job_id,
                scheduled_at=execution.scheduled_at,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                status=execution.status.value,
                error_message=execution.error_message
            ))
        
        return ScheduledJobExecutionListResponse(
            executions=execution_responses,
            total=len(execution_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing scheduled job executions {scheduled_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
