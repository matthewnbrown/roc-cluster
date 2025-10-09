"""
Pydantic schemas for the ROC Cluster API
"""

from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime, timezone
import json

# Generic type for paginated responses
T = TypeVar('T')

def datetime_encoder(dt: datetime) -> str:
    """Custom datetime encoder that ensures UTC timezone suffix"""
    if dt is None:
        return None
    
    # Ensure the datetime is timezone-aware and in UTC
    if dt.tzinfo is None:
        # If no timezone info, assume it's UTC
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC if it has different timezone
        dt = dt.astimezone(timezone.utc)
    
    # Format as ISO string with Z suffix
    return dt.isoformat()


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
        json_encoders = {
            datetime: datetime_encoder
        }


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
        json_encoders = {
            datetime: datetime_encoder
        }


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
        json_encoders = {
            datetime: datetime_encoder
        }


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
    enemy_weapon: int = -1


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
    """Purchase and/or sell items in armory"""
    buy_items: Optional[Dict[str, int]] = None  # weapon_id: quantity to buy
    sell_items: Optional[Dict[str, int]] = None  # weapon_id: quantity to sell


class TrainingPurchaseRequest(SelfActionRequest):
    """Purchase training"""
    training_orders: Dict[str, Any]  # Dictionary of training orders


class SetCreditSavingRequest(SelfActionRequest):
    """Set credit saving to 'on' or 'off'"""
    value: str


class PurchaseUpgradeRequest(SelfActionRequest):
    """Purchase upgrade"""
    upgrade_type: str


class BuyUpgradeRequest(SelfActionRequest):
    """Buy upgrade - supports siege, fortification, covert, recruiter"""
    upgrade_option: str


class GetCardsRequest(SelfActionRequest):
    """Get cards from sendcards page"""
    pass


class SendCardsRequest(UserActionRequest):
    """Send cards to a target user"""
    card_id: str  # Card ID or 'all' to send all cards
    comment: Optional[str] = ""


class MarketPurchaseRequest(SelfActionRequest):
    """Purchase an item from the market"""
    listing_id: str


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
        json_encoders = {
            datetime: datetime_encoder
        }




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


# Job Schemas
class JobStatusEnum(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStepRequest(BaseModel):
    """Request for creating a job step"""
    account_ids: Optional[List[int]] = []  # List of account IDs
    cluster_ids: Optional[List[int]] = []  # List of cluster IDs to expand
    action_type: str
    parameters: Optional[Dict[str, Any]] = None
    max_retries: int = 0
    is_async: bool = False  # Whether this step should be executed asynchronously
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate that at least one of account_ids or cluster_ids is provided (except for delay and collect_async_tasks steps)
        if not self.account_ids and not self.cluster_ids and self.action_type not in ["delay", "collect_async_tasks"]:
            raise ValueError("Either account_ids or cluster_ids must be provided")
        
        # Validate action_type (basic validation - detailed validation happens in job manager)
        if not self.action_type:
            raise ValueError("action_type is required")


class JobCreateRequest(BaseModel):
    """Request for creating a new job"""
    name: Optional[str] = None
    description: Optional[str] = None
    parallel_execution: bool = False  # Execute steps in parallel instead of sequential
    steps: List[JobStepRequest]


class JobStepResponse(BaseModel):
    """Response for a job step"""
    id: int
    step_order: int
    action_type: str
    account_count: int  # Number of accounts in this step (instead of full list)
    original_cluster_ids: Optional[List[int]] = None  # Original cluster IDs for cloning
    original_account_ids: Optional[List[int]] = None  # Original direct account IDs for cloning
    target_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    max_retries: int
    is_async: bool
    status: JobStatusEnum
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_time_seconds: Optional[float] = None  # Duration in seconds from start to completion
    total_accounts: int = 0
    processed_accounts: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
    
    class Config:
        exclude_none = True
        json_encoders = {
            datetime: datetime_encoder
        }


class JobResponse(BaseModel):
    """Response for a job"""
    id: int
    name: str
    description: Optional[str] = None
    status: JobStatusEnum
    parallel_execution: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_steps: int
    completed_steps: int
    failed_steps: int
    error_message: Optional[str] = None
    steps: Optional[List[JobStepResponse]] = None
    
    class Config:
        exclude_none = True
        json_encoders = {
            datetime: datetime_encoder
        }


class JobListResponse(BaseModel):
    """Response for listing jobs"""
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class JobCancelRequest(BaseModel):
    """Request for cancelling a job"""
    reason: Optional[str] = None


# Favorite Job Schemas
class FavoriteJobCreateRequest(BaseModel):
    """Request for creating a favorite job"""
    name: str
    description: Optional[str] = None
    job_config: Dict[str, Any]  # Complete job configuration


class FavoriteJobResponse(BaseModel):
    """Response for a favorite job"""
    id: int
    name: str
    description: Optional[str] = None
    job_config: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    usage_count: int
    last_used_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: datetime_encoder
        }


class FavoriteJobListResponse(BaseModel):
    """Response for listing favorite jobs"""
    favorite_jobs: List[FavoriteJobResponse]
    total: int


