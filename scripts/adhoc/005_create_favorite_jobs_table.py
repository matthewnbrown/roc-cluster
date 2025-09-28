"""
Adhoc script to create the favorite_jobs table
"""

import logging
from api.database import SessionLocal, engine
from api.db_models import Base, FavoriteJob

logger = logging.getLogger(__name__)

def main():
    """Create the favorite_jobs table"""
    try:
        # Create the table
        FavoriteJob.__table__.create(engine, checkfirst=True)
        logger.info("Successfully created favorite_jobs table")
        
        # Verify the table was created
        db = SessionLocal()
        try:
            # Try to query the table to verify it exists
            db.query(FavoriteJob).count()
            logger.info("Verified favorite_jobs table exists and is accessible")
        except Exception as e:
            logger.error(f"Error verifying favorite_jobs table: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creating favorite_jobs table: {e}")
        raise
