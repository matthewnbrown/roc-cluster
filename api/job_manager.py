"""
Job Manager for handling asynchronous job execution
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.database import SessionLocal
from api.db_models import Job, JobStep, JobStatus, Account, ClusterUser
from api.account_manager import AccountManager
from api.schemas import AccountIdentifierType, JobStepResponse, JobResponse

logger = logging.getLogger(__name__)


class JobManager:
    """Manages job execution and status tracking"""
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self._running_jobs: Dict[int, asyncio.Task] = {}
    
    def _validate_action_type(self, action_type: str) -> bool:
        """Validate that action_type is a valid AccountManager.ActionType"""
        try:
            # Try to convert string to ActionType enum
            self.account_manager.ActionType(action_type)
            return True
        except ValueError:
            return False
    
    def _get_valid_action_types(self) -> List[Dict[str, Any]]:
        """Get detailed information about valid action types"""
        action_metadata = {
            "attack": {
                "description": "Attack another user with specified number of turns",
                "category": "user_action",
                "required_parameters": ["target_id", "turns"],
                "optional_parameters": [],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to attack"
                    },
                    "turns": {
                        "type": "integer",
                        "description": "Number of turns to use for the attack (default: 12)",
                        "default": 12
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains attack results",
                    "error": "string (optional)"
                }
            },
            "sabotage": {
                "description": "Sabotage another user's operations",
                "category": "user_action",
                "required_parameters": ["target_id"],
                "optional_parameters": ["spy_count", "enemy_weapon"],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to sabotage"
                    },
                    "spy_count": {
                        "type": "integer",
                        "description": "Number of spies to use (default: 1)",
                        "default": 1
                    },
                    "enemy_weapon": {
                        "type": "integer",
                        "description": "Enemy weapon type to use (default: 1)",
                        "default": 1
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains sabotage results",
                    "error": "string (optional)"
                }
            },
            "spy": {
                "description": "Spy on another user to gather intelligence",
                "category": "user_action",
                "required_parameters": ["target_id"],
                "optional_parameters": ["spy_count"],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to spy on"
                    },
                    "spy_count": {
                        "type": "integer",
                        "description": "Number of spies to use (default: 1)",
                        "default": 1
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains spy intelligence data",
                    "error": "string (optional)"
                }
            },
            "become_officer": {
                "description": "Attempt to become an officer of another user",
                "category": "user_action",
                "required_parameters": ["target_id"],
                "optional_parameters": [],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to become officer for"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains officer status",
                    "error": "string (optional)"
                }
            },
            "send_credits": {
                "description": "Send credits to another user",
                "category": "user_action",
                "required_parameters": ["target_id", "amount"],
                "optional_parameters": [],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to send credits to"
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount of credits to send"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains transaction details",
                    "error": "string (optional)"
                }
            },
            "recruit": {
                "description": "Recruit soldiers for the account",
                "category": "self_action",
                "required_parameters": [],
                "optional_parameters": [],
                "parameter_details": {},
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains recruitment results",
                    "error": "string (optional)"
                }
            },
            "purchase_armory": {
                "description": "Purchase items from the armory",
                "category": "self_action",
                "required_parameters": ["items"],
                "optional_parameters": [],
                "parameter_details": {
                    "items": {
                        "type": "object",
                        "description": "Dictionary of item_name: quantity pairs to purchase"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains purchase details",
                    "error": "string (optional)"
                }
            },
            "purchase_training": {
                "description": "Purchase training for the account",
                "category": "self_action",
                "required_parameters": ["training_type", "count"],
                "optional_parameters": [],
                "parameter_details": {
                    "training_type": {
                        "type": "string",
                        "description": "Type of training to purchase"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of training sessions to purchase"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains training purchase details",
                    "error": "string (optional)"
                }
            },
            "enable_credit_saving": {
                "description": "Enable credit saving feature for the account",
                "category": "self_action",
                "required_parameters": [],
                "optional_parameters": [],
                "parameter_details": {},
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains saving status",
                    "error": "string (optional)"
                }
            },
            "purchase_upgrade": {
                "description": "Purchase an upgrade for the account",
                "category": "self_action",
                "required_parameters": ["upgrade_type"],
                "optional_parameters": [],
                "parameter_details": {
                    "upgrade_type": {
                        "type": "string",
                        "description": "Type of upgrade to purchase"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains upgrade details",
                    "error": "string (optional)"
                }
            },
            "get_metadata": {
                "description": "Retrieve account metadata and current status",
                "category": "info_action",
                "required_parameters": [],
                "optional_parameters": [],
                "parameter_details": {},
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains account metadata",
                    "error": "string (optional)"
                }
            },
            "get_solved_captchas": {
                "description": "Retrieve solved captcha data for the account",
                "category": "info_action",
                "required_parameters": [],
                "optional_parameters": ["count", "min_confidence"],
                "parameter_details": {
                    "count": {
                        "type": "integer",
                        "description": "Number of captchas to retrieve (default: 1)",
                        "default": 1
                    },
                    "min_confidence": {
                        "type": "float",
                        "description": "Minimum confidence threshold (default: 0)",
                        "default": 0
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "array (optional) - contains captcha solution items",
                    "error": "string (optional)"
                }
            }
        }
        
        result = []
        for action_type in self.account_manager.ActionType:
            action_info = action_metadata.get(action_type.value, {})
            result.append({
                "action_type": action_type.value,
                "description": action_info.get("description", "No description available"),
                "category": action_info.get("category", "unknown"),
                "required_parameters": action_info.get("required_parameters", []),
                "optional_parameters": action_info.get("optional_parameters", []),
                "parameter_details": action_info.get("parameter_details", {}),
                "output": action_info.get("output", {})
            })
        
        return result
    
    def _expand_clusters_to_accounts(self, cluster_ids: List[int], db: Session) -> List[int]:
        """Expand cluster IDs to individual account IDs"""
        if not cluster_ids:
            return []
        
        # Get all account IDs from the specified clusters
        account_ids = db.query(ClusterUser.account_id).filter(
            ClusterUser.cluster_id.in_(cluster_ids)
        ).distinct().all()
        
        # Convert from list of tuples to list of integers
        return [account_id[0] for account_id in account_ids]
    
    def _get_all_account_ids_for_step(self, step_data: Dict[str, Any], db: Session) -> List[int]:
        """Get all account IDs for a step, combining direct account_ids and cluster expansion"""
        all_account_ids = set()
        
        # Add direct account IDs
        if "account_ids" in step_data and step_data["account_ids"]:
            all_account_ids.update(step_data["account_ids"])
        
        # Expand cluster IDs to account IDs
        if "cluster_ids" in step_data and step_data["cluster_ids"]:
            cluster_account_ids = self._expand_clusters_to_accounts(step_data["cluster_ids"], db)
            all_account_ids.update(cluster_account_ids)
        
        # Validate that we have at least one account ID
        if not all_account_ids:
            raise ValueError("Step must specify at least account_ids or cluster_ids")
        
        # Return as sorted list for consistent ordering
        return sorted(list(all_account_ids))
    
    async def create_job(self, name: str, description: Optional[str], steps: List[Dict[str, Any]], parallel_execution: bool = False) -> JobResponse:
        """Create a new job with steps"""
        db = SessionLocal()
        try:
            # Validate all action types before creating the job
            for step_data in steps:
                action_type = step_data.get("action_type")
                if not action_type:
                    raise ValueError("Step must specify action_type")
                
                if not self._validate_action_type(action_type):
                    valid_types = self._get_valid_action_types()
                    raise ValueError(f"Invalid action_type '{action_type}'. Valid types are: {', '.join(valid_types)}")
            
            # Calculate total steps after combining account_ids and cluster expansion
            total_steps = 0
            for step_data in steps:
                # Get all account IDs from both direct account_ids and cluster expansion
                all_account_ids = self._get_all_account_ids_for_step(step_data, db)
                total_steps += len(all_account_ids)
            
            # Create the job
            job = Job(
                name=name,
                description=description,
                parallel_execution=parallel_execution,
                total_steps=total_steps,
                status=JobStatus.PENDING
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Create job steps (combining account_ids and cluster expansion)
            step_order = 1
            for step_data in steps:
                # Get all account IDs from both direct account_ids and cluster expansion
                all_account_ids = self._get_all_account_ids_for_step(step_data, db)
                
                # Create a step for each account
                for account_id in all_account_ids:
                    step = JobStep(
                        job_id=job.id,
                        step_order=step_order,
                        action_type=step_data["action_type"],
                        account_id=account_id,
                        parameters=json.dumps(step_data.get("parameters", {})) if step_data.get("parameters") else None,
                        max_retries=step_data.get("max_retries", 0),
                        status=JobStatus.PENDING
                    )
                    db.add(step)
                    step_order += 1
            
            db.commit()
            
            # Start job execution asynchronously
            task = asyncio.create_task(self._execute_job(job.id))
            self._running_jobs[job.id] = task
            
            return await self._job_to_response(job.id, db)
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def get_job(self, job_id: int, include_steps: bool = False) -> Optional[JobResponse]:
        """Get a job by ID"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            return await self._job_to_response(job_id, db, include_steps)
        finally:
            db.close()
    
    async def list_jobs(self, status: Optional[JobStatus] = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List jobs with optional filtering"""
        db = SessionLocal()
        try:
            query = db.query(Job)
            
            if status:
                query = query.filter(Job.status == status)
            
            total = query.count()
            total_pages = (total + per_page - 1) // per_page
            
            jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
            
            job_responses = []
            for job in jobs:
                job_responses.append(await self._job_to_response(job.id, db))
            
            return {
                "jobs": job_responses,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
        finally:
            db.close()
    
    async def cancel_job(self, job_id: int, reason: Optional[str] = None) -> bool:
        """Cancel a running job"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False
            
            # Update job status
            job.status = JobStatus.CANCELLED
            job.error_message = reason or "Cancelled by user"
            job.completed_at = datetime.now(timezone.utc)
            
            # Cancel running task if exists
            if job_id in self._running_jobs:
                task = self._running_jobs[job_id]
                task.cancel()
                del self._running_jobs[job_id]
            
            # Update pending/running steps
            db.query(JobStep).filter(
                and_(
                    JobStep.job_id == job_id,
                    JobStep.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
                )
            ).update({
                "status": JobStatus.CANCELLED,
                "error_message": "Job cancelled",
                "completed_at": datetime.now(timezone.utc)
            })
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def _execute_job(self, job_id: int):
        """Execute a job asynchronously"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return
            
            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            db.commit()
            
            # Get all pending steps
            steps = db.query(JobStep).filter(
                JobStep.job_id == job_id
            ).order_by(JobStep.step_order).all()
            
            if job.parallel_execution:
                # Execute all steps in parallel
                await self._execute_steps_parallel(steps, db)
            else:
                # Execute steps sequentially
                for step in steps:
                    # Check if job was cancelled
                    db.refresh(job)
                    if job.status == JobStatus.CANCELLED:
                        break
                    
                    try:
                        # Execute the step
                        await self._execute_step(step, db)
                        
                    except Exception as e:
                        logger.error(f"Error executing step {step.id}: {e}")
                        step.status = JobStatus.FAILED
                        step.error_message = str(e)
                        step.completed_at = datetime.now(timezone.utc)
                        db.commit()
                        
                        
            
            # Update final job status
            db.refresh(job)
            if job.status != JobStatus.CANCELLED:
                completed_steps = db.query(JobStep).filter(
                    and_(JobStep.job_id == job_id, JobStep.status == JobStatus.COMPLETED)
                ).count()
                
                failed_steps = db.query(JobStep).filter(
                    and_(JobStep.job_id == job_id, JobStep.status == JobStatus.FAILED)
                ).count()
                
                job.completed_steps = completed_steps
                job.failed_steps = failed_steps
                
                if failed_steps == 0:
                    job.status = JobStatus.COMPLETED
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = f"{failed_steps} steps failed"
                
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            
            # Remove from running jobs
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
                
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
    
    async def _execute_step(self, step: JobStep, db: Session):
        """Execute a single job step"""
        step.status = JobStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        db.commit()
        
        try:
            # Get account
            account = db.query(Account).filter(Account.id == step.account_id).first()
            if not account:
                raise ValueError(f"Account {step.account_id} not found")
            
            # Parse parameters
            parameters = {}
            if step.parameters:
                parameters = json.loads(step.parameters)
            
            # Convert string action_type to ActionType enum
            action_type_enum = self.account_manager.ActionType(step.action_type)
            
            # Prepare action parameters
            action_params = {
                "max_retries": step.max_retries,
                **parameters
            }
            
            # Execute action using account manager
            result = await self.account_manager.execute_action(
                id_type=AccountIdentifierType.ID,
                id=step.account_id,
                action=action_type_enum,
                **action_params
            )
            
            # Update step result
            step.status = JobStatus.COMPLETED if result.get("success", False) else JobStatus.FAILED
            step.result = json.dumps(result)
            step.error_message = result.get("error") if not result.get("success", False) else None
            step.completed_at = datetime.now(timezone.utc)
            db.commit()
            
        except Exception as e:
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise
    
    async def _execute_steps_parallel(self, steps: List[JobStep], db: Session):
        """Execute multiple steps in parallel"""
        # Create tasks for all steps
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_step_safe(step, db))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update step statuses based on results
        for i, result in enumerate(results):
            step = steps[i]
            if isinstance(result, Exception):
                step.status = JobStatus.FAILED
                step.error_message = str(result)
                step.completed_at = datetime.now(timezone.utc)
            # If not an exception, the step status was already updated in _execute_step_safe
            db.commit()
    
    async def _execute_step_safe(self, step: JobStep, db: Session):
        """Safely execute a single step with proper error handling"""
        try:
            await self._execute_step(step, db)
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise  # Re-raise to be caught by gather()
    
    async def _job_to_response(self, job_id: int, db: Session, include_steps: bool = False) -> JobResponse:
        """Convert a Job to JobResponse"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        steps = None
        if include_steps:
            db_steps = db.query(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.step_order).all()
            steps = []
            for step in db_steps:
                step_response = JobStepResponse(
                    id=step.id,
                    step_order=step.step_order,
                    action_type=step.action_type,
                    account_id=step.account_id,
                    target_id=step.target_id,
                    parameters=json.loads(step.parameters) if step.parameters else None,
                    max_retries=step.max_retries,
                    status=step.status.value,
                    result=json.loads(step.result) if step.result else None,
                    error_message=step.error_message,
                    started_at=step.started_at,
                    completed_at=step.completed_at
                )
                steps.append(step_response)
        
        return JobResponse(
            id=job.id,
            name=job.name,
            description=job.description,
            status=job.status.value,
            parallel_execution=job.parallel_execution,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            total_steps=job.total_steps,
            completed_steps=job.completed_steps,
            failed_steps=job.failed_steps,
            error_message=job.error_message,
            steps=steps
        )
