# Adhoc Scripts

This directory contains database migration and setup scripts that are executed automatically when the application starts.

## Script Naming Convention

To ensure scripts run in the correct order, use this naming patterns:

### Numeric Prefix 
```
001_initial_setup.py
002_add_user_table.py
003_create_indexes.py
004_populate_data.py
```


## Script Structure

Each script should follow this pattern:

```python
"""
Script description
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def main():
    """Main function for the adhoc script runner"""
    # Your migration/setup code here
    db = SessionLocal()
    try:
        # Check if migration is needed (idempotent)
        # Perform migration
        # Log results
        pass
    except Exception as e:
        logger.error(f"Error in migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
```
