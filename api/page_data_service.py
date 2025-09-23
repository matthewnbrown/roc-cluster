"""
Page Data Service

Processes ROC HTML pages from the queue and updates the database with parsed data.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from api.database import SessionLocal
from api.db_models import PageQueue, PageQueueStatus, Account
from api.page_parsers.spy_parser import parse_recon_data
from api.page_parsers.armory_parser import parse_armory_data
from api.page_parsers.battlefield_parser import parse_battlefield_data
from api.page_parsers.armory_parser import parse_armory_data

logger = logging.getLogger(__name__)


class PageParser(ABC):
    """Abstract base class for page parsers"""
    
    @abstractmethod
    def can_parse(self, page_type: str, page_content: str) -> bool:
        """Check if this parser can handle the given page type and content"""
        pass
    
    @abstractmethod
    async def parse(self, page_content: str, account_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the page content and return structured data"""
        pass


class SpyPageParser(PageParser):
    """Parser for spy/recon pages"""
    
    def can_parse(self, page_type: str, page_content: str) -> bool:
        return page_type == "spy"
    
    async def parse(self, page_content: str, account_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parse spy page data"""
        try:
            result = parse_recon_data(page_content)
            if result["success"]:
                # TODO: Store parsed spy data in database
                logger.info(f"Successfully parsed spy data for account {account_id}")
                return {"success": True, "data": result["data"]}
            else:
                logger.warning(f"Failed to parse spy data for account {account_id}: {result.get('error', 'Unknown error')}")
                return {"success": False, "error": result.get("error", "Unknown error")}
        except Exception as e:
            logger.error(f"Error parsing spy data for account {account_id}: {e}")
            return {"success": False, "error": str(e)}


class AttackPageParser(PageParser):
    """Parser for attack result pages"""
    
    def can_parse(self, page_type: str, page_content: str) -> bool:
        return page_type == "attack"
    
    async def parse(self, page_content: str, account_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parse attack result data"""
        try:
            # TODO: Implement attack result parsing
            logger.info(f"Parsing attack data for account {account_id}")
            return {"success": True, "message": "Attack data parsed (placeholder)"}
        except Exception as e:
            logger.error(f"Error parsing attack data for account {account_id}: {e}")
            return {"success": False, "error": str(e)}


class MetadataPageParser(PageParser):
    """Parser for metadata pages"""
    
    def can_parse(self, page_type: str, page_content: str) -> bool:
        return page_type == "metadata"
    
    async def parse(self, page_content: str, account_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parse metadata page data"""
        try:
            # TODO: Implement metadata parsing and storage
            logger.info(f"Parsing metadata for account {account_id}")
            return {"success": True, "message": "Metadata parsed (placeholder)"}
        except Exception as e:
            logger.error(f"Error parsing metadata for account {account_id}: {e}")
            return {"success": False, "error": str(e)}


class PageDataService:
    """Service for processing pages from the queue"""
    
    def __init__(self):
        self.parsers: List[PageParser] = [
            SpyPageParser(),
            AttackPageParser(),
            MetadataPageParser(),
        ]
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the page data service"""
        if self._running:
            logger.warning("Page data service is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_queue_loop())
        logger.info("Page data service started")
    
    async def stop(self):
        """Stop the page data service"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Page data service stopped")
    
    def _determine_page_type(self, request_url: Optional[str], response_url: Optional[str], page_content: str) -> str:
        """Determine page type from URL and content"""
        # Check response URL first (most accurate)
        if response_url:
            if "inteldetail" in response_url:
                return "spy"
            elif "detail.php?attack_id" in response_url:
                return "attack"
            elif "metadata" in response_url or "s_rank" in page_content:
                return "metadata"
            elif "base.php" in response_url:
                return "base"
            elif "armory.php" in response_url:
                return "armory"
            elif "train.php" in response_url:
                return "train"
            elif "upgrades.php" in response_url:
                return "upgrades"
        # Fall back to request URL
        if request_url:
            if "spy" in request_url or "recon" in request_url:
                return "spy"
            elif "attack" in request_url:
                return "attack"
            elif "metadata" in request_url:
                return "metadata"
        
        # Fall back to content analysis
        if "inteldetail" in page_content:
            return "spy"
        elif "detail.php" in page_content or "ribbon won" in page_content:
            return "attack"
        elif "s_rank" in page_content:
            return "metadata"
        
        return "unknown"
    
    async def _process_queue_loop(self):
        """Main processing loop for the queue"""
        while self._running:
            try:
                await self._process_next_page()
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in page processing loop: {e}")
                await asyncio.sleep(1)  # Wait longer on error
    
    async def _process_next_page(self):
        """Process the next page in the queue"""
        db = SessionLocal()
        try:
            # Get the next pending page
            page = db.query(PageQueue).filter(
                PageQueue.status == PageQueueStatus.PENDING
            ).order_by(PageQueue.created_at.asc()).first()
            
            if not page:
                return  # No pages to process
            
            # Mark as processing
            page.status = PageQueueStatus.PROCESSING
            db.commit()
            
            # Determine page type from URL
            page_type = self._determine_page_type(page.request_url, page.response_url, page.page_content)
            
            # Find appropriate parser
            parser = None
            for p in self.parsers:
                if p.can_parse(page_type, page.page_content):
                    parser = p
                    break
            
            if not parser:
                logger.warning(f"No parser found for page type: {page_type}")
                page.status = PageQueueStatus.FAILED
                page.error_message = f"No parser found for page type: {page_type}"
                page.processed_at = datetime.now(timezone.utc)
                db.commit()
                return
            
            # Parse the page
            metadata = {
                "request_url": page.request_url,
                "response_url": page.response_url,
                "request_method": page.request_method,
                "request_data": json.loads(page.request_data) if page.request_data else None,
                "request_time": page.request_time.isoformat() if page.request_time else None,
                "created_at": page.created_at.isoformat()
            }
            
            result = await parser.parse(page.page_content, page.account_id, metadata)
            
            if result["success"]:
                page.status = PageQueueStatus.COMPLETED
                logger.info(f"Successfully processed page {page.id} for account {page.account_id}")
            else:
                page.status = PageQueueStatus.FAILED
                page.error_message = result.get("error", "Unknown parsing error")
                logger.error(f"Failed to process page {page.id} for account {page.account_id}: {page.error_message}")
            
            page.processed_at = datetime.now(timezone.utc)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error processing page: {e}")
            if 'page' in locals():
                page.status = PageQueueStatus.FAILED
                page.error_message = str(e)
                page.processed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
    
    async def add_page_to_queue(
        self,
        account_id: int,
        page_content: str,
        request_url: Optional[str] = None,
        response_url: Optional[str] = None,
        request_method: str = "GET",
        request_data: Optional[Dict[str, Any]] = None,
        request_time: Optional[datetime] = None
    ) -> int:
        """Add a page to the processing queue"""
        db = SessionLocal()
        try:
            page = PageQueue(
                account_id=account_id,
                request_url=request_url,
                response_url=response_url,
                page_content=page_content,
                request_method=request_method,
                request_data=json.dumps(request_data) if request_data else None,
                request_time=request_time
            )
            db.add(page)
            db.commit()
            db.refresh(page)
            
            logger.info(f"Added page {page.id} to queue for account {account_id}")
            return page.id
            
        except Exception as e:
            logger.error(f"Error adding page to queue: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        db = SessionLocal()
        try:
            stats = {}
            for status in PageQueueStatus:
                count = db.query(PageQueue).filter(PageQueue.status == status).count()
                stats[status.value] = count
            return stats
        finally:
            db.close()


# Global instance
page_data_service = PageDataService()
