"""
Action logging wrapper for the generic async logger
"""

import logging
from typing import Optional, Dict, Any
from api.async_logger import async_logger
from api.models import AccountAction

logger = logging.getLogger(__name__)

class ActionLogger:
    """Wrapper for action logging using the generic async logger"""
    
    def __init__(self):
        self.log_type = 'action_log'
        # Register the action log handler
        async_logger.register_handler(self.log_type, AccountAction)
    
    async def log_action(
        self, 
        account_id: int, 
        action_type: str, 
        target_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """
        Log an account action asynchronously
        
        Args:
            account_id: ID of the account performing the action
            action_type: Type of action (attack, sabotage, spy, etc.)
            target_id: Target user ID for user actions
            parameters: Action parameters
            result: Action result
        """
        log_data = {
            'account_id': account_id,
            'action_type': action_type,
            'target_id': target_id,
            'parameters': str(parameters) if parameters else None,
            'result': str(result) if result else None
        }
        
        await async_logger.log(self.log_type, log_data)

# Global instance
action_logger = ActionLogger()
