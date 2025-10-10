"""
Script to automate market selloff process:
1. Log in with a main account (not in database)
2. For each database account:
   - Get account's armory and calculate selloff value
   - Main account creates marketplace listing for 88% of that account's selloff value
   - Database account sells all their weapons
   - Database account buys the listing that was just created for them
   - Database account purchases armory items based on their preferences
"""

import asyncio
import aiohttp
import sys
import os
from getpass import getpass
from typing import Dict, Any, Optional

# Add parent directory to path so we can import from api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.rocurlgenerator import ROCDecryptUrlGenerator


class MainAccount:
    """Manages the main account session (not in database) - creates marketplace listing"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self.url_generator = ROCDecryptUrlGenerator()
        self.logged_in = False
    
    async def initialize(self):
        """Initialize the session"""
        self.session = aiohttp.ClientSession()
        return True
    
    async def login(self) -> bool:
        """Log in to ROC"""
        try:
            login_url = self.url_generator.login()
            
            # First GET to get the page
            async with self.session.get(login_url) as response:
                if response.status != 200:
                    print(f"Failed to load login page: {response.status}")
                    return False
            
            # POST login credentials
            form_data = {
                "email": self.username,
                "password": self.password,
                "submit": ""
            }
            
            async with self.session.post(login_url, data=form_data) as response:
                if response.status != 200:
                    print(f"Login failed with status: {response.status}")
                    return False
                
                page_text = await response.text()
                
                # Check if login was successful
                if "Login failed" in page_text or "login" in response.url.path.lower():
                    print("Login failed: Invalid credentials")
                    return False
                
                self.logged_in = True
                print(f"✓ Successfully logged in as {self.username}")
                return True
                
        except Exception as e:
            print(f"Error during login: {e}")
            return False
    
    async def create_market_listing(self, gold_amount: int, price_credits: int) -> Optional[str]:
        """Create a market listing (dummy implementation for now)"""

        url = self.url_generator.market_postnew()
        payload = {
            "do": "it",
            "sell": "2",
            "sell_amount": price_credits,
            "buy": "1",
            "buy_amount": gold_amount,
            "click": "Post"
        }
        async with self.session.post(url, data=payload) as response:
            if response.status != 200:
                print(f"Failed to create market listing: {response.status}")
                return None
            await response.text()
            
            return  response.url.query.get("id", None)

    
    async def cleanup(self):
        """Clean up session"""
        if self.session:
            await self.session.close()


async def get_accounts_page(api_base_url: str, page: int, per_page: int) -> Dict[str, Any]:
    """Get a page of accounts from the API"""
    async with aiohttp.ClientSession() as session:
        url = f"{api_base_url}/api/v1/accounts?page={page}&per_page={per_page}"
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get accounts: {response.status}")
            return await response.json()


async def get_armory_data(api_base_url: str, account_id: int) -> Dict[str, Any]:
    """Get armory data for an account via API"""
    async with aiohttp.ClientSession() as session:
        url = f"{api_base_url}/api/v1/actions/account/{account_id}/armory"
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get armory data: {response.status}")
            return await response.json()


def calculate_selloff_value(armory_data: Dict[str, Any]) -> int:
    total_value = 0
    
    # Get user's weapons from armory data
    user_weapons = armory_data.get('weapons', [])
    
    for user_weapon in user_weapons:
        weapon_id = user_weapon.get('id')
        quantity = user_weapon.get('owned_count', 0)
        
        if quantity <= 0:
            continue
        
        # Weapons at full strength sell for 70% of their purchase cost
        weapon_cost = user_weapon.get('cost', 0)
        if weapon_cost > 0:
            selloff_per_weapon = user_weapon.get('sell_value', 0)
            total_value += selloff_per_weapon * quantity
    
    return total_value


async def sell_all_weapons_via_api(api_base_url: str, account_id: int, armory_data: Dict[str, Any]) -> bool:
    """Sell all weapons on an account via API"""
    try:
        user_weapons = armory_data.get('weapons', [])
        
        if not user_weapons:
            print(f"  ! No weapons to sell")
            return True
        
        # Build sell_items dict
        sell_items = {}
        for user_weapon in user_weapons:
            weapon_id = str(user_weapon.get('id'))
            quantity = user_weapon.get('owned_count', 0)
            
            if quantity > 0:
                sell_items[weapon_id] = quantity
        
        if not sell_items:
            print(f"  ! No weapons to sell")
            return True
        
        # Call armory-purchase API to sell
        async with aiohttp.ClientSession() as session:
            url = f"{api_base_url}/api/v1/actions/armory-purchase"
            payload = {
                "acting_user": {
                    "id_type": "id",
                    "id": str(account_id)
                },
                "sell_items": sell_items,
                "max_retries": 0
            }
            
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    result = await response.json()
                    print(f"  ✗ Failed to sell weapons: {result}")
                    return False
                
                result = await response.json()
                if result.get('success'):
                    summary = result.get('data', {})
                    gold_gained = summary.get('gold_change', 0)
                    print(f"  ✓ Sold for {gold_gained} gold")
                    return True
                else:
                    print(f"  ✗ Failed to sell weapons: {result.get('error')}")
                    return False
                    
    except Exception as e:
        print(f"  ✗ Error selling weapons: {e}")
        return False


async def buy_market_listing_via_api(api_base_url: str, account_id: int, listing_id: str) -> bool:
    """Have an account buy a market listing via API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{api_base_url}/api/v1/actions/market-purchase"
            payload = {
                "acting_user": {
                    "id_type": "id",
                    "id": str(account_id)
                },
                "listing_id": listing_id,
                "max_retries": 0
            }
            
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    result = await response.json()
                    print(f"  ✗ Failed to purchase listing: {result}")
                    return False
                
                result = await response.json()
                if result.get('success'):
                    print(f"  ✓ Successfully purchased listing")
                    return True
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"  ✗ Failed to purchase listing: {error}")
                    return False
                    
    except Exception as e:
        print(f"  ✗ Error purchasing listing: {e}")
        return False


