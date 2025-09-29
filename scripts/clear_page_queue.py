#!/usr/bin/env python3
"""
Script to clear the page queue with various options
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

# Add the project root to the Python path
sys.path.insert(0, '.')

from api.database import SessionLocal
from api.db_models import PageQueue, PageQueueStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_queue_stats() -> dict:
    """Get current page queue statistics"""
    db = SessionLocal()
    try:
        stats = {}
        total_count = db.query(PageQueue).count()
        stats['total'] = total_count
        
        for status in PageQueueStatus:
            count = db.query(PageQueue).filter(PageQueue.status == status).count()
            stats[status.value] = count
        
        return stats
    finally:
        db.close()


def clear_all_pages(confirm: bool = False) -> int:
    """Clear all pages from the queue"""
    if not confirm:
        stats = get_queue_stats()
        print(f"⚠️  WARNING: This will delete ALL {stats['total']} pages from the queue!")
        response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("Operation cancelled.")
            return 0
    
    db = SessionLocal()
    try:
        # Count total records before deletion
        total_count = db.query(PageQueue).count()
        
        if total_count == 0:
            print("✅ No pages to clear - queue is already empty")
            return 0
        
        # Delete all records
        deleted_count = db.query(PageQueue).delete()
        db.commit()
        
        print(f"✅ Successfully cleared {deleted_count} pages from the queue")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing page queue: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def clear_by_status(status: PageQueueStatus, confirm: bool = False) -> int:
    """Clear pages by status"""
    db = SessionLocal()
    try:
        # Count records with this status
        count = db.query(PageQueue).filter(PageQueue.status == status).count()
        
        if count == 0:
            print(f"✅ No {status.value} pages to clear")
            return 0
        
        if not confirm:
            print(f"⚠️  WARNING: This will delete {count} {status.value} pages from the queue!")
            response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("Operation cancelled.")
                return 0
        
        # Delete records with this status
        deleted_count = db.query(PageQueue).filter(PageQueue.status == status).delete()
        db.commit()
        
        print(f"✅ Successfully cleared {deleted_count} {status.value} pages from the queue")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing {status.value} pages: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def clear_old_pages(days: int, confirm: bool = False) -> int:
    """Clear pages older than specified days"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Count old records
        count = db.query(PageQueue).filter(PageQueue.created_at < cutoff_date).count()
        
        if count == 0:
            print(f"✅ No pages older than {days} days to clear")
            return 0
        
        if not confirm:
            print(f"⚠️  WARNING: This will delete {count} pages older than {days} days from the queue!")
            response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("Operation cancelled.")
                return 0
        
        # Delete old records
        deleted_count = db.query(PageQueue).filter(PageQueue.created_at < cutoff_date).delete()
        db.commit()
        
        print(f"✅ Successfully cleared {deleted_count} pages older than {days} days from the queue")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing old pages: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def clear_failed_pages(confirm: bool = False) -> int:
    """Clear only failed pages"""
    return clear_by_status(PageQueueStatus.FAILED, confirm)


def clear_processed_pages(confirm: bool = False) -> int:
    """Clear only processed pages (assuming they have processed_at set)"""
    db = SessionLocal()
    try:
        # Count processed records (those with processed_at set)
        count = db.query(PageQueue).filter(PageQueue.processed_at.isnot(None)).count()
        
        if count == 0:
            print("✅ No processed pages to clear")
            return 0
        
        if not confirm:
            print(f"⚠️  WARNING: This will delete {count} processed pages from the queue!")
            response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("Operation cancelled.")
                return 0
        
        # Delete processed records
        deleted_count = db.query(PageQueue).filter(PageQueue.processed_at.isnot(None)).delete()
        db.commit()
        
        print(f"✅ Successfully cleared {deleted_count} processed pages from the queue")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error clearing processed pages: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_queue_stats():
    """Display current queue statistics"""
    stats = get_queue_stats()
    
    print("\n📊 Current Page Queue Statistics:")
    print("=" * 40)
    print(f"Total pages: {stats['total']}")
    print(f"Pending: {stats.get('pending', 0)}")
    print(f"Processing: {stats.get('processing', 0)}")
    print(f"Failed: {stats.get('failed', 0)}")
    print("=" * 40)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Clear pages from the page queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_page_queue.py --stats                    # Show current statistics
  python clear_page_queue.py --clear-all                # Clear all pages (with confirmation)
  python clear_page_queue.py --clear-all --force        # Clear all pages without confirmation
  python clear_page_queue.py --clear-failed             # Clear only failed pages
  python clear_page_queue.py --clear-old 7              # Clear pages older than 7 days
  python clear_page_queue.py --clear-processed          # Clear only processed pages
  python clear_page_queue.py --clear-status pending     # Clear pages with specific status
        """
    )
    
    # Action arguments (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--stats', action='store_true', help='Show current queue statistics')
    action_group.add_argument('--clear-all', action='store_true', help='Clear all pages from the queue')
    action_group.add_argument('--clear-failed', action='store_true', help='Clear only failed pages')
    action_group.add_argument('--clear-processed', action='store_true', help='Clear only processed pages')
    action_group.add_argument('--clear-old', type=int, metavar='DAYS', help='Clear pages older than specified days')
    action_group.add_argument('--clear-status', choices=['pending', 'processing', 'failed'], 
                             help='Clear pages with specific status')
    
    # Options
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.stats:
            show_queue_stats()
            return
        
        # Determine confirmation requirement
        confirm = args.force
        
        if args.clear_all:
            clear_all_pages(confirm)
        elif args.clear_failed:
            clear_failed_pages(confirm)
        elif args.clear_processed:
            clear_processed_pages(confirm)
        elif args.clear_old is not None:
            clear_old_pages(args.clear_old, confirm)
        elif args.clear_status:
            status = PageQueueStatus(args.clear_status)
            clear_by_status(status, confirm)
        
        # Show final statistics
        print()
        show_queue_stats()
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
