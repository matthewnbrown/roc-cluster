

from ast import Tuple
import datetime
import aiohttp
import logging
from typing import Tuple
import random
from config import settings

logger = logging.getLogger(__name__)

class CooldownException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

class Captcha:
    def __init__(self, hash: str, img: bytes = None, ans: str = "-1", creation_date: datetime.datetime = None) -> None:
        self.hash = hash
        self.img = img
        self.ans = ans
        self.creation_date = creation_date

    def __str__(self) -> str:
        return f"Captcha(hash={self.hash}, img={self.img}, ans={self.ans}, correct={self.correct}, captype={self.captype}, creation_date={self.creation_date})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Captcha):
            return self.hash == other.hash and self.img == other.img and self.ans == other.ans and self.correct == other.correct and self.captype == other.captype and self.creation_date == other.creation_date
        return False


class CaptchaSolver:
    def __init__(self, solver_url: str, report_url: str, max_retries: int = 0) -> None:
        self.solverurl = solver_url
        self.report_url = report_url
        self._session = None
        self._connector = None

    async def _get_session(self):
        """Get or create aiohttp session with connection limits"""
        if self._session is None or self._session.closed:
            # Create connector with connection limits
            self._connector = aiohttp.TCPConnector(
                limit=settings.CAPTCHA_CONNECTION_LIMIT,
                limit_per_host=settings.CAPTCHA_CONNECTION_LIMIT_PER_HOST,  
                ttl_dns_cache=settings.HTTP_DNS_CACHE_TTL,
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=settings.CAPTCHA_TIMEOUT)
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout
            )
        return self._session

    async def solve(self, captcha: Captcha) -> Tuple[str, float, str]:
        """Gets a solution to a captcha

        Args:
            captcha (Captcha): captcha to be solved

        Returns:
            Tuple[str, float, str]: A tuple containing the solution, the confidence score and request ID
        """
        try:
            data = aiohttp.FormData()
            data.add_field('captcha_hash', captcha.hash)
            data.add_field('image', captcha.img, filename='captcha.png', content_type='image/png')
            
            # Use shared session
            session = await self._get_session()
            async with session.post(self.solverurl, data=data) as response:
                response.raise_for_status()
                
                # Parse response (assuming JSON format)
                result = await response.json()
                
                # Extract solution, confidence, and request_id
                solution = result.get('predicted_answer', '')
                confidence = float(result.get('confidence', 0.0))
                request_id = result.get('request_id', '')
                
                captcha.ans = solution
                
                return solution, confidence, request_id
            
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to solve captcha: {e}")
        except (ValueError, KeyError) as e:
            raise Exception(f"Invalid response from captcha solver: {e}")

    async def report(self, captcha: Captcha, request_id: str, was_correct: bool, actual_answer: str = None) -> None:
        """Report the captcha to the solver

        Args:
            captcha (Captcha): captcha to be reported
            request_id (str): request ID of the captcha solution
            was_correct (bool): Whether the captcha was solved correctly
            actual_answer (str, optional): The actual correct answer if known
        """
        try:
            data = {
                'request_id': request_id,
                'is_correct': str(was_correct).lower(),
                'actual_answer': str(actual_answer) if actual_answer is not None else ''
            }
            
            # Use shared session
            session = await self._get_session()
            async with session.post(
                self.report_url, 
                data=data, 
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                response.raise_for_status()
            
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to report captcha: {e}")

    async def close(self):
        """Close the HTTP session and connector"""
        # Close session
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing captcha solver session: {e}")
            finally:
                self._session = None
        
        # Close connector
        if self._connector and not self._connector.closed:
            try:
                await self._connector.close()
            except Exception as e:
                logger.warning(f"Error closing captcha solver connector: {e}")
            finally:
                self._connector = None


class CaptchaKeypadSelector():
    __btn_dimensions = (40, 30)
    __keypadTopLeft = {'roc_recruit': [890, 705],
                       'roc_armory': [973, 1011],
                       'roc_attack': [585, 680],
                       'roc_spy': [585, 695],
                       'roc_training': [973, 453]}
    __keypadGap = [52, 42]

    def __init__(self, resolution=None) -> None:
        self.resolution = resolution

    def get_xy(self, number):
        pass

    def get_xy_static(self, number, page):
        if page not in self.__keypadTopLeft:
            raise Exception(
                f'Page {page} does not have coordinates for captchas!'
                )
        number = int(number) - 1
        x_btn = self.__keypadTopLeft[page][0] \
            + (number % 3) * self.__keypadGap[0]
        y_btn = self.__keypadTopLeft[page][1] \
            + (number // 3) * self.__keypadGap[1]

        x_click = -x_btn
        while x_click < x_btn or x_click > x_btn + self.__btn_dimensions[0]:
            x_click = x_btn + random.gauss(0, self.__btn_dimensions[0]/3)
        y_click = -y_btn
        while y_click < y_btn or y_click > y_btn + self.__btn_dimensions[1]:
            y_click = y_btn + random.gauss(0, self.__btn_dimensions[1]/3)

        return (int(x_click), int(y_click))
