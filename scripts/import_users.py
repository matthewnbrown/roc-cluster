#!/usr/bin/env python3
"""
CSV User Import Script for ROC Cluster

This script imports users from a CSV file with the format:
username, pass, email

Usage:
    python import_users.py <csv_file_path> [--dry-run] [--skip-duplicates]
"""

import csv
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Import our models and database
from api.database import SessionLocal, init_db
from api.db_models import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserImportError(Exception):
    """Custom exception for user import errors"""
    pass

class CSVUserImporter:
    """Handles importing users from CSV files"""
    
    def __init__(self, dry_run: bool = False, skip_duplicates: bool = True):
        self.dry_run = dry_run
        self.skip_duplicates = skip_duplicates
        self.stats = {
            'total_rows': 0,
            'valid_rows': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'duplicates': 0
        }
    
    def validate_csv_row(self, row: List[str], row_num: int) -> Dict[str, str]:
        """Validate a CSV row and return cleaned data"""
        if len(row) != 3:
            raise UserImportError(f"Row {row_num}: Expected 3 columns (username, password, email), got {len(row)}")
        
        username, password, email = [field.strip() for field in row]
        
        # Validate username
        if not username:
            raise UserImportError(f"Row {row_num}: Username cannot be empty")
        if len(username) > 100:
            raise UserImportError(f"Row {row_num}: Username too long (max 100 characters)")
        
        # Validate password
        if not password:
            raise UserImportError(f"Row {row_num}: Password cannot be empty")
        if len(password) > 255:
            raise UserImportError(f"Row {row_num}: Password too long (max 255 characters)")
        
        # Validate email
        if not email:
            raise UserImportError(f"Row {row_num}: Email cannot be empty")
        if len(email) > 255:
            raise UserImportError(f"Row {row_num}: Email too long (max 255 characters)")
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise UserImportError(f"Row {row_num}: Invalid email format")
        
        return {
            'username': username,
            'password': password,
            'email': email
        }
    
    def check_duplicates(self, db: Session, user_data: Dict[str, str]) -> bool:
        """Check if user already exists in database"""
        existing_username = db.query(Account).filter(Account.username == user_data['username']).first()
        existing_email = db.query(Account).filter(Account.email == user_data['email']).first()
        
        return existing_username is not None or existing_email is not None
    
    def import_user(self, db: Session, user_data: Dict[str, str], row_num: int) -> bool:
        """Import a single user to the database"""
        try:
            # Check for duplicates if skip_duplicates is enabled
            if self.skip_duplicates and self.check_duplicates(db, user_data):
                logger.warning(f"Row {row_num}: User already exists (username: {user_data['username']}, email: {user_data['email']})")
                self.stats['duplicates'] += 1
                return False
            
            if self.dry_run:
                logger.info(f"Row {row_num}: [DRY RUN] Would import user: {user_data['username']} ({user_data['email']})")
                self.stats['imported'] += 1
                return True
            
            # Create new account
            account = Account(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],  # Note: storing unencrypted as per model
                is_active=True
            )
            
            db.add(account)
            db.commit()
            
            logger.info(f"Row {row_num}: Successfully imported user: {user_data['username']} ({user_data['email']})")
            self.stats['imported'] += 1
            return True
            
        except IntegrityError as e:
            db.rollback()
            if self.skip_duplicates:
                logger.warning(f"Row {row_num}: User already exists (integrity error): {user_data['username']}")
                self.stats['duplicates'] += 1
                return False
            else:
                logger.error(f"Row {row_num}: Integrity error for user {user_data['username']}: {e}")
                self.stats['errors'] += 1
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Row {row_num}: Error importing user {user_data['username']}: {e}")
            self.stats['errors'] += 1
            return False
    
    def import_from_csv(self, csv_file_path: str) -> Dict[str, int]:
        """Import users from CSV file"""
        logger.info(f"Starting CSV import from: {csv_file_path}")
        logger.info(f"Dry run: {self.dry_run}, Skip duplicates: {self.skip_duplicates}")
        
        # Initialize database
        init_db()
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.reader(csvfile, delimiter=delimiter)
                
                # Skip header row if it exists
                first_row = next(reader, None)
                if first_row and first_row[0].lower() in ['username', 'user', 'name']:
                    logger.info("Skipping header row")
                else:
                    # Reset to beginning if no header
                    csvfile.seek(0)
                    reader = csv.reader(csvfile, delimiter=delimiter)
                
                db = SessionLocal()
                try:
                    for row_num, row in enumerate(reader, start=1):
                        self.stats['total_rows'] += 1
                        
                        try:
                            # Validate row
                            user_data = self.validate_csv_row(row, row_num)
                            self.stats['valid_rows'] += 1
                            
                            # Import user
                            success = self.import_user(db, user_data, row_num)
                            if not success:
                                self.stats['skipped'] += 1
                                
                        except UserImportError as e:
                            logger.error(str(e))
                            self.stats['errors'] += 1
                            continue
                        except Exception as e:
                            logger.error(f"Row {row_num}: Unexpected error: {e}")
                            self.stats['errors'] += 1
                            continue
                        
                        # Progress reporting every 100 rows
                        if row_num % 100 == 0:
                            logger.info(f"Processed {row_num} rows...")
                
                finally:
                    db.close()
        
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
        
        return self.stats
    
    def print_summary(self):
        """Print import summary statistics"""
        logger.info("=" * 50)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total rows processed: {self.stats['total_rows']}")
        logger.info(f"Valid rows: {self.stats['valid_rows']}")
        logger.info(f"Successfully imported: {self.stats['imported']}")
        logger.info(f"Skipped (duplicates): {self.stats['duplicates']}")
        logger.info(f"Skipped (other): {self.stats['skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            logger.info("*** DRY RUN - No actual changes made ***")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Import users from CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format:
    username, pass, email

Example:
    python import_users.py users.csv
    python import_users.py users.csv --dry-run
    python import_users.py users.csv --skip-duplicates
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to the CSV file containing user data'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without making actual changes'
    )
    
    parser.add_argument(
        '--skip-duplicates',
        action='store_true',
        default=True,
        help='Skip duplicate users (default: True)'
    )
    
    parser.add_argument(
        '--no-skip-duplicates',
        action='store_true',
        help='Do not skip duplicate users (will cause errors on duplicates)'
    )
    
    args = parser.parse_args()
    
    # Handle skip duplicates logic
    skip_duplicates = args.skip_duplicates and not args.no_skip_duplicates
    
    try:
        importer = CSVUserImporter(
            dry_run=args.dry_run,
            skip_duplicates=skip_duplicates
        )
        
        stats = importer.import_from_csv(args.csv_file)
        importer.print_summary()
        
        # Exit with error code if there were errors
        if stats['errors'] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
