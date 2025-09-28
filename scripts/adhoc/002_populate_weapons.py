"""
Script to populate the weapons table with initial ROC weapon data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal, init_db
from api.db_models import Weapon
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_weapons():
    """Populate the weapons table with ROC weapon data"""
    
    # ROC weapon mapping as provided by user
    weaponmap = {
        1: 'dagger',
        2: 'maul', 
        3: 'blade',
        4: 'excalibur',
        5: 'sai',
        6: 'shield',
        7: 'mithril',
        8: 'dragonskin',
        9: 'cloak',
        10: 'hook',
        11: 'pickaxe',
        12: 'horn',
        13: 'guard_dog',
        14: 'torch'
    }
    
    # Display name mapping for better readability
    display_names = {
        'dagger': 'Dagger',
        'maul': 'Maul',
        'blade': 'Blade',
        'excalibur': 'Excalibur',
        'sai': 'Sai',
        'shield': 'Shield',
        'mithril': 'Mithril',
        'dragonskin': 'Dragonskin',
        'cloak': 'Cloak',
        'hook': 'Hook',
        'pickaxe': 'Pickaxe',
        'horn': 'Horn',
        'guard_dog': 'Guard Dog',
        'torch': 'Torch'
    }
    
    db = SessionLocal()
    try:
        # Check if weapons already exist
        existing_count = db.query(Weapon).count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing weapons in database, skipping population")
            return
        
        # Create weapons
        created_count = 0
        for roc_id, weapon_name in weaponmap.items():
            weapon = Weapon(
                roc_weapon_id=roc_id,
                name=weapon_name,
                display_name=display_names.get(weapon_name, weapon_name.title())
            )
            db.add(weapon)
            created_count += 1
            logger.info(f"Added weapon: {display_names.get(weapon_name, weapon_name.title())} (ROC ID: {roc_id})")
        
        db.commit()
        logger.info(f"Successfully created {created_count} weapons")
        
    except Exception as e:
        logger.error(f"Error populating weapons: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function for migration system"""
    populate_weapons()

if __name__ == "__main__":
    main()
