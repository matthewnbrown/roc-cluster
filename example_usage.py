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
    
    async def bulk_action(self, account_ids: list, action_type: str, **kwargs) -> Dict[str, Any]:
        """Execute bulk action on multiple accounts"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/actions/bulk",
            json={
                "account_ids": account_ids,
                "action_type": action_type,
                "parameters": kwargs
            }
        )
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
        
        # Bulk action example
        print(f"\n7. Attempting bulk training purchase on account {account_id}...")
        try:
            bulk_result = await client.bulk_action(
                [account_id],
                "purchase_training",
                training_type="defense_soldiers",
                count=20
            )
            print(f"✅ Bulk action result: {bulk_result}")
        except httpx.HTTPStatusError as e:
            print(f"⚠️  Bulk action failed: {e.response.text}")
        
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
