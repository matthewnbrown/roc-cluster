#!/usr/bin/env python3
"""
Startup script to clean up expired scheduled jobs.

This script handles scheduled jobs that have a next_execution_at time in the past:
- For "once" jobs: Marks them as canceled
- For "cron" and "daily" jobs: Recalculates next execution time

It's designed to be run during application startup or as a standalone maintenance script.

Usage:
    python scripts/cleanup_expired_jobs.py

Environment Variables:
    DATABASE_URL: Database connection string (optional, defaults to SQLite)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.database import SessionLocal
from api.scheduler_service import SchedulerService
from api.job_manager import JobManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def cleanup_expired_jobs():
    """Clean up expired scheduled jobs."""
    try:
        logger.info("Starting cleanup of expired scheduled jobs...")
        
        # Initialize services (we don't need a running scheduler for cleanup)
        job_manager = JobManager()
        scheduler_service = SchedulerService(job_manager)
        
        # Run the cleanup
        processed_count = await scheduler_service.cleanup_expired_scheduled_jobs()
        
        if processed_count > 0:
            logger.info(f"✅ Successfully processed {processed_count} expired scheduled jobs (canceled once jobs, recalculated recurring jobs)")
        else:
            logger.info("✅ No expired scheduled jobs found to process")
            
        return processed_count
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        raise


def main():
    """Main entry point for the cleanup script."""
    try:
        # Check if database exists
        db_path = project_root / "data" / "roc_cluster.db"
        if not db_path.exists():
            logger.warning(f"Database file not found at {db_path}")
            logger.info("If this is a new installation, this is normal.")
            return 0
        
        # Run the async cleanup
        processed_count = asyncio.run(cleanup_expired_jobs())
        
        logger.info("🏁 Cleanup completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Cleanup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Cleanup failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
