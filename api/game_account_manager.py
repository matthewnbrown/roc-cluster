"""
Manages a single ROC account session
"""


from enum import Enum
import logging
import math
import os
import random
import asyncio

import traceback
from typing import Awaitable, Callable, List, Optional, Tuple
from urllib.parse import urljoin
import json
import aiohttp
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from typing import Dict, Any

from bs4 import BeautifulSoup
from sqlalchemy import false

from api.db_models import Account, UserCookies, ArmoryPreferences, ArmoryWeaponPreference, Weapon
from api.page_parsers.attack import parse_attack_page
from api.page_parsers.cardpage_parser import parse_cards_page
from api.page_parsers.common import get_clockbar_stats
from api.page_parsers.metadata_parser import parse_metadata_data
from api.page_parsers.spy_parser import parse_recon_data
from api.page_parsers.sab_parser import parse_sabotage_page
from api.page_parsers.armory_parser import parse_armory_data
from api.schemas import AccountMetadata, CaptchaSolutionItem
from api.captcha import Captcha, CaptchaSolver, CaptchaKeypadSelector
from api.database import SessionLocal
from api.rocurlgenerator import ROCDecryptUrlGenerator
from api.credit_logger import credit_logger
from api.captcha_feedback_service import captcha_feedback_service
from api.page_data_service import page_data_service
from api.preference_service import PreferenceService
from api.target_rate_limiter import roc_target_rate_limiter
from config import settings
from sqlalchemy.orm import joinedload


logger = logging.getLogger(__name__)

class PageSubmit(Enum):
    TRAINING = "Train+Soldiers"
    RECRUIT = "Recruit"
    ARMORY = "Sell/Buy+Weapons"
    ATTACK = "Attack"
    PROBE = "Probe"
    SPY = "Recon"
    SABOTAGE = "Sabotage"
    UPGRADE = ""
    CREDIT_SAVE = "Send+Credits",
    SEND_CARDS = "Send+Card"

