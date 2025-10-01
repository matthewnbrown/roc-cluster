"""
ROC Target Rate Limiter for managing concurrent HTTP requests to ROC API per target
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timezone, timedelta
from config import settings

logger = logging.getLogger(__name__)


class ROCTargetRateLimiter:
    """
    Rate limiter that prevents too many concurrent HTTP requests to the ROC API for the same target.
    
    This is used for actions that target other users (attack, sabotage, spy, etc.)
    to prevent overwhelming the ROC API with too many simultaneous requests to the same target.
    """
    
    def __init__(self, max_concurrent_requests: int = None, timeout_seconds: int = None):
        """
        Initialize the rate limiter.
        
        Args:
            max_concurrent_requests: Maximum number of concurrent requests per target
            timeout_seconds: Timeout for acquiring a lock (seconds)
        """
        self.max_concurrent_requests = max_concurrent_requests or settings.MAX_CONCURRENT_TARGET_REQUESTS
        self.timeout_seconds = timeout_seconds or settings.TARGET_RATE_LIMIT_TIMEOUT
        
        # Dictionary to track semaphores per target
        # Format: {target_id: asyncio.Semaphore}
        self._target_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # Dictionary to track active requests per target
        # Format: {target_id: Set[request_id]}
        self._active_requests: Dict[str, Set[str]] = {}
        
        # Dictionary to track when semaphores were last used
        # Format: {target_id: datetime}
        self._last_used: Dict[str, datetime] = {}
        
        # Cleanup task for removing unused semaphores
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_started = False
    
    def _start_cleanup_task(self):
        """Start the background cleanup task"""
        if not self._cleanup_started:
            try:
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._cleanup_unused_semaphores())
                    self._cleanup_started = True
            except RuntimeError:
                # No event loop running, skip cleanup task for now
                pass
    
    async def _cleanup_unused_semaphores(self):
        """Background task to clean up unused semaphores"""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                current_time = datetime.now(timezone.utc)
                cleanup_threshold = current_time - timedelta(minutes=5)
                
                # Find semaphores that haven't been used recently
                unused_targets = []
                for target_id, last_used in self._last_used.items():
                    if last_used < cleanup_threshold:
                        # Check if semaphore is not currently in use
                        semaphore = self._target_semaphores.get(target_id)
                        if semaphore and semaphore.locked() == False:
                            unused_targets.append(target_id)
                
                # Remove unused semaphores
                for target_id in unused_targets:
                    self._remove_target_semaphore(target_id)
                    logger.debug(f"Cleaned up unused semaphore for target {target_id}")
                
                if unused_targets:
                    logger.info(f"Cleaned up {len(unused_targets)} unused target semaphores")
                    
            except Exception as e:
                logger.error(f"Error in semaphore cleanup task: {e}", exc_info=True)
    
    def _get_or_create_semaphore(self, target_id: str) -> asyncio.Semaphore:
        """Get or create a semaphore for the given target"""
        if target_id not in self._target_semaphores:
            self._target_semaphores[target_id] = asyncio.Semaphore(self.max_concurrent_requests)
            self._active_requests[target_id] = set()
        
        # Update last used time
        self._last_used[target_id] = datetime.now(timezone.utc)
        
        return self._target_semaphores[target_id]
    
    def _remove_target_semaphore(self, target_id: str):
        """Remove semaphore and related data for a target"""
        self._target_semaphores.pop(target_id, None)
        self._active_requests.pop(target_id, None)
        self._last_used.pop(target_id, None)
    
    def _generate_request_id(self, target_id: str) -> str:
        """Generate a unique request ID for tracking"""
        import uuid
        return f"{target_id}_{uuid.uuid4().hex[:8]}"
    
    async def acquire_lock(self, target_id: str, request_id: Optional[str] = None) -> str:
        """
        Acquire a lock for the given target.
        
        Args:
            target_id: The target user ID to acquire lock for
            request_id: Optional request ID (will generate if not provided)
            
        Returns:
            str: The request ID for this lock
            
        Raises:
            asyncio.TimeoutError: If unable to acquire lock within timeout
        """
        # Start cleanup task if not already started
        self._start_cleanup_task()
        
        if request_id is None:
            request_id = self._generate_request_id(target_id)
        
        semaphore = self._get_or_create_semaphore(target_id)
        
        try:
            # Acquire the semaphore with timeout
            await asyncio.wait_for(
                semaphore.acquire(),
                timeout=self.timeout_seconds
            )
            
            # Track the active request
            self._active_requests[target_id].add(request_id)
            
            logger.debug(f"Acquired lock for target {target_id}, request {request_id}")
            return request_id
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout acquiring lock for target {target_id} after {self.timeout_seconds}s")
            raise
    
    async def release_lock(self, target_id: str, request_id: str):
        """
        Release a lock for the given target.
        
        Args:
            target_id: The target user ID to release lock for
            request_id: The request ID to release
        """
        semaphore = self._target_semaphores.get(target_id)
        if semaphore is None:
            logger.warning(f"Attempted to release lock for unknown target {target_id}")
            return
        
        # Remove from active requests
        self._active_requests[target_id].discard(request_id)
        
        # Release the semaphore
        semaphore.release()
        
        logger.debug(f"Released lock for target {target_id}, request {request_id}")
    
    async def get_target_stats(self, target_id: str) -> Dict[str, int]:
        """
        Get statistics for a specific target.
        
        Args:
            target_id: The target user ID
            
        Returns:
            Dict containing current usage statistics
        """
        semaphore = self._target_semaphores.get(target_id)
        if semaphore is None:
            return {
                "max_concurrent": self.max_concurrent_requests,
                "current_active": 0,
                "available_slots": self.max_concurrent_requests
            }
        
        current_active = len(self._active_requests.get(target_id, set()))
        available_slots = self.max_concurrent_requests - current_active
        
        return {
            "max_concurrent": self.max_concurrent_requests,
            "current_active": current_active,
            "available_slots": available_slots
        }
    
    def get_global_stats(self) -> Dict[str, int]:
        """
        Get global statistics for all targets.
        
        Returns:
            Dict containing global usage statistics
        """
        total_targets = len(self._target_semaphores)
        total_active_requests = sum(len(requests) for requests in self._active_requests.values())
        
        return {
            "total_targets": total_targets,
            "total_active_requests": total_active_requests,
            "max_concurrent_per_target": self.max_concurrent_requests,
            "timeout_seconds": self.timeout_seconds
        }
    
    async def cleanup(self):
        """Clean up resources and stop background tasks"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all data
        self._target_semaphores.clear()
        self._active_requests.clear()
        self._last_used.clear()


# Global instance
roc_target_rate_limiter = ROCTargetRateLimiter()
