"""
Job endpoints for managing asynchronous bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging
from datetime import datetime, timezone

from api.schemas import (
    JobCreateRequest, JobResponse, JobListResponse, JobCancelRequest,
    JobStatusEnum
)
from api.job_manager import JobManager
from api.db_models import JobStatus, JobStep

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

            steps_data.append(step_data)
        
        job = await manager.create_job(
            name=request.name,
            description=request.description,
            steps=steps_data,
            parallel_execution=request.parallel_execution
        )
        
        return job
        
    except Exception as e:
        logger.error(f"Error creating job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatusEnum] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    include_steps: bool = Query(True, description="Include job steps in response"),
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
            per_page=per_page,
            include_steps=include_steps
        )
        
        return JobListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/valid-action-types")
async def get_valid_action_types(
    manager: JobManager = Depends(get_job_manager)
):
    """Get detailed information about valid action types for job steps"""
    try:
        action_types = manager._get_valid_action_types()
        
        # Group by category for better organization
        categories = {}
        for action_type in action_types:
            category = action_type.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(action_type)
        
        return {
            "action_types": action_types,
            "categories": categories,
            "summary": {
                "total_action_types": len(action_types),
                "categories": list(categories.keys()),
                "user_actions": len([a for a in action_types if a.get("category") == "user_action"]),
                "self_actions": len([a for a in action_types if a.get("category") == "self_action"]),
                "info_actions": len([a for a in action_types if a.get("category") == "info_action"])
            }
        }
    except Exception as e:
        logger.error(f"Error getting valid action types: {e}", exc_info=True)
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
        logger.error(f"Error getting job {job_id}: {e}", exc_info=True)
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
        logger.error(f"Error cancelling job {job_id}: {e}", exc_info=True)
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
        
        # Get real-time progress from in-memory tracking if available
        real_time_progress = manager.get_job_progress(job_id)
        
        # Use in-memory progress if available, otherwise fall back to database values
        if real_time_progress["total"] > 0:
            completed_steps = real_time_progress["completed"]
            failed_steps = real_time_progress["failed"]
            total_steps = real_time_progress["total"]
        else:
            completed_steps = job.completed_steps
            failed_steps = job.failed_steps
            total_steps = job.total_steps
        
        return {
            "job_id": job.id,
            "status": job.status,
            "progress": {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "percentage": round((completed_steps / total_steps * 100) if total_steps > 0 else 0, 2)
            },
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{job_id}/progress")
async def get_job_progress(
    job_id: int,
    manager: JobManager = Depends(get_job_manager)
):
    """Get job progress with step details (lightweight endpoint)"""
    try:
        job = await manager.get_job(job_id, include_steps=True)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get real-time progress from in-memory tracking if available
        real_time_progress = manager.get_job_progress(job_id)
        
        # Use in-memory progress if available, otherwise fall back to database values
        if real_time_progress["total"] > 0:
            completed_steps = real_time_progress["completed"]
            failed_steps = real_time_progress["failed"]
            total_steps = real_time_progress["total"]
        else:
            completed_steps = job.completed_steps
            failed_steps = job.failed_steps
            total_steps = job.total_steps
        
        # Extract step progress information - get real-time data from memory
        step_progress = []
        if job.steps:
            for step in job.steps:
                # Get real-time step progress from memory
                memory_progress = manager._get_step_progress(step.id)
                if memory_progress["total_accounts"] > 0:
                    # Use in-memory progress data
                    step_progress.append({
                        "id": step.id,
                        "step_order": step.step_order,
                        "action_type": step.action_type,
                        "status": step.status.value,
                        "total_accounts": memory_progress["total_accounts"],
                        "processed_accounts": memory_progress["processed_accounts"],
                        "successful_accounts": memory_progress["successful_accounts"],
                        "failed_accounts": memory_progress["failed_accounts"],
                        "progress_percentage": round((memory_progress["processed_accounts"] / memory_progress["total_accounts"] * 100) if memory_progress["total_accounts"] > 0 else 0, 2)
                    })
                else:
                    # Fallback to database data if no memory progress
                    step_progress.append({
                        "id": step.id,
                        "step_order": step.step_order,
                        "action_type": step.action_type,
                        "status": step.status.value,
                        "total_accounts": step.total_accounts,
                        "processed_accounts": step.processed_accounts,
                        "successful_accounts": step.successful_accounts,
                        "failed_accounts": step.failed_accounts,
                        "progress_percentage": round((step.processed_accounts / step.total_accounts * 100) if step.total_accounts > 0 else 0, 2)
                    })
        
        return {
            "job_id": job.id,
            "status": job.status,
            "progress": {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "percentage": round((completed_steps / total_steps * 100) if total_steps > 0 else 0, 2)
            },
            "steps": step_progress,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job progress {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
