"""
Database models and Pydantic schemas for the ROC Cluster API
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from api.database import Base

# Database Models
class Account(Base):
    """Account model for storing ROC account information"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Store hashed password
    cookies = Column(Text, nullable=True)  # JSON string of cookies
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    logs = relationship("AccountLog", back_populates="account", cascade="all, delete-orphan")
    actions = relationship("AccountAction", back_populates="account", cascade="all, delete-orphan")

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

# Pydantic Schemas
class AccountBase(BaseModel):
    username: str
    email: EmailStr

class AccountCreate(AccountBase):
    password: str

class AccountUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class AccountResponse(AccountBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class AccountMetadata(BaseModel):
    """Account metadata from ROC website"""
    gold: int
    rank: str
    army_info: Dict[str, Any]
    turn_based_gold: int
    last_updated: datetime

class ActionRequest(BaseModel):
    """Base class for action requests"""
    account_id: int
    parameters: Optional[Dict[str, Any]] = None

class UserActionRequest(ActionRequest):
    """Request for actions targeting other users"""
    target_id: str

class AttackRequest(UserActionRequest):
    """Attack another user"""
    pass

class SabotageRequest(UserActionRequest):
    """Sabotage another user"""
    pass

class SpyRequest(UserActionRequest):
    """Spy on another user"""
    pass

class BecomeOfficerRequest(UserActionRequest):
    """Become an officer of another user"""
    pass

class SendCreditsRequest(UserActionRequest):
    """Send credits to another user"""
    amount: int

class SelfActionRequest(ActionRequest):
    """Request for self-directed actions"""
    pass

class RecruitRequest(SelfActionRequest):
    """Recruit soldiers"""
    soldier_type: str
    count: int

class ArmoryPurchaseRequest(SelfActionRequest):
    """Purchase from armory"""
    items: Dict[str, int]  # item_name: quantity

class TrainingPurchaseRequest(SelfActionRequest):
    """Purchase training"""
    training_type: str
    count: int

class EnableCreditSavingRequest(SelfActionRequest):
    """Enable credit saving"""
    pass

class PurchaseUpgradeRequest(SelfActionRequest):
    """Purchase upgrade"""
    upgrade_type: str

class ActionResponse(BaseModel):
    """Response for action execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime

class BulkActionRequest(BaseModel):
    """Request for bulk actions across multiple accounts"""
    account_ids: List[int]
    action_type: str
    parameters: Optional[Dict[str, Any]] = None
    target_id: Optional[str] = None

class BulkActionResponse(BaseModel):
    """Response for bulk actions"""
    total_accounts: int
    successful: int
    failed: int
    results: List[ActionResponse]
    timestamp: datetime
