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

async def create_account_manager(account: Account, max_retries: int = 0, preloaded_cookies: Optional[Dict[str, Any]] = None, use_page_data_service: bool = False) -> GameAccountManager:
    """Factory function to create a ROCAccountManager instance"""
    roc_account = GameAccountManager(account, max_retries=max_retries, use_page_data_service=use_page_data_service)
    success = await roc_account.initialize(preloaded_cookies=preloaded_cookies)
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
        UPDATE_ARMORY_PREFERENCES = "update_armory_preferences"
        UPDATE_TRAINING_PREFERENCES = "update_training_preferences"
        GET_CARDS = "get_cards"
        SEND_CARDS = "send_cards"
        DELAY = "delay"


    def __init__(self):
        # No longer storing persistent instances
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
    
    async def bulk_load_accounts(self, account_ids: List[int]) -> Dict[int, Account]:
        """Bulk load accounts for multiple account IDs in a single query"""
        from api.database import SessionLocal
        
        if not account_ids:
            return {}
        
        db = SessionLocal()
        try:
            # Single query to get all accounts for the specified account IDs
            accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
            
            # Convert to dictionary format: {account_id: Account}
            accounts_dict = {account.id: account for account in accounts}
            
            logger.info(f"Bulk loaded {len(accounts_dict)} accounts out of {len(account_ids)} requested")
            return accounts_dict
            
        finally:
            db.close()
    
    async def bulk_load_cookies(self, account_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Bulk load cookies for multiple accounts in a single query"""
        from api.database import SessionLocal
        from api.db_models import UserCookies
        import json
        
        if not account_ids:
            return {}
        
        db = SessionLocal()
        try:
            # Single query to get all cookies for the specified account IDs
            user_cookies_list = db.query(UserCookies).filter(
                UserCookies.account_id.in_(account_ids)
            ).all()
            
            # Convert to dictionary format: {account_id: cookies_dict}
            cookies_dict = {}
            for user_cookies in user_cookies_list:
                try:
                    cookies_data = json.loads(user_cookies.cookies)
                    cookies_dict[user_cookies.account_id] = cookies_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse cookies for account {user_cookies.account_id}: {e}")
                    cookies_dict[user_cookies.account_id] = {}
            
            logger.info(f"Bulk loaded cookies for {len(cookies_dict)} accounts out of {len(account_ids)} requested")
            return cookies_dict
            
        finally:
            db.close()
    
    async def execute_action(self, id_type: AccountIdentifierType, id: str, action: ActionType = None, max_retries: int = 0, preloaded_cookies: Optional[Dict[str, Any]] = None, preloaded_account: Optional[Account] = None, bypass_semaphore: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute an action on a specific account using on-demand creation"""
        # Limit concurrent operations (but with much higher limit now)
        # Allow bypassing semaphore for parallel execution
        if bypass_semaphore:
            return await self._execute_action_internal(id_type, id, action, max_retries, preloaded_cookies, preloaded_account, **kwargs)
        else:
            async with self._semaphore:
                return await self._execute_action_internal(id_type, id, action, max_retries, preloaded_cookies, preloaded_account, **kwargs)
    
    async def _execute_action_internal(self, id_type: AccountIdentifierType, id: str, action: ActionType = None, max_retries: int = 0, preloaded_cookies: Optional[Dict[str, Any]] = None, preloaded_account: Optional[Account] = None, **kwargs) -> Dict[str, Any]:
        """Internal method to execute an action without semaphore"""
        # Use preloaded account if available, otherwise get from database
        if preloaded_account is not None:
            account = preloaded_account
        else:
            account = await self.get_account_from_db(id_type, id)
        
        if not account:
            return {"success": False, "error": "Account not found"}
        
        # Create ROCAccountManager instance on-demand
        roc_account = None
        try:
            roc_account = await create_account_manager(account, max_retries=max_retries, preloaded_cookies=preloaded_cookies, use_page_data_service=settings.USE_PAGE_DATA_SERVICE)
            
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
                "update_armory_preferences": roc_account.update_armory_preferences,
                "update_training_preferences": roc_account.update_training_preferences,
                "get_cards": roc_account.get_cards,
                "send_cards": roc_account.send_cards,
            }
            
            if action.value not in action_map:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            result = await action_map[action.value](**kwargs)
            return result
            
        except Exception as e:
            logger.error(f"Error executing action {action} on account {id_type} {id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            # Always cleanup the ROCAccountManager instance
            if roc_account:
                await roc_account.cleanup()
    

    
    async def cleanup(self):
        """Cleanup method - no longer needed since we don't store persistent instances"""
        pass
