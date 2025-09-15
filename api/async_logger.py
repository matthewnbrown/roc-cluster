"""
Generic async logging service for non-blocking database operations
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Type, Union
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from api.database import SessionLocal

logger = logging.getLogger(__name__)

class AsyncLogger:
    """Generic async logger that uses background tasks to avoid blocking the main flow"""
    
    def __init__(self, max_queue_size: int = 1000):
        self._log_queue = asyncio.Queue(maxsize=max_queue_size)
        self._background_task = None
        self._running = False
        self._log_handlers = {}  # Store handlers for different log types
    
    async def start(self):
        """Start the background logging task"""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._process_logs())
            logger.info("Async logger started")
    
    async def stop(self):
        """Stop the background logging task"""
        if self._running:
            self._running = False
            if self._background_task:
                await self._log_queue.put(None)  # Signal to stop
                await self._background_task
                logger.info("Async logger stopped")
    
    def register_handler(self, log_type: str, model_class: Type[DeclarativeMeta], handler_func: Optional[callable] = None):
        """
        Register a handler for a specific log type
        
        Args:
            log_type: String identifier for the log type (e.g., 'credit_log', 'action_log')
            model_class: SQLAlchemy model class to use for logging
            handler_func: Optional custom handler function. If None, uses default handler
        """
        self._log_handlers[log_type] = {
            'model_class': model_class,
            'handler_func': handler_func or self._default_handler
        }
        logger.info(f"Registered handler for log type: {log_type}")
    
    async def log(
        self, 
        log_type: str, 
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """
        Log data asynchronously
        
        Args:
            log_type: Type of log (must be registered)
            data: Dictionary of data to log
            timestamp: Optional timestamp, defaults to now
        """
        if log_type not in self._log_handlers:
            logger.error(f"No handler registered for log type: {log_type}")
            return
        
        log_entry = {
            'log_type': log_type,
            'data': data,
            'timestamp': timestamp or datetime.now(timezone.utc)
        }
        
        try:
            # Non-blocking put - if queue is full, we'll just skip logging
            self._log_queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            logger.warning(f"Log queue is full, skipping {log_type} log entry")
    
    async def _process_logs(self):
        """Background task to process log entries"""
        while self._running:
            try:
                # Wait for log entry with timeout
                log_entry = await asyncio.wait_for(self._log_queue.get(), timeout=1.0)
                
                # Check for stop signal
                if log_entry is None:
                    break
                
                # Process the log entry
                await self._write_log_to_db(log_entry)
                
            except asyncio.TimeoutError:
                # No logs to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing log: {e}")
                # Continue processing even if one log fails
                continue
    
    async def _write_log_to_db(self, log_entry: dict):
        """Write log entry to database using registered handler"""
        log_type = log_entry['log_type']
        data = log_entry['data']
        timestamp = log_entry['timestamp']
        
        if log_type not in self._log_handlers:
            logger.error(f"No handler registered for log type: {log_type}")
            return
        
        handler_info = self._log_handlers[log_type]
        handler_func = handler_info['handler_func']
        
        try:
            await handler_func(handler_info['model_class'], data, timestamp)
        except Exception as e:
            logger.error(f"Failed to write {log_type} log to database: {e}")
            # Don't re-raise the exception to prevent the background task from stopping
    
    async def _default_handler(self, model_class: Type[DeclarativeMeta], data: Dict[str, Any], timestamp: datetime):
        """Default handler that creates a model instance and saves it"""
        db = SessionLocal()
        try:
            # Add timestamp to data if not already present
            if 'timestamp' not in data:
                data['timestamp'] = timestamp
            
            # Create model instance
            log_entry = model_class(**data)
            
            db.add(log_entry)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to write log to database: {e}")
            db.rollback()
            raise
        finally:
            db.close()

# Global instance
async_logger = AsyncLogger()