# Scheduled Job Schemas
class DailyScheduleRange(BaseModel):
    """Daily schedule time range configuration"""
    start_time: str  # "HH:MM" format
    end_time: str    # "HH:MM" format
    interval_minutes: int  # Minutes between executions within this range
    random_noise_minutes: Optional[int] = 0  # Random variation in minutes (Gaussian distribution)


class DailyScheduleConfig(BaseModel):
    """Daily schedule configuration"""
    ranges: List[DailyScheduleRange]  # List of time ranges with intervals


class OnceScheduleConfig(BaseModel):
    """One-time schedule configuration"""
    execution_time: datetime  # When to execute


class CronScheduleConfig(BaseModel):
    """Cron schedule configuration"""
    cron_expression: str  # Standard cron expression


class ScheduledJobCreateRequest(BaseModel):
    """Request for creating a scheduled job"""
    name: str
    description: Optional[str] = None
    job_config: Dict[str, Any]  # Complete job configuration (same as favorite jobs)
    schedule_type: str  # "once", "cron", or "daily"
    
    # Schedule-specific configuration
    once_config: Optional[OnceScheduleConfig] = None
    cron_config: Optional[CronScheduleConfig] = None
    daily_config: Optional[DailyScheduleConfig] = None


class ScheduledJobResponse(BaseModel):
    """Response for a scheduled job"""
    id: int
    name: str
    description: Optional[str] = None
    job_config: Dict[str, Any]
    schedule_type: str
    schedule_config: Dict[str, Any]  # Parsed schedule configuration
    
    # Status and tracking
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_executed_at: Optional[datetime] = None
    next_execution_at: Optional[datetime] = None
    execution_count: int
    failure_count: int

    class Config:
        json_encoders = {
            datetime: datetime_encoder
        }


class ScheduledJobExecutionResponse(BaseModel):
    """Response for a scheduled job execution"""
    id: int
    scheduled_job_id: int
    job_id: Optional[int] = None
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: datetime_encoder
        }


class ScheduledJobListResponse(BaseModel):
    """Response for listing scheduled jobs"""
    scheduled_jobs: List[ScheduledJobResponse]
    total: int


class ScheduledJobExecutionListResponse(BaseModel):
    """Response for listing scheduled job executions"""
    executions: List[ScheduledJobExecutionResponse]
    total: int


# Weapon Schemas
class WeaponResponse(BaseModel):
    """Response schema for weapons"""
    id: int
    roc_weapon_id: int
    name: str
    display_name: str
    created_at: datetime
    
    class Config:
        orm_mode = True


# Armory Preferences Schemas
class ArmoryWeaponPreferenceResponse(BaseModel):
    """Response schema for individual weapon preference"""
    weapon_id: int
    weapon_name: str
    weapon_display_name: str
    percentage: float
    
    class Config:
        orm_mode = True


class ArmoryPreferencesBase(BaseModel):
    """Base schema for armory preferences"""
    weapon_preferences: List[ArmoryWeaponPreferenceResponse] = []


class ArmoryPreferencesCreate(BaseModel):
    """Schema for creating armory preferences"""
    account_id: int
    weapon_percentages: Dict[str, float]  # weapon_name -> percentage


class ArmoryPreferencesUpdate(BaseModel):
    """Schema for updating armory preferences"""
    weapon_percentages: Dict[str, float]  # weapon_name -> percentage


class ArmoryPreferencesResponse(ArmoryPreferencesBase):
    """Response schema for armory preferences"""
    id: int
    account_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


# Soldier Types Schemas
class SoldierTypeResponse(BaseModel):
    """Response schema for soldier types"""
    id: int
    roc_soldier_type_id: str
    name: str
    display_name: str
    costs_soldiers: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


# Training Preferences Schemas
class TrainingSoldierTypePreferenceResponse(BaseModel):
    """Response schema for individual soldier type preference"""
    soldier_type_id: int
    soldier_type_name: str
    soldier_type_display_name: str
    soldier_type_costs_soldiers: bool
    percentage: float
    
    class Config:
        orm_mode = True


class TrainingPreferencesBase(BaseModel):
    """Base schema for training preferences"""
    soldier_type_preferences: List[TrainingSoldierTypePreferenceResponse] = []


class TrainingPreferencesCreate(BaseModel):
    """Schema for creating training preferences"""
    account_id: int
    soldier_type_percentages: Dict[str, float]  # soldier_type_name -> percentage


class TrainingPreferencesUpdate(BaseModel):
    """Schema for updating training preferences"""
    soldier_type_percentages: Dict[str, float]  # soldier_type_name -> percentage


class TrainingPreferencesResponse(TrainingPreferencesBase):
    """Response schema for training preferences"""
    id: int
    account_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


# Race Schemas
class RaceResponse(BaseModel):
    """Response schema for races"""
    id: int
    roc_race_id: int
    name: str
    created_at: datetime
    
    class Config:
        orm_mode = True


# ROC Stats Schemas
class RocStatResponse(BaseModel):
    """Response schema for ROC stats"""
    id: int
    name: str
    created_at: datetime
    
    class Config:
        orm_mode = True