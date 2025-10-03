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
        self._step_progress = {}  # {step_id: {"total_accounts": int, "processed_accounts": int, "successful_accounts": int, "failed_accounts": int}}
        # Track running step tasks for cancellation
        self._running_step_tasks: Dict[int, List[asyncio.Task]] = {}  # {job_id: [task1, task2, ...]}
    
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
    
    def _add_running_step_task(self, job_id: int, task: asyncio.Task):
        """Add a running step task to the tracking list"""
        if job_id not in self._running_step_tasks:
            self._running_step_tasks[job_id] = []
        self._running_step_tasks[job_id].append(task)
    
    def _remove_running_step_task(self, job_id: int, task: asyncio.Task):
        """Remove a completed step task from the tracking list"""
        if job_id in self._running_step_tasks:
            try:
                self._running_step_tasks[job_id].remove(task)
            except ValueError:
                pass  # Task not in list, ignore
    
    def _cancel_running_step_tasks(self, job_id: int):
        """Cancel all running step tasks for a job"""
        if job_id in self._running_step_tasks:
            tasks = self._running_step_tasks[job_id]
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Clear the list
            self._running_step_tasks[job_id] = []
            logger.info(f"Cancelled {len(tasks)} running step tasks for job {job_id}")
    
    def _cleanup_running_step_tasks(self, job_id: int):
        """Clean up the running step tasks tracking for a job"""
        if job_id in self._running_step_tasks:
            del self._running_step_tasks[job_id]
    
    def _init_step_progress(self, step_id: int, total_accounts: int):
        """Initialize in-memory progress tracking for a step"""
        self._step_progress[step_id] = {
            "total_accounts": total_accounts,
            "processed_accounts": 0,
            "successful_accounts": 0,
            "failed_accounts": 0
        }
        logger.info(f"Initialized step progress for step {step_id}: {self._step_progress[step_id]}")
    
    def _update_step_progress_in_memory(self, step_id: int, processed_accounts: int, successful_accounts: int, failed_accounts: int):
        """Update step progress in memory for real-time updates"""
        if step_id in self._step_progress:
            self._step_progress[step_id].update({
                "processed_accounts": processed_accounts,
                "successful_accounts": successful_accounts,
                "failed_accounts": failed_accounts
            })
    
    def _get_step_progress(self, step_id: int) -> Dict[str, int]:
        """Get current step progress from memory"""
        progress = self._step_progress.get(step_id, {
            "total_accounts": 0,
            "processed_accounts": 0,
            "successful_accounts": 0,
            "failed_accounts": 0
        })
        logger.info(f"Getting step progress for step {step_id}: {progress}")
        return progress
    
    def _cleanup_step_progress(self, step_id: int):
        """Clean up in-memory step progress when step is complete"""
        if step_id in self._step_progress:
            del self._step_progress[step_id]
    
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
                "description": "Purchase items from the armory based on user preferences ",
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
                "description": "Update armory preferences for the account",
                "category": "self_action",
                "required_parameters": ["weapon_percentages"],
                "optional_parameters": [],
                "parameter_details": {
                    "weapon_percentages": {
                        "type": "object",
                        "description": "Dictionary of weapon_name: percentage pairs (percentages must sum to <= 100%). "
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
            },
            "get_cards": {
                "description": "Get cards from sendcards page (always uses target_id '1')",
                "category": "self_action",
                "required_parameters": [],
                "optional_parameters": [],
                "parameter_details": {},
                "output": {
                    "success": "boolean",
                    "message": "string (optional) - contains card count summary",
                    "data": "object (optional) - contains parsed cards data with target info and card list",
                    "error": "string (optional)"
                }
            },
            "send_cards": {
                "description": "Send cards to another user",
                "category": "user_action",
                "required_parameters": ["target_id", "card_id"],
                "optional_parameters": ["comment"],
                "parameter_details": {
                    "target_id": {
                        "type": "string",
                        "description": "ROC ID of the target user to send cards to"
                    },
                    "card_id": {
                        "type": "string",
                        "description": "Card ID to send, or 'all' to send all available cards"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional comment to include with the card (default: empty)",
                        "default": ""
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional) - contains cards sent summary",
                    "data": "object (optional) - contains sending results and card counts",
                    "error": "string (optional)"
                }
            },
            "delay": {
                "description": "Wait for a specified amount of time before continuing",
                "category": "system_action",
                "required_parameters": ["duration_seconds"],
                "optional_parameters": ["message"],
                "parameter_details": {
                    "duration_seconds": {
                        "type": "number",
                        "description": "Number of seconds to wait (can be decimal for sub-second precision)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to display during the delay (default: 'Waiting...')",
                        "default": "Waiting..."
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional) - confirmation message",
                    "data": "object (optional) - contains delay details",
                    "error": "string (optional)"
                }
            },
            "collect_async_tasks": {
                "description": "Wait for all previous async tasks to complete before continuing",
                "category": "system_action",
                "required_parameters": [],
                "optional_parameters": ["message", "timeout_seconds"],
                "parameter_details": {
                    "message": {
                        "type": "string",
                        "description": "Optional message to display during the wait (default: 'Waiting for async tasks to complete...')",
                        "default": "Waiting for async tasks to complete..."
                    },
                    "timeout_seconds": {
                        "type": "number",
                        "description": "Maximum time to wait for async tasks to complete in seconds (default: 0 for infinite wait). Set to 0 to wait indefinitely.",
                        "default": 0
                    }
                },
                "output": {
                    "success": "boolean",
                    "message": "string (optional) - confirmation message",
                    "data": "object (optional) - contains task completion details",
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
        # Delay and collect_async_tasks steps don't need account IDs
        if step_data.get("action_type") in ["delay", "collect_async_tasks"]:
            return []
        
        all_account_ids = set()
        
        # Add direct account IDs
        if "account_ids" in step_data and step_data["account_ids"]:
            all_account_ids.update(step_data["account_ids"])
        
        # Expand cluster IDs to account IDs
        if "cluster_ids" in step_data and step_data["cluster_ids"]:
            cluster_account_ids = self._expand_clusters_to_accounts(step_data["cluster_ids"], db)
            all_account_ids.update(cluster_account_ids)
        
        # Validate that we have at least one account ID (except for delay and collect_async_tasks steps)
        if not all_account_ids and step_data.get("action_type") not in ["delay", "collect_async_tasks"]:
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
            logger.error(f"Error creating job: {e}", exc_info=True)
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
    
    async def list_jobs(self, status: Optional[JobStatus] = None, page: int = 1, per_page: int = 20, include_steps: bool = False) -> Dict[str, Any]:
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
                job_responses.append(await self._job_to_response(job.id, db, include_steps))
            
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
            
            # Cancel all running step tasks
            self._cancel_running_step_tasks(job_id)
            
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
            
            # Clean up running step tasks tracking
            self._cleanup_running_step_tasks(job_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}", exc_info=True)
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
            
            # Clean up running step tasks tracking
            self._cleanup_running_step_tasks(job_id)
                
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}", exc_info=True)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            
            # Clean up in-memory progress tracking even on error
            self._cleanup_job_progress(job_id)
            
            # Clean up running step tasks tracking even on error
            self._cleanup_running_step_tasks(job_id)
        finally:
            db.close()
    
    async def _execute_step(self, step: JobStep, db: Session, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute a single job step - handles multiple accounts from clusters and direct account IDs"""
        step.status = JobStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        db.commit()
        
        try:
            # Check if job was cancelled before starting execution
            job = db.query(Job).filter(Job.id == step.job_id).first()
            if job and job.status == JobStatus.CANCELLED:
                step.status = JobStatus.CANCELLED
                step.error_message = "Job cancelled"
                step.completed_at = datetime.now(timezone.utc)
                db.commit()
                return
            
            # Parse parameters
            parameters = {}
            if step.parameters:
                parameters = json.loads(step.parameters)
            
            # Handle special steps that don't need accounts
            if step.action_type == "delay":
                # Initialize progress tracking for delay steps (they have 0 accounts)
                step.total_accounts = 0
                step.processed_accounts = 0
                step.successful_accounts = 0
                step.failed_accounts = 0
                self._init_step_progress(step.id, 0)
                
                result = await self._execute_delay_step(parameters)
            elif step.action_type == "collect_async_tasks":
                # Initialize progress tracking for collect async tasks steps (they have 0 accounts)
                step.total_accounts = 0
                step.processed_accounts = 0
                step.successful_accounts = 0
                step.failed_accounts = 0
                self._init_step_progress(step.id, 0)
                
                result = await self._execute_collect_async_tasks_step(step.job_id, parameters)
            else:
                # Convert string action_type to ActionType enum
                action_type_enum = self.account_manager.ActionType(step.action_type)
                
                # Get account IDs from the step
                if not step.account_ids:
                    raise ValueError("Step must have account_ids")
                
                account_ids = json.loads(step.account_ids)
                result = await self._execute_multi_account_step(account_ids, action_type_enum, parameters, step.max_retries, step, bulk_cookies, bulk_accounts)
            
            # Update step result
            step.status = JobStatus.COMPLETED if result.get("success", False) else JobStatus.FAILED
            step.result = json.dumps(result)
            step.error_message = result.get("error") if not result.get("success", False) else None
            step.completed_at = datetime.now(timezone.utc)
            
            # Commit step status update immediately so it's visible in API
            db.commit()
            
            # Update in-memory progress for real-time tracking
            self._update_step_progress(step.job_id, step.status)
            
            # Update in-memory step progress with final values before cleanup
            if step.id in self._step_progress:
                self._step_progress[step.id].update({
                    "processed_accounts": step.processed_accounts,
                    "successful_accounts": step.successful_accounts,
                    "failed_accounts": step.failed_accounts
                })
                logger.info(f"Updated final step progress for step {step.id}: {self._step_progress[step.id]}")
            
            # Don't cleanup in-memory step progress immediately - let it persist for API access
            # self._cleanup_step_progress(step.id)
            
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}", exc_info=True)
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            
            # Commit step failure status immediately so it's visible in API
            db.commit()
            
            # Update in-memory progress for real-time tracking
            self._update_step_progress(step.job_id, step.status)
            
            # Update in-memory step progress with final values before cleanup
            if step.id in self._step_progress:
                self._step_progress[step.id].update({
                    "processed_accounts": step.processed_accounts,
                    "successful_accounts": step.successful_accounts,
                    "failed_accounts": step.failed_accounts
                })
                logger.info(f"Updated final failed step progress for step {step.id}: {self._step_progress[step.id]}")
            
            # Don't cleanup in-memory step progress immediately - let it persist for API access
            # self._cleanup_step_progress(step.id)

            raise
    
    async def _execute_delay_step(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a delay step - just wait for the specified duration"""
        try:
            duration_seconds = parameters.get("duration_seconds")
            message = parameters.get("message", "Waiting...")
            
            if duration_seconds is None:
                return {
                    "success": False,
                    "error": "duration_seconds parameter is required for delay steps"
                }
            
            # Validate duration
            try:
                duration_seconds = float(duration_seconds)
                if duration_seconds < 0:
                    return {
                        "success": False,
                        "error": "duration_seconds must be non-negative"
                    }
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "error": "duration_seconds must be a valid number"
                }
            
            # Log the delay start
            logger.info(f"Delay step: {message} for {duration_seconds} seconds")
            
            # Wait for the specified duration
            await asyncio.sleep(duration_seconds)
            
            # Log completion
            logger.info(f"Delay step completed after {duration_seconds} seconds")
            
            return {
                "success": True,
                "message": f"Waited {duration_seconds} seconds",
                "data": {
                    "duration_seconds": duration_seconds,
                    "message": message,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in delay step: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_collect_async_tasks_step(self, job_id: int, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a collect async tasks step - wait for all previous async tasks to complete"""
        try:
            message = parameters.get("message", "Waiting for async tasks to complete...")
            timeout_seconds = parameters.get("timeout_seconds", 0)  # Default infinite wait
            
            # Validate timeout
            try:
                timeout_seconds = float(timeout_seconds)
                if timeout_seconds < 0:
                    return {
                        "success": False,
                        "error": "timeout_seconds must be non-negative"
                    }
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "error": "timeout_seconds must be a valid number"
                }
            
            logger.info(f"Collect async tasks step: {message}")
            
            # Get all running async tasks for this job
            if job_id in self._running_step_tasks:
                async_tasks = self._running_step_tasks[job_id].copy()
                if async_tasks:
                    logger.info(f"Waiting for {len(async_tasks)} async tasks to complete for job {job_id}")
                    
                    # Wait for all async tasks to complete with optional timeout
                    try:
                        if timeout_seconds == 0:
                            # Wait indefinitely if timeout_seconds is 0
                            logger.info(f"Waiting indefinitely for {len(async_tasks)} async tasks to complete for job {job_id}")
                            await asyncio.gather(*async_tasks, return_exceptions=True)
                        else:
                            # Wait with timeout
                            await asyncio.wait_for(
                                asyncio.gather(*async_tasks, return_exceptions=True),
                                timeout=timeout_seconds
                            )
                        logger.info(f"All async tasks completed for job {job_id}")
                        
                        return {
                            "success": True,
                            "message": f"Successfully waited for {len(async_tasks)} async tasks to complete: {message}",
                            "data": {
                                "tasks_waited_for": len(async_tasks),
                                "message": message,
                                "completed_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout waiting for async tasks to complete for job {job_id}")
                        return {
                            "success": False,
                            "error": f"Timeout after {timeout_seconds} seconds waiting for async tasks to complete"
                        }
                else:
                    logger.info(f"No async tasks running for job {job_id}")
                    return {
                        "success": True,
                        "message": f"No async tasks were running: {message}",
                        "data": {
                            "tasks_waited_for": 0,
                            "message": message,
                            "completed_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
            else:
                logger.info(f"No running step tasks found for job {job_id}")
                return {
                    "success": True,
                    "message": f"No async tasks were running: {message}",
                    "data": {
                        "tasks_waited_for": 0,
                        "message": message,
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            
        except Exception as e:
            logger.error(f"Error in collect async tasks step: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_multi_account_step(self, account_ids: List[int], action_type_enum, parameters: Dict[str, Any], max_retries: int, step: JobStep = None, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute action for multiple accounts and consolidate results"""
        if not account_ids:
            return {"success": True, "message": "No accounts to process", "results": []}
        
        # Initialize step progress if step is provided
        if step:
            step.total_accounts = len(account_ids)
            step.processed_accounts = 0
            step.successful_accounts = 0
            step.failed_accounts = 0
            # Initialize in-memory progress tracking (even for delay steps with 0 accounts)
            self._init_step_progress(step.id, step.total_accounts)
        
        # Execute actions for all accounts in parallel with real-time progress updates
        tasks = []
        for account_id in account_ids:
            task = asyncio.create_task(
                self._execute_single_account_action(account_id, action_type_enum, parameters, max_retries, bulk_cookies, bulk_accounts)
            )
            # Store account_id as an attribute on the task for later retrieval
            task.account_id = account_id
            tasks.append(task)
            
            # Track individual account action tasks for cancellation if step is provided
            if step:
                self._add_running_step_task(step.job_id, task)
        
        # Check if job was cancelled before processing results
        if step:
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == step.job_id).first()
                if job and job.status == JobStatus.CANCELLED:
                    # Cancel all account tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    return {"success": False, "error": "Job cancelled", "results": []}
            finally:
                db.close()
        
        # Process results as they complete for real-time progress updates
        successful_results = []
        failed_results = []
        total_success = 0
        total_failed = 0
        account_messages = {}
        
        # Use asyncio.as_completed to process results as they finish
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                # Get the account_id from the original task
                # Find the original task that corresponds to this completed task
                account_id = None
                for task in tasks:
                    if task.done() and not hasattr(task, '_processed'):
                        account_id = task.account_id
                        task._processed = True  # Mark as processed
                        break
                
                if account_id is None:
                    logger.warning(f"Could not find account_id for completed task")
                    continue
                
                # Update step progress in memory only
                if step:
                    step.processed_accounts += 1
                    # Store progress in memory for real-time updates
                    self._update_step_progress_in_memory(step.id, step.processed_accounts, step.successful_accounts, step.failed_accounts)
                
                # Process the result
                if isinstance(result, Exception):
                    failed_results.append({
                        "account_id": account_id,
                        "error": str(result),
                        "success": False
                    })
                    total_failed += 1
                    if step:
                        step.failed_accounts += 1
                        # Update progress in memory only
                        self._update_step_progress_in_memory(step.id, step.processed_accounts, step.successful_accounts, step.failed_accounts)
                else:
                    # Check for messages in the result (both old "message" and new "messages" formats)
                    messages = result.get("messages", [])
                    if not messages and result.get("message"):
                        # Convert old single message format to array
                        messages = [result.get("message")]
                    
                    if messages:
                        # Find account username for message attribution
                        account = bulk_accounts.get(account_id) if bulk_accounts else None
                        if account and hasattr(account, 'username'):
                            account_messages[account.username] = messages
                        else:
                            # Fallback to account_id if username not available
                            account_messages[str(account_id)] = messages
                        logger.info(f"Account {account_id} returned {len(messages)} messages")
                    
                    if result.get("success", False):
                        successful_results.append({
                            "account_id": account_id,
                            "result": result,
                            "success": True
                        })
                        total_success += 1
                        if step:
                            step.successful_accounts += 1
                            # Update progress in memory only
                            self._update_step_progress_in_memory(step.id, step.processed_accounts, step.successful_accounts, step.failed_accounts)
                    else:
                        # Handle both old "error" format and new "errors" array format
                        errors = result.get("errors", [])
                        if not errors and result.get("error"):
                            # Convert old single error format to array
                            errors = [result.get("error")]
                        if not errors:
                            errors = ["Unknown error"]
                        
                        failed_results.append({
                            "account_id": account_id,
                            "errors": errors,
                            "success": False
                        })
                        total_failed += 1
                        if step:
                            step.failed_accounts += 1
                            
            except Exception as e:
                logger.error(f"Error processing completed task: {e}", exc_info=True)
                # Still need to update progress even if there's an error
                if step:
                    step.processed_accounts += 1
                    step.failed_accounts += 1
        
        # Determine overall success
        overall_success = total_failed == 0
        
        # Create action-specific summary
        summary = self._create_action_summary(action_type_enum, successful_results, failed_results, account_messages)
        
        # Create consolidated result
        consolidated_result = {
            "success": overall_success,
            "total_accounts": len(account_ids),
            "successful_accounts": total_success,
            "failed_accounts": total_failed,
            "summary": summary,
            "message": f"Processed {len(account_ids)} accounts: {total_success} successful, {total_failed} failed"
        }
        
        # Add messages if any accounts returned messages
        if account_messages:
            consolidated_result["messages"] = account_messages
            logger.info(f"Added {len(account_messages)} account messages to consolidated result")
        
        if not overall_success:
            consolidated_result["error"] = f"{total_failed} out of {len(account_ids)} accounts failed"
        
        # Clean up individual account action tasks from tracking when step completes
        if step:
            for task in tasks:
                self._remove_running_step_task(step.job_id, task)
        
        return consolidated_result
    
    def _create_action_summary(self, action_type_enum, successful_results: List[Dict], failed_results: List[Dict], account_messages: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Create action-specific summary based on action type"""
        action_type = action_type_enum.value if hasattr(action_type_enum, 'value') else str(action_type_enum)
        
        # Create error list with usernames
        error_list = []
        if failed_results:
            db = SessionLocal()
            try:
                for result in failed_results:
                    account_id = result.get("account_id")
                    if account_id is None:
                        logger.warning(f"Failed result missing account_id: {result}")
                        continue
                    
                    account = db.query(Account).filter(Account.id == account_id).first()
                    username = account.username if account else f"Account {account_id}"
                    
                    # Handle both old single error and new errors array format
                    errors = result.get("errors", [])
                    if not errors and result.get("error"):
                        errors = [result.get("error")]
                    if not errors:
                        errors = ["Unknown error"]
                    
                    error_list.append({
                        "username": username,
                        "account_id": account_id,
                        "errors": errors
                    })
            except Exception as e:
                logger.error(f"Error creating error list: {e}", exc_info=True)
            finally:
                db.close()
        
        # Base summary structure
        summary = {
            "action_type": action_type,
            "successes": len(successful_results),
            "failed": len(failed_results),
            "error_list": error_list,
            "messages": account_messages if account_messages else {}
        }
        
        if account_messages:
            logger.info(f"Summary created with {len(account_messages)} account messages")
        
        # Action-specific summaries
        if action_type == "attack":
            summary.update(self._summarize_attack_results(successful_results))
        elif action_type == "sabotage":
            summary.update(self._summarize_sabotage_results(successful_results))
        elif action_type == "spy":
            summary.update(self._summarize_spy_results(successful_results))
        elif action_type == "send_credits":
            summary.update(self._summarize_send_credits_results(successful_results))
        elif action_type == "recruit":
            summary.update(self._summarize_recruit_results(successful_results))
        elif action_type == "purchase_armory":
            summary.update(self._summarize_purchase_armory_results(successful_results))
        elif action_type == "purchase_training":
            summary.update(self._summarize_purchase_training_results(successful_results))
        elif action_type == "become_officer":
            summary.update(self._summarize_become_officer_results(successful_results))
        elif action_type == "get_metadata":
            summary.update(self._summarize_get_metadata_results(successful_results))
        elif action_type == "get_cards":
            summary.update(self._summarize_get_cards_results(successful_results))
        elif action_type == "send_cards":
            summary.update(self._summarize_send_cards_results(successful_results))
        else:
            # Generic summary for other action types
            summary.update(self._summarize_generic_results(successful_results))
        
        return summary
    
    def _summarize_attack_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize attack action results"""
        summary = {
            "battle_wins": 0,
            "battle_losses": 0,
            "protection_buffs": 0,
            "maxed_hits": 0,
            "runs_away": 0,
            "gold_won": 0,
            "troops_killed": 0,
            "troops_lost": 0,
            "soldiers_killed": 0,  # Keep for backward compatibility
            "soldiers_lost": 0,    # Keep for backward compatibility
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                # Extract battle results - handle both old and new formats
                if result_data.get("win") or result_data.get("battle_won"):
                    summary["battle_wins"] += 1
                elif result_data.get("loss") or result_data.get("battle_lost"):
                    summary["battle_losses"] += 1
                elif result_data.get("protection_buff"):
                    summary["protection_buffs"] += 1
                elif result_data.get("maxed_hits"):
                    summary["maxed_hits"] += 1
                elif result_data.get("runs_away"):
                    summary["runs_away"] += 1
                
                # Sum up resources - handle both old and new field names
                summary["gold_won"] += result_data.get("gold_won", 0)
                summary["troops_killed"] += result_data.get("troops_killed", 0)
                summary["troops_lost"] += result_data.get("troops_lost", 0)
                summary["soldiers_killed"] += result_data.get("soldiers_killed", 0)  # Backward compatibility
                summary["soldiers_lost"] += result_data.get("soldiers_lost", 0)      # Backward compatibility
                summary["total_retries"] += result_data.get("retries", 0)
        
        return summary
    
    def _summarize_sabotage_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize sabotage action results"""
        summary = {
            "sabotages_successful": 0,
            "sabotages_defended": 0,
            "weapons_destroyed": 0,
            "total_damage_dealt": 0,
            "maxed_sab_attempts": 0,
            "total_retries": 0,
            "sabotages_failed": 0,
            "weapon_damage_cost": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["sabotages_successful"] += 1
                    summary["total_damage_dealt"] += result_data.get("damage_dealt", 0)
                    summary["weapons_destroyed"] += result_data.get("weapons_destroyed", 0)
                    summary["maxed_sab_attempts"] += result_data.get("maxed_sab_attempts", 0)
                    summary["sabotages_defended"] += result_data.get("sabotages_defended", 0)
                    summary["weapon_damage_cost"] += result_data.get("weapon_damage_cost", 0)
                else:
                    summary["sabotages_failed"] += 1
        
        return summary
    
    def _summarize_spy_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize spy action results"""
        summary = {
            "spies_successful": 0,
            "spies_successful_data": 0,
            "spies_caught": 0,
            "spies_failed": 0,
            "maxed_spy_attempts": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["spies_successful"] += 1
                    summary["spies_successful_data"] += result_data.get("spies_successful_data", 0)
                    summary["maxed_spy_attempts"] += result_data.get("maxed_spy_attempts", 0)
                    summary["spies_caught"] += result_data.get("spies_caught", 0)
                else:
                    summary["spies_failed"] += 1
        
        return summary
    
    def _summarize_send_credits_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize send credits action results"""
        summary = {
            "credits_sent": 0,
            "jackpot_credits": 0,
            "transfers_successful": 0,
            "transfers_failed": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["transfers_successful"] += 1
                    summary["credits_sent"] += result_data.get("credits_sent", 0)
                    summary["jackpot_credits"] += result_data.get("jackpot_credits", 0)
                else:
                    summary["transfers_failed"] += 1
        
        return summary
    
    def _summarize_recruit_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize recruit action results"""
        summary = {
            "recruit_not_needed": 0,
            "recruitments_successful": 0,
            "recruitments_failed": 0,
            "total_cost": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["recruitments_successful"] += 1
                    summary["recruit_not_needed"] += result_data.get("recruit_not_needed", 0)
                    summary["total_cost"] += result_data.get("cost", 0)
                else:
                    summary["recruitments_failed"] += 1
        
        return summary
    
    def _summarize_purchase_armory_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize purchase armory action results"""
        summary = {
            "weapons_purchased": 0,
            "purchases_successful": 0,
            "purchases_failed": 0,
            "total_cost": 0,
            "weapons_sold": 0,
            "total_revenue": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["purchases_successful"] += 1
                    summary["weapons_purchased"] += result_data.get("weapons_purchased", 0)
                    summary["total_cost"] += result_data.get("cost", 0)
                    summary["weapons_sold"] += result_data.get("weapons_sold", 0)
                    summary["total_revenue"] += result_data.get("revenue", 0)
                else:
                    summary["purchases_failed"] += 1
        
        return summary
    
    def _summarize_purchase_training_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize purchase training action results"""
        summary = {
            "soldiers_trained": 0,
            "mercs_trained": 0,
            "soldiers_untrained": 0,
            "mercs_untrained": 0,
            "purchases_successful": 0,
            "purchases_failed": 0,
            "total_cost": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["purchases_successful"] += 1
                    summary["soldiers_trained"] += result_data.get("soldiers_trained", 0)
                    summary["mercs_trained"] += result_data.get("mercs_trained", 0)
                    summary["soldiers_untrained"] += result_data.get("soldiers_untrained", 0)
                    summary["mercs_untrained"] += result_data.get("mercs_untrained", 0)
                    summary["total_cost"] += result_data.get("cost", 0)
                else:
                    summary["purchases_failed"] += 1
        
        return summary
    
    def _summarize_become_officer_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize become officer action results"""
        summary = {
            "officer_applications": 0,
            "applications_successful": 0,
            "applications_failed": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["officer_applications"] += 1
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["applications_successful"] += 1
                else:
                    summary["applications_failed"] += 1
        
        return summary
    
    def _summarize_get_metadata_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize get metadata action results"""
        summary = {
            "metadata_retrieved": 0,
            "retrievals_successful": 0,
            "retrievals_failed": 0,
            "accounts_updated": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if result_data.get("success"):
                    summary["retrievals_successful"] += 1
                    summary["metadata_retrieved"] += 1
                    if result_data.get("account_updated"):
                        summary["accounts_updated"] += 1
                else:
                    summary["retrievals_failed"] += 1
        
        return summary
    
    def _summarize_generic_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Generic summary for action types without specific summarization"""
        summary = {
            "operations_completed": len(successful_results),
            "operations_failed": 0,
            "total_retries": 0
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                if not result_data.get("success", True):
                    summary["operations_failed"] += 1
                    summary["operations_completed"] -= 1
        
        return summary
    
    def _summarize_get_cards_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize get_cards action results"""
        summary = {
            "retrievals_successful": len(successful_results),
            "retrievals_failed": 0,
            "card_count": 0,
            "total_cards": 0,
            "total_retries": 0,
            "card_summaries": []
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                
                # Aggregate card counts from each successful result
                if result_data.get("success", True):
                    summary["card_count"] += result_data.get("card_count", 0)
                    summary["total_cards"] += result_data.get("total_cards", 0)
                    
                    # Aggregate card summaries by card name
                    card_summary = result_data.get("card_summary", [])
                    for card_summary_item in card_summary:
                        if ':' in card_summary_item:
                            card_name, count_str = card_summary_item.split(':', 1)
                            card_name = card_name.strip()
                            count = int(count_str.strip())
                            
                            # Find existing entry or add new one
                            existing = next((item for item in summary["card_summaries"] if item.startswith(card_name + ":")), None)
                            if existing:
                                existing_count = int(existing.split(':')[1].strip())
                                summary["card_summaries"].remove(existing)
                                summary["card_summaries"].append(f"{card_name}: {existing_count + count}")
                            else:
                                summary["card_summaries"].append(card_summary_item)
                else:
                    summary["retrievals_failed"] += 1
                    summary["retrievals_successful"] -= 1
        
        return summary
    
    def _summarize_send_cards_results(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Summarize send_cards action results"""
        summary = {
            "sends_successful": len(successful_results),
            "sends_failed": 0,
            "cards_sent": 0,
            "total_retries": 0,
            "sent_summaries": [],
            "failed_summaries": []
        }
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                summary["total_retries"] += result_data.get("retries", 0)
                
                # Aggregate cards sent from each successful result
                if result_data.get("success", True):
                    summary["cards_sent"] += result_data.get("cards_sent", 0)
                    
                    # Aggregate sent summaries by card name
                    sent_summary = result_data.get("sent_summary", [])
                    for card_summary in sent_summary:
                        if ':' in card_summary:
                            card_name, count_str = card_summary.split(':', 1)
                            card_name = card_name.strip()
                            count = int(count_str.strip())
                            
                            # Find existing entry or add new one
                            existing = next((item for item in summary["sent_summaries"] if item.startswith(card_name + ":")), None)
                            if existing:
                                existing_count = int(existing.split(':')[1].strip())
                                summary["sent_summaries"].remove(existing)
                                summary["sent_summaries"].append(f"{card_name}: {existing_count + count}")
                            else:
                                summary["sent_summaries"].append(card_summary)
                    
                    # Aggregate failed summaries by card name
                    failed_summary = result_data.get("failed_summary", [])
                    for card_summary in failed_summary:
                        if ':' in card_summary:
                            card_name, count_str = card_summary.split(':', 1)
                            card_name = card_name.strip()
                            count = int(count_str.strip())
                            
                            # Find existing entry or add new one
                            existing = next((item for item in summary["failed_summaries"] if item.startswith(card_name + ":")), None)
                            if existing:
                                existing_count = int(existing.split(':')[1].strip())
                                summary["failed_summaries"].remove(existing)
                                summary["failed_summaries"].append(f"{card_name}: {existing_count + count}")
                            else:
                                summary["failed_summaries"].append(card_summary)
                else:
                    summary["sends_failed"] += 1
                    summary["sends_successful"] -= 1
        
        return summary
    
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
        
        # Single pass: Launch async steps immediately, execute sync steps concurrently
        for step in steps:
            # Check if job was cancelled
            db.refresh(job)
            if job.status == JobStatus.CANCELLED:
                break
            
            # Refresh step from database to see latest status updates from async tasks
            db.refresh(step)
            
            # Skip steps that are already completed or failed
            if step.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                print(f"Skipping step {step.id} for job {job.id} - already {step.status.value}")
                continue
            
            # Yield control to allow async tasks to make progress
            await asyncio.sleep(0)
            
            print(f"Executing step {step.id} for job {job.id}")
            try:
                if step.is_async:
                    # Initialize step progress immediately for async steps so it shows up in API
                    # if step.action_type == "delay":
                    #     # Delay steps have 0 accounts
                    #     step.total_accounts = 0
                    #     step.processed_accounts = 0
                    #     step.successful_accounts = 0
                    #     step.failed_accounts = 0
                    #     self._init_step_progress(step.id, 0)
                    #     logger.info(f"Initialized delay step {step.id} progress: total_accounts=0")
                    # else:
                        # For other steps, get account count and initialize progress
                    account_ids = json.loads(step.account_ids) if step.account_ids else []
                    step.total_accounts = len(account_ids)
                    step.processed_accounts = 0
                    step.successful_accounts = 0
                    step.failed_accounts = 0
                    self._init_step_progress(step.id, step.total_accounts)
                    logger.info(f"Initialized async step {step.id} progress: total_accounts={step.total_accounts}")
                
                    # Commit progress initialization immediately so it's visible in API
                    db.commit()
                    
                    # Launch async step without waiting (pass None for db so it creates its own session)
                    task = asyncio.create_task(self._execute_step_safe(step, None, bulk_cookies, bulk_accounts))
                    async_tasks.append(task)
                    # Track the task for cancellation
                    self._add_running_step_task(job.id, task)
                    logger.info(f"Launched async step {step.id} for job {job.id}")
                else:
                    # Execute sync step and wait for completion while async tasks continue in background
                    # Add a small yield to allow async tasks to make progress
                    await asyncio.sleep(0)
                    await self._execute_step(step, db, bulk_cookies, bulk_accounts)
                    # Yield again after sync step completion to allow async tasks to continue
                    await asyncio.sleep(0)
                    logger.info(f"Completed sync step {step.id} for job {job.id}")
                    
            except Exception as e:
                logger.error(f"Error executing step {step.id}: {e}", exc_info=True)
                step.status = JobStatus.FAILED
                step.error_message = str(e)
                step.completed_at = datetime.now(timezone.utc)
                # Don't commit here - batch commits for better performance
        
        # Batch commit for all sequential steps
        db.commit()
        
        # Update job progress once after all sequential steps are processed
        if steps:
            await self._update_job_progress(steps[0].job_id, db)
        
        # Wait for any remaining async tasks to complete
        if async_tasks:
            logger.info(f"Waiting for {len(async_tasks)} remaining async tasks to complete for job {job.id}")
            await asyncio.gather(*async_tasks, return_exceptions=True)
            logger.info(f"All async tasks completed for job {job.id}")
            
            # Remove completed async tasks from tracking
            for task in async_tasks:
                self._remove_running_step_task(job.id, task)

    async def _execute_steps_parallel(self, steps: List[JobStep], db: Session, bulk_cookies: Optional[Dict[int, Dict[str, Any]]] = None, bulk_accounts: Optional[Dict[int, Account]] = None):
        """Execute multiple steps in parallel"""
        # Create tasks for all steps - each gets its own database session
        tasks = []
        for step in steps:
            # Initialize step progress immediately for parallel steps so it shows up in API
            if step.action_type in ["delay", "collect_async_tasks"]:
                # Delay and collect_async_tasks steps have 0 accounts
                step.total_accounts = 0
                step.processed_accounts = 0
                step.successful_accounts = 0
                step.failed_accounts = 0
                self._init_step_progress(step.id, 0)
                logger.info(f"Initialized parallel {step.action_type} step {step.id} progress: total_accounts=0")
            else:
                # For other steps, get account count and initialize progress
                account_ids = json.loads(step.account_ids) if step.account_ids else []
                step.total_accounts = len(account_ids)
                step.processed_accounts = 0
                step.successful_accounts = 0
                step.failed_accounts = 0
                self._init_step_progress(step.id, step.total_accounts)
                logger.info(f"Initialized parallel step {step.id} progress: total_accounts={step.total_accounts}")
            
            # Commit progress initialization immediately so it's visible in API
            db.commit()
            
            task = asyncio.create_task(self._execute_step_safe(step, None, bulk_cookies, bulk_accounts))
            tasks.append(task)
            # Track the task for cancellation
            self._add_running_step_task(step.job_id, task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Remove completed tasks from tracking
        for task in tasks:
            self._remove_running_step_task(steps[0].job_id, task)
        
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
            # Re-query the step object to get a fresh copy attached to our own session
            step_id = step.id
            step = db.query(JobStep).filter(JobStep.id == step_id).first()
            if not step:
                logger.error(f"Step {step_id} not found in new database session")
                return
        
        try:
            await self._execute_step(step, db, bulk_cookies, bulk_accounts)
            # Commit changes for async steps to ensure progress updates are persisted
            if own_db:
                db.commit()
                # Update job progress for async steps
                await self._update_job_progress(step.job_id, db)
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}", exc_info=True)
            step.status = JobStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now(timezone.utc)
            
            # Commit failure status for async steps
            if own_db:
                db.commit()
                # Update job progress for failed async steps
                await self._update_job_progress(step.job_id, db)
            
            # Re-raise to be caught by gather()
            raise
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
                
                # Calculate completion time if both start and end times are available
                completion_time_seconds = None
                if step.started_at and step.completed_at:
                    completion_time_seconds = (step.completed_at - step.started_at).total_seconds()
                
                step_response = JobStepResponse(
                    id=step.id,
                    step_order=step.step_order,
                    action_type=step.action_type,
                    account_count=len(account_ids),
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
                    completed_at=step.completed_at,
                    completion_time_seconds=completion_time_seconds,
                    total_accounts=step.total_accounts,
                    processed_accounts=step.processed_accounts,
                    successful_accounts=step.successful_accounts,
                    failed_accounts=step.failed_accounts
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
