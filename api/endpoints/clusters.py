"""
Cluster management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
import logging

from api.database import get_db
from api.db_models import Cluster, ClusterUser, Account
from api.schemas import (
    ClusterCreate, ClusterUpdate, ClusterResponse, ClusterListResponse,
    ClusterUserAdd, ClusterClone, ClusterSearch, ClusterUserResponse,
    PaginatedResponse
)
from api.pagination import paginate_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    cluster_data: ClusterCreate,
    db: Session = Depends(get_db)
):
    """Create a new cluster"""
    try:
        # Check if cluster with this name already exists
        existing_cluster = db.query(Cluster).filter(Cluster.name == cluster_data.name).first()
        if existing_cluster:
            raise HTTPException(
                status_code=400,
                detail="Cluster with this name already exists"
            )
        
        # Create new cluster
        db_cluster = Cluster(
            name=cluster_data.name,
            description=cluster_data.description
        )
        
        db.add(db_cluster)
        db.commit()
        db.refresh(db_cluster)
        
        # Return cluster with user count
        return _get_cluster_response(db_cluster, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cluster: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=PaginatedResponse[ClusterListResponse])
async def list_clusters(
    page: int = 1,
    per_page: int = 100,
    search: Optional[str] = Query(None, description="Search clusters by name or description"),
    db: Session = Depends(get_db)
):
    """List all clusters with pagination and optional search"""
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")
        if per_page < 1 or per_page > 10000:
            raise HTTPException(status_code=400, detail="Per page must be between 1 and 10000")
        
        # Build query with search
        query = db.query(Cluster)
        
        if search:
            search_filter = or_(
                Cluster.name.ilike(f"%{search}%"),
                Cluster.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        query = query.order_by(Cluster.created_at.desc())
        
        # Get paginated results
        paginated_result = paginate_query(query, page, per_page, ClusterListResponse)
        
        # Add user count to each cluster
        for cluster_data in paginated_result.data:
            user_count = db.query(ClusterUser).filter(ClusterUser.cluster_id == cluster_data.id).count()
            cluster_data.user_count = user_count
        
        return paginated_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: int,
    db: Session = Depends(get_db)
):
    """Get cluster by ID with all users"""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        return _get_cluster_response(cluster, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: int,
    cluster_data: ClusterUpdate,
    db: Session = Depends(get_db)
):
    """Update cluster information"""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Check if new name conflicts with existing cluster
        if cluster_data.name and cluster_data.name != cluster.name:
            existing_cluster = db.query(Cluster).filter(
                and_(Cluster.name == cluster_data.name, Cluster.id != cluster_id)
            ).first()
            if existing_cluster:
                raise HTTPException(
                    status_code=400,
                    detail="Cluster with this name already exists"
                )
        
        # Update fields
        update_data = cluster_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cluster, field, value)
        
        db.commit()
        db.refresh(cluster)
        
        return _get_cluster_response(cluster, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: int,
    db: Session = Depends(get_db)
):
    """Delete a cluster"""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Prevent deletion of the all_users cluster
        if cluster.name == "all_users":
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the all_users cluster"
            )
        
        db.delete(cluster)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{cluster_id}/users", response_model=dict)
async def add_users_to_cluster(
    cluster_id: int,
    user_data: ClusterUserAdd,
    db: Session = Depends(get_db)
):
    """Add users to a cluster"""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        added_count = 0
        skipped_count = 0
        
        for account_id in user_data.account_ids:
            # Check if account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                logger.warning(f"Account {account_id} not found, skipping")
                skipped_count += 1
                continue
            
            # Check if user is already in cluster
            existing = db.query(ClusterUser).filter(
                and_(ClusterUser.cluster_id == cluster_id, ClusterUser.account_id == account_id)
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Add user to cluster
            cluster_user = ClusterUser(
                cluster_id=cluster_id,
                account_id=account_id
            )
            db.add(cluster_user)
            added_count += 1
        
        db.commit()
        
        return {
            "message": f"Added {added_count} users to cluster",
            "added_count": added_count,
            "skipped_count": skipped_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding users to cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{cluster_id}/users/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_cluster(
    cluster_id: int,
    account_id: int,
    db: Session = Depends(get_db)
):
    """Remove a user from a cluster"""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Prevent removal from all_users cluster
        if cluster.name == "all_users":
            raise HTTPException(
                status_code=400,
                detail="Cannot remove users from the all_users cluster"
            )
        
        cluster_user = db.query(ClusterUser).filter(
            and_(ClusterUser.cluster_id == cluster_id, ClusterUser.account_id == account_id)
        ).first()
        
        if not cluster_user:
            raise HTTPException(status_code=404, detail="User not found in cluster")
        
        db.delete(cluster_user)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user {account_id} from cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{cluster_id}/clone", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def clone_cluster(
    cluster_id: int,
    clone_data: ClusterClone,
    db: Session = Depends(get_db)
):
    """Clone an existing cluster"""
    try:
        source_cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not source_cluster:
            raise HTTPException(status_code=404, detail="Source cluster not found")
        
        # Check if new cluster name already exists
        existing_cluster = db.query(Cluster).filter(Cluster.name == clone_data.name).first()
        if existing_cluster:
            raise HTTPException(
                status_code=400,
                detail="Cluster with this name already exists"
            )
        
        # Create new cluster
        new_cluster = Cluster(
            name=clone_data.name,
            description=clone_data.description or source_cluster.description
        )
        db.add(new_cluster)
        db.commit()
        db.refresh(new_cluster)
        
        # Copy users if requested
        if clone_data.include_users:
            source_users = db.query(ClusterUser).filter(ClusterUser.cluster_id == cluster_id).all()
            for source_user in source_users:
                new_cluster_user = ClusterUser(
                    cluster_id=new_cluster.id,
                    account_id=source_user.account_id
                )
                db.add(new_cluster_user)
            db.commit()
        
        return _get_cluster_response(new_cluster, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=PaginatedResponse[ClusterListResponse])
async def search_clusters(
    search_data: ClusterSearch,
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db)
):
    """Advanced search for clusters"""
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be greater than 0")
        if per_page < 1 or per_page > 10000:
            raise HTTPException(status_code=400, detail="Per page must be between 1 and 10000")
        
        # Build search query
        query = db.query(Cluster)
        
        # Name search
        if search_data.name:
            query = query.filter(Cluster.name.ilike(f"%{search_data.name}%"))
        
        # Description search
        if search_data.description:
            query = query.filter(Cluster.description.ilike(f"%{search_data.description}%"))
        
        # User count filters
        if search_data.user_count_min is not None or search_data.user_count_max is not None:
            # Subquery to get user counts
            user_counts = db.query(
                ClusterUser.cluster_id,
                func.count(ClusterUser.account_id).label('user_count')
            ).group_by(ClusterUser.cluster_id).subquery()
            
            query = query.outerjoin(user_counts, Cluster.id == user_counts.c.cluster_id)
            
            if search_data.user_count_min is not None:
                query = query.filter(
                    or_(
                        user_counts.c.user_count >= search_data.user_count_min,
                        user_counts.c.user_count.is_(None)  # Clusters with no users
                    )
                )
            
            if search_data.user_count_max is not None:
                query = query.filter(
                    or_(
                        user_counts.c.user_count <= search_data.user_count_max,
                        user_counts.c.user_count.is_(None)  # Clusters with no users
                    )
                )
        
        query = query.order_by(Cluster.created_at.desc())
        
        # Get paginated results
        paginated_result = paginate_query(query, page, per_page, ClusterListResponse)
        
        # Add user count to each cluster
        for cluster_data in paginated_result.data:
            user_count = db.query(ClusterUser).filter(ClusterUser.cluster_id == cluster_data.id).count()
            cluster_data.user_count = user_count
        
        return paginated_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching clusters: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _get_cluster_response(cluster: Cluster, db: Session) -> ClusterResponse:
    """Helper function to build cluster response with users"""
    # Get users in cluster
    cluster_users = db.query(ClusterUser, Account).join(
        Account, ClusterUser.account_id == Account.id
    ).filter(ClusterUser.cluster_id == cluster.id).all()
    
    # Build user response list
    users = []
    for cluster_user, account in cluster_users:
        user_response = ClusterUserResponse(
            id=cluster_user.id,
            account_id=account.id,
            username=account.username,
            email=account.email,
            added_at=cluster_user.added_at
        )
        users.append(user_response)
    
    # Build cluster response
    return ClusterResponse(
        id=cluster.id,
        name=cluster.name,
        description=cluster.description,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
        user_count=len(users),
        users=users
    )
