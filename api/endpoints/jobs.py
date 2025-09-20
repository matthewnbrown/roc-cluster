"""
Job endpoints for managing asynchronous bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from api.schemas import (
    JobCreateRequest, JobResponse, JobListResponse, JobCancelRequest,
    JobStatusEnum
)
from api.job_manager import JobManager
from api.db_models import JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


def get_job_manager() -> JobManager:
    """Dependency to get job manager"""
    from main import job_manager
    if job_manager is None:
        raise HTTPException(status_code=503, detail="Job manager not initialized")
    return job_manager


@router.post("/", response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    manager: JobManager = Depends(get_job_manager)
):
    """Create a new job with multiple steps"""
    try:
        # Convert steps to the format expected by JobManager
        steps_data = []
        for step in request.steps:
            step_data = {
                "action_type": step.action_type,
                "max_retries": step.max_retries
            }
            
            # Handle account_ids and/or cluster_ids
            if step.account_ids:
                step_data["account_ids"] = step.account_ids
            if step.cluster_ids:
                step_data["cluster_ids"] = step.cluster_ids
            
            # Validate that at least one targeting method is provided
            if not step.account_ids and not step.cluster_ids:
                raise HTTPException(status_code=400, detail="Step must specify at least account_ids or cluster_ids")
            
            if step.parameters:
                step_data["parameters"] = step.parameters
            step_data["skip_on_error"] = step.skip_on_error
            steps_data.append(step_data)
        
        job = await manager.create_job(
            name=request.name,
            description=request.description,
            steps=steps_data,
            parallel_execution=request.parallel_execution
        )
        
        return job
        
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatusEnum] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    manager: JobManager = Depends(get_job_manager)
):
    """List jobs with optional filtering"""
    try:
        # Convert string status to enum
        status_filter = None
        if status:
            status_filter = JobStatus(status.value)
        
        result = await manager.list_jobs(
            status=status_filter,
            page=page,
            per_page=per_page
        )
        
        return JobListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    include_steps: bool = Query(False, description="Include job steps in response"),
    manager: JobManager = Depends(get_job_manager)
):
    """Get a job by ID"""
    try:
        job = await manager.get_job(job_id, include_steps=include_steps)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    request: JobCancelRequest,
    manager: JobManager = Depends(get_job_manager)
):
    """Cancel a running job"""
    try:
        success = await manager.cancel_job(job_id, request.reason)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: int,
    manager: JobManager = Depends(get_job_manager)
):
    """Get job status (lightweight endpoint)"""
    try:
        job = await manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job.id,
            "status": job.status,
            "progress": {
                "total_steps": job.total_steps,
                "completed_steps": job.completed_steps,
                "failed_steps": job.failed_steps
            },
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/valid-action-types")
async def get_valid_action_types(
    manager: JobManager = Depends(get_job_manager)
):
    """Get list of valid action types for job steps"""
    try:
        valid_types = manager._get_valid_action_types()
        return {
            "valid_action_types": valid_types,
            "count": len(valid_types)
        }
    except Exception as e:
        logger.error(f"Error getting valid action types: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
