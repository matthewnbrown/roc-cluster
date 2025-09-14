import base64
import html
from typing import Optional

class URLNotFoundError(Exception):
    pass

class ROCDecryptUrlGenerator():
    def __init__(self) -> None:
        rocurlb64 = "aHR0cHM6Ly9ydWluc29mY2hhb3MuY29tLw=="
        rocurlbytes = base64.b64decode(rocurlb64)
        self._rocburl = rocurlbytes.decode("ascii")

        self._urls = {
            "roc_home": self._rocburl,
            "roc_metadata": self._rocburl + "recruiter3x.php",
            "roc_armory": self._rocburl + "armory.php",
            "roc_login": self._rocburl + "login.php",
            "roc_training": self._rocburl + "train.php",
            "roc_recruit": self._rocburl + "recruiter.php",
            "roc_keep": self._rocburl + "keep.php",
            "roc_upgrade": self._rocburl + "upgrades.php",
            "roc_commander_change": self._rocburl + "commander_change.php",
            "roc_send_credits": self._rocburl + "sendcredits.php"
        }

    def get_page_url(self, page: str) -> str:
        if page not in self._urls:
            raise URLNotFoundError(f"{page} url not known")
        return self._urls[page]

    def home(self) -> str:
        return self.get_page_url("roc_home")
    
    def metadata(self, preload: str | None = 0) -> str:
        if preload:
            return self.get_page_url("roc_metadata") + f"?preload={html.escape(preload)}"
        else:
            return self.get_page_url("roc_metadata")
    
    def armory(self) -> str:
        return self.get_page_url("roc_armory")

    def training(self) -> str:
        return self.get_page_url("roc_training")

    def base(self) -> str:
        return self.get_page_url("roc_home") + "base.php"

    def recruit(self) -> str:
        return self.get_page_url("roc_recruit")

    def login(self) -> str:
        return self.get_page_url("roc_login")

    def upgrade(self) -> str:
        return self.get_page_url("roc_upgrade")
    
    def keep(self) -> str:
        return self.get_page_url("roc_keep")
 
    def offensive_action(self, id: str) -> str:
        # MetaData page with the offensive action options
        return self.get_home() + f"attack.php?id={id}"
    
    def attack(self, id: str) -> str:
        # extra form data
        # defender_id = <target id>
        # missiontype = "attack"
        # attacks = <numattacks>
        return self.get_home() + f"attack.php"
    def spy(self, id: str) -> str:
        # Extra Form Data
        # missiontype = "Recon"
        # reconspies = <numspies>
        return self.get_attack(id)
    
    def sabotage(self, id: str) -> str:
        # Extra Form Data
        # missiontype = "sabotage"
        # sabspies = <numspies>
        # enemy_weapon = <weaponid>
        return self.get_attack(id)
    
    # new commander ID is used when you want to load the page with a new commander ID
    # for the actual POST request to change, do not use new_commander_id, include it in the form data
    def commander_change(self, id: str, new_commander_id: Optional[str]) -> str:
        # Extra Form Data
        # new_commander_id = <target id>
        
        if new_commander_id:
            new_commander_id = html.escape(new_commander_id)
            return self.get_page_url("roc_commander_change") + f"?new_commander_id={new_commander_id}"
        else:
            return self.get_page_url("roc_commander_change")
    
    def send_credits(self, target_id: str | None = None) -> str:
        # Extra Form Data
        # to = <target id>
        # comment = <comment>
        # amount = <amount>
        # targetid is optional, its just used for the gui page
        if target_id:
            target_id = html.escape(target_id)
            return self.get_page_url("roc_send_credits") + f"?to={target_id}"
        else:
            return self.get_page_url("roc_send_credits")