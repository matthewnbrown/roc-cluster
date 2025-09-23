"""
Armory preferences management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.database import get_db
from api.db_models import (
    Weapon, ArmoryPreferences, ArmoryWeaponPreference, Account,
    SoldierType, TrainingPreferences, TrainingSoldierTypePreference
)
from api.schemas import (
    WeaponResponse, 
    ArmoryPreferencesCreate, 
    ArmoryPreferencesUpdate, 
    ArmoryPreferencesResponse,
    ArmoryWeaponPreferenceResponse,
    SoldierTypeResponse,
    TrainingPreferencesCreate,
    TrainingPreferencesUpdate,
    TrainingPreferencesResponse,
    TrainingSoldierTypePreferenceResponse
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
    
    # Check for duplicate weapon names in the request
    weapon_names = list(preferences_data.weapon_percentages.keys())
    if len(weapon_names) != len(set(weapon_names)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate weapon names found in preferences"
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
    try:
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
    except Exception as e:
        db.rollback()
        if "unique_preference_weapon" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Duplicate weapon preference detected. Each weapon can only have one preference per account."
            )
        raise HTTPException(
            status_code=500,
            detail="Failed to create weapon preferences"
        )
    
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
    from api.preference_service import PreferenceService
    
    # Use the service to update preferences
    result = PreferenceService.update_armory_preferences(account_id, preferences_data.weapon_percentages, db)
    
    if not result["success"]:
        if "Account not found" in result["error"]:
            raise HTTPException(status_code=404, detail=result["error"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    
    # Get the updated preferences to build response
    preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == account_id
    ).first()
    
    # Build response
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


# Soldier Types Endpoints
@router.get("/soldier-types", response_model=List[SoldierTypeResponse])
async def get_soldier_types(db: Session = Depends(get_db)):
    """Get all available soldier types"""
    soldier_types = db.query(SoldierType).all()
    return soldier_types


# Training Preferences Endpoints
@router.get("/training-preferences/{account_id}", response_model=TrainingPreferencesResponse)
async def get_training_preferences(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Get training preferences for a specific account"""
    # Check if account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    preferences = db.query(TrainingPreferences).filter(
        TrainingPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        # Create default preferences if none exist
        preferences = TrainingPreferences(account_id=account_id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    # Build response with soldier type preferences
    soldier_type_preferences = []
    for stp in preferences.soldier_type_preferences:
        soldier_type_preferences.append(TrainingSoldierTypePreferenceResponse(
            soldier_type_id=stp.soldier_type.id,
            soldier_type_name=stp.soldier_type.name,
            soldier_type_display_name=stp.soldier_type.display_name,
            soldier_type_costs_soldiers=stp.soldier_type.costs_soldiers,
            percentage=stp.percentage
        ))
    
    return TrainingPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        soldier_type_preferences=soldier_type_preferences
    )


