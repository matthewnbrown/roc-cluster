"""
Account management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.database import get_db
from api.models import Account, AccountCreate, AccountUpdate, AccountResponse, UserCookies, UserCookiesCreate, UserCookiesUpdate, UserCookiesResponse
from api.account_manager import AccountManager

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
        
        # Add to account manager
        success = await manager.add_account(db_account)
        if not success:
            # Rollback database changes
            db.delete(db_account)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Failed to initialize account"
            )
        
        return AccountResponse.from_orm(db_account)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all accounts"""
    try:
        accounts = db.query(Account).offset(skip).limit(limit).all()
        return [AccountResponse.from_orm(account) for account in accounts]
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/loaded")
async def list_loaded_accounts(
    manager: AccountManager = Depends(get_account_manager)
):
    """List accounts currently loaded in the account manager"""
    try:
        loaded_accounts = await manager.get_all_accounts()
        return {
            "loaded_count": len(loaded_accounts),
            "accounts": [
                {
                    "id": account.account.id,
                    "username": account.account.username,
                    "email": account.account.email,
                    "is_logged_in": account.is_logged_in
                }
                for account in loaded_accounts
            ]
        }
    except Exception as e:
        logger.error(f"Error listing loaded accounts: {e}")
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
        
        # Remove from account manager
        await manager.remove_account(account_id)
        
        # Delete from database
        db.delete(account)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{account_id}/metadata")
async def get_account_metadata(
    account_id: int,
    manager: AccountManager = Depends(get_account_manager)
):
    """Get account metadata from ROC website"""
    try:
        account = await manager.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        metadata = await account.get_metadata()
        if not metadata:
            raise HTTPException(status_code=503, detail="Failed to retrieve metadata")
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{account_id}/cookies", response_model=UserCookiesResponse, status_code=status.HTTP_201_CREATED)
async def create_user_cookies(
    account_id: int,
    cookies_data: UserCookiesCreate,
    db: Session = Depends(get_db)
):
    """Create or update cookies for a user"""
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Check if cookies already exist for this account
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
        logger.error(f"Error creating/updating cookies for account {account_id}: {e}")
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
    """Update cookies for a user"""
    try:
        user_cookies = db.query(UserCookies).filter(
            UserCookies.account_id == account_id
        ).first()
        
        if not user_cookies:
            raise HTTPException(status_code=404, detail="No cookies found for this account")
        
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
