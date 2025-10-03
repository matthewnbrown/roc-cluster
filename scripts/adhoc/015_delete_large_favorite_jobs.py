"""
Adhoc script to delete favorite jobs with more than 1000 users attached to them
"""

import sys
import os
import json
import logging
from typing import List, Dict, Any, Set

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.database import SessionLocal
from api.db_models import FavoriteJob, Account, ClusterUser

logger = logging.getLogger(__name__)


def count_users_in_job_config(job_config: Dict[str, Any], db) -> int:
    """
    Count the total number of unique users that would be affected by this job configuration.
    
    Args:
        job_config: The job configuration dictionary
        db: Database session
        
    Returns:
        Total number of unique users
    """
    all_account_ids: Set[int] = set()
    
    # Get steps from job config
    steps = job_config.get('steps', [])
    
    for step in steps:
        # Add direct account IDs
        account_ids = step.get('account_ids', [])
        if account_ids:
            all_account_ids.update(account_ids)
        
        # Add accounts from clusters
        cluster_ids = step.get('cluster_ids', [])
        if cluster_ids:
            # Get all accounts in these clusters
            cluster_accounts = db.query(ClusterUser.account_id).filter(
                ClusterUser.cluster_id.in_(cluster_ids)
            ).all()
            
            for (account_id,) in cluster_accounts:
                all_account_ids.add(account_id)
    
    return len(all_account_ids)


def main():
    """Delete favorite jobs with more than 1000 users"""
    db = SessionLocal()
    
    try:
        # Get all favorite jobs
        favorite_jobs = db.query(FavoriteJob).all()
        logger.info(f"Found {len(favorite_jobs)} favorite jobs to analyze")
        
        jobs_to_delete = []
        threshold = 1000
        
        for fav_job in favorite_jobs:
            try:
                # Parse the job configuration
                job_config = json.loads(fav_job.job_config)
                
                # Count users
                user_count = count_users_in_job_config(job_config, db)
                
                logger.info(f"Favorite job '{fav_job.name}' (ID: {fav_job.id}) has {user_count} users")
                
                if user_count > threshold:
                    jobs_to_delete.append({
                        'id': fav_job.id,
                        'name': fav_job.name,
                        'user_count': user_count
                    })
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing job config for favorite job '{fav_job.name}' (ID: {fav_job.id}): {e}")
                continue
        
        if not jobs_to_delete:
            logger.info(f"No favorite jobs found with more than {threshold} users")
            return
        
        # Display jobs to be deleted
        logger.info(f"Found {len(jobs_to_delete)} favorite jobs with more than {threshold} users:")
        for job in jobs_to_delete:
            logger.info(f"  - '{job['name']}' (ID: {job['id']}) - {job['user_count']} users")
        
        # Delete the jobs
        deleted_count = 0
        for job in jobs_to_delete:
            try:
                fav_job = db.query(FavoriteJob).filter(FavoriteJob.id == job['id']).first()
                if fav_job:
                    db.delete(fav_job)
                    deleted_count += 1
                    logger.info(f"Deleted favorite job '{job['name']}' (ID: {job['id']})")
                else:
                    logger.warning(f"Favorite job with ID {job['id']} not found")
            except Exception as e:
                logger.error(f"Error deleting favorite job '{job['name']}' (ID: {job['id']}): {e}")
        
        # Commit the changes
        db.commit()
        logger.info(f"Successfully deleted {deleted_count} favorite jobs")
        
    except Exception as e:
        logger.error(f"Error during favorite job deletion: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
