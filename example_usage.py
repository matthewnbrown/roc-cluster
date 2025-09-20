"""
Example usage of the ROC Cluster Management API

This script demonstrates how to interact with the API programmatically.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

class ROCAPIClient:
    """Client for interacting with the ROC Cluster Management API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def create_account(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Create a new ROC account"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/accounts/",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def list_accounts(self) -> Dict[str, Any]:
        """List all accounts"""
        response = await self.client.get(f"{self.base_url}/api/v1/accounts/")
        response.raise_for_status()
        return response.json()
    
    async def get_account_metadata(self, account_id: int) -> Dict[str, Any]:
        """Get account metadata"""
        response = await self.client.get(f"{self.base_url}/api/v1/accounts/{account_id}/metadata")
        response.raise_for_status()
        return response.json()
    
    async def attack_user(self, account_id: int, target_id: str) -> Dict[str, Any]:
        """Attack another user"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/actions/attack",
            json={
                "account_id": account_id,
                "target_id": target_id
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def recruit_soldiers(self, account_id: int, soldier_type: str, count: int) -> Dict[str, Any]:
        """Recruit soldiers"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/actions/recruit",
            json={
                "account_id": account_id,
                "soldier_type": soldier_type,
                "count": count
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def purchase_armory(self, account_id: int, items: Dict[str, int]) -> Dict[str, Any]:
        """Purchase items from armory"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/actions/armory-purchase",
            json={
                "account_id": account_id,
                "items": items
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def create_job(self, name: str, description: str, steps: list, parallel_execution: bool = False) -> Dict[str, Any]:
        """Create a new job with multiple steps
        
        Steps can contain:
        - account_ids: List of account IDs
        - cluster_ids: List of cluster IDs (will be expanded to individual accounts)
        - Both account_ids and cluster_ids in the same step (will be combined)
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/jobs/",
            json={
                "name": name,
                "description": description,
                "parallel_execution": parallel_execution,
                "steps": steps
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get job status"""
        response = await self.client.get(f"{self.base_url}/api/v1/jobs/{job_id}/status")
        response.raise_for_status()
        return response.json()
    
    async def cancel_job(self, job_id: int, reason: str = None) -> Dict[str, Any]:
        """Cancel a job"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/jobs/{job_id}/cancel",
            json={"reason": reason} if reason else {}
        )
        response.raise_for_status()
        return response.json()
    
    async def list_jobs(self, status: str = None, page: int = 1) -> Dict[str, Any]:
        """List jobs"""
        params = {"page": page, "per_page": 20}
        if status:
            params["status"] = status
        
        response = await self.client.get(f"{self.base_url}/api/v1/jobs/", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_valid_action_types(self) -> Dict[str, Any]:
        """Get list of valid action types for job steps"""
        response = await self.client.get(f"{self.base_url}/api/v1/jobs/valid-action-types")
        response.raise_for_status()
        return response.json()

async def main():
    """Example usage of the ROC API"""
    client = ROCAPIClient()
    
    try:
        print("🚀 ROC Cluster Management API Example")
        print("=" * 50)
        
        # Create a test account
        print("\n1. Creating a test account...")
        account = await client.create_account(
            username="test_player",
            email="test@example.com",
            password="securepassword123"
        )
        print(f"✅ Account created: {account['username']} (ID: {account['id']})")
        
        account_id = account['id']
        
        # List all accounts
        print("\n2. Listing all accounts...")
        accounts = await client.list_accounts()
        print(f"✅ Found {len(accounts)} accounts")
        for acc in accounts:
            print(f"   - {acc['username']} ({acc['email']})")
        
        # Get account metadata
        print(f"\n3. Getting metadata for account {account_id}...")
        try:
            metadata = await client.get_account_metadata(account_id)
            print(f"✅ Metadata retrieved: {json.dumps(metadata, indent=2)}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Could not retrieve metadata: {e.response.text}")
        
        # Example actions (these will fail without proper ROC website integration)
        print(f"\n4. Attempting to attack user 'enemy_player' with account {account_id}...")
        try:
            attack_result = await client.attack_user(account_id, "enemy_player")
            print(f"✅ Attack result: {attack_result}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Attack failed: {e.response.text}")
        
        # Recruit soldiers
        print(f"\n5. Attempting to recruit 10 attack soldiers with account {account_id}...")
        try:
            recruit_result = await client.recruit_soldiers(account_id, "attack_soldiers", 10)
            print(f"✅ Recruit result: {recruit_result}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Recruit failed: {e.response.text}")
        
        # Purchase armory items
        print(f"\n6. Attempting to purchase armory items with account {account_id}...")
        try:
            armory_result = await client.purchase_armory(account_id, {
                "dagger": 5,
                "shield": 3
            })
            print(f"✅ Armory purchase result: {armory_result}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Armory purchase failed: {e.response.text}")
        
        # Job creation example (replaces bulk actions)
        print(f"\n7. Creating a sequential job for training purchase on account {account_id}...")
        try:
            job_result = await client.create_job(
                name="Sequential Training Job",
                description="Purchase training for defense soldiers (sequential)",
                parallel_execution=False,  # Sequential execution
                steps=[{
                    "account_ids": [account_id],
                    "action_type": "purchase_training",
                    "parameters": {
                        "training_type": "defense_soldiers",
                        "count": 20
                    }
                }]
            )
            print(f"✅ Sequential job created: {job_result}")
            
            # Check job status
            job_id = job_result["id"]
            print(f"\n8. Checking sequential job {job_id} status...")
            status_result = await client.get_job_status(job_id)
            print(f"✅ Sequential job status: {status_result}")
            
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Sequential job creation failed: {e.response.text}")
        except Exception as e:
            print(f"⚠️  Sequential job creation failed: {str(e)}")
        
        # Cluster-based job example
        print(f"\n9. Creating a cluster-based job for recruiting across multiple accounts...")
        try:
            cluster_job_result = await client.create_job(
                name="Cluster Recruitment Job",
                description="Recruit soldiers across all accounts in cluster 1",
                parallel_execution=True,  # Parallel execution for speed
                steps=[
                    {
                        "cluster_ids": [1],  # Will expand to all accounts in cluster 1
                        "action_type": "recruit",
                        "parameters": {
                            "soldier_type": "infantry",
                            "count": 100
                        }
                    }
                ]
            )
            print(f"✅ Cluster job created: {cluster_job_result}")
            
            # Check cluster job status
            cluster_job_id = cluster_job_result["id"]
            print(f"\n10. Checking cluster job {cluster_job_id} status...")
            cluster_status_result = await client.get_job_status(cluster_job_id)
            print(f"✅ Cluster job status: {cluster_status_result}")
            
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Cluster job creation failed: {e.response.text}")
        except Exception as e:
            print(f"⚠️  Cluster job creation failed: {str(e)}")
        
        # Combined account_ids and cluster_ids job example
        print(f"\n11. Creating a combined job with both account_ids and cluster_ids in same step...")
        try:
            combined_job_result = await client.create_job(
                name="Combined Account/Cluster Job",
                description="Execute action on specific accounts AND all cluster members in one step",
                parallel_execution=True,
                steps=[
                    {
                        "account_ids": [account_id, account_id + 1],  # Specific accounts
                        "cluster_ids": [1],  # All accounts in cluster 1
                        "action_type": "recruit",
                        "parameters": {
                            "soldier_type": "cavalry",
                            "count": 50
                        }
                    }
                ]
            )
            print(f"✅ Combined job created: {combined_job_result}")
            
            # Check combined job status
            combined_job_id = combined_job_result["id"]
            print(f"\n12. Checking combined job {combined_job_id} status...")
            combined_status_result = await client.get_job_status(combined_job_id)
            print(f"✅ Combined job status: {combined_status_result}")
            
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Combined job creation failed: {e.response.text}")
        except Exception as e:
            print(f"⚠️  Combined job creation failed: {str(e)}")
        
        # Multiple clusters and accounts example
        print(f"\n13. Creating a multi-target job with multiple clusters and accounts...")
        try:
            multi_job_result = await client.create_job(
                name="Multi-Target Job",
                description="Execute action on multiple accounts and multiple clusters",
                parallel_execution=True,
                steps=[
                    {
                        "account_ids": [account_id],  # Specific account
                        "cluster_ids": [1, 2],  # Multiple clusters
                        "action_type": "purchase_training",
                        "parameters": {
                            "training_type": "defense_soldiers",
                            "count": 25
                        }
                    }
                ]
            )
            print(f"✅ Multi-target job created: {multi_job_result}")
            
            # Check multi-target job status
            multi_job_id = multi_job_result["id"]
            print(f"\n14. Checking multi-target job {multi_job_id} status...")
            multi_status_result = await client.get_job_status(multi_job_id)
            print(f"✅ Multi-target job status: {multi_status_result}")
            
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Multi-target job creation failed: {e.response.text}")
        except Exception as e:
            print(f"⚠️  Multi-target job creation failed: {str(e)}")
        
        # Async steps example
        print(f"\n15. Creating a job with async steps...")
        try:
            async_job_result = await client.create_job(
                name="Async Steps Demo Job",
                description="Demonstrates async step execution - some steps run in background",
                parallel_execution=False,  # Sequential execution with async steps
                steps=[
                    {
                        "account_ids": [account_id],
                        "action_type": "get_metadata",
                        "parameters": {},
                        "is_async": False  # Sync step - waits for completion
                    },
                    {
                        "account_ids": [account_id],
                        "action_type": "recruit",
                        "parameters": {},
                        "is_async": True  # Async step - launches without waiting
                    },
                    {
                        "account_ids": [account_id],
                        "action_type": "get_metadata",
                        "parameters": {},
                        "is_async": False  # Another sync step
                    },
                    {
                        "account_ids": [account_id],
                        "action_type": "purchase_training",
                        "parameters": {
                            "training_type": "defense_soldiers",
                            "count": 10
                        },
                        "is_async": True  # Another async step
                    }
                ]
            )
            print(f"✅ Async job created: {async_job_result}")
            
            # Wait a bit and check job status
            await asyncio.sleep(2)
            job_status = await client.get_job(async_job_result['id'], include_steps=True)
            print(f"📊 Job status after 2 seconds: {job_status['status']}")
            print(f"📊 Completed steps: {job_status['completed_steps']}/{job_status['total_steps']}")
            
            # Show which steps are async
            if job_status.get('steps'):
                print("📋 Step details:")
                for step in job_status['steps']:
                    async_indicator = "🔄 ASYNC" if step['is_async'] else "⏳ SYNC"
                    print(f"  Step {step['step_order']}: {step['action_type']} - {async_indicator} - Status: {step['status']}")
            
        except Exception as e:
            print(f"⚠️  Async job creation failed: {str(e)}")

        # Get valid action types example
        print(f"\n16. Getting valid action types...")
        try:
            valid_types = await client.get_valid_action_types()
            print(f"✅ Valid action types: {valid_types}")
        except Exception as e:
            print(f"⚠️  Failed to get valid action types: {str(e)}")
        
        print("\n🎉 Example completed successfully!")
        print("\nNote: Some actions may fail because they require actual ROC website integration.")
        print("The API structure is ready - you just need to implement the actual ROC website")
        print("interaction logic in the account_manager.py file.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
