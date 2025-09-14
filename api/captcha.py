

from ast import Tuple
import datetime
import aiohttp
from typing import Tuple

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
    def __init__(self, solver_url: str, report_url: str) -> None:
        self.solverurl = solver_url
        self.report_url = report_url

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
            
            # Make API call to solver URL
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.report_url, 
                    data=data, 
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    response.raise_for_status()
            
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to report captcha: {e}")
