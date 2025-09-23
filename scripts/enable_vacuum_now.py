#!/usr/bin/env python3
"""
Quick script to enable auto vacuum immediately
"""

import sqlite3
import os

def enable_auto_vacuum():
    db_path = 'data/roc_cluster.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current setting
        cursor.execute("PRAGMA auto_vacuum")
        current = cursor.fetchone()[0]
        print(f"Current auto_vacuum setting: {current}")
        
        if current == 0:
            print("Auto vacuum is disabled. For existing databases, we need to perform a full vacuum first.")
            print("This will enable auto vacuum and reclaim space at the same time...")
            
            # Set auto vacuum mode first
            cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")
            conn.commit()
            
            print("Performing full vacuum to enable auto vacuum...")
            cursor.execute("VACUUM")
            conn.commit()
            print("Full vacuum completed")
            
            # Verify
            cursor.execute("PRAGMA auto_vacuum")
            new_setting = cursor.fetchone()[0]
            print(f"New auto_vacuum setting: {new_setting}")
            
            if new_setting == 1:
                print("✅ Auto vacuum enabled successfully!")
            else:
                print("❌ Failed to enable auto vacuum")
                print("This might be due to SQLite version limitations")
        else:
            print("✅ Auto vacuum is already enabled!")
        
        # Show database info
        cursor.execute("PRAGMA page_count")
        pages = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        print(f"Database: {pages} pages, {page_size} bytes per page")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enable_auto_vacuum()
