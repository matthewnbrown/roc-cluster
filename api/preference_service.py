"""
Preference service for managing armory and training preferences
"""

from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import logging

from api.db_models import (
    Account, ArmoryPreferences, ArmoryWeaponPreference, Weapon,
    TrainingPreferences, TrainingSoldierTypePreference, SoldierType
)

logger = logging.getLogger(__name__)


class PreferenceService:
    """Service for managing account preferences"""
    
    @staticmethod
    def validate_weapon_percentages(weapon_percentages: Dict[str, float], db: Session) -> Tuple[bool, Optional[str], Optional[Dict[str, Weapon]]]:
        """
        Validate weapon percentages and return weapon mapping
        
        Returns:
            Tuple of (is_valid, error_message, weapon_by_name_dict)
        """
        # Validate weapon names and get weapons
        weapons = db.query(Weapon).all()
        weapon_by_name = {weapon.name: weapon for weapon in weapons}
        
        # Validate that all weapon names exist
        invalid_weapons = []
        for weapon_name in weapon_percentages.keys():
            if weapon_name not in weapon_by_name:
                invalid_weapons.append(weapon_name)
        
        if invalid_weapons:
            return False, f"Invalid weapon names: {', '.join(invalid_weapons)}", None
        
        # Check for duplicate weapon names in the request
        weapon_names = list(weapon_percentages.keys())
        if len(weapon_names) != len(set(weapon_names)):
            return False, "Duplicate weapon names found in preferences", None
        
        # Validate that percentages sum to <= 100%
        total_percentage = sum(weapon_percentages.values())
        if total_percentage > 100.0:
            return False, f"Total percentage ({total_percentage:.2f}%) cannot exceed 100%", None
        
        return True, None, weapon_by_name
    
    @staticmethod
    def validate_soldier_type_percentages(soldier_type_percentages: Dict[str, float], db: Session) -> Tuple[bool, Optional[str], Optional[Dict[str, SoldierType]]]:
        """
        Validate soldier type percentages and return soldier type mapping
        
        Returns:
            Tuple of (is_valid, error_message, soldier_type_by_name_dict)
        """
        # Validate soldier type names and get soldier types
        soldier_types = db.query(SoldierType).all()
        soldier_type_by_name = {st.name: st for st in soldier_types}
        
        # Validate that all soldier type names exist
        invalid_soldier_types = []
        for soldier_type_name in soldier_type_percentages.keys():
            if soldier_type_name not in soldier_type_by_name:
                invalid_soldier_types.append(soldier_type_name)
        
        if invalid_soldier_types:
            return False, f"Invalid soldier type names: {', '.join(invalid_soldier_types)}", None
        
        # Validate that percentages sum to <= 100%
        total_percentage = sum(soldier_type_percentages.values())
        if total_percentage > 100.0:
            return False, f"Total percentage ({total_percentage:.2f}%) cannot exceed 100%", None
        
        return True, None, soldier_type_by_name
    
    @staticmethod
    def get_or_create_armory_preferences(account_id: int, db: Session) -> ArmoryPreferences:
        """Get existing armory preferences or create new ones"""
        preferences = db.query(ArmoryPreferences).filter(
            ArmoryPreferences.account_id == account_id
        ).first()
        
        if not preferences:
            preferences = ArmoryPreferences(account_id=account_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
        
        return preferences
    
    @staticmethod
    def get_or_create_training_preferences(account_id: int, db: Session) -> TrainingPreferences:
        """Get existing training preferences or create new ones"""
        preferences = db.query(TrainingPreferences).filter(
            TrainingPreferences.account_id == account_id
        ).first()
        
        if not preferences:
            preferences = TrainingPreferences(account_id=account_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
        
        return preferences
    
    @staticmethod
    def update_armory_preferences(account_id: int, weapon_percentages: Dict[str, float], db: Session) -> Dict[str, Any]:
        """
        Update armory preferences for an account
        
        Returns:
            Dict with success status and message/error
        """
        try:
            # Check if account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Validate weapon percentages
            is_valid, error_message, weapon_by_name = PreferenceService.validate_weapon_percentages(weapon_percentages, db)
            if not is_valid:
                return {"success": False, "error": error_message}
            
            # Get or create preferences
            preferences = PreferenceService.get_or_create_armory_preferences(account_id, db)
            
            # Delete existing weapon preferences
            db.query(ArmoryWeaponPreference).filter(
                ArmoryWeaponPreference.preferences_id == preferences.id
            ).delete()
            
            # Create new weapon preferences
            for weapon_name, percentage in weapon_percentages.items():
                if percentage > 0:  # Only create entries for weapons with > 0%
                    weapon = weapon_by_name[weapon_name]
                    weapon_preference = ArmoryWeaponPreference(
                        preferences_id=preferences.id,
                        weapon_id=weapon.id,
                        percentage=percentage
                    )
                    db.add(weapon_preference)
            
            db.commit()
            
            logger.debug(f"Updated armory preferences for account {account_id}")
            return {"success": True }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating armory preferences for account {account_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_training_preferences(account_id: int, soldier_type_percentages: Dict[str, float], db: Session) -> Dict[str, Any]:
        """
        Update training preferences for an account
        
        Returns:
            Dict with success status and message/error
        """
        try:
            # Check if account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Validate soldier type percentages
            is_valid, error_message, soldier_type_by_name = PreferenceService.validate_soldier_type_percentages(soldier_type_percentages, db)
            if not is_valid:
                return {"success": False, "error": error_message}
            
            # Get or create preferences
            preferences = PreferenceService.get_or_create_training_preferences(account_id, db)
            
            # Delete existing soldier type preferences
            db.query(TrainingSoldierTypePreference).filter(
                TrainingSoldierTypePreference.preferences_id == preferences.id
            ).delete()
            
            # Create new soldier type preferences
            for soldier_type_name, percentage in soldier_type_percentages.items():
                if percentage > 0:  # Only create entries for soldier types with > 0%
                    soldier_type = soldier_type_by_name[soldier_type_name]
                    soldier_type_preference = TrainingSoldierTypePreference(
                        preferences_id=preferences.id,
                        soldier_type_id=soldier_type.id,
                        percentage=percentage
                    )
                    db.add(soldier_type_preference)
            
            db.commit()
            
            logger.info(f"Updated training preferences for account {account_id}")
            return {"success": True, "message": "Training preferences updated successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating training preferences for account {account_id}: {e}")
            return {"success": False, "error": str(e)}
