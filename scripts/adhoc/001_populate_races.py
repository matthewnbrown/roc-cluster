"""
Script to populate the races table with initial ROC race data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import Race
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_races():
    """Populate the races table with ROC race data"""
    
    # ROC race mapping as provided by user
    race_data = [
        {
            "roc_race_id": 1,
            "name": "human"
        },
        {
            "roc_race_id": 2,
            "name": "dwarves"
        },
        {
            "roc_race_id": 3,
            "name": "elves"
        },
        {
            "roc_race_id": 4,
            "name": "orcs"
        },
        {
            "roc_race_id": 5,
            "name": "pixies"
        }
    ]
    
    db = SessionLocal()
    try:
        # Check if races already exist
        existing_count = db.query(Race).count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing races in database, skipping population")
            return
        
        # Create races
        created_count = 0
        for race_info in race_data:
            race = Race(
                roc_race_id=race_info["roc_race_id"],
                name=race_info["name"]
            )
            db.add(race)
            created_count += 1
            logger.info(f"Added race: {race_info['name']} (ROC ID: {race_info['roc_race_id']})")
        
        db.commit()
        logger.info(f"Successfully created {created_count} races")
        
    except Exception as e:
        logger.error(f"Error populating races: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    populate_races()

if __name__ == "__main__":
    populate_races()
