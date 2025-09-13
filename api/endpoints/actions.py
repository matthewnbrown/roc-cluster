"""
Action endpoints for ROC account operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
from datetime import datetime

from api.models import (
    AttackRequest, SabotageRequest, SpyRequest, BecomeOfficerRequest, SendCreditsRequest,
    RecruitRequest, ArmoryPurchaseRequest, TrainingPurchaseRequest, 
    EnableCreditSavingRequest, PurchaseUpgradeRequest, ActionResponse,
    BulkActionRequest, BulkActionResponse
)
from api.account_manager import AccountManager

logger = logging.getLogger(__name__)
router = APIRouter()

def get_account_manager() -> AccountManager:
    """Dependency to get account manager"""
    from main import account_manager
    if account_manager is None:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    return account_manager

# User Actions (targeting other users)
@router.post("/attack", response_model=ActionResponse)
async def attack_user(
    request: AttackRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Attack another user"""
    try:
        result = await manager.execute_action(
            request.account_id,
            "attack",
            target_id=request.target_id
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in attack action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sabotage", response_model=ActionResponse)
async def sabotage_user(
    request: SabotageRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Sabotage another user"""
    try:
        result = await manager.execute_action(
            request.account_id,
            "sabotage",
            target_id=request.target_id
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
        )
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
            request.account_id,
            "spy",
            target_id=request.target_id
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
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
            request.account_id,
            "become_officer",
            target_id=request.target_id
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
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
            request.account_id,
            "send_credits",
            target_id=request.target_id,
            amount=request.amount
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
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
            request.account_id,
            "recruit",
            soldier_type=request.soldier_type,
            count=request.count
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
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
            request.account_id,
            "purchase_armory",
            items=request.items
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
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
            request.account_id,
            "purchase_training",
            training_type=request.training_type,
            count=request.count
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in training purchase action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/enable-credit-saving", response_model=ActionResponse)
async def enable_credit_saving(
    request: EnableCreditSavingRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Enable credit saving"""
    try:
        result = await manager.execute_action(
            request.account_id,
            "enable_credit_saving"
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in enable credit saving action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/purchase-upgrade", response_model=ActionResponse)
async def purchase_upgrade(
    request: PurchaseUpgradeRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Purchase upgrade"""
    try:
        result = await manager.execute_action(
            request.account_id,
            "purchase_upgrade",
            upgrade_type=request.upgrade_type
        )
        
        return ActionResponse(
            success=result["success"],
            message=result.get("message", ""),
            error=result.get("error"),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in purchase upgrade action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Bulk Actions
@router.post("/bulk", response_model=BulkActionResponse)
async def execute_bulk_action(
    request: BulkActionRequest,
    manager: AccountManager = Depends(get_account_manager)
):
    """Execute an action on multiple accounts"""
    try:
        # Prepare parameters for bulk action
        kwargs = {}
        if request.parameters:
            kwargs.update(request.parameters)
        if request.target_id:
            kwargs["target_id"] = request.target_id
        
        results = await manager.execute_bulk_action(
            request.account_ids,
            request.action_type,
            **kwargs
        )
        
        # Count successful and failed actions
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        
        return BulkActionResponse(
            total_accounts=len(request.account_ids),
            successful=successful,
            failed=failed,
            results=[
                ActionResponse(
                    success=r.get("success", False),
                    message=r.get("message", ""),
                    error=r.get("error"),
                    timestamp=datetime.now()
                ) for r in results
            ],
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in bulk action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Utility endpoints
@router.get("/account/{account_id}/metadata")
async def get_account_metadata(
    account_id: int,
    manager: AccountManager = Depends(get_account_manager)
):
    """Get account metadata from ROC website"""
    try:
        result = await manager.execute_action(account_id, "get_metadata")
        
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
