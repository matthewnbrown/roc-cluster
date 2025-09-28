"""
Enable auto vacuum on SQLite database
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import engine, SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def enable_auto_vacuum():
    """Enable auto vacuum on SQLite database"""
    
    db = SessionLocal()
    try:
        # Check if auto vacuum is already enabled
        result = db.execute(text("PRAGMA auto_vacuum")).fetchone()
        current_setting = result[0] if result else 0
        
        if current_setting == 1:
            logger.info("Auto vacuum is already enabled (INCREMENTAL mode)")
            return
        elif current_setting == 2:
            logger.info("Auto vacuum is already enabled (FULL mode)")
            return
        
        logger.info(f"Current auto vacuum setting: {current_setting}")
        
        if current_setting == 0:
            logger.info("Auto vacuum is disabled. For existing databases, we need to perform a full vacuum first.")
            logger.info("This will enable auto vacuum and reclaim space at the same time...")
            
            # For existing databases, we need to do a full vacuum to enable auto vacuum
            # This is the only way to enable auto vacuum on an existing database
            db.execute(text("PRAGMA auto_vacuum = INCREMENTAL"))
            db.commit()
            
            logger.info("Performing full vacuum to enable auto vacuum...")
            db.execute(text("VACUUM"))
            db.commit()
            logger.info("Full vacuum completed")
            
            # Verify the setting
            result = db.execute(text("PRAGMA auto_vacuum")).fetchone()
            new_setting = result[0] if result else 0
            
            if new_setting == 1:
                logger.info("✅ Successfully enabled auto vacuum in INCREMENTAL mode")
            else:
                logger.warning(f"Auto vacuum setting is {new_setting}, expected 1")
                logger.warning("Auto vacuum may not be enabled on this database version")
        else:
            logger.info("Auto vacuum is already enabled")
        
        # Show database page count for reference
        result = db.execute(text("PRAGMA page_count")).fetchone()
        page_count = result[0] if result else 0
        logger.info(f"Database has {page_count} pages")
        
    except Exception as e:
        logger.error(f"Error enabling auto vacuum: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function for the adhoc script runner"""
    enable_auto_vacuum()

if __name__ == "__main__":
    main()
