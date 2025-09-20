"""
Script to populate the soldier types table with initial ROC soldier type data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import SoldierType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_soldier_types():
    """Populate the soldier types table with ROC soldier type data"""
    
    # ROC soldier type mapping as provided by user
    soldier_type_data = [
        {
            "roc_soldier_type_id": "attack_soldiers",
            "name": "attack_soldiers",
            "display_name": "Attack Soldiers",
            "costs_soldiers": True
        },
        {
            "roc_soldier_type_id": "defense_soldiers", 
            "name": "defense_soldiers",
            "display_name": "Defense Soldiers",
            "costs_soldiers": True
        },
        {
            "roc_soldier_type_id": "spies",
            "name": "spies",
            "display_name": "Spies",
            "costs_soldiers": True
        },
        {
            "roc_soldier_type_id": "sentries",
            "name": "sentries",
            "display_name": "Sentries",
            "costs_soldiers": True
        },
        {
            "roc_soldier_type_id": "attack_mercs",
            "name": "attack_mercs",
            "display_name": "Attack Mercenaries",
            "costs_soldiers": False
        },
        {
            "roc_soldier_type_id": "defense_mercs",
            "name": "defense_mercs",
            "display_name": "Defense Mercenaries",
            "costs_soldiers": False
        },
        {
            "roc_soldier_type_id": "untrained_mercs",
            "name": "untrained_mercs",
            "display_name": "Untrained Mercenaries",
            "costs_soldiers": False
        }
    ]
    
    db = SessionLocal()
    try:
        # Check if soldier types already exist
        existing_count = db.query(SoldierType).count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing soldier types in database, skipping population")
            return
        
        # Create soldier types
        created_count = 0
        for soldier_type_info in soldier_type_data:
            soldier_type = SoldierType(
                roc_soldier_type_id=soldier_type_info["roc_soldier_type_id"],
                name=soldier_type_info["name"],
                display_name=soldier_type_info["display_name"],
                costs_soldiers=soldier_type_info["costs_soldiers"]
            )
            db.add(soldier_type)
            created_count += 1
            logger.info(f"Added soldier type: {soldier_type_info['display_name']} (ROC ID: {soldier_type_info['roc_soldier_type_id']}, Costs Soldiers: {soldier_type_info['costs_soldiers']})")
        
        db.commit()
        logger.info(f"Successfully created {created_count} soldier types")
        
    except Exception as e:
        logger.error(f"Error populating soldier types: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    populate_soldier_types()
