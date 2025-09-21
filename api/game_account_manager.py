"""
Manages a single ROC account session
"""


from enum import Enum
import logging
import os
import random

from typing import Awaitable, Callable, List, Optional, Tuple
from urllib.parse import urljoin
import json
import aiohttp
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from typing import Dict, Any

from bs4 import BeautifulSoup
from sqlalchemy import false

from api.db_models import Account, UserCookies
from api.page_parsers.spy_parser import parse_recon_data
from api.schemas import AccountMetadata, CaptchaSolutionItem
from api.captcha import Captcha, CaptchaSolver, CaptchaKeypadSelector
from api.database import SessionLocal
from api.rocurlgenerator import ROCDecryptUrlGenerator
from api.credit_logger import credit_logger
from api.captcha_feedback_service import captcha_feedback_service
from config import settings


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
    CREDIT_SAVE = ""

class GameAccountManager:
    """Manages a single ROC account session"""


    
    def __init__(self, account: Account, max_retries: int = 0):
        self.account = account
        self.last_metadata_update = None
        self._metadata_cache: Optional[AccountMetadata] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self.url_generator = ROCDecryptUrlGenerator()
        self._is_logged_in = False
        self.captcha_solver = CaptchaSolver(solver_url=settings.CAPTCHA_SOLVER_URL, report_url=settings.CAPTCHA_REPORT_URL, max_retries=max_retries)
        self.max_retries = max_retries
        self.use_captcha = False

    @property
    def is_logged_in(self) -> bool:
        """Check if the account is logged in"""
        return self._is_logged_in and self.session is not None

    def parse_roc_number(self, number: str) -> int:
        """Parse a ROC number"""
        return int(number.replace(',', ''))

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
            logger.error(f"Failed to get solved captchas: {e}")
            return []
    
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
            logger.error(f"Failed to get captcha: {e}")
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
            logger.error(f"Failed to submit captcha: {e}")
            raise e
    
    async def initialize(self) -> bool:
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
            
            # Load cookies from UserCookies table
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
            logger.error(f"Failed to initialize account {self.account.username}: {e}")
            return False

    def __save_error(self, filename: str, error: str):
        error_folder = "errors"
        if not os.path.exists(error_folder):
            os.makedirs(error_folder)
        with open(os.path.join(error_folder, filename), "w", encoding="utf-8") as f:
            f.write(error)

    def __check_logged_in(self, page_text: str) -> bool:
        """Check if the account is logged in"""
        return page_text.find('<form action="login.php" method="post">') == -1

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
                    filename = f"{self.account.username}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "error": "Failed to load metadata"}
                page_text = await response.text()
            
            if not self.__check_logged_in(page_text):
                await self.login();
            
            async with self.session.get(metadata_url) as response:
                if response.status != 200:
                    filename = f"{self.account.username}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{response.status}_metadata.html"
                    self.__save_error(filename=filename, error=await response.read())
                    return {"success": False, "error": "Failed to load metadata"}
                page_text = await response.text()

            soup = BeautifulSoup(page_text, 'html.parser')
            rank = soup.find('new', {'id': 's_rank'}).text
            turns = soup.find('new', {'id': 's_turns'}).text
            next_turn = soup.find('new', {'id': 's_next'}).text
            gold = soup.find('new', {'id': 's_gold'}).text
            last_hit = soup.find('new', {'id': 's_hit'})

            if last_hit:
                last_hit = last_hit.find('span').get('data-timestamp')
            else:
                last_hit = 'unknown'
            
            last_sabbed = soup.find('new', {'id': 's_sabbed'})

            if last_sabbed:

                last_sabbed = last_sabbed.find('span').get('data-timestamp')
            else:
                last_sabbed = 'unknown'
            
            mail = soup.find('new', {'id': 's_mail'}).text
            credits = soup.find('new', {'id': 's_credits'}).text
            username = soup.find('new', {'id': 's_username'}).text
            lastclicked = soup.find('new', {'id': 's_lastclicked'}).text
            
            saving = soup.find('saving')
            if saving:
                if saving.get('status') == '0':
                    saving = 'disabled'
                else:
                    saving = 'enabled'
            else:
                saving = 'unknown'
            
            credits = soup.find('new', {'id': 'credits'}).text
            gets = soup.find('new', {'id': 'gets'}).text
            credits_given = soup.find('new', {'id': 't_gives'}).text
            credits_received = soup.find('new', {'id': 't_gets'}).text
            userid = soup.find('new', {'id': 'userid'}).text
            allianceid = soup.find('new', {'id': 'allianceid'}).text
            servertime = soup.find('new', {'id': 'servertime'}).text
        
            metadata = AccountMetadata(
                gold=self.parse_roc_number(gold),
                rank=self.parse_roc_number(rank),
                turns=self.parse_roc_number(turns),
                # Using UTC time for consistency
                next_turn=datetime.now(timezone.utc) + timedelta(minutes=int(next_turn.split(':')[0]), seconds=int(next_turn.split(':')[1])),
                last_hit=datetime.fromtimestamp(int(last_hit), timezone.utc),
                last_sabbed=datetime.fromtimestamp(int(last_sabbed), timezone.utc),
                mail=mail,
                credits=self.parse_roc_number(credits),
                username=username,
                # last clicked is an roc_num, number of mins since last click
                lastclicked=datetime.now(timezone.utc) - timedelta(minutes=self.parse_roc_number(lastclicked)),
                saving=saving,
                gets=self.parse_roc_number(gets),
                credits_given=self.parse_roc_number(credits_given),
                credits_received=self.parse_roc_number(credits_received),
                userid=userid,
                allianceid=allianceid,
                servertime=servertime
            )
            
            self._metadata_cache = metadata
            self.last_metadata_update = datetime.now(timezone.utc)
            return { "success": True, "data": metadata }
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {self.account.username}: {e}")
            return None
    
    async def attack(self, target_id: str, turns: int = -1) -> Dict[str, Any]:
        """Attack another user"""

        try:
            turns = int(turns)
        except ValueError:
            return {"success": False, "error": "Turn count must be an integer"}

        if turns < 1 or turns > 12:
            return {"success": False, "error": "Turn count must be between 1 and 12"}

        try:
            spy_url = self.url_generator.attack(target_id)
            
            payload = {
                "defender_id": target_id,
                "mission_type": "attack",
                "attacks": turns
            }
            
            results = []
            
            async def _submit():                
                return await self.__submit_page(spy_url, payload, PageSubmit.ATTACK)

            for i in range(self.max_retries+1):
                result = await self.__retry_login_wrapper(_submit)
            
                if 'detail.php' not in result.url.path:
                    logger.error(f"Unknown error. No captcha error, but not on attack detail url: {result.url}")
                    with open(f"./errors/{self.account.username}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_attack_error.html", "w", encoding="utf-8") as f:
                        f.write(await result.read())
                    return {"success": False, "error": "Unknown error. No captcha error, but not on attack detail url"}
                
                page_text = await result.text()
                if 'You Get Nothing' in page_text:
                    return {"success": True, "error": "Enemy defended"}
                elif 'ribbon won' in page_text:
                    soup = BeautifulSoup(page_text, 'html.parser')
                    won_ribbon = soup.find('div', class_='ribbon won')
                    if won_ribbon:
                        gold_span = won_ribbon.find('span', class_='gold')
                        gold = gold_span.text
                        return {"success": True, "message": f"Defeated {target_id} for {gold} gold"}
                    else:
                        return {"success": False, "error": "Unknown error. No gold found"}
                
                return {"success": False, "message": "Unknown error. Could not determine result"}

            
            results_str = "\n".join([f"{i+1}. {result.get('error', 'Unknown error')}" for i, result in enumerate(results)])
            return {"success": False, "error": "Failed to spy on user:\n" + results_str}

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def sabotage(self, target_id: str, spy_count: int = 1, enemy_weapon: int = 1) -> Dict[str, Any]:
        """Sabotage another user
        
        Args:
            target_id: The ID of the user to sabotage
            spy_count: Number of spies to send (default: 1)
            enemy_weapon: Weapon ID to sabotage (default: 1)
            
        Returns:
            Dict containing success status and sabotage result or error message
        """

        
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
            
            #todo check if the sabotage was successful
            return {"success": True, "message": f"Sabotaged user {target_id}"}
        
        return {"success": False, "error": "Failed to sabotage user"}
            
        try:
            # Implement sabotage logic
            return {"success": True, "message": f"Sabotaged user {target_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def __submit_page(self, url: str, data: Dict[str, Any], page_submit: PageSubmit) -> aiohttp.ClientResponse:
        """Submits a page"""
        if type(page_submit) != PageSubmit:
            raise Exception("Page submit must be a PageSubmit enum")
        if page_submit.value != "":
            data["submit"] = page_submit.value
        
        if self.use_captcha: # [Untested]
            return await self.__submit_with_captcha(url, data, page_submit)
        
        async with self.session.post(url, data=data) as response:
            _ = await response.read()
            return response
    
    async def __get_page(self, url: str) -> aiohttp.ClientResponse:
        async with self.session.get(url) as response:
            _ = await response.read()
            return response
    
    async def spy(self, target_id: str, spy_count: int = 1 ) -> Dict[str, Any]:
        """Spy on another user
        
        Args:
            target_id: The ID of the user to spy on
            spy_count: Number of spies to send (1-25, default: 1)
            
        Returns:
            Dict containing success status and spy data or error message
        """
            
        if spy_count < 1 or spy_count > 25:
            return {"success": False, "error": "Spy count must be between 1 and 25"}

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
            
                if 'inteldetail' not in result.url.path:
                    return {"success": False, "error": "Unknown error. No captcha error, but not on intel url"}
                
                page_text = await result.text()
                if 'As they approach, an alarm is cried out by enemy sentries' in page_text:
                    return {"success": True, "message": "Enemy sentries detected"}
                data = parse_recon_data(page_text)
                if data["success"]:
                    return {"success": True, "data": data}
                else:
                    return {"success": False, "error": data["error"]}
            
            results_str = "\n".join([f"{i+1}. {result.get('error', 'Unknown error')}" for i, result in enumerate(results)])
            return {"success": False, "error": "Failed to spy on user:\n" + results_str}

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
    
    async def send_credits(self, target_id: str, amount: int, dry_run = False) -> Dict[str, Any]:
        """Send credits to another user"""            
        try:
            # check if amount is 'all' or an int
            if str(amount).lower() == 'all':
                return await self.send_all_credits(target_id)
            else:
                try:
                    amount = int(amount)
                except ValueError:
                    return {"success": False, "error": "Invalid amount. Must be an integer or 'all'"}
            
            if amount < 100:
                return {"success": False, "error": "Amount must be at least 100"}
            
            send_url = self.url_generator.send_credits()

            async def _submit_credits():
                # captcha = await self._get_captcha()
                # if not captcha:
                #     return {"success": False, "error": "Failed to get captcha"}
                
                # logger.info(f"Got captcha {captcha.hash}")
                captcha = Captcha(hash="", img=None, ans="")
                payload = {
                    "to": target_id,
                    "amount": amount,
                    "comment": "",
                    "submit": "Send+Credits"
                }
                
                if dry_run:
                    return {"success": True, "message": f"Would have sent {amount} credits to user {target_id}"}
                
                captcha_response, request_id = await self.submit_captca(send_url, payload, captcha)
                page_text = await captcha_response.text()
                # correct = self.__was_captcha_correct(page_text, send_url)
                correct = True
                path = captcha_response.url.path
                if correct and path not in self.url_generator.base():
                    
                    return {"success": False, "error": "Unknown error. No captcha error, but not on base url. " + captcha_response.url}
                
                if correct:
                    # await captcha_feedback_service.report_feedback(
                    #     account_id=self.account.id,
                    #     captcha=captcha,
                    #     request_id=request_id,
                    #     was_correct=True
                    # )
                    await credit_logger.log_credit_attempt(
                        sender_account_id=self.account.id,
                        target_user_id=target_id,
                        amount=amount,
                        success=True
                    )
                    return {"success": True, "message": f"Sent {amount} credits to user {target_id}"}
                else:
                    logger.info(f"Captcha was incorrect for {self.account.username} sending {amount} credits to {target_id}")
                    # Report failed captcha asynchronously
                    await captcha_feedback_service.report_feedback(
                        account_id=self.account.id,
                        captcha=captcha,
                        request_id=request_id,
                        was_correct=False
                    )
                    # Log failed credit send
                    await credit_logger.log_credit_attempt(
                        sender_account_id=self.account.id,
                        target_user_id=target_id,
                        amount=amount,
                        success=False,
                        error_message="Captcha was incorrect"
                    )
                    return {"success": False, "error": "Captcha was incorrect"}

            for i in range(self.max_retries+1):
                result = await _submit_credits()
                if result["success"]:
                    return result

                    

            return {"success": False, "error": "Failed to send credits"}

        except Exception as e:
            return {"success": False, "error": str(e)} 
    
    async def send_all_credits(self, target_id: str) -> Dict[str, Any]:
        get_metadata = await self.get_metadata()
        if not get_metadata["success"]:
            return {"success": False, "error": "Failed to get metadata"}
        
        credits = int(get_metadata["data"].credits)

        if credits == 0:
            return {"success": False, "error": "No credits to send"}
        
        return await self.send_credits(target_id, str(credits))
    
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
                
                return {"success": True, "message": "Successfully recruited"}
            
        except Exception as e:
            logger.error(f"Error recruiting for {self.account.username}: {e}")
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
                
                return {"success": True, "message": f"Credit saving {action}"}
            
        except Exception as e:
            logger.error(f"Error setting credit saving for {self.account.username}: {e}")
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
                
                return {"success": True, "message": f"Successfully purchased {upgrade_option} upgrade"}
            
        except Exception as e:
            logger.error(f"Error buying upgrade {upgrade_option} for {self.account.username}: {e}")
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources"""
        self._is_logged_in = False
        
        # Close session
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.warning(f"Error closing session for {self.account.username}: {e}")
            finally:
                self.session = None
        
        # Close connector
        if self._connector:
            try:
                await self._connector.close()
            except Exception as e:
                logger.warning(f"Error closing connector for {self.account.username}: {e}")
            finally:
                self._connector = None
        
        # Also cleanup the captcha solver
        try:
            await self.captcha_solver.close()
        except Exception as e:
            logger.warning(f"Error closing captcha solver for {self.account.username}: {e}")