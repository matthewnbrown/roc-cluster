from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from bs4 import BeautifulSoup


def __parse_roc_number(number: str) -> int:
    """Parse a ROC number"""
    return int(number.replace(',', ''))

def parse_metadata_data(metadata_page: str | BeautifulSoup) -> Dict[str, Any]:
    if isinstance(metadata_page, BeautifulSoup):
        soup = metadata_page
    else:
        soup = BeautifulSoup(metadata_page, 'lxml')
    
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
    
    return {
        "rank": __parse_roc_number(rank),
        "turns": __parse_roc_number(turns),
        "next_turn": datetime.now(timezone.utc) + timedelta(minutes=int(next_turn.split(':')[0]), seconds=int(next_turn.split(':')[1])),
        "gold": __parse_roc_number(gold),
        "last_hit": datetime.fromtimestamp(int(last_hit), timezone.utc),
        "last_sabbed": datetime.fromtimestamp(int(last_sabbed), timezone.utc),
        "mail": mail,
        "credits": __parse_roc_number(credits),
        "username": username,
        "lastclicked": datetime.now(timezone.utc) - timedelta(minutes=__parse_roc_number(lastclicked)),
        "saving": saving,
        "gets": __parse_roc_number(gets),
        "credits_given": __parse_roc_number(credits_given),
        "credits_received": __parse_roc_number(credits_received),
        "userid": userid,
        "allianceid": allianceid,
        "servertime": servertime
    }