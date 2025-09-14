"""
Account Manager for handling multiple ROC accounts
"""

import asyncio
from enum import Enum
import logging
from typing import Dict, List, Optional, Any
from api.models import Account, AccountIdentifier, AccountIdentifierType
from api.game_account_manager import GameAccountManager

logger = logging.getLogger(__name__)

async def create_account_manager(account: Account) -> GameAccountManager:
    """Factory function to create a ROCAccountManager instance"""
    roc_account = GameAccountManager(account)
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
        PURCHASE_TRAINING = "purchase_training"
        ENABLE_CREDIT_SAVING = "enable_credit_saving"
        PURCHASE_UPGRADE = "purchase_upgrade"
        GET_METADATA = "get_metadata"


    def __init__(self):
        # No longer storing persistent instances
        pass
    
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
    
    async def execute_action(self, id_type: AccountIdentifierType, id: str, action: ActionType = None, **kwargs) -> Dict[str, Any]:
        """Execute an action on a specific account using on-demand creation"""
        # Get account from database
        
        account = await self.get_account_from_db(id_type, id)
        
        if not account:
            return {"success": False, "error": "Account not found"}
        
        # Create ROCAccountManager instance on-demand
        roc_account = None
        try:
            roc_account = await create_account_manager(account)
            
            # Map action names to methods
            action_map = {
                "attack": roc_account.attack,
                "sabotage": roc_account.sabotage,
                "spy": roc_account.spy,
                "become_officer": roc_account.become_officer,
                "send_credits": roc_account.send_credits,
                "recruit": roc_account.recruit,
                "purchase_armory": roc_account.purchase_armory,
                "purchase_training": roc_account.purchase_training,
                "enable_credit_saving": roc_account.enable_credit_saving,
                "purchase_upgrade": roc_account.purchase_upgrade,
                "get_metadata": roc_account.get_metadata,
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
    
    async def execute_bulk_action(self, accounts: List[AccountIdentifier], action: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute an action on multiple accounts using on-demand creation"""
        tasks = []
        
        # find if action is an actiontype
        if action in self.ActionType:
            action = self.ActionType(action)
        else:
            return {"success": False, "error": "Invalid action"}
        
        for account_id in accounts:
            task = self.execute_action(account_id.id_type, account_id.id, action, **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "account_id_type": accounts[i].id_type,
                    "account_id": accounts[i].id,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "account_id_type": accounts[i].id_type,
                    "account_id": accounts[i].id,
                    **result
                })
        
        return processed_results
    
    async def cleanup(self):
        """Cleanup method - no longer needed since we don't store persistent instances"""
        pass
