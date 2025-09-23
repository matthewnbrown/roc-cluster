"""
Favorite Jobs API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json
import logging
from datetime import datetime, timezone

from api.database import get_db
from api.db_models import FavoriteJob
from api.schemas import (
    FavoriteJobCreateRequest, 
    FavoriteJobResponse, 
    FavoriteJobListResponse
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=FavoriteJobResponse, status_code=201)
async def create_favorite_job(
    request: FavoriteJobCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new favorite job configuration"""
    try:
        # Check if a favorite with the same name already exists
        existing_favorite = db.query(FavoriteJob).filter(
            FavoriteJob.name == request.name
        ).first()
        
        if existing_favorite:
            raise HTTPException(
                status_code=400, 
                detail=f"A favorite job with name '{request.name}' already exists"
            )
        
        # Create new favorite job
        favorite_job = FavoriteJob(
            name=request.name,
            description=request.description,
            job_config=json.dumps(request.job_config)
        )
        
        db.add(favorite_job)
        db.commit()
        db.refresh(favorite_job)
        
        logger.info(f"Created favorite job: {favorite_job.name} (ID: {favorite_job.id})")
        
        return FavoriteJobResponse(
            id=favorite_job.id,
            name=favorite_job.name,
            description=favorite_job.description,
            job_config=json.loads(favorite_job.job_config),
            created_at=favorite_job.created_at,
            updated_at=favorite_job.updated_at,
            usage_count=favorite_job.usage_count,
            last_used_at=favorite_job.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating favorite job: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=FavoriteJobListResponse)
async def list_favorite_jobs(
    db: Session = Depends(get_db)
):
    """List all favorite job configurations"""
    try:
        favorite_jobs = db.query(FavoriteJob).order_by(
            FavoriteJob.usage_count.desc(),
            FavoriteJob.last_used_at.desc(),
            FavoriteJob.created_at.desc()
        ).all()
        
        favorite_job_responses = []
        for fav_job in favorite_jobs:
            favorite_job_responses.append(FavoriteJobResponse(
                id=fav_job.id,
                name=fav_job.name,
                description=fav_job.description,
                job_config=json.loads(fav_job.job_config),
                created_at=fav_job.created_at,
                updated_at=fav_job.updated_at,
                usage_count=fav_job.usage_count,
                last_used_at=fav_job.last_used_at
            ))
        
        return FavoriteJobListResponse(
            favorite_jobs=favorite_job_responses,
            total=len(favorite_job_responses)
        )
        
    except Exception as e:
        logger.error(f"Error listing favorite jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{favorite_job_id}", response_model=FavoriteJobResponse)
async def get_favorite_job(
    favorite_job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific favorite job configuration"""
    try:
        favorite_job = db.query(FavoriteJob).filter(
            FavoriteJob.id == favorite_job_id
        ).first()
        
        if not favorite_job:
            raise HTTPException(
                status_code=404, 
                detail=f"Favorite job with ID {favorite_job_id} not found"
            )
        
        return FavoriteJobResponse(
            id=favorite_job.id,
            name=favorite_job.name,
            description=favorite_job.description,
            job_config=json.loads(favorite_job.job_config),
            created_at=favorite_job.created_at,
            updated_at=favorite_job.updated_at,
            usage_count=favorite_job.usage_count,
            last_used_at=favorite_job.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting favorite job {favorite_job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{favorite_job_id}", response_model=FavoriteJobResponse)
async def update_favorite_job(
    favorite_job_id: int,
    request: FavoriteJobCreateRequest,
    db: Session = Depends(get_db)
):
    """Update a favorite job configuration"""
    try:
        favorite_job = db.query(FavoriteJob).filter(
            FavoriteJob.id == favorite_job_id
        ).first()
        
        if not favorite_job:
            raise HTTPException(
                status_code=404, 
                detail=f"Favorite job with ID {favorite_job_id} not found"
            )
        
        # Check if another favorite with the same name exists (excluding current one)
        existing_favorite = db.query(FavoriteJob).filter(
            FavoriteJob.name == request.name,
            FavoriteJob.id != favorite_job_id
        ).first()
        
        if existing_favorite:
            raise HTTPException(
                status_code=400, 
                detail=f"A favorite job with name '{request.name}' already exists"
            )
        
        # Update the favorite job
        favorite_job.name = request.name
        favorite_job.description = request.description
        favorite_job.job_config = json.dumps(request.job_config)
        favorite_job.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(favorite_job)
        
        logger.info(f"Updated favorite job: {favorite_job.name} (ID: {favorite_job.id})")
        
        return FavoriteJobResponse(
            id=favorite_job.id,
            name=favorite_job.name,
            description=favorite_job.description,
            job_config=json.loads(favorite_job.job_config),
            created_at=favorite_job.created_at,
            updated_at=favorite_job.updated_at,
            usage_count=favorite_job.usage_count,
            last_used_at=favorite_job.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating favorite job {favorite_job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{favorite_job_id}")
async def delete_favorite_job(
    favorite_job_id: int,
    db: Session = Depends(get_db)
):
    """Delete a favorite job configuration"""
    try:
        favorite_job = db.query(FavoriteJob).filter(
            FavoriteJob.id == favorite_job_id
        ).first()
        
        if not favorite_job:
            raise HTTPException(
                status_code=404, 
                detail=f"Favorite job with ID {favorite_job_id} not found"
            )
        
        favorite_name = favorite_job.name
        db.delete(favorite_job)
        db.commit()
        
        logger.info(f"Deleted favorite job: {favorite_name} (ID: {favorite_job_id})")
        
        return {"message": f"Favorite job '{favorite_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting favorite job {favorite_job_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{favorite_job_id}/use")
async def mark_favorite_job_used(
    favorite_job_id: int,
    db: Session = Depends(get_db)
):
    """Mark a favorite job as used (increment usage count and update last used time)"""
    try:
        favorite_job = db.query(FavoriteJob).filter(
            FavoriteJob.id == favorite_job_id
        ).first()
        
        if not favorite_job:
            raise HTTPException(
                status_code=404, 
                detail=f"Favorite job with ID {favorite_job_id} not found"
            )
        
        # Update usage statistics
        favorite_job.usage_count += 1
        favorite_job.last_used_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"Marked favorite job as used: {favorite_job.name} (ID: {favorite_job.id})")
        
        return {"message": f"Favorite job '{favorite_job.name}' marked as used"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking favorite job {favorite_job_id} as used: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
