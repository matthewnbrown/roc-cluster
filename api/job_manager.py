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
        # In-memory job progress tracking for real-time updates
        self._job_progress = {}  # {job_id: {"completed": int, "failed": int, "total": int}}
    
    def _init_job_progress(self, job_id: int, total_steps: int):
        """Initialize in-memory progress tracking for a job"""
        self._job_progress[job_id] = {
            "completed": 0,
            "failed": 0,
            "total": total_steps
        }
    
    def _update_step_progress(self, job_id: int, step_status: JobStatus):
        """Update in-memory progress when a step completes"""
        if job_id not in self._job_progress:
            return
        
        if step_status == JobStatus.COMPLETED:
            self._job_progress[job_id]["completed"] += 1
        elif step_status == JobStatus.FAILED:
            self._job_progress[job_id]["failed"] += 1
    
    def _get_job_progress(self, job_id: int) -> Dict[str, int]:
        """Get current job progress from memory"""
        return self._job_progress.get(job_id, {"completed": 0, "failed": 0, "total": 0})
    
    def _cleanup_job_progress(self, job_id: int):
        """Clean up in-memory progress when job is complete"""
        if job_id in self._job_progress:
            del self._job_progress[job_id]
    
    def get_job_progress(self, job_id: int) -> Dict[str, int]:
        """Get current job progress for API endpoints"""
        return self._get_job_progress(job_id)
    
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
                        "description": "Enemy weapon type to use (default: -1)",
                        "default": -1
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
            "purchase_armory_by_preferences": {
                "description": "Purchase items from the armory based on user preferences",
                "category": "self_action",
                "required_parameters": [],
                "optional_parameters": [],
                "parameter_details": {},
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains purchase details",
                    "error": "string (optional)"
                }
            },
            "purchase_training": {
                "description": "Purchase training for soldiers and mercenaries",
                "category": "self_action",
                "required_parameters": ["training_orders"],
                "optional_parameters": [],
                "parameter_details": {
                    "training_orders": {
                        "type": "object",
                        "description": "Dictionary of training orders with keys like 'buy[attack_soldiers]', 'train[defense_soldiers]', 'untrain[spies]', etc. Values should be strings or numbers representing quantities."
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains training purchase details",
                    "error": "string (optional)"
                }
            },
            "set_credit_saving": {
                "description": "Set credit saving to 'on' or 'off' for the account",
                "category": "self_action",
                "required_parameters": ["value"],
                "optional_parameters": [],
                "parameter_details": {
                    "value": {
                        "type": "string",
                        "description": "Credit saving setting: 'on' to enable, 'off' to disable",
                        "enum": ["on", "off"]
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains saving status",
                    "error": "string (optional)"
                }
            },
            "buy_upgrade": {
                "description": "Buy upgrade - supports siege, fortification, covert, recruiter",
                "category": "self_action",
                "required_parameters": ["upgrade_option"],
                "optional_parameters": [],
                "parameter_details": {
                    "upgrade_option": {
                        "type": "string",
                        "description": "Upgrade option: siege, fortification, covert, or recruiter",
                        "enum": ["siege", "fortification", "covert", "recruiter"]
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains upgrade purchase details",
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
            },
            "update_armory_preferences": {
                "description": "Update armory preferences for the account. Available weapons: dagger, maul, blade, excalibur, sai, shield, mithril, dragonskin, cloak, hook, pickaxe, horn, guard_dog, torch",
                "category": "self_action",
                "required_parameters": ["weapon_percentages"],
                "optional_parameters": [],
                "parameter_details": {
                    "weapon_percentages": {
                        "type": "object",
                        "description": "Dictionary of weapon_name: percentage pairs (percentages must sum to <= 100%). Available weapons: dagger, maul, blade, excalibur, sai, shield, mithril, dragonskin, cloak, hook, pickaxe, horn, guard_dog, torch"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains preference update details",
                    "error": "string (optional)"
                }
            },
            "update_training_preferences": {
                "description": "Update training preferences for the account",
                "category": "self_action",
                "required_parameters": ["soldier_type_percentages"],
                "optional_parameters": [],
                "parameter_details": {
                    "soldier_type_percentages": {
                        "type": "object",
                        "description": "Dictionary of soldier_type_name: percentage pairs (percentages must sum to <= 100%)"
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional)",
                    "data": "object (optional) - contains preference update details",
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
            
            # Calculate total steps - now one step per job step definition (combining all accounts/clusters)
            total_steps = len(steps)
            
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
            
            # Create job steps - one step per step definition, combining all accounts/clusters
            step_order = 1
            for step_data in steps:
                # Get all account IDs from both direct account_ids and cluster expansion
                all_account_ids = self._get_all_account_ids_for_step(step_data, db)
                
                # Create one step that handles all accounts
                step = JobStep(
                    job_id=job.id,
                    step_order=step_order,
                    action_type=step_data["action_type"],
                    account_ids=json.dumps(all_account_ids) if all_account_ids else "[]",
                    original_cluster_ids=json.dumps(step_data.get("cluster_ids", [])) if step_data.get("cluster_ids") else None,
                    original_account_ids=json.dumps(step_data.get("account_ids", [])) if step_data.get("account_ids") else None,
                    parameters=json.dumps(step_data.get("parameters", {})) if step_data.get("parameters") else None,
                    max_retries=step_data.get("max_retries", 0),
                    is_async=step_data.get("is_async", False),
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
            
            # Initialize in-memory progress tracking for real-time updates
            self._init_job_progress(job_id, len(steps))
            
            # Bulk load accounts and cookies for all accounts in this job to optimize performance
            all_account_ids = set()
            for step in steps:
                if step.account_ids:
                    # Multi-account step
                    step_account_ids = json.loads(step.account_ids)
                    all_account_ids.update(step_account_ids)
            
            account_ids = list(all_account_ids)
            
            # Load both accounts and cookies in parallel for maximum performance
            bulk_accounts_task = self.account_manager.bulk_load_accounts(account_ids)
            bulk_cookies_task = self.account_manager.bulk_load_cookies(account_ids)
            
            bulk_accounts, bulk_cookies = await asyncio.gather(
                bulk_accounts_task,
                bulk_cookies_task
            )
            
            logger.info(f"Pre-loaded {len(bulk_accounts)} accounts and {len(bulk_cookies)} cookie sets for job {job_id}")
            
            if job.parallel_execution:
                # Execute all steps in parallel
                await self._execute_steps_parallel(steps, db, bulk_cookies, bulk_accounts)
            else:
                # Execute steps sequentially with async step support
                await self._execute_steps_sequential(steps, db, job, bulk_cookies, bulk_accounts)
                        
                        
            
            # Update final job status - ensure all steps are actually completed
            db.refresh(job)
            if job.status != JobStatus.CANCELLED:
                # Wait a moment for any async steps to complete and update their status
                await asyncio.sleep(0.1)
                
                # Update progress counters one final time
                await self._update_job_progress(job_id, db)
                db.commit()  # Ensure progress updates are committed
                
                # Re-query the job to get the latest values
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    logger.error(f"Job {job_id} not found after progress update")
                    return
                
                # Count async steps for logging
                async_steps = db.query(JobStep).filter(
                    and_(JobStep.job_id == job_id, JobStep.is_async == True)
                ).count()
                
                logger.info(f"Job {job_id} completed: {job.completed_steps} completed, {job.failed_steps} failed, {async_steps} async steps")
                
                # Check if all steps are actually completed (not just that none failed)
                total_actual_steps = job.completed_steps + job.failed_steps
                
                # Debug logging
                logger.info(f"Job {job_id} completion check: total_steps={job.total_steps}, completed_steps={job.completed_steps}, failed_steps={job.failed_steps}, total_actual_steps={total_actual_steps}")
                
                if total_actual_steps == job.total_steps and job.failed_steps == 0:
                    job.status = JobStatus.COMPLETED
                    logger.info(f"Job {job_id} marked as COMPLETED")
                elif total_actual_steps == job.total_steps and job.failed_steps > 0:
                    job.status = JobStatus.FAILED
                    job.error_message = f"{job.failed_steps} steps failed"
                    logger.info(f"Job {job_id} marked as FAILED due to {job.failed_steps} failed steps")
                else:
                    # This shouldn't happen, but if it does, mark as failed
                    job.status = JobStatus.FAILED
                    job.error_message = f"Job execution incomplete: {total_actual_steps}/{job.total_steps} steps finished"
                    logger.warning(f"Job {job_id} marked as FAILED due to incomplete execution: {total_actual_steps}/{job.total_steps} steps finished")
                
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            
            # Remove from running jobs
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
            
            # Clean up in-memory progress tracking
            self._cleanup_job_progress(job_id)
                
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            
            # Clean up in-memory progress tracking even on error
            self._cleanup_job_progress(job_id)
        finally:
            db.close()
    
    async def _execute_step(self, step: JobStep, db: Session, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute a single job step - handles multiple accounts from clusters and direct account IDs"""
        step.status = JobStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        db.commit()
        
        try:
            # Parse parameters
            parameters = {}
            if step.parameters:
                parameters = json.loads(step.parameters)
            
            # Convert string action_type to ActionType enum
            action_type_enum = self.account_manager.ActionType(step.action_type)
            
            # Get account IDs from the step
            if not step.account_ids:
                raise ValueError("Step must have account_ids")
            
            account_ids = json.loads(step.account_ids)
            result = await self._execute_multi_account_step(account_ids, action_type_enum, parameters, step.max_retries, bulk_cookies, bulk_accounts)
            
            # Update step result
            step.status = JobStatus.COMPLETED if result.get("success", False) else JobStatus.FAILED
            step.result = json.dumps(result)
            step.error_message = result.get("error") if not result.get("success", False) else None
            step.completed_at = datetime.now(timezone.utc)
            
            # Update in-memory progress for real-time tracking
            self._update_step_progress(step.job_id, step.status)
            
        except Exception as e:
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            
            # Update in-memory progress for real-time tracking
            self._update_step_progress(step.job_id, step.status)

            raise
    
    async def _execute_multi_account_step(self, account_ids: List[int], action_type_enum, parameters: Dict[str, Any], max_retries: int, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute action for multiple accounts and consolidate results"""
        if not account_ids:
            return {"success": True, "message": "No accounts to process", "results": []}
        
        # Execute actions for all accounts in parallel
        tasks = []
        for account_id in account_ids:
            task = asyncio.create_task(
                self._execute_single_account_action(account_id, action_type_enum, parameters, max_retries, bulk_cookies, bulk_accounts)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Consolidate results
        successful_results = []
        failed_results = []
        total_success = 0
        total_failed = 0
        
        for i, result in enumerate(results):
            account_id = account_ids[i]
            if isinstance(result, Exception):
                failed_results.append({
                    "account_id": account_id,
                    "error": str(result),
                    "success": False
                })
                total_failed += 1
            else:
                if result.get("success", False):
                    successful_results.append({
                        "account_id": account_id,
                        "result": result,
                        "success": True
                    })
                    total_success += 1
                else:
                    failed_results.append({
                        "account_id": account_id,
                        "error": result.get("error", "Unknown error"),
                        "success": False
                    })
                    total_failed += 1
        
        # Determine overall success
        overall_success = total_failed == 0
        
        # Create consolidated result
        consolidated_result = {
            "success": overall_success,
            "total_accounts": len(account_ids),
            "successful_accounts": total_success,
            "failed_accounts": total_failed,
            "successful_results": successful_results,
            "failed_results": failed_results,
            "message": f"Processed {len(account_ids)} accounts: {total_success} successful, {total_failed} failed"
        }
        
        if not overall_success:
            consolidated_result["error"] = f"{total_failed} out of {len(account_ids)} accounts failed"
        
        return consolidated_result
    
    async def _execute_single_account_action(self, account_id: int, action_type_enum, parameters: Dict[str, Any], max_retries: int, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute action for a single account"""
        # Get account from preloaded data or fallback to database
        account = None
        if bulk_accounts and account_id in bulk_accounts:
            account = bulk_accounts[account_id]
        else:
            # Fallback to database query (should rarely happen now)
            db = SessionLocal()
            try:
                account = db.query(Account).filter(Account.id == account_id).first()
            finally:
                db.close()
        
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # Get preloaded cookies for this account if available
        preloaded_cookies = None
        if bulk_cookies and account_id in bulk_cookies:
            preloaded_cookies = bulk_cookies[account_id]
        
        # Prepare action parameters
        action_params = {
            "max_retries": max_retries,
            "preloaded_cookies": preloaded_cookies,
            "preloaded_account": account,
            **parameters
        }
        
        # Execute action using account manager
        result = await self.account_manager.execute_action(
            id_type=AccountIdentifierType.ID,
            id=account_id,
            action=action_type_enum,
            bypass_semaphore=False,
            **action_params
        )
        
        return result
    
    async def _execute_steps_sequential(self, steps: List[JobStep], db: Session, job: Job, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute steps sequentially with support for async steps"""
        async_tasks = []  # Track async tasks that are running
        
        for step in steps:
            # Check if job was cancelled
            db.refresh(job)
            if job.status == JobStatus.CANCELLED:
                break
            
            try:
                if step.is_async:
                    # Launch async step without waiting
                    task = asyncio.create_task(self._execute_step_safe(step, db, bulk_cookies, bulk_accounts))
                    async_tasks.append(task)
                    logger.info(f"Launched async step {step.id} for job {job.id}")
                else:
                    # Execute sync step and wait for completion
                    await self._execute_step(step, db, bulk_cookies, bulk_accounts)
                    
            except Exception as e:
                logger.error(f"Error executing step {step.id}: {e}")
                step.status = JobStatus.FAILED
                step.error_message = str(e)
                step.completed_at = datetime.now(timezone.utc)
                # Don't commit here - batch commits for better performance
        
        # Batch commit for all sequential steps
        db.commit()
        
        # Update job progress once after all sequential steps are processed
        if steps:
            await self._update_job_progress(steps[0].job_id, db)
        
        # Wait for all async tasks to complete
        if async_tasks:
            logger.info(f"Waiting for {len(async_tasks)} async tasks to complete for job {job.id}")
            await asyncio.gather(*async_tasks, return_exceptions=True)
            logger.info(f"All async tasks completed for job {job.id}")

    async def _execute_steps_parallel(self, steps: List[JobStep], db: Session, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute multiple steps in parallel"""
        # Create tasks for all steps - each gets its own database session
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_step_safe(step, None, bulk_cookies, bulk_accounts))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update step statuses based on results - use the main db session for final updates
        for i, result in enumerate(results):
            step = steps[i]
            if isinstance(result, Exception):
                step.status = JobStatus.FAILED
                step.error_message = str(result)
                step.completed_at = datetime.now(timezone.utc)
            # If not an exception, the step status was already updated in _execute_step_safe
        
        # Single commit for all step updates (much faster!)
        db.commit()
        
        # Update job progress once after all steps are processed
        if steps:
            await self._update_job_progress(steps[0].job_id, db)
    
    async def _update_job_progress(self, job_id: int, db: Session):
        """Update job progress counters based on current step statuses"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        
        # Use in-memory progress if available (for real-time updates during execution)
        if job_id in self._job_progress:
            progress = self._job_progress[job_id]
            completed_steps = progress["completed"]
            failed_steps = progress["failed"]
        else:
            # Fall back to database count (for completed jobs or when memory is not available)
            completed_steps = db.query(JobStep).filter(
                and_(JobStep.job_id == job_id, JobStep.status == JobStatus.COMPLETED)
            ).count()
            
            failed_steps = db.query(JobStep).filter(
                and_(JobStep.job_id == job_id, JobStep.status == JobStatus.FAILED)
            ).count()
        
        # Also count pending and running steps for debugging
        pending_steps = db.query(JobStep).filter(
            and_(JobStep.job_id == job_id, JobStep.status == JobStatus.PENDING)
        ).count()
        
        running_steps = db.query(JobStep).filter(
            and_(JobStep.job_id == job_id, JobStep.status == JobStatus.RUNNING)
        ).count()
        
        # Update job counters
        job.completed_steps = completed_steps
        job.failed_steps = failed_steps
        
        logger.info(f"Updated job {job_id} progress: {completed_steps} completed, {failed_steps} failed, {pending_steps} pending, {running_steps} running")

    async def _execute_step_safe(self, step: JobStep, db: Session | None = None, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Safely execute a single step with proper error handling"""
        # Create own database session if none provided (for parallel execution)
        own_db = None
        if db is None:
            own_db = SessionLocal()
            db = own_db
        
        try:
            await self._execute_step(step, db, bulk_cookies, bulk_accounts)
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            
            # Don't update progress or commit here - let the main loop handle it
            # This avoids database contention in parallel execution
            raise  # Re-raise to be caught by gather()
        finally:
            # Close own database session if we created it
            if own_db:
                own_db.close()
    
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
                # Parse account_ids and original IDs
                account_ids = json.loads(step.account_ids) if step.account_ids else []
                original_cluster_ids = json.loads(step.original_cluster_ids) if step.original_cluster_ids else None
                original_account_ids = json.loads(step.original_account_ids) if step.original_account_ids else None
                
                step_response = JobStepResponse(
                    id=step.id,
                    step_order=step.step_order,
                    action_type=step.action_type,
                    account_ids=account_ids,
                    original_cluster_ids=original_cluster_ids,
                    original_account_ids=original_account_ids,
                    target_id=step.target_id,
                    parameters=json.loads(step.parameters) if step.parameters else None,
                    max_retries=step.max_retries,
                    is_async=step.is_async,
                    status=step.status.value,
                    result=json.loads(step.result) if step.result else None,
                    error_message=step.error_message,
                    started_at=step.started_at,
                    completed_at=step.completed_at
                )
                steps.append(step_response)
        
        # Get real-time progress from in-memory tracking if available
        real_time_progress = self.get_job_progress(job.id)
        
        # Use in-memory progress if available, otherwise fall back to database values
        if real_time_progress["total"] > 0:
            completed_steps = real_time_progress["completed"]
            failed_steps = real_time_progress["failed"]
            total_steps = real_time_progress["total"]
        else:
            completed_steps = job.completed_steps
            failed_steps = job.failed_steps
            total_steps = job.total_steps
        
        return JobResponse(
            id=job.id,
            name=job.name,
            description=job.description,
            status=job.status.value,
            parallel_execution=job.parallel_execution,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            total_steps=total_steps,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            error_message=job.error_message,
            steps=steps
        )
