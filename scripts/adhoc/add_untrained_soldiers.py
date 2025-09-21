"""
Script to add untrained_soldiers to the soldier_types table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import SoldierType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_untrained_soldiers():
    """Add untrained_soldiers to the soldier_types table"""
    
    db = SessionLocal()
    try:
        # Check if untrained_soldiers already exists
        existing = db.query(SoldierType).filter(SoldierType.roc_soldier_type_id == "untrained_soldiers").first()
        if existing:
            logger.info("untrained_soldiers already exists in database, skipping addition")
            return
        
        # Create untrained_soldiers soldier type
        soldier_type = SoldierType(
            roc_soldier_type_id="untrained_soldiers",
            name="untrained_soldiers",
            display_name="Untrained Soldiers",
            costs_soldiers=True
        )
        db.add(soldier_type)
        
        db.commit()
        logger.info("Successfully added untrained_soldiers to soldier_types table")
        
    except Exception as e:
        logger.error(f"Error adding untrained_soldiers: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    add_untrained_soldiers()

if __name__ == "__main__":
    add_untrained_soldiers()
