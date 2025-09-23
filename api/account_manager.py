"""
Account Manager for handling multiple ROC accounts
"""

import asyncio
from enum import Enum
import logging
from typing import Dict, List, Optional, Any
from api.db_models import Account
from api.schemas import AccountIdentifier, AccountIdentifierType
from api.game_account_manager import GameAccountManager
from config import settings

logger = logging.getLogger(__name__)

async def create_account_manager(account: Account, max_retries: int = 0) -> GameAccountManager:
    """Factory function to create a ROCAccountManager instance"""
    roc_account = GameAccountManager(account, max_retries=max_retries)
    success = await roc_account.initialize()
    if not success:
        raise Exception(f"Failed to initialize account {account.username}")
    return roc_account

class AccountManager:
    """Manages multiple ROC accounts using on-demand creation"""
    
    # enum for action types
    class ActionType(Enum):
        ATTACK = "attack"
        SABOTAGE = "sabotage"
        SPY = "spy"
        BECOME_OFFICER = "become_officer"
        SEND_CREDITS = "send_credits"
        RECRUIT = "recruit"
        PURCHASE_ARMORY = "purchase_armory"
        PURCHASE_ARMORY_BY_PREFERENCES = "purchase_armory_by_preferences"
        PURCHASE_TRAINING = "purchase_training"
        SET_CREDIT_SAVING = "set_credit_saving"
        BUY_UPGRADE = "buy_upgrade"
        GET_METADATA = "get_metadata"
        GET_SOLVED_CAPTCHAS = "get_solved_captchas"


    def __init__(self):
        # No longer storing persistent instances
        # Limit concurrent operations to prevent resource exhaustion
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_OPERATIONS)
    
    async def get_account_from_db(self, id_type: AccountIdentifierType, id: str) -> Optional[Account]:
        """Get account from database by ID"""
        from api.database import SessionLocal
        
        db = SessionLocal()
        try:
            if id_type == AccountIdentifierType.ID:
                return db.query(Account).filter(Account.id == id).first()
            elif id_type == AccountIdentifierType.USERNAME:
                return db.query(Account).filter(Account.username.ilike(id)).first()
            elif id_type == AccountIdentifierType.ROC_ID:
                return db.query(Account).filter(Account.roc_id == id).first()
        finally:
            db.close()
    
    async def get_all_accounts_from_db(self) -> List[Account]:
        """Get all accounts from database"""
        from api.database import SessionLocal
        
        db = SessionLocal()
        try:
            return db.query(Account).all()
        finally:
            db.close()
    
    async def execute_action(self, id_type: AccountIdentifierType, id: str, action: ActionType = None, max_retries: int = 0, **kwargs) -> Dict[str, Any]:
        """Execute an action on a specific account using on-demand creation"""
        # Limit concurrent operations
        async with self._semaphore:
            # Get account from database
            account = await self.get_account_from_db(id_type, id)
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Create ROCAccountManager instance on-demand
            roc_account = None
            try:
                roc_account = await create_account_manager(account, max_retries=max_retries)
                
                # Map action names to methods
                action_map = {
                    "attack": roc_account.attack,
                    "sabotage": roc_account.sabotage,
                    "spy": roc_account.spy,
                    "become_officer": roc_account.become_officer,
                    "send_credits": roc_account.send_credits,
                    "recruit": roc_account.recruit,
                    "purchase_armory": roc_account.purchase_armory,
                    "purchase_armory_by_preferences": roc_account.purchase_armory_by_preferences,
                    "purchase_training": roc_account.purchase_training,
                    "set_credit_saving": roc_account.set_credit_saving,
                    "buy_upgrade": roc_account.buy_upgrade,
                    "get_metadata": roc_account.get_metadata,
                    "get_solved_captchas": roc_account.get_solved_captchas,
                }
                
                if action.value not in action_map:
                    return {"success": False, "error": f"Unknown action: {action}"}
                
                result = await action_map[action.value](**kwargs)
                return result
                
            except Exception as e:
                logger.error(f"Error executing action {action} on account {id_type} {id}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                # Always cleanup the ROCAccountManager instance
                if roc_account:
                    await roc_account.cleanup()
    

    
    async def cleanup(self):
        """Cleanup method - no longer needed since we don't store persistent instances"""
        pass
