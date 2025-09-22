"""
Page Queue API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from api.database import get_db
from api.page_data_service import page_data_service
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/stats")
async def get_queue_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get page queue statistics"""
    try:
        stats = page_data_service.get_queue_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check if page data service is running"""
    return {
        "success": True,
        "data": {
            "service_running": page_data_service._running,
            "status": "healthy" if page_data_service._running else "stopped"
        }
    }
