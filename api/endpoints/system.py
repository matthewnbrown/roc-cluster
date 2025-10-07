"""
System endpoints for maintenance and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta

from api.job_pruning_service import job_pruning_service
from api.database import SessionLocal, auto_save_service
from api.db_models import AccountLog
from api.async_logger import async_logger
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pruning/stats")
async def get_pruning_stats():
    """Get job pruning statistics"""
    try:
        stats = await job_pruning_service.get_pruning_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting pruning stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/database/stats")
async def get_database_stats():
    """Get database statistics including vacuum info"""
    try:
        from api.database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get database statistics
            page_count = db.execute(text("PRAGMA page_count")).fetchone()[0]
            page_size = db.execute(text("PRAGMA page_size")).fetchone()[0]
            auto_vacuum = db.execute(text("PRAGMA auto_vacuum")).fetchone()[0]
            freelist_count = db.execute(text("PRAGMA freelist_count")).fetchone()[0]
            
            # Calculate database size
            db_size_bytes = page_count * page_size
            db_size_mb = db_size_bytes / (1024 * 1024)
            
            # Get auto vacuum mode description
            auto_vacuum_modes = {0: "NONE", 1: "INCREMENTAL", 2: "FULL"}
            auto_vacuum_mode = auto_vacuum_modes.get(auto_vacuum, "UNKNOWN")
            
            return {
                "success": True,
                "data": {
                    "page_count": page_count,
                    "page_size": page_size,
                    "database_size_bytes": db_size_bytes,
                    "database_size_mb": round(db_size_mb, 2),
                    "freelist_count": freelist_count,
                    "auto_vacuum_mode": auto_vacuum_mode,
                    "auto_vacuum_enabled": auto_vacuum > 0,
                    "wasted_space_pages": freelist_count,
                    "wasted_space_mb": round((freelist_count * page_size) / (1024 * 1024), 2)
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notifications")
async def get_system_notifications(
    limit: int = 10,
    notification_type: str = None
):
    """Get recent system notifications"""
    try:
        db = SessionLocal()
        try:
            # Query for system notifications from the last 24 hours
            since = datetime.now() - timedelta(days=1)
            
            query = db.query(AccountLog).filter(
                AccountLog.action == "system_notification",
                AccountLog.timestamp >= since
            )
            
            if notification_type:
                # Filter by specific notification type if provided
                query = query.filter(AccountLog.details.like(f'%"type":"{notification_type}"%'))
            
            notifications = query.order_by(AccountLog.timestamp.desc()).limit(limit).all()
            
            result = []
            for notification in notifications:
                try:
                    import json
                    details = json.loads(notification.details) if notification.details else {}
                    result.append({
                        "id": notification.id,
                        "timestamp": notification.timestamp.isoformat(),
                        "success": notification.success,
                        "message": details.get("message", ""),
                        "type": details.get("type", ""),
                        "details": details
                    })
                except json.JSONDecodeError:
                    # Skip malformed JSON
                    continue
            
            return {
                "success": True,
                "data": {
                    "notifications": result,
                    "total": len(result),
                    "since": since.isoformat()
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting system notifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pruning/trigger")
async def trigger_manual_pruning():
    """Manually trigger job pruning (for testing/admin purposes)"""
    try:
        await job_pruning_service._prune_job_steps()
        return {
            "success": True,
            "message": "Job pruning completed successfully"
        }
    except Exception as e:
        logger.error(f"Error triggering manual pruning: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vacuum")
async def trigger_manual_vacuum():
    """Manually trigger database vacuum (for admin purposes)"""
    try:
        from api.database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get database info before vacuum
            page_count_before = db.execute(text("PRAGMA page_count")).fetchone()[0]
            auto_vacuum = db.execute(text("PRAGMA auto_vacuum")).fetchone()[0]
            freelist_before = db.execute(text("PRAGMA freelist_count")).fetchone()[0]
            
            # Perform vacuum based on auto_vacuum mode
            if auto_vacuum == 1:  # INCREMENTAL mode
                # Use incremental vacuum
                db.execute(text("PRAGMA incremental_vacuum"))
                logger.info("Performed incremental vacuum")
            elif auto_vacuum == 2:  # FULL mode
                # Use full vacuum
                db.execute(text("VACUUM"))
                logger.info("Performed full vacuum")
            else:  # NONE mode
                # Use ANALYZE and then try to reclaim space
                db.execute(text("ANALYZE"))
                db.execute(text("PRAGMA optimize"))
                # Try to force some cleanup
                db.execute(text("PRAGMA shrink_memory"))
                logger.info("Performed analyze and optimize (auto vacuum disabled)")
            
            db.commit()
            
            # Get database info after vacuum
            page_count_after = db.execute(text("PRAGMA page_count")).fetchone()[0]
            freelist_after = db.execute(text("PRAGMA freelist_count")).fetchone()[0]
            pages_freed = page_count_before - page_count_after
            freelist_freed = freelist_before - freelist_after
            
            return {
                "success": True,
                "message": "Database vacuum completed successfully",
                "details": {
                    "pages_before": page_count_before,
                    "pages_after": page_count_after,
                    "pages_freed": pages_freed,
                    "freelist_before": freelist_before,
                    "freelist_after": freelist_after,
                    "freelist_freed": freelist_freed,
                    "auto_vacuum_mode": auto_vacuum,
                    "operation": "incremental" if auto_vacuum == 1 else "full" if auto_vacuum == 2 else "analyze_optimize"
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error triggering manual vacuum: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vacuum/full")
async def trigger_full_vacuum():
    """Manually trigger full database vacuum (more aggressive, reclaims all space)"""
    try:
        from api.database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get database info before vacuum
            page_count_before = db.execute(text("PRAGMA page_count")).fetchone()[0]
            freelist_before = db.execute(text("PRAGMA freelist_count")).fetchone()[0]
            
            # Perform full vacuum (this is more aggressive and reclaims all space)
            logger.info("Performing full database vacuum...")
            db.execute(text("VACUUM"))
            db.commit()
            logger.info("Full vacuum completed")
            
            # Get database info after vacuum
            page_count_after = db.execute(text("PRAGMA page_count")).fetchone()[0]
            freelist_after = db.execute(text("PRAGMA freelist_count")).fetchone()[0]
            pages_freed = page_count_before - page_count_after
            freelist_freed = freelist_before - freelist_after
            
            return {
                "success": True,
                "message": "Full database vacuum completed successfully",
                "details": {
                    "pages_before": page_count_before,
                    "pages_after": page_count_after,
                    "pages_freed": pages_freed,
                    "freelist_before": freelist_before,
                    "freelist_after": freelist_after,
                    "freelist_freed": freelist_freed,
                    "operation": "full_vacuum"
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error triggering full vacuum: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including service status"""
    try:
        # Get basic health info
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "job_pruning_service": {
                    "running": job_pruning_service.is_running,
                    "scheduler_active": job_pruning_service.scheduler is not None and job_pruning_service.scheduler.running if job_pruning_service.scheduler else False
                }
            }
        }
        
        # Add pruning stats
        pruning_stats = await job_pruning_service.get_pruning_stats()
        health_info["job_pruning"] = pruning_stats
        
        return health_info
        
    except Exception as e:
        logger.error(f"Error in detailed health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/auto-save/status")
async def get_auto_save_status():
    """Get auto-save service status"""
    try:
        return {
            "success": True,
            "data": {
                "enabled": settings.USE_IN_MEMORY_DB and settings.AUTO_SAVE_ENABLED,
                "in_memory_db": settings.USE_IN_MEMORY_DB,
                "auto_save_enabled": settings.AUTO_SAVE_ENABLED,
                "auto_save_interval": settings.AUTO_SAVE_INTERVAL,
                "auto_save_background": settings.AUTO_SAVE_BACKGROUND,
                "auto_save_memory_snapshot": settings.AUTO_SAVE_MEMORY_SNAPSHOT,
                "running": auto_save_service._running
            }
        }
    except Exception as e:
        logger.error(f"Error getting auto-save status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auto-save/force")
async def force_auto_save():
    """Force an immediate save of in-memory database to file"""
    try:
        if not settings.USE_IN_MEMORY_DB:
            raise HTTPException(status_code=400, detail="Not using in-memory database")
        
        await auto_save_service.force_save()
        return {
            "success": True,
            "message": "Database saved to file successfully"
        }
    except Exception as e:
        logger.error(f"Error forcing auto-save: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