class GameAccountManager:
    """Manages a single ROC account session"""

    def __init__(self, account: Account, max_retries: int = 0, use_page_data_service: bool = false):
        self.account = account
        self.session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self.url_generator = ROCDecryptUrlGenerator()
        self.max_retries = max_retries
        self.use_captcha = False
        
        if self.use_captcha:
            self.captcha_solver = CaptchaSolver(solver_url=settings.CAPTCHA_SOLVER_URL, report_url=settings.CAPTCHA_REPORT_URL, max_retries=max_retries)
        else:
            self.captcha_solver = None
            
        self.use_page_data_service = use_page_data_service

    def _is_target_based_action(self, action_name: str) -> bool:
        """Check if an action requires target rate limiting"""
        target_based_actions = {
            "attack",
            "sabotage", 
            "spy",
            "become_officer",
            "send_credits",
            "send_cards"
        }
        return action_name in target_based_actions

    async def _with_target_rate_limit(self, target_id: str, action_name: str, func):
        """
        Execute a function with target-based rate limiting for ROC API calls.
        
        Args:
            target_id: The target user ID
            action_name: Name of the action being performed
            func: Async function to execute
            
        Returns:
            Result of the function execution
        """
        if not self._is_target_based_action(action_name):
            # Not a target-based action, execute directly
            return await func()
        
        # Acquire rate limit lock for this target
        request_id = None
        try:
            request_id = await roc_target_rate_limiter.acquire_lock(target_id)
            logger.debug(f"Acquired ROC rate limit lock for target {target_id}, action {action_name}, request {request_id}")
            
            # Execute the actual action
            return await func()
            
        except asyncio.TimeoutError:
            logger.warning(f"Rate limit timeout for target {target_id}, action {action_name}")
            return {
                "success": False,
                "error": f"Rate limit exceeded for target {target_id}. Too many concurrent ROC API requests. Please try again later."
            }
        except Exception as e:
            logger.error(f"Error in rate-limited action for target {target_id}, action {action_name}: {e}")
            raise
        finally:
            # Always release the lock if we acquired it
            if request_id:
                try:
                    await roc_target_rate_limiter.release_lock(target_id, request_id)
                    logger.debug(f"Released ROC rate limit lock for target {target_id}, request {request_id}")
                except Exception as e:
                    logger.error(f"Error releasing ROC rate limit lock for target {target_id}, request {request_id}: {e}")

    def parse_roc_number(self, number: str) -> int:
        """Parse a ROC number"""
        return int(number.replace(',', ''))
    
    async def _push_page_to_queue(
        self, 
        page_content: str, 
        request_url: str = None,
        response_url: str = None,
        request_method: str = "GET",
        request_data: Dict[str, Any] = None,
        request_time: datetime = None
    ):
        """Push a page to the processing queue"""
        
        if not self.use_page_data_service:
            return
        try:
            await page_data_service.add_page_to_queue(
                account_id=self.account.id,
                page_content=page_content,
                request_url=str(request_url),
                response_url=str(response_url),
                request_method=request_method,
                request_data=request_data,
                request_time=request_time
            )
        except Exception as e:
            logger.error(f"Failed to push page to queue for account {self.account.username}: {e}", exc_info=True)

    def __roc_format_number(self, number: int) -> str:
        """Format a number in ROC format"""
        return f"{number:,}"
    
    def __was_captcha_correct(self, page_text: str, submit_url: str) -> bool:
        """Check if the captcha was correct"""
        
        if submit_url == self.url_generator.send_credits():
            return page_text.find('<td colspan="2" class="error">Wrong number</td>') == -1
        elif self.url_generator.spy() in submit_url \
             or self.url_generator.attack() in submit_url \
             or self.url_generator.sabotage() in submit_url:
            return page_text.find('>Wrong number<') == -1
        else:
            raise Exception("Unknown submit url")
        
    async def _get_captcha(self, page_text: str = None) -> Captcha:
        try:
            
            if page_text is None:
                async def _get_captcha_page(post_login = False):
                    async with self.session.get(self.url_generator.armory()) as response:
                        text = await response.text()
                       
                        if not self.__check_logged_in(text) and not post_login:
                            logger.info(f"{self.account.username} session expired, logging in")
                            await self.login()
                            return await _get_captcha_page(post_login=True)
                        return text
                    
                page_text = await _get_captcha_page()
                
                if page_text is None:
                    logger.warning("Failed to get home page")
                    raise Exception("Failed to get home page")
                
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
            
            base_url = self.url_generator.get_page_url("roc_home")
            captcha_url = urljoin(base_url, captcha_url)
            
            hash_value = captcha_url.split('hash=')[1] if 'hash=' in captcha_url else 'unknown'
            if hash_value == 'unknown':
                logger.warning("Could not extract captcha hash from URL")
                return None
            
            async with self.session.get(captcha_url) as img_response:
                if img_response.status == 200:
                    img_data = await img_response.read()
                    return Captcha(hash=hash_value, img=img_data)
                else:
                    logger.warning(f"Failed to download captcha image: {img_response.status}")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to get captcha: {e}", exc_info=True)
            return None
    
    async def submit_captca(self, url: str, data: Dict[str, Any], captcha: Captcha, page_name = 'roc_recruit') -> Tuple[aiohttp.ClientResponse, str]:
        """solves and submits a captcha

        Args:
            url (str): url to submit the captcha to
            data (Dict[str, Any]): data to submit the captcha with
            captcha (Captcha): captcha to solve
            page_name (str): name of the page

        Returns:
            aiohttp.Response: response from the captcha submission
        """
        keypad_selector = CaptchaKeypadSelector()
        
        try:
            # coords = keypad_selector.get_xy_static(captcha.ans, page_name)
            # ans, _, request_id = await self.captcha_solver.solve(captcha)
            # data["num"] = ans
            # data["coordinates[x]"] = coords[0]
            # data["coordinates[y]"] = coords[1]
            # data["captcha"] = captcha.hash
            # captcha.ans = ans
            request_id = ""
            return await self.session.post(url, data=data), request_id
        except Exception as e:
            logger.error(f"Failed to submit captcha: {e}", exc_info=True)
            raise e
    
    async def __submit_with_captcha(self, url: str, data: Dict[str, Any], page_name: PageSubmit) -> aiohttp.ClientResponse:
        """[Untested]Submits a form with a captcha"""
        captcha = await self._get_captcha()
        if not captcha:
            return None
        
        return await self.submit_captca(url, data, captcha, page_name)
    
    async def __retry_login_wrapper(self, func: Callable[[], Awaitable[aiohttp.ClientResponse]]) -> bool:
        """ Attempts a ROC action, if it fails due to login, it will retry the action after logging in"""

        result = await func()
        
        text = await result.text()
        if not self.__check_logged_in(text):
            await self.login()
            result = await func()
            text = await result.text()
            if not self.__check_logged_in(text):
                raise Exception("Failed to login")
        
        return result
    
    async def __get_page(self, url: str) -> aiohttp.ClientResponse:
        async with self.session.get(url) as response:
            pagetext = await response.read()
            await self._push_page_to_queue(pagetext, url, response.url, "GET", None, datetime.now(timezone.utc))
            return response
        
    
    async def __submit_page(self, url: str, data: Dict[str, Any], page_submit: PageSubmit) -> aiohttp.ClientResponse:
        """Submits a page"""
        if type(page_submit) != PageSubmit:
            raise Exception("Page submit must be a PageSubmit enum")
        if page_submit.value != "":
            data["submit"] = page_submit.value
        
        request_time = datetime.now(timezone.utc)
        if self.use_captcha: # [Untested]
            r = await self.__submit_with_captcha(url, data, page_submit)
            text = await r.text()
        
        async with self.session.post(url, data=data) as response:
            r = response
            text = await r.text()
            
        await self._push_page_to_queue(text, url, response.url, "POST", data, request_time)
        return r
    
    
    async def login(self) -> bool:
        """Login to the account"""
        async with self.session.post(self.url_generator.login(), data={
            'email': self.account.email,
            'password': self.account.password
        }) as response:
            page_text = await response.text()
            is_logged_in = self.__check_logged_in(page_text)

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
                    
                    # Upsert cookies - update existing or create new
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
                    logger.debug(f"Saved {len(cookie_data)} cookies for account {self.account.username}: {list(cookie_data.keys())}")
                except Exception as e:
                    logger.error(f"Failed to save cookies for account {self.account.username}: {e}", exc_info=True)
                    db.rollback()
                finally:
                    db.close()
                
                self._is_logged_in = True
                return True
            return is_logged_in
        
    ###############
    ### ACTIONS ###
    ###############
    
    async def get_metadata(self) -> Optional[AccountMetadata]:
        """Get current account metadata from ROC website"""
        try:
            metadata_url = self.url_generator.metadata()
            request_time = datetime.now(timezone.utc)
            async with self.session.get(metadata_url) as response:
                if response.status != 200:
                    filename = f"{self.account.username}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "errors": ["Failed to load metadata"]}
                page_text = await response.text()
            
            if not self.__check_logged_in(page_text):
                await self.login();
            
            async with self.session.get(metadata_url) as response:
                if response.status != 200:
                    filename = f"{self.account.username}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "errors": ["Failed to load metadata"]}
                page_text = await response.text()

            # Push page to queue for processing
            await self._push_page_to_queue(
                page_content=page_text,
                request_url=metadata_url,
                response_url=str(response.url),
                request_method="GET",
                request_time=request_time
            )
            
            metadata_data = parse_metadata_data(page_text)
        
            metadata = AccountMetadata(
                gold=metadata_data["gold"],
                rank=metadata_data["rank"],
                turns=metadata_data["turns"],
                # Using UTC time for consistency
                next_turn=metadata_data["next_turn"],
                last_hit=metadata_data["last_hit"],
                last_sabbed=metadata_data["last_sabbed"],
                mail=metadata_data["mail"],
                credits=metadata_data["credits"],
                username=metadata_data["username"],
                # last clicked is an roc_num, number of mins since last click
                lastclicked=metadata_data["lastclicked"],
                saving=metadata_data["saving"],
                gets=metadata_data["gets"],
                credits_given=metadata_data["credits_given"],
                credits_received=metadata_data["credits_received"],
                userid=metadata_data["userid"],
                allianceid=metadata_data["allianceid"],
                servertime=metadata_data["servertime"]
            )
            
            
            return { "success": True, "data": metadata }
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {self.account.username}: {e}", exc_info=True)
            return None
    
    async def attack(self, target_id: str, turns: int = -1) -> Dict[str, Any]:
        """Attack another user"""

        try:
            turns = int(turns)
        except ValueError:
            return {"success": False, "errors": ["Turn count must be an integer"]}

        if turns < 1 or turns > 12:
            return {"success": False, "errors": ["Turn count must be between 1 and 12"]}
    
        async def _attack_implementation():
            try:
                attack_url = self.url_generator.attack(target_id)
                
                payload = {
                    "defender_id": target_id,
                    "mission_type": "attack",
                    "attacks": turns
                }
                
                results = []
                
                async def _submit():                
                    return await self.__submit_page(attack_url, payload, PageSubmit.ATTACK)

                errors = []
                for i in range(self.max_retries+1):
                    result = await self.__retry_login_wrapper(_submit)
                
                    page_text = await result.text()
                    page_data = parse_attack_page(page_text)
                    if page_data["result"] == "ProtectionBuff":
                        return {"success": True, "protection_buff": 1, "retries": i}
                    elif page_data["result"] == "MaxedHits":
                        return {"success": True, "maxed_hits": 1, "retries": i}
                    elif page_data["result"] == "RunAway":
                        return {"success": True, "runs_away": 1, "retries": i}
                    elif page_data["result"] == "Win":
                        return {
                            "success": True,
                            "win": 1,
                            "gold_won": page_data["gold_won"],
                            "troops_killed": page_data["troops_killed"],
                            "troops_lost": page_data["troops_lost"],
                            "retries": i}
                    elif page_data["result"] == "Loss":
                        return {
                            "success": True,
                            "loss": 1,
                            "troops_killed": page_data["troops_killed"],
                            "troops_lost": page_data["troops_lost"],
                            "retries": i
                            }
                    
                    errors.append('Unknown error. Could not determine result')

                return {"success": False, "errors": errors}

            except Exception as e:
                logger.error(f"Error in attack for {self.account.username}: {e}", exc_info=True)
                return {"success": False, "errors": [str(e)]}

        # Execute with rate limiting
        return await self._with_target_rate_limit(target_id, "attack", _attack_implementation)
    
    async def sabotage(self, target_id: str, spy_count: int = 1, enemy_weapon: int = -1) -> Dict[str, Any]:
        """Sabotage another user
        
        Args:
            target_id: The ID of the user to sabotage
            spy_count: Number of spies to send (default: 1)
            enemy_weapon: Weapon ID to sabotage (default: -1)
            
        Returns:
            Dict containing success status and sabotage result or error message
        """

        
        if enemy_weapon is None or enemy_weapon == -1:
            return {"success": False, "errors": ["Enemy weapon must be specified"]}
        
        if spy_count is None or spy_count < 1 or spy_count > 25:
            return {"success": False, "errors": ["Spy count must be between 1 and 25"]}
        
        async def _sabotage_implementation():
            payload = {
                "defender_id": target_id,
                "mission_type": "sabotage",
                "sabspies": spy_count,
                "enemy_weapon": enemy_weapon
            }
            
            sabotage_url = self.url_generator.sabotage(target_id)
            
            async def _submit_sabotage():                
                return await self.__submit_page(sabotage_url, payload, PageSubmit.SABOTAGE)
            
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_sabotage)
                
                page_text = await result.text()
                
                sabotage_data = parse_sabotage_page(page_text)
                

                if sabotage_data["result"] == "max_sabbed":
                    return {
                        "success": True,
                        "maxed_sab_attempts": 1,
                        "retries": i
                    }
                elif sabotage_data["result"] == "defended":
                    return {
                        "success": True,
                        "sabotages_defended": 1,
                        "weapon_damage_cost": sabotage_data["weapon_damage_cost"],
                        "retries": i
                    }
                elif sabotage_data["result"] == "success":
                    return {
                        "success": True,
                        "weapon_damage_cost": sabotage_data["weapon_damage_cost"],
                        "damage_dealt": sabotage_data["damage_to_enemy"],
                        "weapon_count": sabotage_data["weapon_count"],
                        "retries": i
                    }
                
            return {"success": False, "errors": ["Failed to sabotage user, I guess?"], "retries": self.max_retries}

        # Execute with rate limiting
        return await self._with_target_rate_limit(target_id, "sabotage", _sabotage_implementation)
    
    async def spy(self, target_id: str, spy_count: int = 1 ) -> Dict[str, Any]:
        """Spy on another user
        
        Args:
            target_id: The ID of the user to spy on
            spy_count: Number of spies to send (1-25, default: 1)
            
        Returns:
            Dict containing success status and spy data or error message
        """
            
        if spy_count < 1 or spy_count > 25:
            return {"success": False, "errors": ["Spy count must be between 1 and 25"]}

        async def _spy_implementation():
            try:
                spy_url = self.url_generator.spy(target_id)
                
                payload = {
                    "defender_id": target_id,
                    "mission_type": "recon",
                    "reconspies": spy_count
                }
                
                results = []
                
                async def _submit_spy():                
                    return await self.__submit_page(spy_url, payload, PageSubmit.SPY)

                for i in range(self.max_retries+1):
                    result = await self.__retry_login_wrapper(_submit_spy)
                    page_text = await result.text()
                    if 'You cannot recon this person again today!' in page_text:
                        return {"success": True, "maxed_spy_attempts": 1, "retries": i}
                    
                    if 'As they approach, an alarm is cried out by enemy sentries' in page_text:
                        return {"success": True, "spies_caught": 1, "retries": i}
                    
                    if 'inteldetail' not in result.url.path:
                        return {"success": False, "errors": ["Unknown error. No captcha error, but not on intel url"]}
                    
                    _ = parse_recon_data(page_text)
                    return {"success": True, "spies_successful_data": 1, "retries": i}

                results_str = "\n".join([f"{i+1}. {result.get('error', 'Unknown error')}" for i, result in enumerate(results)])
                return {"success": False, "errors": [f"Failed to spy on user: {results_str}"]}

            except Exception as e:
                stack_trace = traceback.format_exc()
                return {"success": False, "errors": [str(e) + "\n" + stack_trace]}

        # Execute with rate limiting
        return await self._with_target_rate_limit(target_id, "spy", _spy_implementation)
    
    # not implemented
    async def become_officer(self, target_id: str) -> Dict[str, Any]:
        """Become an officer of another user"""
        async def _become_officer_implementation():
            try:
                # Implement become officer logic
                return {"success": True, "messages": [f"Became officer of user {target_id}"]}
            except Exception as e:
                logger.error(f"Error in become_officer for {self.account.username}: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        # Execute with rate limiting
        return await self._with_target_rate_limit(target_id, "become_officer", _become_officer_implementation)
    
    async def send_credits(self, target_id: str, amount: int, dry_run = False, cur_credits: int = -1) -> Dict[str, Any]:
        """Send credits to another user"""            
        # check if amount is 'all' or an int
        if str(amount).lower() == 'all':
            return await self.send_all_credits(target_id)
        
        try:
            amount = int(amount)
        except ValueError:
            return {"success": False, "errors": ["Invalid amount. Must be an integer or 'all'"]}
        
        if amount < 100:
            return {"success": False, "errors": ["Amount must be at least 100"]}

        async def _send_credits_implementation():
            try:
                # if cur_credits == -1:
                #     get_metadata = await self.get_metadata()
                #     if not get_metadata["success"]:
                #         return {"success": False, "error": "Failed to get metadata"}
                #     cur_credits = get_metadata["data"].credits
                
                send_url = self.url_generator.send_credits()
                
                payload = {
                    "to": target_id,
                    "amount": amount,
                    "comment": "",
                    "submit": "Send+Credits"
                }
                
                # Ceiling of 0.9 * amount
                expected_sent_credits = math.ceil(0.9 * amount)
                jackpot_credits = amount - expected_sent_credits
                    
                async def _submit_credits():
                    if dry_run:
                        return {"success": True, "messages": [f"{self.account.username} would have sent {self.__roc_format_number(amount)} credits to user {target_id}"]}

                    return await self.__submit_page(send_url, payload, PageSubmit.CREDIT_SAVE)
                
                errors = []
                for i in range(self.max_retries+1):
                    result = await self.__retry_login_wrapper(_submit_credits)
                    
                    page_text = await result.text()
                    path = result.url.path
                    if path not in self.url_generator.base():
                        errors.append("Unknown error. No captcha error, but not on base url. " + path.url)
                    if f'You sent {self.__roc_format_number(expected_sent_credits)} credits to' not in page_text:
                        errors.append("On base url, but missing expected sent credits message.")                    
                    else:
                        return {"success": True, "credits_sent": expected_sent_credits, "jackpot_credits": jackpot_credits, "retries": i}

                return {"success": False, "error": "Failed to send credits:\n" + "\n".join(errors)}

            except Exception as e:
                logger.error(f"Error in send_credits for {self.account.username}: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        # Execute with rate limiting
        return await self._with_target_rate_limit(target_id, "send_credits", _send_credits_implementation) 
    
    async def send_all_credits(self, target_id: str) -> Dict[str, Any]:
        get_metadata = await self.get_metadata()
        if not get_metadata["success"]:
            return {"success": False, "error": "Failed to get metadata"}
        
        credits = int(get_metadata["data"].credits)

        if credits == 0:
            return {"success": False, "error": "No credits to send"}
        
        return await self.send_credits(target_id, str(credits), cur_credits=credits)
    
    async def recruit(self) -> Dict[str, Any]:
        """Recruit soldiers"""
        
        try:
            recruit_url = self.url_generator.recruit()
            
            async def _submit_upgrade():                
                return await self.__submit_page(recruit_url, {}, PageSubmit.RECRUIT)
            
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_upgrade)
                
                page_text = await result.text()
                
                # TODO: Check if the recruit was successful (recruit button exists?)
                
                return {"success": True, "messages": ["Successfully recruited"]}
            
        except Exception as e:
            logger.error(f"Error recruiting for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # not implemented
    async def purchase_armory(self, items: Dict[str, int]) -> Dict[str, Any]:
        """Purchase items from armory"""
       
        try:
            # Implement armory purchase logic
            return {"success": True, "messages": [f"Purchased armory items: {items}"]}
        except Exception as e:
            logger.error(f"Error in purchase_armory for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def purchase_armory_by_preferences(self, preference_id = -1) -> Dict[str, Any]:
        """Purchase armory items based on user preferences"""
        #TODO: Login check, preference_id check get default if -1
        try:
            # Get user preferences from database with relationships loaded
            

            db = SessionLocal()
            try:
                preferences = db.query(ArmoryPreferences).options(
                    joinedload(ArmoryPreferences.weapon_preferences).joinedload(ArmoryWeaponPreference.weapon)
                ).filter(
                    ArmoryPreferences.account_id == self.account.id
                ).first()
                
                if not preferences:
                    return {"success": False, "error": "No armory preferences found for this account"}
                
                logger.debug(f"Found {len(preferences.weapon_preferences)} weapon preferences for account {self.account.id}")
                
                # Load armory page
                armory_url = self.url_generator.armory()
                
                
                armory_resp = await self.__get_page(armory_url)
                armory_text = await armory_resp.text()
                
                stats = get_clockbar_stats(armory_text)
                name = stats.get("name")
                current_gold = stats.get("gold", -1)
                if not name or current_gold < 0:
                    return {"success": False, "error": "Failed to get current user gold"}
                
                
                # Parse armory data
                armory_data = parse_armory_data(armory_text)
                
                # Log available weapons in armory
                logger.debug(f"Available weapons in armory: {[w.get('id') for w in armory_data.get('weapons', [])]}")
                
                # Calculate weapon portions based on preferences and available gold
                weapon_purchases = self._calculate_weapon_purchases(
                    armory_data, preferences, current_gold, db
                )
                
                if not weapon_purchases:
                    return {"success": True, "messages": ["No weapons to purchase based on current gold and preferences"]}
                
                # Submit purchase form
                purchase_result = await self._submit_armory_purchase(weapon_purchases)
                
                purchase_result_text = await purchase_result.text()
                purchase_result_data = parse_armory_data(purchase_result_text)
                
                if armory_data["current_user"]["gold"] <= purchase_result_data["current_user"]["gold"]:
                    return {"success": False, "error": "Failed to purchase armory items"}
                
                else:
                    # Calculate summary data
                    total_weapons_purchased = sum(weapon_purchases.values())
                    total_gold_spent = armory_data["current_user"]["gold"] - purchase_result_data["current_user"]["gold"]
                    
                    # Create detailed weapon breakdown
                    weapon_breakdown = []
                    for weapon_id, quantity in weapon_purchases.items():
                        # Find weapon details
                        weapon_data = None
                        for weapon in armory_data.get('weapons', []):
                            if str(weapon['id']) == str(weapon_id):
                                weapon_data = weapon
                                break
                        
                        if weapon_data:
                            weapon_breakdown.append({
                                "weapon_id": weapon_id,
                                "weapon_name": weapon_data.get('name', 'Unknown'),
                                "quantity": quantity,
                                "unit_cost": weapon_data.get('cost', 0),
                                "total_cost": weapon_data.get('cost', 0) * quantity
                            })
                    
                    return {
                        "success": True, 
                        "data": weapon_purchases,
                        "summary": {
                            "total_weapons_purchased": total_weapons_purchased,
                            "total_gold_spent": total_gold_spent,
                            "weapon_breakdown": weapon_breakdown,
                            "weapons_purchased": total_weapons_purchased,
                            "cost": total_gold_spent
                        }
                    }
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error purchasing armory by preferences for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _calculate_weapon_purchases(self, armory_data: Dict[str, Any], preferences, current_gold: int, db) -> Dict[str, int]:
        """Calculate weapon purchases based on preferences and available gold"""
        weapon_purchases = {}
        
        # Get weapon preferences sorted by percentage (highest first)
        weapon_prefs = sorted(preferences.weapon_preferences, key=lambda x: x.percentage, reverse=True)
        
        for weapon_pref in weapon_prefs:
            if weapon_pref.percentage <= 0:
                continue
                
            logger.debug(f"Processing weapon preference: {weapon_pref.weapon.display_name} (ROC ID: {weapon_pref.weapon.roc_weapon_id}, Percentage: {weapon_pref.percentage}%)")
                
            # Find weapon in armory data using the roc_weapon_id
            weapon_data = None
            for weapon in armory_data.get('weapons', []):
                if str(weapon['id']) == str(weapon_pref.weapon.roc_weapon_id):
                    weapon_data = weapon
                    break
            
            if not weapon_data:
                logger.warning(f"Weapon {weapon_pref.weapon.display_name} (ROC ID: {weapon_pref.weapon.roc_weapon_id}) not found in armory data")
                continue
                
            if weapon_data.get('cost', 0) <= 0:
                logger.warning(f"Weapon {weapon_pref.weapon.display_name} has no cost or cost is 0")
                continue
            
            # Calculate gold allocation for this weapon based on original gold amount
            gold_for_weapon = int(current_gold * (weapon_pref.percentage / 100.0))
            
            # Calculate how many weapons we can buy
            weapon_cost = weapon_data['cost']
            max_weapons = gold_for_weapon // weapon_cost
            
            logger.debug(f"Weapon {weapon_pref.weapon.display_name}: Gold allocated: {gold_for_weapon}, Cost: {weapon_cost}, Max weapons: {max_weapons}")
            
            if max_weapons > 0:
                weapon_purchases[str(weapon_pref.weapon.roc_weapon_id)] = max_weapons
        
        return weapon_purchases
    
    async def _submit_armory_purchase(self, weapon_purchases: Dict[str, int]) -> Dict[str, Any]:
        """Submit armory purchase form with calculated weapon amounts"""
        try:
            armory_url = self.url_generator.armory()
            
            # Build form data
            form_data = {
                "email": "self.account.email",
                "password": "",
                "submit": "Sell/Buy+Weapons"
            }
            
            # Initialize all sell fields to empty
            for i in range(3, 15):  # sell[3] to sell[14]
                form_data[f"sell[{i}]"] = ""
            
            # Initialize all buy fields to empty
            for i in range(1, 15):  # buy[1] to buy[14]
                form_data[f"buy[{i}]"] = ""
            
            # Set the weapon purchases
            for weapon_id, quantity in weapon_purchases.items():
                form_data[f"buy[{weapon_id}]"] = str(quantity)
            
            # Submit the form
            async def _submit():
                return await self.__submit_page(armory_url, form_data, PageSubmit.ARMORY)
            
            return await self.__retry_login_wrapper(_submit)
        except Exception as e:
            logger.error(f"Error submitting armory purchase: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_armory_preferences(self, weapon_percentages: Dict[str, float]) -> Dict[str, Any]:
        """Update armory preferences for the account"""
        try:
            db = SessionLocal()
            try:
                return PreferenceService.update_armory_preferences(self.account.id, weapon_percentages, db)
            finally:
                db.close()
                
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Error updating armory preferences for {self.account.username}: {e}\n{stack_trace}")
            
            return {"success": False, "error": [str(e) + "\n" + stack_trace]}
    
    
    async def update_training_preferences(self, soldier_type_percentages: Dict[str, float]) -> Dict[str, Any]:
        """Update training preferences for the account"""
        try:
            db = SessionLocal()
            try:
                return PreferenceService.update_training_preferences(self.account.id, soldier_type_percentages, db)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error updating training preferences for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def purchase_training(self, training_orders: Dict[str, Any]) -> Dict[str, Any]:
        """Purchase training for soldiers and mercenaries
        
        Args:
            training_orders: Dictionary with training orders in format:
                {
                "train[attack_soldiers]": "",
                "train[defense_soldiers]": "",
                "train[spies]": "",
                "train[sentries]": "13",
                "buy[attack_mercs]": "",
                "buy[defense_mercs]": "",
                "buy[untrained_mercs]": "",
                "untrain[attack_soldiers]": "",
                "untrain[defense_soldiers]": "56",
                "untrain[attack_mercs]": "",
                "untrain[defense_mercs]": "",
                "untrain[untrained_mercs]": "",
                }
        
        Returns:
            Dict containing success status and training result or error message
        """
        try:
            training_url = self.url_generator.training()
            
            # Build form data with all possible training fields
            form_data = {
                "train[attack_soldiers]": "",
                "train[defense_soldiers]": "",
                "train[spies]": "",
                "train[sentries]": "",
                "buy[attack_mercs]": "",
                "buy[defense_mercs]": "",
                "buy[untrained_mercs]": "",
                "untrain[attack_soldiers]": "",
                "untrain[defense_soldiers]": "",
                "untrain[attack_mercs]": "",
                "untrain[defense_mercs]": "",
                "untrain[untrained_mercs]": "",
                "submit": "Train+Soldiers"
            }
            
            # Update form data with user-provided values
            for key, value in training_orders.items():
                if key in form_data:
                    form_data[key] = str(value) if value is not None else ""
                else:
                    logger.warning(f"Unknown training field: {key}")
            
            # Submit the training form
            async def _submit_training():
                return await self.__submit_page(training_url, form_data, PageSubmit.TRAINING)
            
            for i in range(self.max_retries + 1):
                result = await self.__retry_login_wrapper(_submit_training)
                
                page_text = await result.text()
                
                # Check if training was successful by looking for success indicators
                # This could be enhanced with more specific success/failure detection
                return {"success": True, "messages": ["Training purchase completed. Validation not implemented yet"], "data": training_orders}
                
                # if "Train Soldiers" in page_text or "training" in page_text.lower():
                #     return {"success": True, "message": "Training purchase completed", "data": training_orders}
                # else:
                #     # If we don't see expected content, it might still be successful
                #     # but we should log this for debugging
                #     logger.info(f"Training submission completed for {self.account.username}, but success status unclear")
                #     return {"success": True, "message": "Training purchase submitted", "data": training_orders}
            
            return {"success": False, "error": "Failed to complete training purchase after retries"}
            
        except Exception as e:
            logger.error(f"Error purchasing training for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def set_credit_saving(self, value: str) -> Dict[str, Any]:
        """Set credit saving to 'on' or 'off'"""
        
        # Validate value parameter
        if value.lower() not in ['on', 'off']:
            return {"success": False, "error": "Value must be 'on' or 'off'"}
            
        try:
            # Determine the URL based on the value
            if value.lower() == 'off':
                url = "https://ruinsofchaos.com/recruiter.php?turnoffautosave=1"
                action = "disabled"
            else:  # 'on'
                url = "https://ruinsofchaos.com/recruiter.php?turnonautosave=1"
                action = "enabled"
            
            async def _submit_credit_saving():                
                return await self.__submit_page(url, {}, PageSubmit.CREDIT_SAVE)
            
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_credit_saving)
                
                page_text = await result.text()
                
                # TODO: Check if the credit saving was successful
                
                return {"success": True, "messages": [f"Credit saving {action}"]}
            
        except Exception as e:
            logger.error(f"Error setting credit saving for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def buy_upgrade(self, upgrade_option: str) -> Dict[str, Any]:
        """Buy upgrade - supports siege, fortification, covert, recruiter"""
        
        upgrade_option = upgrade_option.lower().strip()
        
        # Validate upgrade option
        valid_options = ["siege", "fortification", "covert", "recruiter"]
        if upgrade_option not in valid_options:
            return {"success": False, "error": f"Invalid upgrade option. Must be one of: {', '.join(valid_options)}"}
        
        try:
            # Map upgrade options to form data
            form_data_mapping = {
                "siege": {"upgrade[siege]": "Upgrade+Siege"},
                "fortification": {"upgrade[fort]": "Upgrade+Fortification"},
                "covert": {"upgrade[skill]": "Upgrade+Skill"},
                "recruiter": {"upgrade[recruiter_gold]": "Upgrade+(Gold)"}
            }
            
            form_data = form_data_mapping[upgrade_option]
            
           
            upgrades_url = self.url_generator.upgrades()
            
            
            # TODO GET CURRENT, CHECK GOLD
            async def _submit_upgrade():                
                return await self.__submit_page(upgrades_url, form_data, PageSubmit.UPGRADE)
            
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_upgrade)
                
                page_text = await result.text()
                
                # TODO: Compare upgrades cost with previous cost to see if it was successful
                
                return {"success": True }
            
        except Exception as e:
            logger.error(f"Error buying upgrade {upgrade_option} for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_solved_captchas(self, count: int = 1, min_confidence: float = 0, page_name = 'roc_armory') -> List[CaptchaSolutionItem]:
        """Get solved captchas"""
        try:
            results = []
            keypad_selector = CaptchaKeypadSelector()
            
            while len(results) < count:
                captcha = await self._get_captcha()
                _, confidence, _ = await self.captcha_solver.solve(captcha)
                if confidence >= min_confidence:
                    coords = keypad_selector.get_xy_static(captcha.ans, page_name)
                    results.append({
                        "account_id": self.account.id,
                        "hash": captcha.hash,
                        "answer": captcha.ans,
                        "x": coords[0],
                        "y": coords[1],
                        "timestamp": datetime.now(timezone.utc)
                    })
                else:
                    logger.info(f"Ignoring captcha {captcha.hash} because it was incorrect with confidence {confidence}")
            
            return results
        except Exception as e:
            logger.error(f"Failed to get solved captchas: {e}", exc_info=True)
            return []
    
    async def get_cards(self) -> Dict[str, Any]:
        """Get cards from sendcards page"""
        try:
            cards_url = self.url_generator.send_cards("1")
            
            async def _get_cards_page():
                return await self.__get_page(cards_url)
            
            for i in range(self.max_retries+1):
                page =  await self.__retry_login_wrapper(_get_cards_page)

                page_text = await page.text()
                
                cards_data = parse_cards_page(page_text)
                if cards_data["target_name"]:           
                    unique_card_count = len(cards_data["cards"])
                    total_cards = sum(card["count"] for card in cards_data["cards"])
                    
                    # Create detailed summary
                    card_summary = []
                    for card in cards_data["cards"]:
                        card_summary.append(f"{card['card_name']}: {card['count']}")
                    
                    summary_message = f"Retrieved {unique_card_count} unique card types ({total_cards} total cards): {', '.join(card_summary)}"
                    
                    return {
                        "success": True,
                        "data": cards_data,
                        "message": summary_message,
                        "card_count": unique_card_count,
                        "total_cards": total_cards,
                        "card_summary": card_summary,
                        "cards": cards_data["cards"]
                    }
                else:
                    logger.warning(f"{self.account.username}: Failed to get cards'")
                                   
            return {"success": False, "errors": ["Failed to get cards"]}
            
        except Exception as e:
            logger.error(f"Error getting cards for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def send_cards(self, target_id: str, card_id: str, comment: str = "") -> Dict[str, Any]:
        """Send cards to a target user"""
       
        cards_to_send = []
        sent_summary = []
        failed_summary = []
        total_sent = 0
        try:
            if card_id.lower() == 'all':
                cards_result = await self.get_cards()
                if not cards_result or not cards_result["success"]:
                    return {"success": False, "error": "Failed to get cards list"}
                
                cards_to_send = cards_result["data"]["cards"]
                if not cards_to_send:
                    return {"success": True, "message": f"{self.account.username}: No cards available to send"}

            else:
                cards_to_send = [{"card_id": card_id, "count": 1}]
        
            
            # Track counts per card name
            card_counts = {}
            card_failures = {}
            
            for card in cards_to_send:
                count = card["count"]
                card_name = card.get("card_name", f"Card {card['card_id']}")
                
                for _ in range(count):
                    result = await self._send_single_card(target_id, card["card_id"], comment)
                    if result["success"]:
                        total_sent += 1
                        card_counts[card_name] = card_counts.get(card_name, 0) + 1
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        card_failures[card_name] = card_failures.get(card_name, 0) + 1
            
            # Build summaries from accumulated counts
            sent_summary = [f"{card_name}: {count}" for card_name, count in card_counts.items()]
            failed_summary = [f"{card_name}: {count}" for card_name, count in card_failures.items()]
                
        
        except Exception as e:
            logger.error(f"Error sending cards for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        
        return {
                "success": total_sent > 0,
                "cards_sent": total_sent,
                "sent_summary": sent_summary,
                "failed_summary": failed_summary
            }
        
       #  return await self._with_target_rate_limit(target_id, "send_cards", _send_cards_implementation)
    
    async def _send_single_card(self, target_id: str, card_id: str, comment: str = "") -> Dict[str, Any]:
        """Send a single card to a target user"""
        try:
            send_url = self.url_generator.send_cards()  # No target_id in URL for POST
            
            payload = {
                "to": target_id,
                "comment": comment,
                "card_type": card_id,
            }
            
            async def _submit_card():
                return await self.__submit_page(send_url, payload, PageSubmit.SEND_CARDS)
            
            errors = []
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_card)
                
                page_text = await result.text()
                path = result.url.path
                
                # Check for success indicators
                if "Card sent successfully" in page_text or "successfully sent" in page_text.lower():
                    return {"success": True, "message": f"Card {card_id} sent successfully", "cards_sent": 1}
                
                # Check for error indicators
                if "error" in page_text.lower() or "invalid" in page_text.lower():
                    errors.append(f"Error sending card {card_id}")
                elif path not in self.url_generator.base():
                    errors.append("Unknown error. Not on expected page after sending card.")
                else:
                    # Assume success if no clear error
                    return {"success": True, "message": f"Card {card_id} sent", "cards_sent": 1}
            
            return {"success": False, "error": "Failed to send card:\n" + "\n".join(errors)}
            
        except Exception as e:
            logger.error(f"Error sending single card {card_id} for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def market_purchase(self, listing_id: str) -> Dict[str, Any]:
        """Purchase an item from the market"""
        try:
            market_url = self.url_generator.market_post()
            
            payload = {
                "do": "it",
                "id": listing_id,
                "click": "Buy+Now"
            }
            
            async def _submit_purchase():
                return await self.__submit_page(market_url, payload, PageSubmit.UPGRADE)
            
            errors = []
            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit_purchase)
                
                page_text = await result.text()
                page_text = page_text.lower()
                
                if 'have enough to cover the final cost of' in page_text:
                    return {"success": True, "message": f"Can't afford to purchase listing {listing_id}", "retries": i}
                if 'logview' in result.url.path:
                    return {"success": True, "message": f"Successfully purchased listing {listing_id}", "retries": i}

                errors.append(f"Error purchasing listing {listing_id}: Check page response for details")

            return {"success": False, "error": "Failed to purchase from market:\n" + "\n".join(errors)}
            
        except Exception as e:
            logger.error(f"Error purchasing from market for {self.account.username}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    ###################
    ### END ACTIONS ###
    ###################
    
    def __save_error(self, filename: str, error: str):
        error_folder = "errors"
        if not os.path.exists(error_folder):
            os.makedirs(error_folder)
        with open(os.path.join(error_folder, filename), "w", encoding="utf-8") as f:
            f.write(error)

    def __check_logged_in(self, page_text: str) -> bool:
        """Check if the account is logged in"""
        return page_text.find('<form action="login.php" method="post">') == -1
    
    async def initialize(self, preloaded_cookies: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the account login"""
        try:
            # Create aiohttp session with connection limits
            self._connector = aiohttp.TCPConnector(
                limit=settings.HTTP_CONNECTION_LIMIT,  # Total connection pool size
                limit_per_host=settings.HTTP_CONNECTION_LIMIT_PER_HOST,  # Max connections per host
                ttl_dns_cache=settings.HTTP_DNS_CACHE_TTL,  # DNS cache TTL
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=settings.HTTP_TIMEOUT)
            self.session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout
            )
            
            # Load cookies - either from preloaded data or from database
            if preloaded_cookies is not None:
                # Use preloaded cookies
                self.session.cookie_jar.update_cookies(preloaded_cookies)
                logger.debug(f"Loaded {len(preloaded_cookies)} preloaded cookies for account {self.account.username}: {list(preloaded_cookies.keys())}")
            else:
                # Load cookies from UserCookies table (fallback to original behavior)
                db = SessionLocal()
                try:
                    user_cookies = db.query(UserCookies).filter(
                        UserCookies.account_id == self.account.id
                    ).first()
                    
                    if user_cookies:
                        cookies = json.loads(user_cookies.cookies)
                        self.session.cookie_jar.update_cookies(cookies)
                        logger.info(f"Loaded {len(cookies)} cookies for account {self.account.username}: {list(cookies.keys())}")
                    else:
                        logger.info(f"No cookies found for account {self.account.username}")
                finally:
                    db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize account {self.account.username}: {e}", exc_info=True)
            return False   
    
    async def cleanup(self):
        """Cleanup resources"""
        self._is_logged_in = False
        
        # Close session
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.warning(f"Error closing session for {self.account.username}: {e}", exc_info=True)
            finally:
                self.session = None
        
        # Close connector
        if self._connector:
            try:
                await self._connector.close()
            except Exception as e:
                logger.warning(f"Error closing connector for {self.account.username}: {e}", exc_info=True)
            finally:
                self._connector = None
        
        # Also cleanup the captcha solver
        if self.captcha_solver:
            try:
                await self.captcha_solver.close()
            except Exception as e:
                logger.warning(f"Error closing captcha solver for {self.account.username}: {e}", exc_info=True)