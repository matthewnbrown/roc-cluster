"""
Pydantic schemas for the ROC Cluster API
"""

from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime

# Generic type for paginated responses
T = TypeVar('T')


# Account Schemas
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


# User Cookies Schemas
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


# Credit Log Schemas
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


# Account Metadata Schema
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


# Account Identifier Schemas
class AccountIdentifierType(Enum):
    USERNAME = "username"
    ID = "id"
    ROC_ID = "roc_id"


class AccountIdentifier(BaseModel):
    id_type: AccountIdentifierType
    id: str


# Action Request Schemas
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
    turns: int = 12


class SabotageRequest(UserActionRequest):
    """Sabotage another user"""
    spy_count: int = 1
    enemy_weapon: int = 1


class SpyRequest(UserActionRequest):
    """Spy on another user"""
    spy_count: int = 1


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
    pass


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


# Action Response Schemas
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


# Retry Configuration Schema
class RetryConfig(BaseModel):
    """Configuration for request retries"""
    max_retries: int = 0
    retry_delay: float = 1.0  # seconds
    backoff_factor: float = 2.0  # exponential backoff multiplier
    retry_on_status_codes: List[int] = [500, 502, 503, 504, 429]  # HTTP status codes to retry on
    retry_on_exceptions: List[str] = ["aiohttp.ClientError", "asyncio.TimeoutError"]  # Exception types to retry on


# Pagination Schemas
class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper"""
    data: List[T]
    pagination: PaginationMeta
    
    class Config:
        orm_mode = True


# Captcha Schema
class CaptchaSolutionItem(BaseModel):
    account_id: int
    hash: str
    answer: str
    x: int
    y: int
    timestamp: datetime


# Cluster Schemas
class ClusterBase(BaseModel):
    name: str
    description: Optional[str] = None


class ClusterCreate(ClusterBase):
    pass


class ClusterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ClusterUserResponse(BaseModel):
    id: int
    account_id: int
    username: str
    email: str
    added_at: datetime
    
    class Config:
        orm_mode = True


class ClusterResponse(ClusterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_count: int = 0
    users: List[ClusterUserResponse] = []
    
    class Config:
        orm_mode = True


class ClusterListResponse(ClusterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_count: int = 0
    
    class Config:
        orm_mode = True


class ClusterUserAdd(BaseModel):
    account_ids: List[int]


class ClusterClone(BaseModel):
    name: str
    description: Optional[str] = None
    include_users: bool = True


class ClusterSearch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_count_min: Optional[int] = None
    user_count_max: Optional[int] = None