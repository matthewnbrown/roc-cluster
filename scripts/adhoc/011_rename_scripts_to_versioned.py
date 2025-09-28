"""
Utility script to rename existing scripts to use versioned naming
This script will help transition existing scripts to the new versioned format
"""

import os
import shutil
from pathlib import Path

def rename_scripts_to_versioned():
    """Rename existing scripts to use versioned naming convention"""
    
    scripts_dir = Path(__file__).parent
    
    # Mapping of existing scripts to their versioned names
    # This is just an example - adjust based on your actual execution order needs
    script_mappings = {
        'populate_races.py': '001_populate_races.py',
        'populate_weapons.py': '002_populate_weapons.py', 
        'populate_soldier_types.py': '003_populate_soldier_types.py',
        'populate_roc_stats.py': '004_populate_roc_stats.py',
        'create_favorite_jobs_table.py': '005_create_favorite_jobs_table.py',
        'add_pruned_field_to_jobs.py': '006_add_pruned_field_to_jobs.py',
        'add_untrained_soldiers.py': '007_add_untrained_soldiers.py',
        'migrate_armory_preferences.py': '008_migrate_armory_preferences.py',
        'enable_auto_vacuum.py': '009_enable_auto_vacuum.py',
        'cleanup_page_queue.py': '010_cleanup_page_queue.py',
    }
    
    print("Script renaming utility")
    print("=" * 50)
    
    for old_name, new_name in script_mappings.items():
        old_path = scripts_dir / old_name
        new_path = scripts_dir / new_name
        
        if old_path.exists() and not new_path.exists():
            shutil.move(str(old_path), str(new_path))
        elif old_path.exists() and new_path.exists():
            print(f"SKIP: {new_name} already exists")
        else:
            print(f"SKIP: {old_name} not found")
    

def main():
    """Main function for migration system"""
    rename_scripts_to_versioned()

if __name__ == "__main__":
    main()
