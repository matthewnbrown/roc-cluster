"""
SQLAlchemy database models for the ROC Cluster API
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


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
