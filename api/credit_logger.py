"""
Credit logging wrapper for the generic async logger
"""

import logging
from typing import Optional
from api.async_logger import async_logger
from api.db_models import SentCreditLog

logger = logging.getLogger(__name__)

class CreditLogger:
    """Wrapper for credit logging using the generic async logger"""
    
    def __init__(self):
        self.log_type = 'credit_log'
        # Register the credit log handler
        async_logger.register_handler(self.log_type, SentCreditLog)
    
    async def log_credit_attempt(
        self, 
        sender_account_id: int, 
        target_user_id: str, 
        amount: int, 
        success: bool, 
        error_message: Optional[str] = None
    ):
        """
        Log a credit sending attempt asynchronously
        
        Args:
            sender_account_id: ID of the account sending credits
            target_user_id: ROC user ID of the target
            amount: Amount of credits attempted to send
            success: Whether the credit send was successful
            error_message: Error message if failed
        """
        log_data = {
            'sender_account_id': sender_account_id,
            'target_user_id': target_user_id,
            'amount': amount,
            'success': success,
            'error_message': error_message
        }
        
        await async_logger.log(self.log_type, log_data)

# Global instance
credit_logger = CreditLogger()
