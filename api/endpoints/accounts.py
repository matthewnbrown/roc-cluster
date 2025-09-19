"""
Account management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.database import get_db
from api.db_models import Account, UserCookies, SentCreditLog, Cluster, ClusterUser
from api.schemas import AccountCreate, AccountUpdate, AccountResponse, UserCookiesCreate, UserCookiesUpdate, UserCookiesResponse, SentCreditLogResponse, PaginatedResponse
from api.account_manager import AccountManager
from api.pagination import paginate_query

logger = logging.getLogger(__name__)
router = APIRouter()

def get_account_manager() -> AccountManager:
    """Dependency to get account manager"""
    # This will be injected by the main app
    from main import account_manager
    if account_manager is None:
        raise HTTPException(status_code=503, detail="Account manager not initialized")
    return account_manager

@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: Session = Depends(get_db),
    manager: AccountManager = Depends(get_account_manager)
):
    """Create a new ROC account"""
    try:
        # Check if account already exists
        existing_account = db.query(Account).filter(
            (Account.email == account_data.email) | 
            (Account.username == account_data.username)
        ).first()
        
        if existing_account:
            raise HTTPException(
                status_code=400,
                detail="Account with this email or username already exists"
            )
        
        # Create new account
        db_account = Account(
            username=account_data.username,
            email=account_data.email,
            password=account_data.password,  # Store unencrypted password
        )
        
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        
        # Add new account to all_users cluster
        all_users_cluster = db.query(Cluster).filter(Cluster.name == "all_users").first()
        if all_users_cluster:
            cluster_user = ClusterUser(
                cluster_id=all_users_cluster.id,
                account_id=db_account.id
            )
            db.add(cluster_user)
            db.commit()
            logger.info(f"Added new account {db_account.id} to all_users cluster")
        
        return AccountResponse.from_orm(db_account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db)
):
    """List all accounts with pagination"""
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")
        if per_page < 1 or per_page > 1000:
            raise HTTPException(status_code=400, detail="Per page must be between 1 and 1000")
        
        query = db.query(Account).order_by(Account.id)
        return paginate_query(query, page, per_page, AccountResponse)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Get account by ID"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return AccountResponse.from_orm(account)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    db: Session = Depends(get_db),
    manager: AccountManager = Depends(get_account_manager)
):
    """Update account information"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Update fields
        update_data = account_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        
        db.commit()
        db.refresh(account)
        
        return AccountResponse.from_orm(account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    manager: AccountManager = Depends(get_account_manager)
):
    """Delete an account"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        db.delete(account)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{account_id}/cookies", response_model=UserCookiesResponse, status_code=status.HTTP_201_CREATED)
async def upsert_user_cookies(
    account_id: int,
    cookies_data: UserCookiesCreate,
    db: Session = Depends(get_db)
):
    """Create or update cookies for a user (upsert operation)"""
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Use upsert logic - get existing cookies or create new
        existing_cookies = db.query(UserCookies).filter(
            UserCookies.account_id == account_id
        ).first()
        
        if existing_cookies:
            # Update existing cookies
            existing_cookies.cookies = cookies_data.cookies
            db.commit()
            db.refresh(existing_cookies)
            return UserCookiesResponse.from_orm(existing_cookies)
        else:
            # Create new cookies
            user_cookies = UserCookies(
                account_id=account_id,
                cookies=cookies_data.cookies
            )
            db.add(user_cookies)
            db.commit()
            db.refresh(user_cookies)
            return UserCookiesResponse.from_orm(user_cookies)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upserting cookies for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{account_id}/cookies", response_model=UserCookiesResponse)
async def get_user_cookies(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Get cookies for a user"""
    try:
        user_cookies = db.query(UserCookies).filter(
            UserCookies.account_id == account_id
        ).first()
        
        if not user_cookies:
            raise HTTPException(status_code=404, detail="No cookies found for this account")
        
        return UserCookiesResponse.from_orm(user_cookies)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cookies for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{account_id}/cookies", response_model=UserCookiesResponse)
async def update_user_cookies(
    account_id: int,
    cookies_data: UserCookiesUpdate,
    db: Session = Depends(get_db)
):
    """Update cookies for a user (creates if not exists)"""
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        user_cookies = db.query(UserCookies).filter(
            UserCookies.account_id == account_id
        ).first()
        
        if not user_cookies:
            # Create new cookies if they don't exist
            user_cookies = UserCookies(
                account_id=account_id,
                cookies=cookies_data.cookies
            )
            db.add(user_cookies)
        else:
            # Update existing cookies
            user_cookies.cookies = cookies_data.cookies
        
        db.commit()
        db.refresh(user_cookies)
        
        return UserCookiesResponse.from_orm(user_cookies)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cookies for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{account_id}/cookies", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_cookies(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Delete cookies for a user"""
    try:
        user_cookies = db.query(UserCookies).filter(
            UserCookies.account_id == account_id
        ).first()
        
        if not user_cookies:
            raise HTTPException(status_code=404, detail="No cookies found for this account")
        
        db.delete(user_cookies)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cookies for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{account_id}/credit-logs", response_model=PaginatedResponse[SentCreditLogResponse])
async def get_credit_logs(
    account_id: int,
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db)
):
    """Get credit sending logs for a specific account with pagination"""
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")
        if per_page < 1 or per_page > 1000:
            raise HTTPException(status_code=400, detail="Per page must be between 1 and 1000")
        
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Get credit logs query
        query = db.query(SentCreditLog).filter(
            SentCreditLog.sender_account_id == account_id
        ).order_by(SentCreditLog.timestamp.desc())
        
        return paginate_query(query, page, per_page, SentCreditLogResponse)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit logs for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/credit-logs", response_model=PaginatedResponse[SentCreditLogResponse])
async def get_all_credit_logs(
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db)
):
    """Get all credit sending logs across all accounts with pagination"""
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")
        if per_page < 1 or per_page > 1000:
            raise HTTPException(status_code=400, detail="Per page must be between 1 and 1000")
        
        query = db.query(SentCreditLog).order_by(SentCreditLog.timestamp.desc())
        return paginate_query(query, page, per_page, SentCreditLogResponse)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all credit logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

