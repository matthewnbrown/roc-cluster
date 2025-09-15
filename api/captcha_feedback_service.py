"""
Async captcha feedback service for non-blocking captcha solver reporting
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from api.captcha import Captcha, CaptchaSolver

logger = logging.getLogger(__name__)

@dataclass
class CaptchaFeedback:
    """Data class for captcha feedback"""
    captcha: Captcha
    request_id: str
    was_correct: bool
    actual_answer: Optional[str] = None

class AsyncCaptchaFeedbackService:
    """Async service for reporting captcha feedback without blocking the main flow"""
    
    def __init__(self, max_queue_size: int = 1000):
        self._feedback_queue = asyncio.Queue(maxsize=max_queue_size)
        self._background_task = None
        self._running = False
        # Single captcha solver instance for all feedback
        self._captcha_solver = CaptchaSolver(
            solver_url="http://localhost:8000/api/v1/solve", 
            report_url="http://localhost:8000/api/v1/feedback"
        )
    
    async def start(self):
        """Start the background feedback processing task"""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._process_feedback())
            logger.info("Async captcha feedback service started")
    
    async def stop(self):
        """Stop the background feedback processing task"""
        if self._running:
            self._running = False
            if self._background_task:
                await self._feedback_queue.put(None)  # Signal to stop
                await self._background_task
                logger.info("Async captcha feedback service stopped")
    
    async def report_feedback(
        self, 
        account_id: int,
        captcha: Captcha,
        request_id: str,
        was_correct: bool,
        actual_answer: Optional[str] = None
    ):
        """
        Report captcha feedback asynchronously
        
        Args:
            account_id: ID of the account (for logging purposes)
            captcha: The captcha object
            request_id: Request ID from the captcha solver
            was_correct: Whether the captcha was solved correctly
            actual_answer: The actual correct answer if known
        """
        feedback = CaptchaFeedback(
            captcha=captcha,
            request_id=request_id,
            was_correct=was_correct,
            actual_answer=actual_answer
        )
        
        feedback_data = {
            'account_id': account_id,
            'feedback': feedback
        }
        
        try:
            # Non-blocking put - if queue is full, we'll just skip feedback
            self._feedback_queue.put_nowait(feedback_data)
        except asyncio.QueueFull:
            logger.warning("Captcha feedback queue is full, skipping feedback report")
    
    async def _process_feedback(self):
        """Background task to process captcha feedback"""
        while self._running:
            try:
                # Wait for feedback with timeout
                feedback_data = await asyncio.wait_for(self._feedback_queue.get(), timeout=1.0)
                
                # Check for stop signal
                if feedback_data is None:
                    break
                
                # Process the feedback
                await self._send_feedback(feedback_data)
                
            except asyncio.TimeoutError:
                # No feedback to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing captcha feedback: {e}")
                # Continue processing even if one feedback fails
                continue
    
    async def _send_feedback(self, feedback_data: dict):
        """Send feedback to the captcha solver"""
        account_id = feedback_data['account_id']
        feedback = feedback_data['feedback']
        
        try:
            await self._captcha_solver.report(
                captcha=feedback.captcha,
                request_id=feedback.request_id,
                was_correct=feedback.was_correct,
                actual_answer=feedback.actual_answer
            )
            logger.debug(f"Successfully reported captcha feedback for account {account_id}")
        except Exception as e:
            logger.error(f"Failed to send captcha feedback for account {account_id}: {e}")

# Global instance
captcha_feedback_service = AsyncCaptchaFeedbackService()
