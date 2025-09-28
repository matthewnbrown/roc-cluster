"""
Migration script to add the pruned field to existing jobs
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import engine, SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def add_pruned_field_to_jobs():
    """Add the pruned field to the jobs table if it doesn't exist"""
    
    db = SessionLocal()
    try:
        # Check if the pruned column already exists
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('jobs') 
            WHERE name = 'pruned'
        """)).fetchone()
        
        if result and result.count > 0:
            logger.info("Pruned column already exists in jobs table")
            return
        
        # Add the pruned column
        logger.info("Adding pruned column to jobs table...")
        db.execute(text("ALTER TABLE jobs ADD COLUMN pruned BOOLEAN DEFAULT FALSE NOT NULL"))
        db.commit()
        
        logger.info("Successfully added pruned column to jobs table")
        
    except Exception as e:
        logger.error(f"Error adding pruned field to jobs table: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function for the adhoc script runner"""
    add_pruned_field_to_jobs()

if __name__ == "__main__":
    main()
