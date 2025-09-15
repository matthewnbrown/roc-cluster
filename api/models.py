"""
Database models and Pydantic schemas for the ROC Cluster API
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    password = Column(String(255), nullable=False)  # Store unencrypted password
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    logs = relationship("AccountLog", back_populates="account", cascade="all, delete-orphan")
    actions = relationship("AccountAction", back_populates="account", cascade="all, delete-orphan")
    cookies = relationship("UserCookies", back_populates="account", cascade="all, delete-orphan")

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

class UserCookiesCreate(BaseModel):
    account_id: int
    cookies: str  # JSON string of cookies

class UserCookiesUpdate(BaseModel):
    cookies: str  # JSON string of cookies

class UserCookiesResponse(BaseModel):
    id: int
    account_id: int
    cookies: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class AccountResponse(AccountBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class SentCreditLogResponse(BaseModel):
    """Response schema for sent credit logs"""
    id: int
    sender_account_id: int
    target_user_id: str
    amount: int
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime
    
    class Config:
        orm_mode = True

            
class AccountMetadata(BaseModel):
    """Account metadata from ROC website"""
    rank: int
    turns: int
    next_turn: datetime
    gold: int
    last_hit: datetime
    last_sabbed: datetime
    mail: str
    credits: int
    username: str
    lastclicked: datetime
    saving: str
    gets: int
    credits_given: int
    credits_received: int
    userid: str
    allianceid: str
    servertime: str

class AccountIdentifierType(Enum):
    USERNAME = "username"
    ID = "id"
    ROC_ID = "roc_id"

class AccountIdentifier(BaseModel):
    id_type: AccountIdentifierType
    id: str

class ActionRequest(BaseModel):
    """Base class for action requests"""
    acting_user: AccountIdentifier
    parameters: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = 0

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
    amount: str

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
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime
    
    class Config:
        exclude_none = True

class BulkActionSubresponse(ActionResponse):
    account: AccountIdentifier
    
    class Config:
        exclude_none = True

class BulkActionRequest(BaseModel):
    """Request for bulk actions across multiple accounts"""
    accounts: List[AccountIdentifier]
    action_type: str
    parameters: Optional[Dict[str, Any]] = None
    target_id: Optional[str] = None
    max_retries: Optional[int] = 0

class BulkActionResponse(BaseModel):
    """Response for bulk actions"""
    total_accounts: int
    successful: int
    failed: int
    results: List[BulkActionSubresponse]
    timestamp: datetime

class RetryConfig(BaseModel):
    """Configuration for request retries"""
    max_retries: int = 0
    retry_delay: float = 1.0  # seconds
    backoff_factor: float = 2.0  # exponential backoff multiplier
    retry_on_status_codes: List[int] = [500, 502, 503, 504, 429]  # HTTP status codes to retry on
    retry_on_exceptions: List[str] = ["aiohttp.ClientError", "asyncio.TimeoutError"]  # Exception types to retry on
    
    