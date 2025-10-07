"""
ROC Cluster Management API

A lightweight API for managing multiple ROC accounts simultaneously.
Built on FastAPI for high performance and easy frontend integration.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import List, Dict, Any, Optional
import logging

from api.database import init_db, get_db, auto_save_service
from api.db_models import Account, Cluster, ClusterUser
from api.schemas import AccountCreate, AccountResponse
from api.account_manager import AccountManager
from api.endpoints import accounts, actions, clusters, jobs, armory, reference_data, page_queue, favorite_jobs, scheduled_jobs, system
from api.async_logger import async_logger
from api.captcha_feedback_service import captcha_feedback_service
from api.page_data_service import page_data_service
from api.job_pruning_service import job_pruning_service

# Configure logging
from config import settings
import logging.config

# Configure logging with file support if LOG_FILE is specified
log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': settings.LOG_LEVEL.upper(),
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': settings.LOG_LEVEL.upper(),
        'handlers': ['console'],
    },
}

# Add file handler if LOG_FILE is specified
if settings.LOG_FILE:
    log_config['handlers']['file'] = {
        'class': 'logging.FileHandler',
        'level': settings.LOG_LEVEL.upper(),
        'formatter': 'default',
        'filename': settings.LOG_FILE,
        'mode': 'a',
    }
    log_config['root']['handlers'].append('file')

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)

# Log the logging configuration
logger.info(f"Logging configured - Level: {settings.LOG_LEVEL.upper()}")
if settings.LOG_FILE:
    logger.info(f"Logging to file: {settings.LOG_FILE}")
else:
    logger.info("Logging to console only")

# Global instances
account_manager: Optional[AccountManager] = None
job_manager: Optional[Any] = None
scheduler_service: Optional[Any] = None

async def create_initial_all_users_cluster():
    """Create the initial all_users cluster and add all existing users to it"""
    from api.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Check if all_users cluster already exists
        all_users_cluster = db.query(Cluster).filter(Cluster.name == "all_users").first()
        
        if not all_users_cluster:
            # Create the all_users cluster
            all_users_cluster = Cluster(
                name="all_users",
                description="Default cluster containing all users"
            )
            db.add(all_users_cluster)
            db.commit()
            db.refresh(all_users_cluster)
            logger.info("Created all_users cluster")
        
        # Get all existing accounts
        all_accounts = db.query(Account).all()
        
        # Add all accounts to the all_users cluster if they're not already there
        added_count = 0
        for account in all_accounts:
            existing_cluster_user = db.query(ClusterUser).filter(
                ClusterUser.cluster_id == all_users_cluster.id,
                ClusterUser.account_id == account.id
            ).first()
            
            if not existing_cluster_user:
                cluster_user = ClusterUser(
                    cluster_id=all_users_cluster.id,
                    account_id=account.id
                )
                db.add(cluster_user)
                added_count += 1
        
        if added_count > 0:
            db.commit()
            logger.info(f"Added {added_count} existing users to all_users cluster")
        
    except Exception as e:
        logger.error(f"Error creating initial all_users cluster: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global account_manager, job_manager, scheduler_service
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Run adhoc scripts (migrations, setup, etc.)
    from scripts.adhoc import run_adhoc_scripts, migrate_legacy_executed_scripts
    migrate_legacy_executed_scripts()  # Migrate legacy file-based tracking to database
    run_adhoc_scripts()
    logger.info("Adhoc scripts completed")
    
    # Create initial all_users cluster
    await create_initial_all_users_cluster()
    logger.info("Initial all_users cluster created/verified")
    
    # Start async logger
    await async_logger.start()
    
    # Register handlers for system logging
    from api.db_models import AccountLog
    from api.job_pruning_service import system_notification_handler, job_pruning_handler
    async_logger.register_handler("job_pruning", AccountLog, job_pruning_handler)
    async_logger.register_handler("system_notification", AccountLog, system_notification_handler)
    
    logger.info("Async logger started")
    
    # Start captcha feedback service
    await captcha_feedback_service.start()
    logger.info("Captcha feedback service started")
    
    # Start page data service
    if settings.USE_PAGE_DATA_SERVICE:
        await page_data_service.start()
        logger.info("Page data service started")
    else:
        logger.info("Page data service not started")
    
    account_manager = AccountManager()
    logger.info("Account manager initialized")
    
    # Initialize job manager
    from api.job_manager import JobManager
    job_manager = JobManager(account_manager)
    logger.info("Job manager initialized")
    
    # Initialize scheduler service
    from api.scheduler_service import SchedulerService
    scheduler_service = SchedulerService(job_manager)
    
    # Clean up expired scheduled jobs before starting scheduler
    try:
        processed_count = await scheduler_service.cleanup_expired_scheduled_jobs()
        if processed_count > 0:
            logger.info(f"Processed {processed_count} expired scheduled jobs during startup (canceled once jobs, recalculated recurring jobs)")
        else:
            logger.info("No expired scheduled jobs found during startup")
    except Exception as e:
        logger.error(f"Error cleaning up expired scheduled jobs during startup: {e}")
        # Don't fail startup if cleanup fails
    
    await scheduler_service.start_scheduler()
    logger.info("Scheduler service initialized and started")
    
    # Set scheduler service in endpoints
    from api.endpoints import scheduled_jobs
    scheduled_jobs.set_scheduler_service(scheduler_service)
    
    # Start job pruning service
    await job_pruning_service.start()
    logger.info("Job pruning service started")
    
    # Start auto-save service for in-memory database
    await auto_save_service.start()
    logger.info("Auto-save service started")
    
    yield
    
    # Stop auto-save service
    await auto_save_service.stop()
    logger.info("Auto-save service stopped")
    
    # Stop scheduler service
    if scheduler_service:
        await scheduler_service.stop_scheduler()
        logger.info("Scheduler service stopped")
    
    # Stop job pruning service
    await job_pruning_service.stop()
    logger.info("Job pruning service stopped")
    
    # Stop page data service
    if settings.USE_PAGE_DATA_SERVICE:
        await page_data_service.stop()
        logger.info("Page data service stopped")
    
    # Stop captcha feedback service
    await captcha_feedback_service.stop()
    logger.info("Captcha feedback service stopped")
    
    # Stop async logger
    await async_logger.stop()
    logger.info("Async logger stopped")
    
    # Cleanup account manager
    if account_manager:
        await account_manager.cleanup()
        logger.info("Account manager cleaned up")
    
    # Close database engine
    from api.database import engine
    engine.dispose()
    logger.info("Database engine disposed")
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="ROC Cluster Management API",
    description="Lightweight API for managing multiple ROC accounts",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(actions.router, prefix="/api/v1/actions", tags=["actions"])
app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(armory.router, prefix="/api/v1/armory", tags=["armory"])
app.include_router(reference_data.router, prefix="/api/v1/reference-data", tags=["reference-data"])
app.include_router(page_queue.router, prefix="/api/v1/page-queue", tags=["page-queue"])
app.include_router(favorite_jobs.router, prefix="/api/v1/favorite-jobs", tags=["favorite-jobs"])
app.include_router(scheduled_jobs.router, prefix="/api/v1/scheduled-jobs", tags=["scheduled-jobs"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ROC Cluster Management API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "account_manager": account_manager is not None,
        "database": "connected"  # Add actual DB health check
    }

# Dependency to get account manager
def get_account_manager() -> AccountManager:
    if account_manager is None:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    return account_manager

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
