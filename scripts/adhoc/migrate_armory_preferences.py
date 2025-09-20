"""
Migration script to convert armory preferences from column-based to normalized schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import Weapon
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_armory_preferences():
    """Migrate from old column-based schema to new normalized schema"""
    
    # ROC weapon mapping for migration
    weapon_mapping = {
        'dagger_percentage': 'dagger',
        'maul_percentage': 'maul',
        'blade_percentage': 'blade',
        'excalibur_percentage': 'excalibur',
        'sai_percentage': 'sai',
        'shield_percentage': 'shield',
        'mithril_percentage': 'mithril',
        'dragonskin_percentage': 'dragonskin',
        'cloak_percentage': 'cloak',
        'hook_percentage': 'hook',
        'pickaxe_percentage': 'pickaxe',
        'horn_percentage': 'horn',
        'guard_dog_percentage': 'guard_dog',
        'torch_percentage': 'torch'
    }
    
    db = SessionLocal()
    try:
        # Check if old table exists and has data
        from sqlalchemy import text
        
        # Check if old armory_preferences table exists with old schema
        result = db.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='armory_preferences'
        """)).fetchone()
        
        if not result:
            logger.info("No existing armory_preferences table found, migration not needed")
            return
        
        # Check if old table has the old column structure
        columns_result = db.execute(text("PRAGMA table_info(armory_preferences)")).fetchall()
        old_columns = [col[1] for col in columns_result]
        
        has_old_columns = any(col.endswith('_percentage') for col in old_columns)
        
        if not has_old_columns:
            logger.info("Armory preferences already migrated to new schema")
            return
        
        logger.info("Found old armory_preferences table, starting migration...")
        
        # Get all old preferences data
        old_preferences = db.execute(text("SELECT * FROM armory_preferences")).fetchall()
        
        if not old_preferences:
            logger.info("No existing preferences data to migrate")
            return
        
        # Get weapon mappings
        weapons = db.query(Weapon).all()
        weapon_by_name = {weapon.name: weapon for weapon in weapons}
        
        # Create new armory_preferences table (this will be done by SQLAlchemy on next init)
        # For now, we'll just log what would be migrated
        migrated_count = 0
        
        for pref_row in old_preferences:
            account_id = pref_row[1]  # Assuming account_id is second column
            logger.info(f"Would migrate preferences for account {account_id}")
            
            # Check each weapon percentage column
            for col_idx, col_name in enumerate([col[1] for col in columns_result]):
                if col_name in weapon_mapping:
                    weapon_name = weapon_mapping[col_name]
                    percentage = pref_row[col_idx]
                    
                    if percentage and percentage > 0:
                        if weapon_name in weapon_by_name:
                            weapon = weapon_by_name[weapon_name]
                            logger.info(f"  {weapon.display_name}: {percentage}%")
                        else:
                            logger.warning(f"  Weapon '{weapon_name}' not found in weapons table")
            
            migrated_count += 1
        
        logger.info(f"Migration analysis complete. Would migrate {migrated_count} preference sets.")
        logger.info("Note: Actual data migration will happen when the new schema is applied.")
        
    except Exception as e:
        logger.error(f"Error during migration analysis: {e}")
        raise
    finally:
        db.close()

def main():
    """Main migration function"""
    migrate_armory_preferences()
