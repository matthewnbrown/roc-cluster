"""
Armory preferences management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.database import get_db
from api.db_models import Weapon, ArmoryPreferences, ArmoryWeaponPreference, Account
from api.schemas import (
    WeaponResponse, 
    ArmoryPreferencesCreate, 
    ArmoryPreferencesUpdate, 
    ArmoryPreferencesResponse,
    ArmoryWeaponPreferenceResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/weapons", response_model=List[WeaponResponse])
async def get_weapons(db: Session = Depends(get_db)):
    """Get all available weapons"""
    weapons = db.query(Weapon).all()
    return weapons


@router.get("/preferences/{account_id}", response_model=ArmoryPreferencesResponse)
async def get_armory_preferences(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Get armory preferences for a specific account"""
    # Check if account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        # Create default preferences if none exist
        preferences = ArmoryPreferences(account_id=account_id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    # Build response with weapon preferences
    weapon_preferences = []
    for wp in preferences.weapon_preferences:
        weapon_preferences.append(ArmoryWeaponPreferenceResponse(
            weapon_id=wp.weapon.id,
            weapon_name=wp.weapon.name,
            weapon_display_name=wp.weapon.display_name,
            percentage=wp.percentage
        ))
    
    return ArmoryPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        weapon_preferences=weapon_preferences
    )


@router.post("/preferences", response_model=ArmoryPreferencesResponse, status_code=status.HTTP_201_CREATED)
async def create_armory_preferences(
    preferences_data: ArmoryPreferencesCreate,
    db: Session = Depends(get_db)
):
    """Create armory preferences for an account"""
    # Check if account exists
    account = db.query(Account).filter(Account.id == preferences_data.account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    # Check if preferences already exist
    existing_preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == preferences_data.account_id
    ).first()
    
    if existing_preferences:
        raise HTTPException(
            status_code=400,
            detail="Armory preferences already exist for this account"
        )
    
    # Validate weapon names and get weapons
    weapons = db.query(Weapon).all()
    weapon_by_name = {weapon.name: weapon for weapon in weapons}
    
    # Validate that all weapon names exist
    invalid_weapons = []
    for weapon_name in preferences_data.weapon_percentages.keys():
        if weapon_name not in weapon_by_name:
            invalid_weapons.append(weapon_name)
    
    if invalid_weapons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weapon names: {', '.join(invalid_weapons)}"
        )
    
    # Validate that percentages sum to <= 100%
    total_percentage = sum(preferences_data.weapon_percentages.values())
    
    if total_percentage > 100.0:
        raise HTTPException(
            status_code=400,
            detail=f"Total percentage ({total_percentage:.2f}%) cannot exceed 100%"
        )
    
    # Create preferences
    preferences = ArmoryPreferences(account_id=preferences_data.account_id)
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    
    # Create weapon preferences
    for weapon_name, percentage in preferences_data.weapon_percentages.items():
        if percentage > 0:  # Only create entries for weapons with > 0%
            weapon = weapon_by_name[weapon_name]
            weapon_preference = ArmoryWeaponPreference(
                preferences_id=preferences.id,
                weapon_id=weapon.id,
                percentage=percentage
            )
            db.add(weapon_preference)
    
    db.commit()
    db.refresh(preferences)
    
    # Build response
    weapon_preferences = []
    for wp in preferences.weapon_preferences:
        weapon_preferences.append(ArmoryWeaponPreferenceResponse(
            weapon_id=wp.weapon.id,
            weapon_name=wp.weapon.name,
            weapon_display_name=wp.weapon.display_name,
            percentage=wp.percentage
        ))
    
    logger.info(f"Created armory preferences for account {preferences_data.account_id}")
    
    return ArmoryPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        weapon_preferences=weapon_preferences
    )


@router.put("/preferences/{account_id}", response_model=ArmoryPreferencesResponse)
async def update_armory_preferences(
    account_id: int,
    preferences_data: ArmoryPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Update armory preferences for an account"""
    # Check if account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        # Create new preferences if none exist
        preferences = ArmoryPreferences(account_id=account_id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    # Validate weapon names and get weapons
    weapons = db.query(Weapon).all()
    weapon_by_name = {weapon.name: weapon for weapon in weapons}
    
    # Validate that all weapon names exist
    invalid_weapons = []
    for weapon_name in preferences_data.weapon_percentages.keys():
        if weapon_name not in weapon_by_name:
            invalid_weapons.append(weapon_name)
    
    if invalid_weapons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weapon names: {', '.join(invalid_weapons)}"
        )
    
    # Validate that percentages sum to <= 100%
    total_percentage = sum(preferences_data.weapon_percentages.values())
    
    if total_percentage > 100.0:
        raise HTTPException(
            status_code=400,
            detail=f"Total percentage ({total_percentage:.2f}%) cannot exceed 100%"
        )
    
    # Delete existing weapon preferences
    db.query(ArmoryWeaponPreference).filter(
        ArmoryWeaponPreference.preferences_id == preferences.id
    ).delete()
    
    # Create new weapon preferences
    for weapon_name, percentage in preferences_data.weapon_percentages.items():
        if percentage > 0:  # Only create entries for weapons with > 0%
            weapon = weapon_by_name[weapon_name]
            weapon_preference = ArmoryWeaponPreference(
                preferences_id=preferences.id,
                weapon_id=weapon.id,
                percentage=percentage
            )
            db.add(weapon_preference)
    
    db.commit()
    db.refresh(preferences)
    
    # Build response
    weapon_preferences = []
    for wp in preferences.weapon_preferences:
        weapon_preferences.append(ArmoryWeaponPreferenceResponse(
            weapon_id=wp.weapon.id,
            weapon_name=wp.weapon.name,
            weapon_display_name=wp.weapon.display_name,
            percentage=wp.percentage
        ))
    
    logger.info(f"Updated armory preferences for account {account_id}")
    
    return ArmoryPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        weapon_preferences=weapon_preferences
    )


@router.delete("/preferences/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_armory_preferences(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Delete armory preferences for an account"""
    preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        raise HTTPException(
            status_code=404,
            detail="Armory preferences not found"
        )
    
    db.delete(preferences)
    db.commit()
    
    logger.info(f"Deleted armory preferences for account {account_id}")
