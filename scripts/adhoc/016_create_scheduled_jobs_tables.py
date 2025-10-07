"""
Migration script to create scheduled jobs tables
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import SessionLocal, engine
from api.db_models import Base, ScheduledJob, ScheduledJobExecution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create scheduled jobs tables"""
    try:
        logger.info("Creating scheduled jobs tables...")
        
        # Create the new tables
        ScheduledJob.__table__.create(engine, checkfirst=True)
        ScheduledJobExecution.__table__.create(engine, checkfirst=True)
        
        logger.info("Successfully created scheduled jobs tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating scheduled jobs tables: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed")
        sys.exit(1)

