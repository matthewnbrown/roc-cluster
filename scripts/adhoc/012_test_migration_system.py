"""
Test script for the new database migration system
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from api.database import SessionLocal
from api.db_models import DatabaseMigration

logger = logging.getLogger(__name__)

def main():
    """Test the migration system by checking database migrations table"""
    db = SessionLocal()
    try:
        # Check if migrations table exists and has data
        migrations = db.query(DatabaseMigration).all()
        logger.info(f"Found {len(migrations)} migration records in database:")
        
        for migration in migrations:
            status = "✅ SUCCESS" if migration.success else "❌ FAILED"
            version_info = f" v{migration.version}" if migration.version else ""
            order_info = f" (order: {migration.execution_order})" if migration.execution_order else ""
            logger.info(f"  - {migration.script_name}{version_info}: {status} ({migration.executed_at}){order_info}")
            if migration.error_message:
                logger.info(f"    Error: {migration.error_message}")
        
        logger.info("Migration system test completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing migration system: {e}")
        raise
    finally:
        db.close()
