#!/usr/bin/env python3
"""
Migration script to add multi-account job step support.

This script adds the account_ids field to the job_steps table and removes
the account_id field to support multi-account execution.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from config import settings

def run_migration():
    """Run the migration to add multi-account job step support"""
    engine = create_engine(settings.get_database_url())
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            # Check if account_ids column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('job_steps') 
                WHERE name = 'account_ids'
            """)).scalar()
            
            if result == 0:
                print("Adding account_ids column to job_steps table...")
                conn.execute(text("""
                    ALTER TABLE job_steps 
                    ADD COLUMN account_ids TEXT
                """))
            else:
                print("account_ids column already exists, skipping...")
            
            # Check if original_cluster_ids column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('job_steps') 
                WHERE name = 'original_cluster_ids'
            """)).scalar()
            
            if result == 0:
                print("Adding original_cluster_ids column to job_steps table...")
                conn.execute(text("""
                    ALTER TABLE job_steps 
                    ADD COLUMN original_cluster_ids TEXT
                """))
            else:
                print("original_cluster_ids column already exists, skipping...")
            
            # Check if original_account_ids column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('job_steps') 
                WHERE name = 'original_account_ids'
            """)).scalar()
            
            if result == 0:
                print("Adding original_account_ids column to job_steps table...")
                conn.execute(text("""
                    ALTER TABLE job_steps 
                    ADD COLUMN original_account_ids TEXT
                """))
            else:
                print("original_account_ids column already exists, skipping...")
            
            # Check if account_id column still exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('job_steps') 
                WHERE name = 'account_id'
            """)).scalar()
            
            if result > 0:
                print("Removing account_id column by recreating table...")
                
                # SQLite doesn't support DROP COLUMN with foreign keys, so we need to recreate the table
                # First, create a backup of existing data
                conn.execute(text("""
                    CREATE TABLE job_steps_backup AS 
                    SELECT id, job_id, step_order, action_type, target_id, parameters, 
                           max_retries, is_async, status, result, error_message, 
                           started_at, completed_at
                    FROM job_steps
                """))
                
                # Drop the original table
                conn.execute(text("DROP TABLE job_steps"))
                
                # Recreate the table with the new schema (without account_id)
                conn.execute(text("""
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
                        max_retries INTEGER NOT NULL DEFAULT 0,
                        is_async BOOLEAN NOT NULL DEFAULT 0,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        result TEXT,
                        error_message TEXT,
                        started_at DATETIME,
                        completed_at DATETIME,
                        FOREIGN KEY (job_id) REFERENCES jobs (id)
                    )
                """))
                
                # Copy data back, setting account_ids to empty array for existing steps
                conn.execute(text("""
                    INSERT INTO job_steps (
                        id, job_id, step_order, action_type, account_ids, 
                        original_cluster_ids, original_account_ids, target_id, 
                        parameters, max_retries, is_async, status, result, 
                        error_message, started_at, completed_at
                    )
                    SELECT 
                        id, job_id, step_order, action_type, '[]' as account_ids,
                        NULL as original_cluster_ids, NULL as original_account_ids,
                        target_id, parameters, max_retries, is_async, status, 
                        result, error_message, started_at, completed_at
                    FROM job_steps_backup
                """))
                
                # Drop the backup table
                conn.execute(text("DROP TABLE job_steps_backup"))
                
                print("Successfully recreated job_steps table without account_id column")
            else:
                print("account_id column already removed, skipping...")
            
            # Commit the transaction
            trans.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"Migration failed: {e}")
            raise

def main():
    """Main function for adhoc script system"""
    run_migration()

if __name__ == "__main__":
    run_migration()
