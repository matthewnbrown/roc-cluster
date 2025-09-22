"""
Reference data endpoints for races, ROC stats, soldier types, and weapons
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.database import get_db
from api.db_models import Race, RocStat, SoldierType, Weapon
from api.schemas import RaceResponse, RocStatResponse, SoldierTypeResponse, WeaponResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Race endpoints
@router.get("/races", response_model=List[RaceResponse])
async def list_races(db: Session = Depends(get_db)):
    """List all races"""
    try:
        races = db.query(Race).order_by(Race.name).all()
        return [RaceResponse.from_orm(race) for race in races]
    except Exception as e:
        logger.error(f"Error listing races: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/races/{race_id}", response_model=RaceResponse)
async def get_race(race_id: int, db: Session = Depends(get_db)):
    """Get a specific race by ID"""
    try:
        race = db.query(Race).filter(Race.id == race_id).first()
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        return RaceResponse.from_orm(race)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting race {race_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ROC Stats endpoints
@router.get("/roc-stats", response_model=List[RocStatResponse])
async def list_roc_stats(db: Session = Depends(get_db)):
    """List all ROC stats"""
    try:
        roc_stats = db.query(RocStat).order_by(RocStat.name).all()
        return [RocStatResponse.from_orm(stat) for stat in roc_stats]
    except Exception as e:
        logger.error(f"Error listing ROC stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/roc-stats/{stat_id}", response_model=RocStatResponse)
async def get_roc_stat(stat_id: int, db: Session = Depends(get_db)):
    """Get a specific ROC stat by ID"""
    try:
        roc_stat = db.query(RocStat).filter(RocStat.id == stat_id).first()
        if not roc_stat:
            raise HTTPException(status_code=404, detail="ROC stat not found")
        return RocStatResponse.from_orm(roc_stat)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ROC stat {stat_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Soldier Types endpoints
@router.get("/soldier-types", response_model=List[SoldierTypeResponse])
async def list_soldier_types(db: Session = Depends(get_db)):
    """List all soldier types"""
    try:
        soldier_types = db.query(SoldierType).order_by(SoldierType.name).all()
        return [SoldierTypeResponse.from_orm(st) for st in soldier_types]
    except Exception as e:
        logger.error(f"Error listing soldier types: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/soldier-types/{soldier_type_id}", response_model=SoldierTypeResponse)
async def get_soldier_type(soldier_type_id: int, db: Session = Depends(get_db)):
    """Get a specific soldier type by ID"""
    try:
        soldier_type = db.query(SoldierType).filter(SoldierType.id == soldier_type_id).first()
        if not soldier_type:
            raise HTTPException(status_code=404, detail="Soldier type not found")
        return SoldierTypeResponse.from_orm(soldier_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting soldier type {soldier_type_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Weapons endpoints
@router.get("/weapons", response_model=List[WeaponResponse])
async def list_weapons(db: Session = Depends(get_db)):
    """List all weapons"""
    try:
        weapons = db.query(Weapon).order_by(Weapon.name).all()
        return [WeaponResponse.from_orm(weapon) for weapon in weapons]
    except Exception as e:
        logger.error(f"Error listing weapons: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/weapons/{weapon_id}", response_model=WeaponResponse)
async def get_weapon(weapon_id: int, db: Session = Depends(get_db)):
    """Get a specific weapon by ID"""
    try:
        weapon = db.query(Weapon).filter(Weapon.id == weapon_id).first()
        if not weapon:
            raise HTTPException(status_code=404, detail="Weapon not found")
        return WeaponResponse.from_orm(weapon)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weapon {weapon_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
