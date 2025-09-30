"""
SQLAlchemy database models for the ROC Cluster API
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, Table, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base
import enum


class Account(Base):
    """Account model for storing ROC account information"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # Store unencrypted password
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    logs = relationship("AccountLog", back_populates="account", cascade="all, delete-orphan")
    actions = relationship("AccountAction", back_populates="account", cascade="all, delete-orphan")
    cookies = relationship("UserCookies", back_populates="account", cascade="all, delete-orphan")
    clusters = relationship("ClusterUser", back_populates="account", cascade="all, delete-orphan")
    armory_preferences = relationship("ArmoryPreferences", back_populates="account", cascade="all, delete-orphan")
    training_preferences = relationship("TrainingPreferences", back_populates="account", cascade="all, delete-orphan")


class AccountLog(Base):
    """Log entries for account activities"""
    __tablename__ = "account_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)  # JSON string of action details
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="logs")


class AccountAction(Base):
    """Track account actions and their results"""
    __tablename__ = "account_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # attack, sabotage, spy, etc.
    target_id = Column(String(100), nullable=True)  # Target user ID for user actions
    parameters = Column(Text, nullable=True)  # JSON string of action parameters
    result = Column(Text, nullable=True)  # JSON string of action result
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="actions")


class UserCookies(Base):
    """Store cookies for each user"""
    __tablename__ = "user_cookies"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, unique=True)
    cookies = Column(Text, nullable=False)  # JSON string of cookies
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="cookies", uselist=False)


class SentCreditLog(Base):
    """Log entries for credit sending attempts"""
    __tablename__ = "sent_credit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    target_user_id = Column(String(100), nullable=False)  # ROC user ID of the target
    amount = Column(Integer, nullable=False)  # Amount of credits attempted to send
    success = Column(Boolean, nullable=False)  # Whether the credit send was successful
    error_message = Column(Text, nullable=True)  # Error message if failed
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender_account = relationship("Account", foreign_keys=[sender_account_id])


class Cluster(Base):
    """Cluster model for grouping users"""
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("ClusterUser", back_populates="cluster", cascade="all, delete-orphan")


class ClusterUser(Base):
    """Many-to-many relationship between clusters and users"""
    __tablename__ = "cluster_users"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cluster = relationship("Cluster", back_populates="users")
    account = relationship("Account", back_populates="clusters")
    
    # Ensure unique cluster-user pairs
    __table_args__ = (
        UniqueConstraint('cluster_id', 'account_id', name='unique_cluster_user'),
    )


class JobStatus(enum.Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job model for tracking bulk operations"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # User-friendly job name
    description = Column(Text, nullable=True)  # Optional job description
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    parallel_execution = Column(Boolean, default=False, nullable=False)  # Execute steps in parallel
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_steps = Column(Integer, default=0, nullable=False)
    completed_steps = Column(Integer, default=0, nullable=False)
    failed_steps = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)  # Error message if job failed
    pruned = Column(Boolean, default=False, nullable=False)  # Mark if job steps have been pruned
    
    # Relationships
    steps = relationship("JobStep", back_populates="job", cascade="all, delete-orphan")


class JobStep(Base):
    """Individual step within a job"""
    __tablename__ = "job_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    step_order = Column(Integer, nullable=False)  # Order of execution within the job
    action_type = Column(String(50), nullable=False)  # attack, sabotage, spy, etc.
    account_ids = Column(Text, nullable=False)  # JSON string of account IDs for multi-account execution
    original_cluster_ids = Column(Text, nullable=True)  # JSON string of original cluster IDs for cloning
    original_account_ids = Column(Text, nullable=True)  # JSON string of original direct account IDs for cloning
    target_id = Column(String(100), nullable=True)  # Target user ID for user actions
    parameters = Column(Text, nullable=True)  # JSON string of action parameters
    max_retries = Column(Integer, default=0, nullable=False)
    is_async = Column(Boolean, default=False, nullable=False)  # Whether this step should be executed asynchronously
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    result = Column(Text, nullable=True)  # JSON string of step result
    error_message = Column(Text, nullable=True)  # Error message if step failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_accounts = Column(Integer, default=0, nullable=False)  # Total number of accounts in this step
    processed_accounts = Column(Integer, default=0, nullable=False)  # Number of accounts processed so far
    successful_accounts = Column(Integer, default=0, nullable=False)  # Number of successful account operations
    failed_accounts = Column(Integer, default=0, nullable=False)  # Number of failed account operations
    
    # Relationships
    job = relationship("Job", back_populates="steps")


class Weapon(Base):
    """Weapon model for storing ROC weapon information"""
    __tablename__ = "weapons"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_weapon_id = Column(Integer, unique=True, nullable=False)  # The in-game ROC weapon ID
    name = Column(String(50), unique=True, nullable=False)  # weapon name (dagger, maul, etc.)
    display_name = Column(String(100), nullable=False)  # Human-readable display name
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SoldierType(Base):
    """Soldier type model for storing ROC soldier/training information"""
    __tablename__ = "soldier_types"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_soldier_type_id = Column(String(50), unique=True, nullable=False)  # The in-game ROC soldier type ID
    name = Column(String(50), unique=True, nullable=False)  # soldier type name (attack_soldiers, etc.)
    display_name = Column(String(100), nullable=False)  # Human-readable display name
    costs_soldiers = Column(Boolean, default=True, nullable=False)  # Whether this type costs soldiers
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ArmoryPreferences(Base):
    """Armory purchase preferences for each account"""
    __tablename__ = "armory_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="armory_preferences")
    weapon_preferences = relationship("ArmoryWeaponPreference", back_populates="preferences", cascade="all, delete-orphan")


