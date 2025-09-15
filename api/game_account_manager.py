"""
Manages a single ROC account session
"""


import logging
import os
import random

from typing import Optional, Tuple
from urllib.parse import urljoin
import json
import aiohttp
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from typing import Dict, Any

from bs4 import BeautifulSoup
from sqlalchemy import false

from api.models import Account, AccountMetadata
from api.captcha import Captcha, CaptchaSolver, CaptchaKeypadSelector
from api.database import SessionLocal
from api.models import Account, AccountMetadata, UserCookies
from api.rocurlgenerator import ROCDecryptUrlGenerator
from api.credit_logger import credit_logger
from api.captcha_feedback_service import captcha_feedback_service
from config import settings


logger = logging.getLogger(__name__)

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
        self.captcha_solver = CaptchaSolver(solver_url="http://localhost:8000/api/v1/solve", report_url="http://localhost:8000/api/v1/feedback", max_retries=max_retries)
        self.max_retries = max_retries

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
        else:
            raise Exception("Unknown submit url")
        
    
    async def _get_captcha(self, page_text: str = None) -> Captcha:
        """Extract captcha from response"""
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
            coords = keypad_selector.get_xy_static(captcha.ans, page_name)
            ans, _, request_id = await self.captcha_solver.solve(captcha)
            data["num"] = ans
            data["coordinates[x]"] = coords[0]
            data["coordinates[y]"] = coords[1]
            data["captcha"] = captcha.hash
            captcha.ans = ans
            
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
    
    async def login_if_needed(self, current_page: str | None = None) -> bool:
        """Login if the account is not logged in"""
        if current_page is None:
            async with self.session.get(self.url_generator.home()) as response:
                page = response.text()
                if not self.__check_logged_in(page):
                    return await self.login()
                self._is_logged_in = True
                return True
        else:
            if not self.__check_logged_in(current_page):
                return await self.login()
            self._is_logged_in = True
            return True
    
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
                captcha = await self._get_captcha()
                if not captcha:
                    return {"success": False, "error": "Failed to get captcha"}
                
                logger.info(f"Got captcha {captcha.hash}")
                
                payload = {
                    "to": target_id,
                    "amount": amount,
                    "comment": "",
                }
                
                if dry_run:
                    return {"success": True, "message": f"Would have sent {amount} credits to user {target_id}"}
                
                captcha_response, request_id = await self.submit_captca(send_url, payload, captcha)
                page_text = await captcha_response.text()
                correct = self.__was_captcha_correct(page_text, send_url)

                if correct:
                    # Report successful captcha asynchronously
                    await captcha_feedback_service.report_feedback(
                        account_id=self.account.id,
                        captcha=captcha,
                        request_id=request_id,
                        was_correct=True
                    )
                    # Log successful credit send
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