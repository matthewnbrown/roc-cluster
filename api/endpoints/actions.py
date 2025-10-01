"""
Action endpoints for ROC account operations
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import logging
from datetime import datetime, timezone

from api.schemas import (
    AccountIdentifier, AccountIdentifierType, AttackRequest, CaptchaSolutionItem, SabotageRequest, SpyRequest, BecomeOfficerRequest, SendCreditsRequest,
    RecruitRequest, ArmoryPurchaseRequest, TrainingPurchaseRequest, 
    SetCreditSavingRequest, PurchaseUpgradeRequest, BuyUpgradeRequest, ActionResponse
)
from api.account_manager import AccountManager
from api.database import get_db
from api.db_models import Weapon
from api.target_rate_limiter import roc_target_rate_limiter
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()

def get_account_manager() -> AccountManager:
    """Dependency to get account manager"""
    from main import account_manager
    if account_manager is None:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    return account_manager

def validate_weapon_id(weapon_id: int, db: Session) -> bool:
    """Validate that the weapon ID exists in the database"""
    weapon = db.query(Weapon).filter(Weapon.roc_weapon_id == weapon_id).first()
    return weapon is not None

# User Actions (targeting other users)
@router.post("/attack", response_model=ActionResponse)
async def attack_user(
    request: AttackRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Attack another user"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.ATTACK,
            max_retries=request.max_retries,
            target_id=request.target_id,
            turns=request.turns
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in attack action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sabotage", response_model=ActionResponse)
async def sabotage_user(
    request: SabotageRequest,
    manager: AccountManager = Depends(get_account_manager),
    db: Session = Depends(get_db)
):
    """Sabotage another user"""
    try:
        # Validate that the enemy_weapon is a valid ROC weapon
        if not validate_weapon_id(request.enemy_weapon, db):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid weapon ID: {request.enemy_weapon}. Weapon not found in database."
            )
        
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.SABOTAGE,
            max_retries=request.max_retries,
            target_id=request.target_id,
            spy_count=request.spy_count,  # Fixed: was using 'spies' instead of 'spy_count'
            enemy_weapon=request.enemy_weapon
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sabotage action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/spy", response_model=ActionResponse)
async def spy_user(
    request: SpyRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Spy on another user"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.SPY,
            max_retries=request.max_retries,
            target_id=request.target_id,
            spy_count=request.spy_count
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in spy action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/become-officer", response_model=ActionResponse)
async def become_officer(
    request: BecomeOfficerRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Become an officer of another user"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.BECOME_OFFICER,
            max_retries=request.max_retries,
            target_id=request.target_id
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in become officer action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/send-credits", response_model=ActionResponse)
async def send_credits(
    request: SendCreditsRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Send credits to another user"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.SEND_CREDITS,
            max_retries=request.max_retries,
            target_id=request.target_id,
            amount=request.amount
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in send credits action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Self Actions
@router.post("/recruit", response_model=ActionResponse)
async def recruit_soldiers(
    request: RecruitRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Recruit soldiers"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.RECRUIT,
            max_retries=request.max_retries,
            soldier_type=request.soldier_type,
            count=request.count
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in recruit action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/armory-purchase", response_model=ActionResponse)
async def purchase_armory(
    request: ArmoryPurchaseRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Purchase items from armory"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.PURCHASE_ARMORY,
            max_retries=request.max_retries,
            items=request.items
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in armory purchase action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/training-purchase", response_model=ActionResponse)
async def purchase_training(
    request: TrainingPurchaseRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Purchase training"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.PURCHASE_TRAINING,
            max_retries=request.max_retries,
            training_orders=request.training_orders
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in training purchase action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/set-credit-saving", response_model=ActionResponse)
async def set_credit_saving(
    request: SetCreditSavingRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Set credit saving to 'on' or 'off'"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.SET_CREDIT_SAVING,
            max_retries=request.max_retries,
            value=request.value
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in set credit saving action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/buy-upgrade", response_model=ActionResponse)
async def buy_upgrade(
    request: BuyUpgradeRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Buy upgrade - supports siege, fortification, covert, recruiter"""
    try:
        result = await manager.execute_action(
            id_type=request.acting_user.id_type,
            id=request.acting_user.id,
            action=AccountManager.ActionType.BUY_UPGRADE,
            max_retries=request.max_retries,
            upgrade_option=request.upgrade_option
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message"),
            error=result.get("error"),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error in buy upgrade action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{account_id}/solved-captchas", response_model=List[CaptchaSolutionItem])
async def get_solved_captchas(
    account_id: int,
    count: int = 1,
    min_confidence: float = 0,
    manager: AccountManager = Depends(get_account_manager)
):
    """Get solved captchas"""
    try:    
        result = await manager.execute_action(
            id_type=AccountIdentifierType.ID,
            id=account_id,
            action=AccountManager.ActionType.GET_SOLVED_CAPTCHAS,
            count=count,
            min_confidence=min_confidence
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting solved captchas: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Utility endpoints
@router.get("/account/{account_id}/metadata")
async def get_account_metadata(
    account_id: int,
    max_retries: int = 0,
    manager: AccountManager = Depends(get_account_manager)
):
    """Get account metadata from ROC website"""
    try:
        result = await manager.execute_action(
            id_type=AccountIdentifierType.ID,
            id=account_id,
            action=AccountManager.ActionType.GET_METADATA,
            max_retries=max_retries)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=503, 
                detail=result.get("error", "Failed to retrieve metadata")
            )
        
        return result.get("data")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/rate-limits/stats")
async def get_rate_limit_stats():
    """Get ROC API rate limiting statistics"""
    try:
        global_stats = roc_target_rate_limiter.get_global_stats()
        return {
            "global_stats": global_stats,
            "description": "ROC API rate limiting prevents too many concurrent requests to the same target user"
        }
    except Exception as e:
        logger.error(f"Error getting rate limit stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/rate-limits/target/{target_id}")
async def get_target_rate_limit_stats(target_id: str):
    """Get rate limiting statistics for a specific target"""
    try:
        target_stats = await roc_target_rate_limiter.get_target_stats(target_id)
        return {
            "target_id": target_id,
            "stats": target_stats,
            "description": f"Current ROC API request status for target {target_id}"
        }
    except Exception as e:
        logger.error(f"Error getting target rate limit stats for {target_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