class ArmoryWeaponPreference(Base):
    """Individual weapon preference within armory preferences"""
    __tablename__ = "armory_weapon_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    preferences_id = Column(Integer, ForeignKey("armory_preferences.id"), nullable=False)
    weapon_id = Column(Integer, ForeignKey("weapons.id"), nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    preferences = relationship("ArmoryPreferences", back_populates="weapon_preferences")
    weapon = relationship("Weapon")
    
    # Ensure unique weapon per preferences
    __table_args__ = (
        UniqueConstraint('preferences_id', 'weapon_id', name='unique_preference_weapon'),
    )


class TrainingPreferences(Base):
    """Training purchase preferences for each account"""
    __tablename__ = "training_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="training_preferences")
    soldier_type_preferences = relationship("TrainingSoldierTypePreference", back_populates="preferences", cascade="all, delete-orphan")


class TrainingSoldierTypePreference(Base):
    """Individual soldier type preference within training preferences"""
    __tablename__ = "training_soldier_type_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    preferences_id = Column(Integer, ForeignKey("training_preferences.id"), nullable=False)
    soldier_type_id = Column(Integer, ForeignKey("soldier_types.id"), nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    preferences = relationship("TrainingPreferences", back_populates="soldier_type_preferences")
    soldier_type = relationship("SoldierType")
    
    # Ensure unique soldier type per preferences
    __table_args__ = (
        UniqueConstraint('preferences_id', 'soldier_type_id', name='unique_preference_soldier_type'),
    )


class Race(Base):
    """Race model for storing ROC race information"""
    __tablename__ = "races"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_race_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RocUser(Base):
    """ROC user model for storing in-game user information"""
    __tablename__ = "roc_users"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_user_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    race = Column(String(50), nullable=True)
    created = Column(Boolean, default=False, nullable=False)
    create_date = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    alliance = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RocStat(Base):
    """ROC stat model for storing stat type information"""
    __tablename__ = "roc_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RocUserStats(Base):
    """ROC user stats model for storing user stat values"""
    __tablename__ = "roc_user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_user_id = Column(String(100), ForeignKey("roc_users.roc_user_id"), nullable=False)
    roc_stat_id = Column(Integer, ForeignKey("roc_stats.id"), nullable=False)
    value = Column(Float, default=0.0, nullable=False)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roc_user = relationship("RocUser", foreign_keys=[roc_user_id])
    roc_stat = relationship("RocStat")
    
    # Ensure unique user-stat pairs
    __table_args__ = (
        UniqueConstraint('roc_user_id', 'roc_stat_id', name='unique_user_stat'),
    )


class RocUserSoldiers(Base):
    """ROC user soldiers model for storing user soldier counts"""
    __tablename__ = "roc_user_soldiers"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_user_id = Column(String(100), ForeignKey("roc_users.roc_user_id"), nullable=False)
    roc_soldier_type_id = Column(String(50), ForeignKey("soldier_types.roc_soldier_type_id"), nullable=False)
    count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roc_user = relationship("RocUser", foreign_keys=[roc_user_id])
    soldier_type = relationship("SoldierType", foreign_keys=[roc_soldier_type_id])
    
    # Ensure unique user-soldier type pairs
    __table_args__ = (
        UniqueConstraint('roc_user_id', 'roc_soldier_type_id', name='unique_user_soldier_type'),
    )


class RocUserWeapons(Base):
    """ROC user weapons model for storing user weapon counts"""
    __tablename__ = "roc_user_weapons"
    
    id = Column(Integer, primary_key=True, index=True)
    roc_user_id = Column(String(100), ForeignKey("roc_users.roc_user_id"), nullable=False)
    roc_weapon_id = Column(Integer, ForeignKey("weapons.roc_weapon_id"), nullable=False)
    count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roc_user = relationship("RocUser", foreign_keys=[roc_user_id])
    weapon = relationship("Weapon", foreign_keys=[roc_weapon_id])
    
    # Ensure unique user-weapon pairs
    __table_args__ = (
        UniqueConstraint('roc_user_id', 'roc_weapon_id', name='unique_user_weapon'),
    )


class PageQueueStatus(enum.Enum):
    """Page queue status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PageQueue(Base):
    """Page queue model for storing ROC HTML pages to be processed"""
    __tablename__ = "page_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    request_url = Column(String(500), nullable=True)  # URL that was requested
    response_url = Column(String(500), nullable=True)  # URL that was actually returned
    page_content = Column(Text, nullable=False)  # HTML content of the page
    request_method = Column(String(10), nullable=False)  # GET, POST
    request_data = Column(Text, nullable=True)  # JSON string of POST data if applicable
    request_time = Column(DateTime(timezone=True), nullable=True)  # When the request was made
    status = Column(Enum(PageQueueStatus), default=PageQueueStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    account = relationship("Account")


class FavoriteJob(Base):
    """Favorite job model for storing frequently used job configurations"""
    __tablename__ = "favorite_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # User-friendly name for the favorite
    description = Column(Text, nullable=True)  # Optional description
    job_config = Column(Text, nullable=False)  # JSON string of the complete job configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    usage_count = Column(Integer, default=0, nullable=False)  # Track how often it's used
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # When it was last used


class DatabaseMigration(Base):
    """Track executed database migration scripts"""
    __tablename__ = "database_migrations"
    
    id = Column(Integer, primary_key=True, index=True)
    script_name = Column(String(255), unique=True, nullable=False, index=True)
    version = Column(String(50), nullable=True)  # Version identifier (e.g., "001", "1.0.0")
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)  # Optional: file checksum for integrity
    execution_order = Column(Integer, nullable=True)  # Order in which script was executed