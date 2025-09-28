"""
Adhoc scripts package for running database migrations and setup scripts
"""

import os
import sys
import logging
import hashlib
from pathlib import Path
from typing import Set, Dict, Optional
from sqlalchemy.exc import IntegrityError

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.database import SessionLocal
from api.db_models import DatabaseMigration

logger = logging.getLogger(__name__)

def get_executed_scripts() -> Dict[str, DatabaseMigration]:
    """Get the dictionary of script names and their migration records that have already been executed"""
    db = SessionLocal()
    try:
        migrations = db.query(DatabaseMigration).filter(DatabaseMigration.success == True).all()
        return {migration.script_name: migration for migration in migrations}
    except Exception as e:
        logger.warning(f"Error reading executed scripts from database: {e}")
        return {}
    finally:
        db.close()

def extract_script_version(script_name: str) -> Optional[str]:
    """Extract version from script filename. Supports formats like:
    - 001_add_table.py -> "001"
    - v1.0.0_create_index.py -> "1.0.0"
    - add_data.py -> None (no version)
    """
    # Remove .py extension
    name = script_name.replace('.py', '')
    
    # Check for version prefix patterns
    import re
    
    # Pattern 1: Numeric prefix (001, 002, etc.)
    match = re.match(r'^(\d+)_', name)
    if match:
        return match.group(1)
    
    # Pattern 2: v1.0.0 format
    match = re.match(r'^v?(\d+\.\d+\.\d+)_', name)
    if match:
        return match.group(1)
    
    # Pattern 3: v1.0 format
    match = re.match(r'^v?(\d+\.\d+)_', name)
    if match:
        return match.group(1)
    
    # Pattern 4: v1 format
    match = re.match(r'^v?(\d+)_', name)
    if match:
        return match.group(1)
    
    return None

def get_next_execution_order() -> int:
    """Get the next execution order number"""
    db = SessionLocal()
    try:
        max_order = db.query(DatabaseMigration.execution_order).filter(
            DatabaseMigration.execution_order.isnot(None)
        ).order_by(DatabaseMigration.execution_order.desc()).first()
        
        if max_order and max_order[0] is not None:
            return max_order[0] + 1
        return 1
    except Exception as e:
        logger.warning(f"Error getting next execution order: {e}")
        return 1
    finally:
        db.close()

def mark_script_executed(script_name: str, success: bool = True, error_message: Optional[str] = None, file_path: Optional[Path] = None):
    """Mark a script as executed in the database"""
    db = SessionLocal()
    try:
        # Calculate checksum if file path provided
        checksum = None
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Extract version from script name
        version = extract_script_version(script_name)
        
        # Get execution order
        execution_order = get_next_execution_order()
        
        migration = DatabaseMigration(
            script_name=script_name,
            version=version,
            success=success,
            error_message=error_message,
            checksum=checksum,
            execution_order=execution_order
        )
        
        db.add(migration)
        db.commit()
        logger.info(f"Marked script {script_name} as executed in database (success: {success}, order: {execution_order})")
        
    except IntegrityError:
        # Script already exists, update it
        migration = db.query(DatabaseMigration).filter(DatabaseMigration.script_name == script_name).first()
        if migration:
            migration.success = success
            migration.error_message = error_message
            migration.checksum = checksum
            migration.version = extract_script_version(script_name)
            if migration.execution_order is None:
                migration.execution_order = get_next_execution_order()
            db.commit()
            logger.info(f"Updated script {script_name} execution record in database")
    except Exception as e:
        logger.error(f"Error marking script {script_name} as executed in database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def sort_scripts_by_version(script_files: list) -> list:
    """Sort script files by version number for proper execution order"""
    def version_sort_key(script_file):
        version = extract_script_version(script_file.name)
        if version is None:
            # Scripts without versions go last, sorted alphabetically
            return (float('inf'), script_file.name)
        
        # Try to parse as number first (001, 002, etc.)
        try:
            return (float(version), script_file.name)
        except ValueError:
            # Try to parse as semantic version (1.0.0, etc.)
            try:
                parts = version.split('.')
                # Convert each part to float, padding with 0s if needed
                numeric_parts = []
                for part in parts:
                    numeric_parts.append(float(part))
                # Pad to 3 parts for consistent sorting
                while len(numeric_parts) < 3:
                    numeric_parts.append(0.0)
                return (tuple(numeric_parts), script_file.name)
            except ValueError:
                # Fallback to string comparison
                return (float('inf'), version, script_file.name)
    
    return sorted(script_files, key=version_sort_key)

def run_adhoc_scripts():
    """Run all new adhoc scripts that haven't been executed yet"""
    scripts_dir = Path(__file__).parent
    executed_scripts = get_executed_scripts()
    
    # Find all Python scripts in the adhoc directory
    script_files = [f for f in scripts_dir.glob("*.py") if f.name != "__init__.py"]
    
    # Sort scripts by version for proper execution order
    script_files = sort_scripts_by_version(script_files)
    
    logger.info(f"Found {len(script_files)} scripts to process (sorted by version)")
    
    for script_file in script_files:
        script_name = script_file.name
        
        if script_name in executed_scripts:
            logger.debug(f"Skipping already executed script: {script_name}")
            continue
        
        logger.info(f"Running new adhoc script: {script_name}")
        
        try:
            # Import and run the script
            module_name = script_file.stem
            spec = __import__(f"scripts.adhoc.{module_name}", fromlist=[module_name])
            
            # Try to find and run the main function
            if hasattr(spec, 'main'):
                spec.main()
            elif hasattr(spec, module_name):
                # If the function name matches the module name
                getattr(spec, module_name)()
            else:
                # Try to run the module directly
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, script_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            # Mark as executed if successful
            mark_script_executed(script_name, success=True, file_path=script_file)
            logger.info(f"Successfully executed adhoc script: {script_name}")
            
        except Exception as e:
            logger.error(f"Error executing adhoc script {script_name}: {e}")
            # Mark as failed
            mark_script_executed(script_name, success=False, error_message=str(e), file_path=script_file)
            # Don't re-raise - continue with other scripts
            logger.warning(f"Continuing with remaining scripts after {script_name} failure")

def migrate_legacy_executed_scripts():
    """Migrate legacy executed_scripts.txt to database"""
    legacy_file = Path(__file__).parent / "executed_scripts.txt"
    if not legacy_file.exists():
        return
    
    logger.info("Migrating legacy executed_scripts.txt to database")
    
    try:
        with open(legacy_file, 'r') as f:
            script_names = [line.strip() for line in f if line.strip()]
        
        for script_name in script_names:
            # Check if already in database
            executed_scripts = get_executed_scripts()
            if script_name not in executed_scripts:
                mark_script_executed(script_name, success=True)
                logger.info(f"Migrated legacy script {script_name} to database")
        
        # Backup and remove the legacy file
        legacy_file.rename(legacy_file.with_suffix('.txt.backup'))
        logger.info("Legacy executed_scripts.txt migrated and backed up")
        
    except Exception as e:
        logger.error(f"Error migrating legacy executed scripts: {e}")