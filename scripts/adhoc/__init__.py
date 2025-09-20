"""
Adhoc scripts package for running database migrations and setup scripts
"""

import os
import sys
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

# File to track which scripts have been executed
EXECUTED_SCRIPTS_FILE = Path(__file__).parent / "executed_scripts.txt"

def get_executed_scripts() -> Set[str]:
    """Get the set of script names that have already been executed"""
    if not EXECUTED_SCRIPTS_FILE.exists():
        return set()
    
    try:
        with open(EXECUTED_SCRIPTS_FILE, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.warning(f"Error reading executed scripts file: {e}")
        return set()

def mark_script_executed(script_name: str):
    """Mark a script as executed"""
    try:
        executed_scripts = get_executed_scripts()
        executed_scripts.add(script_name)
        
        with open(EXECUTED_SCRIPTS_FILE, 'w') as f:
            for script in sorted(executed_scripts):
                f.write(f"{script}\n")
        
        logger.info(f"Marked script {script_name} as executed")
    except Exception as e:
        logger.error(f"Error marking script {script_name} as executed: {e}")

def run_adhoc_scripts():
    """Run all new adhoc scripts that haven't been executed yet"""
    scripts_dir = Path(__file__).parent
    executed_scripts = get_executed_scripts()
    
    # Find all Python scripts in the adhoc directory
    script_files = [f for f in scripts_dir.glob("*.py") if f.name != "__init__.py"]
    
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
            mark_script_executed(script_name)
            logger.info(f"Successfully executed adhoc script: {script_name}")
            
        except Exception as e:
            logger.error(f"Error executing adhoc script {script_name}: {e}")
            # Don't mark as executed if it failed
            raise
