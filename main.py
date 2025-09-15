"""
ROC Cluster Management API

A lightweight API for managing multiple ROC accounts simultaneously.
Built on FastAPI for high performance and easy frontend integration.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import List, Dict, Any, Optional
import logging

from api.database import init_db, get_db
from api.models import Account, AccountCreate, AccountResponse
from api.account_manager import AccountManager
from api.endpoints import accounts, actions
from api.async_logger import async_logger
from api.captcha_feedback_service import captcha_feedback_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global account manager instance
account_manager: Optional[AccountManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global account_manager
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start async logger
    await async_logger.start()
    logger.info("Async logger started")
    
    # Start captcha feedback service
    await captcha_feedback_service.start()
    logger.info("Captcha feedback service started")
    
    account_manager = AccountManager()
    logger.info("Account manager initialized")
    
    yield
    
    # Stop captcha feedback service
    await captcha_feedback_service.stop()
    logger.info("Captcha feedback service stopped")
    
    # Stop async logger
    await async_logger.stop()
    logger.info("Async logger stopped")
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="ROC Cluster Management API",
    description="Lightweight API for managing multiple ROC accounts",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(actions.router, prefix="/api/v1/actions", tags=["actions"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ROC Cluster Management API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "account_manager": account_manager is not None,
        "database": "connected"  # Add actual DB health check
    }

# Dependency to get account manager
def get_account_manager() -> AccountManager:
    if account_manager is None:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    return account_manager

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
