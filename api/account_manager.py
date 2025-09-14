"""
Account Manager for handling multiple ROC accounts
"""

import asyncio
from fileinput import filename
import os
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
import secrets

import aiohttp
from sqlalchemy.orm import Session
from api.captcha import Captcha, CaptchaSolver
from api.database import get_db, SessionLocal
from api.models import Account, AccountLog, AccountAction, AccountMetadata, UserCookies

from api.rocurlgenerator import ROCDecryptUrlGenerator

logger = logging.getLogger(__name__)

class ROCAccountManager:
    """Manages a single ROC account session"""
    def __init__(self, account: Account):
        self.account = account
        self.last_metadata_update = None
        self._metadata_cache: Optional[AccountMetadata] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.url_generator = ROCDecryptUrlGenerator()
        self._is_logged_in = False
        self.captcha_solver = CaptchaSolver(solver_url="http://localhost:8000/api/v1/solve", report_url="http://localhost:8000/api/v1/feedback")

    @property
    def is_logged_in(self) -> bool:
        """Check if the account is logged in"""
        return self._is_logged_in and self.session is not None

    async def __was_captcha_correct(self, responsetext: str) -> bool:
        """Check if the captcha was correct"""
        return responsetext.find('<td colspan="2" class="error">Wrong number</td>') == -1
    
    async def _get_captcha(self, page_text: str) -> Captcha:
        """Extract captcha from response"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            page_text
            soup = BeautifulSoup(page_text, 'html.parser')

            # Find captcha image
            captcha_img = soup.find('img', {'id': 'captcha_image'})
            if not captcha_img:
                logger.warning("No captcha image found with id 'captcha_image'")
                return None
                
            captcha_url = captcha_img.get('src')
            if not captcha_url:
                logger.warning("No CAPTCHA URL found in image src")
                return None
            
            # TODO: Setup appsettings so we can pass in the base url
            base_url = "https://ruinsofchaos.com"
            captcha_url = urljoin(base_url, captcha_url)
            
            hash_value = captcha_url.split('hash=')[1] if 'hash=' in captcha_url else 'unknown'
            if hash_value == 'unknown':
                logger.warning("Could not extract captcha hash from URL")
                return None
            
            # make request to download the captcha image
            async with self.session.get(captcha_url) as img_response:
                if img_response.status == 200:
                    img_data = await img_response.read()
                    return Captcha(hash=hash_value, img=img_data)
                else:
                    logger.warning(f"Failed to download captcha image: {img_response.status}")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to get captcha: {e}")
            return None
    
    async def initialize(self) -> bool:
        """Initialize the account login"""
        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Load cookies from UserCookies table
            db = SessionLocal()
            try:
                user_cookies = db.query(UserCookies).filter(
                    UserCookies.account_id == self.account.id
                ).first()
                
                if user_cookies:
                    cookies = json.loads(user_cookies.cookies)
                    # Set cookies in the session
                    self.session.cookie_jar.update_cookies(cookies)
                    logger.info(f"Loaded {len(cookies)} cookies for account {self.account.username}: {list(cookies.keys())}")
                else:
                    logger.info(f"No cookies found for account {self.account.username}")
            finally:
                db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize account {self.account.username}: {e}")
            return False

    async def __save_error(self, filename: str, error: str):
        error_folder = "errors"
        if not os.path.exists(error_folder):
            os.makedirs(error_folder)
        with open(os.path.join(error_folder, filename), "w") as f:
            f.write(error)

    async def __check_logged_in(self, page_text: str) -> bool:
        """Check if the account is logged in"""
        return page_text.find('placeholder="email@address.com') == -1
    
    async def login_if_needed(self, current_page: str | None = None) -> bool:
        """Login if the account is not logged in"""
        if current_page is None:
            async with self.session.get(self.url_generator.home()) as response:
                page = response.text()
                if not await self.__check_logged_in(page):
                    return await self.login()
                self._is_logged_in = True
                return True
        else:
            if not await self.__check_logged_in(current_page):
                return await self.login()
            self._is_logged_in = True
            return True
    
    async def login(self) -> bool:
        """Login to the account"""
        async with self.session.post(self.url_generator.login(), data={
            'email': self.account.email,
            'password': self.account.password
        }) as response:
            is_logged_in = await self.__check_logged_in(response)

            if is_logged_in:
                # Save cookies to database
                db = SessionLocal()
                try:
                    # get domain from response.url
                    domain = response.url.origin()
                    cookies = self.session.cookie_jar.filter_cookies(domain.scheme + "://" + domain.host)
                    cookie_data = {}
                    for key, morsel in cookies.items():
                        cookie_data[key] = morsel.value
                    
                    # Check if cookies already exist for this account
                    existing_cookies = db.query(UserCookies).filter(
                        UserCookies.account_id == self.account.id
                    ).first()
                    
                    if existing_cookies:
                        # Update existing cookies
                        existing_cookies.cookies = json.dumps(cookie_data)
                    else:
                        # Create new cookies
                        user_cookies = UserCookies(
                            account_id=self.account.id,
                            cookies=json.dumps(cookie_data)
                        )
                        db.add(user_cookies)
                    
                    db.commit()
                    logger.info(f"Saved {len(cookie_data)} cookies for account {self.account.username}: {list(cookie_data.keys())}")
                except Exception as e:
                    logger.error(f"Failed to save cookies for account {self.account.username}: {e}")
                    db.rollback()
                finally:
                    db.close()
                
                self._is_logged_in = True
                return True
            return is_logged_in
        
    async def get_metadata(self) -> Optional[AccountMetadata]:
        """Get current account metadata from ROC website"""
        try:
            metadata_url = self.url_generator.metadata()
            async with self.session.get(metadata_url) as response:
                if response.status != 200:
                    filename = f"{self.account.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "error": "Failed to load metadata"}
                page_text = await response.text()
            
            if not await self.__check_logged_in(page_text):
                self.login();
            
            async with self.session.get(metadata_url) as response:
                if response.status != 200:
                    filename = f"{self.account.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "error": "Failed to load metadata"}
                page_text = await response.text()

            soup = BeautifulSoup(page_text, 'html.parser')
            rank = soup.find('new', {'id': 's_rank'}).text
            turns = soup.find('new', {'id': 's_turns'}).text
            next_turn = soup.find('new', {'id': 's_next'}).text
            gold = soup.find('new', {'id': 's_gold'}).text
            last_hit = soup.find('new', {'id': 's_hit'}).text
            last_sabbed = soup.find('new', {'id': 's_sabbed'}).text
            mail = soup.find('new', {'id': 's_mail'}).text
            credits = soup.find('new', {'id': 's_credits'}).text
            username = soup.find('new', {'id': 's_username'}).text
            lastclicked = soup.find('new', {'id': 's_lastclicked'}).text
            saving = soup.find('saving', {'status': '1'}).text
            credits = soup.find('new', {'id': 'credits'}).text
            gets = soup.find('new', {'id': 'gets'}).text
            credits_given = soup.find('new', {'id': 't_gives'}).text
            credits_received = soup.find('new', {'id': 't_gets'}).text
            userid = soup.find('new', {'id': 'userid'}).text
            allianceid = soup.find('new', {'id': 'allianceid'}).text
            servertime = soup.find('new', {'id': 'servertime'}).text
        
            metadata = AccountMetadata(
                gold=gold,
                rank=rank,
                turns=turns,
                next_turn=next_turn,
                last_hit=last_hit,
                last_sabbed=last_sabbed,
                mail=mail,
                credits=credits,
                username=username,
                lastclicked=lastclicked,
                saving=saving,
                gets=gets,
                credits_given=credits_given,
                credits_received=credits_received,
                userid=userid,
                allianceid=allianceid,
                servertime=servertime
            )
            
            self._metadata_cache = metadata
            self.last_metadata_update = datetime.now()
            return { "success": True, "data": metadata }
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {self.account.username}: {e}")
            return None
    
    async def attack(self, target_id: str) -> Dict[str, Any]:
        """Attack another user"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement attack logic
            # This is a placeholder
            return {"success": True, "message": f"Attacked user {target_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def sabotage(self, target_id: str) -> Dict[str, Any]:
        """Sabotage another user"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement sabotage logic
            return {"success": True, "message": f"Sabotaged user {target_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def spy(self, target_id: str) -> Dict[str, Any]:
        """Spy on another user"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement spy logic
            return {"success": True, "message": f"Spied on user {target_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def become_officer(self, target_id: str) -> Dict[str, Any]:
        """Become an officer of another user"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement become officer logic
            return {"success": True, "message": f"Became officer of user {target_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_credits(self, target_id: str, amount: int) -> Dict[str, Any]:
        """Send credits to another user"""            
        try:
            credits_url = self.url_generator.send_credits(target_id)
            send_url = self.url_generator.send_credits()
            
            async with self.session.get(credits_url) as response:
                if response.status != 200:
                    return {"success": False, "error": "Failed to load credits page"}
                page_text = await response.text()
                
            login_was_needed = not await self.__check_logged_in(page_text=page_text)
            logger.info(f"Login was needed: {login_was_needed}")
            
            if not await self.login_if_needed(page_text):
                return {"success": False, "error": "Login failed"}
            
            # If login was needed, we need to make a fresh request to the credits page
            # because the current response is from the login page
            if login_was_needed:
                async with self.session.get(credits_url) as fresh_response:
                    if fresh_response.status != 200:
                        return {"success": False, "error": "Failed to load credits page after login"}
                    
                    page_text = await fresh_response.text()

            captcha = await self._get_captcha(page_text)
            if not captcha:
                return {"success": False, "error": "Failed to get captcha"}
            
            # Solve captcha
            ans, _, request_id = await self.captcha_solver.solve(captcha)

            async with self.session.post(send_url, data={
                "to": target_id,
                "amount": amount,
                "comment": "",
                "captcha": captcha.hash,
                "num": ans,
                "coordinates[x]": getattr(captcha, 'x', 123),
                "coordinates[y]": getattr(captcha, 'y', 422)
            }) as submit_response:
                text = await submit_response.text()
                url = submit_response.url

            if "base.php" in url.path:
                return {"success": True, "message": f"Sent {amount} credits to user {target_id}"}
            elif not await self.__was_captcha_correct(text):
                await self.captcha_solver.report(captcha, request_id, True, ans)
                return {"success": False, "error": "Captcha was incorrect"}
            else:
                filename = f"{self.account.username}_{request_id}_send_credits.html"
                self.__save_error(filename=filename, text=text)
                return {"success": False, "error": "Unknown error... please check the error file " + filename}

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def recruit(self, soldier_type: str, count: int) -> Dict[str, Any]:
        """Recruit soldiers"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement recruit logic
            return {"success": True, "message": f"Recruited {count} {soldier_type} soldiers"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def purchase_armory(self, items: Dict[str, int]) -> Dict[str, Any]:
        """Purchase items from armory"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement armory purchase logic
            return {"success": True, "message": f"Purchased armory items: {items}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def purchase_training(self, training_type: str, count: int) -> Dict[str, Any]:
        """Purchase training"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement training purchase logic
            return {"success": True, "message": f"Purchased {count} {training_type} training"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def enable_credit_saving(self) -> Dict[str, Any]:
        """Enable credit saving"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement credit saving logic
            return {"success": True, "message": "Credit saving enabled"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def purchase_upgrade(self, upgrade_type: str) -> Dict[str, Any]:
        """Purchase upgrade"""
        if not self.is_logged_in:
            return {"success": False, "error": "Not logged in"}
            
        try:
            # Implement upgrade purchase logic
            return {"success": True, "message": f"Purchased {upgrade_type} upgrade"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources"""
        self._is_logged_in = False
        if self.session:
            await self.session.close()
            self.session = None

class AccountManager:
    """Manages multiple ROC accounts"""
    
    def __init__(self):
        self.accounts: Dict[int, ROCAccountManager] = {}
        self._lock = asyncio.Lock()
    
    async def load_existing_accounts(self) -> int:
        """Load all existing accounts from the database"""
        from api.database import SessionLocal
        
        db = SessionLocal()
        try:
            existing_accounts = db.query(Account).all()
            loaded_count = 0
            
            for account in existing_accounts:
                success = await self.add_account(account)
                if success:
                    loaded_count += 1
                    logger.info(f"Loaded existing account: {account.username} (ID: {account.id})")
                else:
                    logger.warning(f"Failed to load account: {account.username} (ID: {account.id})")
            
            logger.info(f"Loaded {loaded_count} existing accounts from database")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading existing accounts: {e}")
            return 0
        finally:
            db.close()
    
    async def add_account(self, account: Account) -> bool:
        """Add a new account to the manager"""
        async with self._lock:
            if account.id in self.accounts:
                return False
            
            # Create account manager (password is already stored unencrypted in account)
            roc_account = ROCAccountManager(account)
            success = await roc_account.initialize()
            
            if success:
                self.accounts[account.id] = roc_account
                return True
            return False
    
    async def remove_account(self, account_id: int) -> bool:
        """Remove an account from the manager"""
        async with self._lock:
            if account_id in self.accounts:
                await self.accounts[account_id].cleanup()
                del self.accounts[account_id]
                return True
            return False
    
    async def get_account(self, account_id: int) -> Optional[ROCAccountManager]:
        """Get account manager by ID"""
        return self.accounts.get(account_id)
    
    async def get_all_accounts(self) -> List[ROCAccountManager]:
        """Get all account managers"""
        return list(self.accounts.values())
    
    async def execute_action(self, account_id: int, action: str, **kwargs) -> Dict[str, Any]:
        """Execute an action on a specific account"""
        account = await self.get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}
        
        # Map action names to methods
        action_map = {
            "attack": account.attack,
            "sabotage": account.sabotage,
            "spy": account.spy,
            "become_officer": account.become_officer,
            "send_credits": account.send_credits,
            "recruit": account.recruit,
            "purchase_armory": account.purchase_armory,
            "purchase_training": account.purchase_training,
            "enable_credit_saving": account.enable_credit_saving,
            "purchase_upgrade": account.purchase_upgrade,
            "get_metadata": account.get_metadata,
        }
        
        if action not in action_map:
            return {"success": False, "error": f"Unknown action: {action}"}
        
        try:
            result = await action_map[action](**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing action {action} on account {account_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_bulk_action(self, account_ids: List[int], action: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute an action on multiple accounts"""
        tasks = []
        for account_id in account_ids:
            task = self.execute_action(account_id, action, **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "account_id": account_ids[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "account_id": account_ids[i],
                    **result
                })
        
        return processed_results
    
    async def cleanup(self):
        """Cleanup all accounts"""
        async with self._lock:
            for account in self.accounts.values():
                await account.cleanup()
            self.accounts.clear()