@router.post("/training-preferences", response_model=TrainingPreferencesResponse, status_code=status.HTTP_201_CREATED)
async def create_training_preferences(
    preferences_data: TrainingPreferencesCreate,
    db: Session = Depends(get_db)
):
    """Create training preferences for an account"""
    # Check if account exists
    account = db.query(Account).filter(Account.id == preferences_data.account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    # Check if preferences already exist
    existing_preferences = db.query(TrainingPreferences).filter(
        TrainingPreferences.account_id == preferences_data.account_id
    ).first()
    
    if existing_preferences:
        raise HTTPException(
            status_code=400,
            detail="Training preferences already exist for this account"
        )
    
    # Validate soldier type names and get soldier types
    soldier_types = db.query(SoldierType).all()
    soldier_type_by_name = {st.name: st for st in soldier_types}
    
    # Validate that all soldier type names exist
    invalid_soldier_types = []
    for soldier_type_name in preferences_data.soldier_type_percentages.keys():
        if soldier_type_name not in soldier_type_by_name:
            invalid_soldier_types.append(soldier_type_name)
    
    if invalid_soldier_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid soldier type names: {', '.join(invalid_soldier_types)}"
        )
    
    # Validate that percentages sum to <= 100%
    total_percentage = sum(preferences_data.soldier_type_percentages.values())
    
    if total_percentage > 100.0:
        raise HTTPException(
            status_code=400,
            detail=f"Total percentage ({total_percentage:.2f}%) cannot exceed 100%"
        )
    
    # Create preferences
    preferences = TrainingPreferences(account_id=preferences_data.account_id)
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    
    # Create soldier type preferences
    for soldier_type_name, percentage in preferences_data.soldier_type_percentages.items():
        if percentage > 0:  # Only create entries for soldier types with > 0%
            soldier_type = soldier_type_by_name[soldier_type_name]
            soldier_type_preference = TrainingSoldierTypePreference(
                preferences_id=preferences.id,
                soldier_type_id=soldier_type.id,
                percentage=percentage
            )
            db.add(soldier_type_preference)
    
    db.commit()
    db.refresh(preferences)
    
    # Build response
    soldier_type_preferences = []
    for stp in preferences.soldier_type_preferences:
        soldier_type_preferences.append(TrainingSoldierTypePreferenceResponse(
            soldier_type_id=stp.soldier_type.id,
            soldier_type_name=stp.soldier_type.name,
            soldier_type_display_name=stp.soldier_type.display_name,
            soldier_type_costs_soldiers=stp.soldier_type.costs_soldiers,
            percentage=stp.percentage
        ))
    
    logger.info(f"Created training preferences for account {preferences_data.account_id}")
    
    return TrainingPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        soldier_type_preferences=soldier_type_preferences
    )


@router.put("/training-preferences/{account_id}", response_model=TrainingPreferencesResponse)
async def update_training_preferences(
    account_id: int,
    preferences_data: TrainingPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Update training preferences for an account"""
    from api.preference_service import PreferenceService
    
    # Use the service to update preferences
    result = PreferenceService.update_training_preferences(account_id, preferences_data.soldier_type_percentages, db)
    
    if not result["success"]:
        if "Account not found" in result["error"]:
            raise HTTPException(status_code=404, detail=result["error"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    
    # Get the updated preferences to build response
    preferences = db.query(TrainingPreferences).filter(
        TrainingPreferences.account_id == account_id
    ).first()
    
    # Build response
    soldier_type_preferences = []
    for stp in preferences.soldier_type_preferences:
        soldier_type_preferences.append(TrainingSoldierTypePreferenceResponse(
            soldier_type_id=stp.soldier_type.id,
            soldier_type_name=stp.soldier_type.name,
            soldier_type_display_name=stp.soldier_type.display_name,
            soldier_type_costs_soldiers=stp.soldier_type.costs_soldiers,
            percentage=stp.percentage
        ))
    
    return TrainingPreferencesResponse(
        id=preferences.id,
        account_id=preferences.account_id,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
        soldier_type_preferences=soldier_type_preferences
    )


@router.delete("/training-preferences/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_preferences(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Delete training preferences for an account"""
    preferences = db.query(TrainingPreferences).filter(
        TrainingPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        raise HTTPException(
            status_code=404,
            detail="Training preferences not found"
        )
    
    db.delete(preferences)
    db.commit()
    
    logger.info(f"Deleted training preferences for account {account_id}")


@router.post("/purchase/{account_id}")
async def purchase_armory_by_preferences(
    account_id: int,
    db: Session = Depends(get_db)
):
    """Purchase armory items based on user preferences"""
    from api.account_manager import AccountManager
    from api.schemas import AccountIdentifierType
    
    # Check if account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )
    
    # Get armory preferences
    preferences = db.query(ArmoryPreferences).filter(
        ArmoryPreferences.account_id == account_id
    ).first()
    
    if not preferences:
        raise HTTPException(
            status_code=404,
            detail="Armory preferences not found for this account"
        )

    # Create account manager and execute armory purchase
    try:
        account_manager = AccountManager()
        result = await account_manager.execute_action(
            id_type=AccountIdentifierType.ID,
            id=account_id,
            action=AccountManager.ActionType.PURCHASE_ARMORY_BY_PREFERENCES,
            max_retries=0
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message"),
            "data": result.get("data"),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error purchasing armory for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