async def purchase_armory_by_preferences_via_api(api_base_url: str, account_id: int) -> bool:
    """Have an account purchase armory items based on their preferences via API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{api_base_url}/api/v1/actions/armory-purchase-by-preferences"
            payload = {
                "acting_user": {
                    "id_type": "id",
                    "id": str(account_id)
                },
                "max_retries": 0
            }
            
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    result = await response.json()
                    print(f"  ✗ Failed to purchase armory by preferences: {result}")
                    return False
                
                result = await response.json()
                # if result.get('success'):
                #     summary = result.get('summary', {})
                #     weapons_purchased = summary.get('total_weapons_purchased', 0)
                #     gold_spent = summary.get('total_gold_spent', 0)
                #     print(f"  ✓ Purchased {weapons_purchased} weapons for {gold_spent} gold")
                #     return True
                # else:
                #     error = result.get('error', 'Unknown error')
                #     print(f"  ✗ Failed to purchase armory by preferences: {error}")
                #     return False
                    
    except Exception as e:
        print(f"  ✗ Error purchasing armory by preferences: {e}")
        return False


async def process_account(main_account: MainAccount, api_base_url: str, account: Dict[str, Any], min_selloff_value: int) -> bool:
    """Process a single account - create listing, sell weapons, and buy listing"""
    account_id = account['id']
    username = account['username']
    
    print(f"\nProcessing account: {username} (ID: {account_id})")
    
    try:
        # Step 1: Get armory data
        print(f"  → Getting armory data...")
        armory_data = await get_armory_data(api_base_url, account_id)
        
        # Step 2: Calculate selloff value
        selloff_value = calculate_selloff_value(armory_data)
        # format with commas
        print(f"  → Selloff value: {"{:,}".format(selloff_value)} gold")
        
        if selloff_value < min_selloff_value:
            print(f"  ! Selloff value is less than {"{:,}".format(min_selloff_value)} gold, skipping")
            return True
        
        if selloff_value == 0:
            print(f"  ! No weapons to sell, skipping")
            return True
        
        # Step 3: Calculate listing amount (89% of selloff value)
        listing_amount = int(selloff_value * 0.89)
        print(f"  → Listing amount (89%): {listing_amount} gold for 100 credits")
        
        # Step 4: Main account creates listing for this specific account
        print(f"  → Main account creating listing...")
        listing_id = await main_account.create_market_listing(listing_amount, 100)
        
        print(f"  ✓ Created listing: {listing_id}")
        
        if not listing_id or not int(listing_id):
            print(f"  ✗ Failed to create listing")
            return False
        
        
        
        # Step 5: Sell all weapons on this account
        print(f"  → Selling all weapons...")
        if not await sell_all_weapons_via_api(api_base_url, account_id, armory_data):
           print(f"  ✗ Failed to sell weapons")
            # Continue anyway to try to buy listing
        
        # Step 6: This account buys the listing that was just created for them
        print(f"  → Purchasing listing {listing_id}...")
        if not await buy_market_listing_via_api(api_base_url, account_id, listing_id):
            print(f"  ✗ Failed to purchase listing")
            return False
        
        # Step 7: Purchase armory items based on preferences
        print(f"  → Purchasing armory items by preferences...")
        await purchase_armory_by_preferences_via_api(api_base_url, account_id)
        # Don't fail the whole process if armory purchase fails
        
        print(f"✓ Successfully processed {username}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing account {username}: {e}")
        return False


async def main():
    """Main entry point"""
    print("=" * 60)
    print("Market Selloff Automation Script")
    print("=" * 60)
    
    # Get main account credentials
    print("\nEnter main account credentials (creates marketplace listings):")
    main_username = input("Username: ")
    main_password = getpass("Password: ")
    
    # Get API base URL
    api_base_url = input("\nAPI base URL (default: http://localhost:8000): ").strip()
    if not api_base_url:
        api_base_url = "http://localhost:8000"
    
    # Remove trailing slash
    api_base_url = api_base_url.rstrip('/')
    
    # Get pagination settings
    try:
        per_page = int(input("Accounts per page (default: 50): ") or "50")
        start_page = int(input("Start from page (default: 1): ") or "1")
        max_pages = input("Max pages to process (default: all): ").strip()
        max_pages = int(max_pages) if max_pages else None
        min_selloff_value = int(input("Minimum selloff value (default: 1B): ") or "1_000_000_000")
    except ValueError:
        print("Invalid input, using defaults")
        per_page = 50
        start_page = 1
        max_pages = None
    
    # Initialize main account
    print(f"\nInitializing main account: {main_username}")
    main_account = MainAccount(main_username, main_password)
    
    try:
        await main_account.initialize()
        
        # Log in
        if not await main_account.login():
            print("Failed to log in main account. Exiting.")
            return
        
        # Process accounts
        print("\n" + "=" * 60)
        print("Processing database accounts")
        print("=" * 60)
        print(f"For each account:")
        print(f"  1. Get armory and calculate selloff value")
        print(f"  2. Main account creates listing (89% of selloff)")
        print(f"  3. Account sells all weapons")
        print(f"  4. Account buys the listing")
        print(f"  5. Account purchases armory by preferences")
        print(f"\nStarting to process accounts (page {start_page}, {per_page} per page)...")
        print("-" * 60)
        
        current_page = start_page
        processed_count = 0
        success_count = 0
        pages_processed = 0
        total_gold_consolidated = 0
        total_listings_created = 0
        
        while True:
            # Check if we've hit max pages
            if max_pages and pages_processed >= max_pages:
                print(f"\nReached max pages limit ({max_pages})")
                break
            
            # Get accounts page
            try:
                accounts_data = await get_accounts_page(api_base_url, current_page, per_page)
            except Exception as e:
                print(f"\nError getting accounts page {current_page}: {e}")
                break
            
            accounts = accounts_data.get('data', [])
            pagination = accounts_data.get('pagination', {})
            
            if not accounts:
                print(f"\nNo more accounts to process (page {current_page})")
                break
            
            print(f"\n--- Page {current_page} ({len(accounts)} accounts) ---")
            
            # Process each account
            for account in accounts:
                processed_count += 1
                if await process_account(main_account, api_base_url, account, min_selloff_value):
                    success_count += 1
                    total_listings_created += 1
            
            pages_processed += 1
            
            # Check if there are more pages
            if not pagination.get('has_next', False):
                print(f"\nReached last page")
                break
            
            current_page += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Main account: {main_username}")
        print(f"\nDatabase accounts processed: {processed_count}")
        print(f"Successful: {success_count}")
        print(f"Failed: {processed_count - success_count}")
        print(f"Listings created: {total_listings_created}")
        print(f"Pages processed: {pages_processed}")
        
    finally:
        await main_account.cleanup()
        print("\nCleaned up main account session")


if __name__ == "__main__":
    asyncio.run(main())

