"""
Database configuration and session management
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import os
import asyncio
import logging
import threading
import pickle
import tempfile
from typing import Generator, Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = settings.IN_MEMORY_DB_URL if settings.USE_IN_MEMORY_DB else settings.DATABASE_URL

# Create engine with appropriate settings for SQLite
# SQLite doesn't support connection pooling parameters with SingletonThreadPool
if "sqlite" in DATABASE_URL:
    # SQLite database: use basic configuration without pooling parameters
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        # SQLite uses SingletonThreadPool by default, no pooling parameters needed
    )
else:
    # Non-SQLite database: use connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,  # Number of connections to maintain in the pool
        max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections that can be created on demand
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after specified time
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    
    # If using in-memory database, copy data from file-based database
    if settings.USE_IN_MEMORY_DB:
        copy_data_to_memory_db()

def copy_data_to_memory_db():
    """Copy data from file-based database to in-memory database"""
    try:
        from sqlalchemy import create_engine as create_engine_func
        from sqlalchemy.orm import sessionmaker as sessionmaker_func
        
        # Create connection to file-based database
        if "sqlite" in settings.DATABASE_URL:
            file_engine = create_engine_func(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
        else:
            file_engine = create_engine_func(settings.DATABASE_URL)
        FileSessionLocal = sessionmaker_func(autocommit=False, autoflush=False, bind=file_engine)
        
        # Import models
        from api.db_models import (
            Account, Job, JobStep, Weapon, Race, SoldierType, RocStat,
            AccountLog, AccountAction, UserCookies, SentCreditLog,
            Cluster, ClusterUser, ArmoryPreferences, ArmoryWeaponPreference,
            TrainingPreferences, TrainingSoldierTypePreference,
            RocUser, RocUserStats, RocUserSoldiers, RocUserWeapons,
            PageQueue, FavoriteJob
        )
        
        # Copy data from file to memory
        with FileSessionLocal() as file_db:
            with SessionLocal() as memory_db:
                # Copy accounts
                accounts = file_db.query(Account).all()
                for account in accounts:
                    memory_db.merge(account)
                
                # Copy jobs and steps
                jobs = file_db.query(Job).all()
                for job in jobs:
                    memory_db.merge(job)
                
                job_steps = file_db.query(JobStep).all()
                for step in job_steps:
                    memory_db.merge(step)
                
                # Copy reference data
                weapons = file_db.query(Weapon).all()
                for weapon in weapons:
                    memory_db.merge(weapon)
                
                races = file_db.query(Race).all()
                for race in races:
                    memory_db.merge(race)
                
                soldier_types = file_db.query(SoldierType).all()
                for soldier_type in soldier_types:
                    memory_db.merge(soldier_type)
                
                roc_stats = file_db.query(RocStat).all()
                for stats in roc_stats:
                    memory_db.merge(stats)
                
                # Copy additional models
                account_logs = file_db.query(AccountLog).all()
                for log in account_logs:
                    memory_db.merge(log)
                
                account_actions = file_db.query(AccountAction).all()
                for action in account_actions:
                    memory_db.merge(action)
                
                user_cookies = file_db.query(UserCookies).all()
                for cookie in user_cookies:
                    memory_db.merge(cookie)
                
                sent_credit_logs = file_db.query(SentCreditLog).all()
                for log in sent_credit_logs:
                    memory_db.merge(log)
                
                clusters = file_db.query(Cluster).all()
                for cluster in clusters:
                    memory_db.merge(cluster)
                
                cluster_users = file_db.query(ClusterUser).all()
                for cluster_user in cluster_users:
                    memory_db.merge(cluster_user)
                
                armory_preferences = file_db.query(ArmoryPreferences).all()
                for pref in armory_preferences:
                    memory_db.merge(pref)
                
                armory_weapon_preferences = file_db.query(ArmoryWeaponPreference).all()
                for pref in armory_weapon_preferences:
                    memory_db.merge(pref)
                
                training_preferences = file_db.query(TrainingPreferences).all()
                for pref in training_preferences:
                    memory_db.merge(pref)
                
                training_soldier_type_preferences = file_db.query(TrainingSoldierTypePreference).all()
                for pref in training_soldier_type_preferences:
                    memory_db.merge(pref)
                
                roc_users = file_db.query(RocUser).all()
                for user in roc_users:
                    memory_db.merge(user)
                
                roc_user_stats = file_db.query(RocUserStats).all()
                for stats in roc_user_stats:
                    memory_db.merge(stats)
                
                roc_user_soldiers = file_db.query(RocUserSoldiers).all()
                for soldiers in roc_user_soldiers:
                    memory_db.merge(soldiers)
                
                roc_user_weapons = file_db.query(RocUserWeapons).all()
                for weapons in roc_user_weapons:
                    memory_db.merge(weapons)
                
                page_queues = file_db.query(PageQueue).all()
                for queue in page_queues:
                    memory_db.merge(queue)
                
                favorite_jobs = file_db.query(FavoriteJob).all()
                for job in favorite_jobs:
                    memory_db.merge(job)
                
                memory_db.commit()
                print(f"✅ Copied {len(accounts)} accounts, {len(jobs)} jobs, {len(job_steps)} steps, {len(account_logs)} logs, {len(clusters)} clusters to in-memory database")
        
        file_engine.dispose()
        
    except Exception as e:
        print(f"⚠️  Warning: Could not copy data to in-memory database: {e}")
        print("Starting with empty in-memory database")

def save_memory_to_file():
    """Save in-memory database data back to file-based database"""
    if not settings.USE_IN_MEMORY_DB:
        return  # Not using in-memory database
    
    try:
        from sqlalchemy import create_engine as create_engine_func
        from sqlalchemy.orm import sessionmaker as sessionmaker_func
        
        # Create connection to file-based database
        if "sqlite" in settings.DATABASE_URL:
            file_engine = create_engine_func(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
        else:
            file_engine = create_engine_func(settings.DATABASE_URL)
        FileSessionLocal = sessionmaker_func(autocommit=False, autoflush=False, bind=file_engine)
        
        # Import models
        from api.db_models import (
            Account, Job, JobStep, Weapon, Race, SoldierType, RocStat,
            AccountLog, AccountAction, UserCookies, SentCreditLog,
            Cluster, ClusterUser, ArmoryPreferences, ArmoryWeaponPreference,
            TrainingPreferences, TrainingSoldierTypePreference,
            RocUser, RocUserStats, RocUserSoldiers, RocUserWeapons,
            PageQueue, FavoriteJob
        )
        
        # Copy data from memory to file
        with SessionLocal() as memory_db:
            with FileSessionLocal() as file_db:
                # Clear existing data in file database (in reverse dependency order)
                file_db.query(JobStep).delete()
                file_db.query(Job).delete()
                file_db.query(FavoriteJob).delete()
                file_db.query(PageQueue).delete()
                file_db.query(RocUserWeapons).delete()
                file_db.query(RocUserSoldiers).delete()
                file_db.query(RocUserStats).delete()
                file_db.query(RocUser).delete()
                file_db.query(TrainingSoldierTypePreference).delete()
                file_db.query(TrainingPreferences).delete()
                file_db.query(ArmoryWeaponPreference).delete()
                file_db.query(ArmoryPreferences).delete()
                file_db.query(ClusterUser).delete()
                file_db.query(Cluster).delete()
                file_db.query(SentCreditLog).delete()
                file_db.query(UserCookies).delete()
                file_db.query(AccountAction).delete()
                file_db.query(AccountLog).delete()
                file_db.query(Account).delete()
                file_db.query(Weapon).delete()
                file_db.query(Race).delete()
                file_db.query(SoldierType).delete()
                file_db.query(RocStat).delete()
                
                # Copy accounts
                accounts = memory_db.query(Account).all()
                for account in accounts:
                    file_db.merge(account)
                
                # Copy jobs and steps
                jobs = memory_db.query(Job).all()
                for job in jobs:
                    file_db.merge(job)
                
                job_steps = memory_db.query(JobStep).all()
                for step in job_steps:
                    file_db.merge(step)
                
                # Copy reference data
                weapons = memory_db.query(Weapon).all()
                for weapon in weapons:
                    file_db.merge(weapon)
                
                races = memory_db.query(Race).all()
                for race in races:
                    file_db.merge(race)
                
                soldier_types = memory_db.query(SoldierType).all()
                for soldier_type in soldier_types:
                    file_db.merge(soldier_type)
                
                roc_stats = memory_db.query(RocStat).all()
                for stats in roc_stats:
                    file_db.merge(stats)
                
                # Copy additional models
                account_logs = memory_db.query(AccountLog).all()
                for log in account_logs:
                    file_db.merge(log)
                
                account_actions = memory_db.query(AccountAction).all()
                for action in account_actions:
                    file_db.merge(action)
                
                user_cookies = memory_db.query(UserCookies).all()
                for cookie in user_cookies:
                    file_db.merge(cookie)
                
                sent_credit_logs = memory_db.query(SentCreditLog).all()
                for log in sent_credit_logs:
                    file_db.merge(log)
                
                clusters = memory_db.query(Cluster).all()
                for cluster in clusters:
                    file_db.merge(cluster)
                
                cluster_users = memory_db.query(ClusterUser).all()
                for cluster_user in cluster_users:
                    file_db.merge(cluster_user)
                
                armory_preferences = memory_db.query(ArmoryPreferences).all()
                for pref in armory_preferences:
                    file_db.merge(pref)
                
                armory_weapon_preferences = memory_db.query(ArmoryWeaponPreference).all()
                for pref in armory_weapon_preferences:
                    file_db.merge(pref)
                
                training_preferences = memory_db.query(TrainingPreferences).all()
                for pref in training_preferences:
                    file_db.merge(pref)
                
                training_soldier_type_preferences = memory_db.query(TrainingSoldierTypePreference).all()
                for pref in training_soldier_type_preferences:
                    file_db.merge(pref)
                
                roc_users = memory_db.query(RocUser).all()
                for user in roc_users:
                    file_db.merge(user)
                
                roc_user_stats = memory_db.query(RocUserStats).all()
                for stats in roc_user_stats:
                    file_db.merge(stats)
                
                roc_user_soldiers = memory_db.query(RocUserSoldiers).all()
                for soldiers in roc_user_soldiers:
                    file_db.merge(soldiers)
                
                roc_user_weapons = memory_db.query(RocUserWeapons).all()
                for weapons in roc_user_weapons:
                    file_db.merge(weapons)
                
                page_queues = memory_db.query(PageQueue).all()
                for queue in page_queues:
                    file_db.merge(queue)
                
                favorite_jobs = memory_db.query(FavoriteJob).all()
                for job in favorite_jobs:
                    file_db.merge(job)
                
                file_db.commit()
                print(f"✅ Saved {len(accounts)} accounts, {len(jobs)} jobs, {len(job_steps)} steps, {len(account_logs)} logs, {len(clusters)} clusters to file database")
        
        file_engine.dispose()
        
    except Exception as e:
        print(f"❌ Error saving in-memory data to file: {e}")

def save_critical_data_only():
    """Save only critical data (accounts, jobs, steps, cookies) - much faster"""
    if not settings.USE_IN_MEMORY_DB:
        return  # Not using in-memory database
    
    try:
        from sqlalchemy import create_engine as create_engine_func
        from sqlalchemy.orm import sessionmaker as sessionmaker_func
        
        # Create connection to file-based database
        if "sqlite" in settings.DATABASE_URL:
            file_engine = create_engine_func(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
        else:
            file_engine = create_engine_func(settings.DATABASE_URL)
        FileSessionLocal = sessionmaker_func(autocommit=False, autoflush=False, bind=file_engine)
        
        # Import only critical models
        from api.db_models import Account, Job, JobStep, UserCookies, Cluster, ClusterUser
        
        # Copy only critical data from memory to file
        with SessionLocal() as memory_db:
            with FileSessionLocal() as file_db:
                # Clear only critical data
                file_db.query(JobStep).delete()
                file_db.query(Job).delete()
                file_db.query(ClusterUser).delete()
                file_db.query(Cluster).delete()
                file_db.query(UserCookies).delete()
                file_db.query(Account).delete()
                
                # Copy only critical data
                accounts = memory_db.query(Account).all()
                for account in accounts:
                    file_db.merge(account)
                
                jobs = memory_db.query(Job).all()
                for job in jobs:
                    file_db.merge(job)
                
                job_steps = memory_db.query(JobStep).all()
                for step in job_steps:
                    file_db.merge(step)
                
                user_cookies = memory_db.query(UserCookies).all()
                for cookie in user_cookies:
                    file_db.merge(cookie)
                
                clusters = memory_db.query(Cluster).all()
                for cluster in clusters:
                    file_db.merge(cluster)
                
                cluster_users = memory_db.query(ClusterUser).all()
                for cluster_user in cluster_users:
                    file_db.merge(cluster_user)
                
                file_db.commit()
                logger.info(f"✅ Auto-saved critical data: {len(accounts)} accounts, {len(jobs)} jobs, {len(job_steps)} steps, {len(user_cookies)} cookies")
        
        file_engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Error auto-saving critical data: {e}")

def create_memory_snapshot() -> Dict[str, Any]:
    """Create a fast memory snapshot of all database data"""
    if not settings.USE_IN_MEMORY_DB:
        return {}
    
    try:
        # Import all models
        from api.db_models import (
            Account, Job, JobStep, Weapon, Race, SoldierType, RocStat,
            AccountLog, AccountAction, UserCookies, SentCreditLog,
            Cluster, ClusterUser, ArmoryPreferences, ArmoryWeaponPreference,
            TrainingPreferences, TrainingSoldierTypePreference,
            RocUser, RocUserStats, RocUserSoldiers, RocUserWeapons,
            PageQueue, FavoriteJob
        )
        
        snapshot = {}
        
        with SessionLocal() as db:
            # Create snapshot of all data
            snapshot['accounts'] = [obj.__dict__.copy() for obj in db.query(Account).all()]
            snapshot['jobs'] = [obj.__dict__.copy() for obj in db.query(Job).all()]
            snapshot['job_steps'] = [obj.__dict__.copy() for obj in db.query(JobStep).all()]
            snapshot['weapons'] = [obj.__dict__.copy() for obj in db.query(Weapon).all()]
            snapshot['races'] = [obj.__dict__.copy() for obj in db.query(Race).all()]
            snapshot['soldier_types'] = [obj.__dict__.copy() for obj in db.query(SoldierType).all()]
            snapshot['roc_stats'] = [obj.__dict__.copy() for obj in db.query(RocStat).all()]
            snapshot['account_logs'] = [obj.__dict__.copy() for obj in db.query(AccountLog).all()]
            snapshot['account_actions'] = [obj.__dict__.copy() for obj in db.query(AccountAction).all()]
            snapshot['user_cookies'] = [obj.__dict__.copy() for obj in db.query(UserCookies).all()]
            snapshot['sent_credit_logs'] = [obj.__dict__.copy() for obj in db.query(SentCreditLog).all()]
            snapshot['clusters'] = [obj.__dict__.copy() for obj in db.query(Cluster).all()]
            snapshot['cluster_users'] = [obj.__dict__.copy() for obj in db.query(ClusterUser).all()]
            snapshot['armory_preferences'] = [obj.__dict__.copy() for obj in db.query(ArmoryPreferences).all()]
            snapshot['armory_weapon_preferences'] = [obj.__dict__.copy() for obj in db.query(ArmoryWeaponPreference).all()]
            snapshot['training_preferences'] = [obj.__dict__.copy() for obj in db.query(TrainingPreferences).all()]
            snapshot['training_soldier_type_preferences'] = [obj.__dict__.copy() for obj in db.query(TrainingSoldierTypePreference).all()]
            snapshot['roc_users'] = [obj.__dict__.copy() for obj in db.query(RocUser).all()]
            snapshot['roc_user_stats'] = [obj.__dict__.copy() for obj in db.query(RocUserStats).all()]
            snapshot['roc_user_soldiers'] = [obj.__dict__.copy() for obj in db.query(RocUserSoldiers).all()]
            snapshot['roc_user_weapons'] = [obj.__dict__.copy() for obj in db.query(RocUserWeapons).all()]
            snapshot['page_queues'] = [obj.__dict__.copy() for obj in db.query(PageQueue).all()]
            snapshot['favorite_jobs'] = [obj.__dict__.copy() for obj in db.query(FavoriteJob).all()]
            
            # Clean up SQLAlchemy internal state
            for table_name, records in snapshot.items():
                for record in records:
                    if '_sa_instance_state' in record:
                        del record['_sa_instance_state']
        
        logger.info(f"✅ Created memory snapshot: {sum(len(records) for records in snapshot.values())} total records")
        return snapshot
        
    except Exception as e:
        logger.error(f"❌ Error creating memory snapshot: {e}")
        return {}

def save_snapshot_to_file(snapshot: Dict[str, Any]):
    """Save memory snapshot to file database in background"""
    if not settings.USE_IN_MEMORY_DB or not snapshot:
        return
    
    try:
        from sqlalchemy import create_engine as create_engine_func
        from sqlalchemy.orm import sessionmaker as sessionmaker_func
        
        # Create connection to file-based database
        if "sqlite" in settings.DATABASE_URL:
            file_engine = create_engine_func(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
        else:
            file_engine = create_engine_func(settings.DATABASE_URL)
        FileSessionLocal = sessionmaker_func(autocommit=False, autoflush=False, bind=file_engine)
        
        # Import all models
        from api.db_models import (
            Account, Job, JobStep, Weapon, Race, SoldierType, RocStat,
            AccountLog, AccountAction, UserCookies, SentCreditLog,
            Cluster, ClusterUser, ArmoryPreferences, ArmoryWeaponPreference,
            TrainingPreferences, TrainingSoldierTypePreference,
            RocUser, RocUserStats, RocUserSoldiers, RocUserWeapons,
            PageQueue, FavoriteJob
        )
        
        with FileSessionLocal() as file_db:
            # Clear existing data
            file_db.query(JobStep).delete()
            file_db.query(Job).delete()
            file_db.query(FavoriteJob).delete()
            file_db.query(PageQueue).delete()
            file_db.query(RocUserWeapons).delete()
            file_db.query(RocUserSoldiers).delete()
            file_db.query(RocUserStats).delete()
            file_db.query(RocUser).delete()
            file_db.query(TrainingSoldierTypePreference).delete()
            file_db.query(TrainingPreferences).delete()
            file_db.query(ArmoryWeaponPreference).delete()
            file_db.query(ArmoryPreferences).delete()
            file_db.query(ClusterUser).delete()
            file_db.query(Cluster).delete()
            file_db.query(SentCreditLog).delete()
            file_db.query(UserCookies).delete()
            file_db.query(AccountAction).delete()
            file_db.query(AccountLog).delete()
            file_db.query(Account).delete()
            file_db.query(Weapon).delete()
            file_db.query(Race).delete()
            file_db.query(SoldierType).delete()
            file_db.query(RocStat).delete()
            
            # Restore data from snapshot
            model_mapping = {
                'accounts': Account,
                'jobs': Job,
                'job_steps': JobStep,
                'weapons': Weapon,
                'races': Race,
                'soldier_types': SoldierType,
                'roc_stats': RocStat,
                'account_logs': AccountLog,
                'account_actions': AccountAction,
                'user_cookies': UserCookies,
                'sent_credit_logs': SentCreditLog,
                'clusters': Cluster,
                'cluster_users': ClusterUser,
                'armory_preferences': ArmoryPreferences,
                'armory_weapon_preferences': ArmoryWeaponPreference,
                'training_preferences': TrainingPreferences,
                'training_soldier_type_preferences': TrainingSoldierTypePreference,
                'roc_users': RocUser,
                'roc_user_stats': RocUserStats,
                'roc_user_soldiers': RocUserSoldiers,
                'roc_user_weapons': RocUserWeapons,
                'page_queues': PageQueue,
                'favorite_jobs': FavoriteJob
            }
            
            # Restore data in dependency order
            for table_name, model_class in model_mapping.items():
                if table_name in snapshot:
                    for record_data in snapshot[table_name]:
                        # Create new instance without SQLAlchemy state
                        instance = model_class()
                        for key, value in record_data.items():
                            if hasattr(instance, key):
                                setattr(instance, key, value)
                        file_db.add(instance)
            
            file_db.commit()
            total_records = sum(len(records) for records in snapshot.values())
            logger.info(f"✅ Saved snapshot to file: {total_records} total records")
        
        file_engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Error saving snapshot to file: {e}")

class AutoSaveService:
    """Service for automatically saving in-memory database to file"""
    
    def __init__(self):
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the auto-save service"""
        if not settings.USE_IN_MEMORY_DB or not settings.AUTO_SAVE_ENABLED:
            logger.info("Auto-save service not needed (not using in-memory DB or disabled)")
            return
        
        if self._running:
            logger.warning("Auto-save service already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._auto_save_loop())
        logger.info(f"Auto-save service started (interval: {settings.AUTO_SAVE_INTERVAL}s)")
    
    async def stop(self):
        """Stop the auto-save service"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Final save before stopping
        await self._save_to_file()
        logger.info("Auto-save service stopped")
    
    async def _auto_save_loop(self):
        """Main auto-save loop"""
        while self._running:
            try:
                await asyncio.sleep(settings.AUTO_SAVE_INTERVAL)
                if self._running:  # Check again after sleep
                    await self._save_to_file()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-save loop: {e}")
                # Continue running even if one save fails
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _save_to_file(self):
        """Save in-memory database to file"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Use memory snapshot approach for minimal performance impact
            if settings.AUTO_SAVE_MEMORY_SNAPSHOT:
                # Create snapshot quickly (minimal impact)
                snapshot = create_memory_snapshot()
                
                if settings.AUTO_SAVE_BACKGROUND:
                    # Save snapshot in background thread (zero impact on main system)
                    def background_save():
                        try:
                            save_snapshot_to_file(snapshot)
                        except Exception as e:
                            logger.error(f"Background snapshot save failed: {e}")
                    
                    # Run in background thread
                    thread = threading.Thread(target=background_save, daemon=True)
                    thread.start()
                    # Don't wait - let it run completely in background
                    logger.info("Auto-save snapshot started in background")
                else:
                    # Save snapshot synchronously
                    save_snapshot_to_file(snapshot)
            else:
                # Use traditional approach
                if settings.AUTO_SAVE_BACKGROUND:
                    def background_save():
                        try:
                            if settings.AUTO_SAVE_ONLY_CRITICAL:
                                save_critical_data_only()
                            else:
                                save_memory_to_file()
                        except Exception as e:
                            logger.error(f"Background auto-save failed: {e}")
                    
                    # Run in background thread
                    thread = threading.Thread(target=background_save, daemon=True)
                    thread.start()
                    thread.join(timeout=30)  # Wait max 30 seconds
                    
                    if thread.is_alive():
                        logger.warning("Auto-save taking longer than expected, continuing in background")
                else:
                    # Use optimized critical data saving for auto-save
                    if settings.AUTO_SAVE_ONLY_CRITICAL:
                        save_critical_data_only()
                    else:
                        save_memory_to_file()
            
            end_time = asyncio.get_event_loop().time()
            logger.info(f"Auto-save completed in {end_time - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
    
    async def force_save(self):
        """Force an immediate save"""
        if settings.USE_IN_MEMORY_DB:
            await self._save_to_file()

# Global auto-save service instance
auto_save_service = AutoSaveService()

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
