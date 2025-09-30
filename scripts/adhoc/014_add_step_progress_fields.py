#!/usr/bin/env python3
"""
Add progress tracking fields to job_steps table
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the project root to the path so we can import from config
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import settings

def main():
    """Add progress tracking fields to job_steps table"""
    # Extract the database path from the DATABASE_URL
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        # Make it relative to the project root (where the script is being run from)
        # The script is in scripts/adhoc/, so we need to go up 2 levels to get to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        db_path = os.path.join(project_root, db_path)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"Adding progress tracking fields to job_steps table in {db_path}")
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        print("Creating database file...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the job_steps table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_steps'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("job_steps table does not exist. Creating table with progress fields...")
            # Create the job_steps table with all required columns including progress fields
            cursor.execute("""
                CREATE TABLE job_steps (
                    id INTEGER PRIMARY KEY,
                    job_id INTEGER NOT NULL,
                    step_order INTEGER NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    account_ids TEXT NOT NULL,
                    original_cluster_ids TEXT,
                    original_account_ids TEXT,
                    target_id VARCHAR(100),
                    parameters TEXT,
                    max_retries INTEGER DEFAULT 0 NOT NULL,
                    is_async BOOLEAN DEFAULT 0 NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    started_at DATETIME,
                    completed_at DATETIME,
                    total_accounts INTEGER DEFAULT 0 NOT NULL,
                    processed_accounts INTEGER DEFAULT 0 NOT NULL,
                    successful_accounts INTEGER DEFAULT 0 NOT NULL,
                    failed_accounts INTEGER DEFAULT 0 NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)
            print("Created job_steps table with progress tracking fields")
        else:
            # Table exists, check if the columns already exist
            cursor.execute("PRAGMA table_info(job_steps)")
            columns = [column[1] for column in cursor.fetchall()]
            
            new_columns = [
                ('total_accounts', 'INTEGER DEFAULT 0 NOT NULL'),
                ('processed_accounts', 'INTEGER DEFAULT 0 NOT NULL'),
                ('successful_accounts', 'INTEGER DEFAULT 0 NOT NULL'),
                ('failed_accounts', 'INTEGER DEFAULT 0 NOT NULL')
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in columns:
                    print(f"Adding column: {column_name}")
                    cursor.execute(f"ALTER TABLE job_steps ADD COLUMN {column_name} {column_def}")
                else:
                    print(f"Column {column_name} already exists, skipping")
        
        # Commit the changes
        conn.commit()
        print("Successfully added progress tracking fields to job_steps table")
        
    except Exception as e:
        print(f"Error adding progress tracking fields: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
