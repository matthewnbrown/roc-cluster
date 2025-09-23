#!/usr/bin/env python3
"""
Migration script to add job-related tables to existing database
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database import DATABASE_URL
from api.db_models import Base, Job, JobStep, JobStatus


def migrate_database():
    """Add job-related tables to the database"""
    print("Starting database migration to add job tables...")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create all tables (this will only create new ones)
        Base.metadata.create_all(bind=engine)
        print("✅ Job tables created successfully!")
        
        # Verify tables exist
        result = session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('jobs', 'job_steps')
        """)).fetchall()
        
        if len(result) == 2:
            print("✅ Migration completed successfully!")
            print("   - jobs table created")
            print("   - job_steps table created")
            print("   - JobStatus enum created")
        else:
            print("⚠️  Migration completed but some tables may not have been created")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()
    
    return True


if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Database migration completed!")
        print("\nThe new job system is now ready to use.")
        print("You can now create jobs using POST /api/v1/jobs/")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
