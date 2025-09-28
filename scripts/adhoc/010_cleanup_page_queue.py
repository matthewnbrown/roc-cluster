"""
Adhoc script to clean up all page_queue records
"""

import logging
from api.database import SessionLocal
from api.db_models import PageQueue

logger = logging.getLogger(__name__)

def main():
    """Clean up all page_queue records"""
    db = SessionLocal()
    try:
        # Count total records
        total_count = db.query(PageQueue).count()
        
        logger.info(f"Page queue cleanup - Found {total_count} total records to delete")
        
        if total_count == 0:
            logger.info("No records to clean up")
            return
        
        # Delete all records
        deleted_count = db.query(PageQueue).delete()
        
        db.commit()
        
        logger.info(f"Successfully deleted {deleted_count} page queue records")
        
    except Exception as e:
        logger.error(f"Error during page queue cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()
