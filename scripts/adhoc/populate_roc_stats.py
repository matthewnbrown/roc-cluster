"""
Script to populate the roc_stats table with initial ROC stat data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import RocStat
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_roc_stats():
    """Populate the roc_stats table with ROC stat data"""
    
    # ROC stat mapping as provided by user
    stat_data = [
        {"name": "Rank"},
        {"name": "TotalFightingForce"},
        {"name": "Gold"},
        {"name": "StrikeAction"},
        {"name": "DefenceAction"},
        {"name": "SpyAction"},
        {"name": "SentryAction"},
        {"name": "SiegeTech"},
        {"name": "CovertTech"},
        {"name": "AttackTurns"}
    ]
    
    db = SessionLocal()
    try:
        # Check if roc_stats already exist
        existing_count = db.query(RocStat).count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing roc_stats in database, skipping population")
            return
        
        # Create roc_stats
        created_count = 0
        for stat_info in stat_data:
            roc_stat = RocStat(
                name=stat_info["name"]
            )
            db.add(roc_stat)
            created_count += 1
            logger.info(f"Added roc_stat: {stat_info['name']}")
        
        db.commit()
        logger.info(f"Successfully created {created_count} roc_stats")
        
    except Exception as e:
        logger.error(f"Error populating roc_stats: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    populate_roc_stats()

if __name__ == "__main__":
    populate_roc_stats()
