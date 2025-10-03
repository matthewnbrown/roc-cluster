"""
Job endpoints for managing asynchronous bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging
import uuid
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
            # Skip empty steps (no action_type or empty action_type)
            if not step.action_type or not step.action_type.strip():
                continue
                
            step_data = {
                "action_type": step.action_type,
                "max_retries": step.max_retries,
                "is_async": step.is_async
            }
            
            # Handle account_ids and/or cluster_ids
            if step.account_ids:
                step_data["account_ids"] = step.account_ids
            if step.cluster_ids:
                step_data["cluster_ids"] = step.cluster_ids
            
            # Validate that at least one targeting method is provided (except for delay steps)
            has_account_ids = step.account_ids and len(step.account_ids) > 0
            has_cluster_ids = step.cluster_ids and len(step.cluster_ids) > 0
            
            if (step.action_type != "delay" and 
                not has_account_ids and not has_cluster_ids):
                raise HTTPException(status_code=400, detail="Step must specify at least account_ids or cluster_ids")
            
            if step.parameters:
                step_data["parameters"] = step.parameters

            steps_data.append(step_data)
        
        # Ensure there's at least one valid step
        if not steps_data:
            raise HTTPException(status_code=400, detail="Job must have at least one valid step")
        
        # Generate job name and description if not provided
        job_name = request.name
        job_description = request.description
        
        if not job_name or job_name.strip() == '':
            # Generate a random GUID for the job name
            job_name = str(uuid.uuid4())
            
            # Create CSV description from step action types
            step_names = [step.action_type for step in request.steps if step.action_type and step.action_type.strip()]
            job_description = ', '.join(step_names) if step_names else 'No steps defined'
        
        job = await manager.create_job(
            name=job_name,
            description=job_description,
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
        
        # Calculate overall job progress percentage based on step completion
        # For async jobs, this represents the percentage of steps that have completed
        job_progress_percentage = 0
        if total_steps > 0:
            job_progress_percentage = round(((completed_steps + failed_steps) / total_steps * 100), 2)
        
        # Extract step progress information - get real-time data from memory
        step_progress = []
        if job.steps:
            for step in job.steps:
                # Get real-time step progress from memory
                memory_progress = manager._get_step_progress(step.id)
                
                # Debug logging for async steps
                if step.is_async:
                    logger.info(f"Async step {step.id} progress: memory={memory_progress}, db_total={step.total_accounts}, db_processed={step.processed_accounts}, status={step.status.value}")
                
                # For async steps, prefer memory data if available, otherwise use database
                # For sync steps, use database data as they complete immediately
                # Check if memory progress exists (even for delay steps with 0 accounts)
                if step.id in manager._step_progress:
                    # Use in-memory progress data (most up-to-date for async steps)
                    total_accounts = memory_progress["total_accounts"]
                    processed_accounts = memory_progress["processed_accounts"]
                    successful_accounts = memory_progress["successful_accounts"]
                    failed_accounts = memory_progress["failed_accounts"]
                else:
                    # Fallback to database data
                    total_accounts = step.total_accounts
                    processed_accounts = step.processed_accounts
                    successful_accounts = step.successful_accounts
                    failed_accounts = step.failed_accounts
                
                # Calculate progress percentage
                progress_percentage = 0
                if total_accounts > 0:
                    progress_percentage = round((processed_accounts / total_accounts * 100), 2)
                elif step.action_type == "delay":
                    # Delay steps with 0 accounts show 100% when completed
                    progress_percentage = 100 if step.status.value in ["completed", "failed"] else 0
                
                step_progress.append({
                    "id": step.id,
                    "step_order": step.step_order,
                    "action_type": step.action_type,
                    "status": step.status.value,
                    "total_accounts": total_accounts,
                    "processed_accounts": processed_accounts,
                    "successful_accounts": successful_accounts,
                    "failed_accounts": failed_accounts,
                    "progress_percentage": progress_percentage
                })
        
        return {
            "job_id": job.id,
            "name": job.name,
            "description": job.description,
            "status": job.status,
            "parallel_execution": job.parallel_execution,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "progress": {
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "percentage": job_progress_percentage
            },
            "steps": step_progress,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job progress {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
