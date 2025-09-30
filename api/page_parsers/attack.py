#!/usr/bin/env python3
"""
BS4 Parser for Ruins of Chaos Attack Pages
Parses attack result files (win.htm, attack_loss.htm, runaway.htm, max_hits.htm)
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, Any


def parse_attack_page(html_content: str) -> Dict[str, Any]:
    """
    Parse attack page HTML and extract battle data
    
    Returns:
        Dict containing attack battle information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        "result": None,
        "target_id": None,
        "target_name": None,
        "gold_won": None,
        "damage_inflicted": None,
        "damage_taken": None,
        "troops_killed": None,
        "troops_lost": None
    }
    
    # Determine result type based on page content
    if 'protection buff active' in html_content:
        result["result"] = "ProtectionBuff"
    elif "You may not attack a player more often than 5 times a day" in html_content:
        result["result"] = "MaxedHits"
    elif "RUNS AWAY!" in html_content:
        result["result"] = "RunAway"
    elif "ribbon won" in html_content:
        result["result"] = "Win"
    elif "ribbon lost" in html_content or "Lost!" in html_content:
        result["result"] = "Loss"
    else:
        result["result"] = "unknown"
    
    # Extract target ID and name from stats.php links
    stats_links = soup.find_all('a', href=re.compile(r'stats\.php\?id=(\d+)'))
    if stats_links:
        # Look for defender links specifically
        defender_links = [link for link in stats_links if 'Defender:' in str(link.parent) or 'defender' in str(link.parent).lower()]
        if defender_links:
            match = re.search(r'stats\.php\?id=(\d+)', defender_links[0]['href'])
            if match:
                result["target_id"] = match.group(1)
                result["target_name"] = defender_links[0].get_text(strip=True)
        else:
            # Fallback to any stats link
            match = re.search(r'stats\.php\?id=(\d+)', stats_links[0]['href'])
            if match:
                result["target_id"] = match.group(1)
                result["target_name"] = stats_links[0].get_text(strip=True)
    
    # Extract gold won from ribbon
    gold_span = soup.find('span', class_='gold')
    if gold_span:
        gold_text = gold_span.get_text(strip=True)
        if "gold" in gold_text.lower() and "nothing" not in gold_text.lower():
            # Extract number from gold text
            gold_match = re.search(r'([\d,]+)', gold_text)
            if gold_match:
                result["gold_won"] = int(gold_match.group(1).replace(',', ''))
        else:
            result["gold_won"] = 0
    else:
        result["gold_won"] = 0
    
    # Extract damage inflicted (your attack strength)
    attack_strength_spans = soup.find_all('span', class_='green lg')
    for span in attack_strength_spans:
        text = span.get_text(strip=True)
        if re.match(r'^[\d,]+$', text) and len(text) > 6:  # Large numbers are likely damage
            # Check if this is in the attack strength context
            parent_text = str(span.parent)
            if "attack strength" in parent_text or "inflict" in parent_text:
                result["damage_inflicted"] = int(text.replace(',', ''))
                break
    
    # Extract damage taken (enemy defense strength)
    defense_strength_spans = soup.find_all('span', class_='red lg')
    for span in defense_strength_spans:
        text = span.get_text(strip=True)
        if re.match(r'^[\d,]+$', text) and len(text) > 6:  # Large numbers are likely damage
            # Check if this is in the defense strength context
            parent_text = str(span.parent)
            if "defense strength" in parent_text or "inflict" in parent_text:
                result["damage_taken"] = int(text.replace(',', ''))
                break
    
    # Extract troops killed (enemy casualties)
    troops_killed = None
    for span in attack_strength_spans:
        text = span.get_text(strip=True)
        if re.match(r'^[\d,]+$', text) and len(text) <= 6:  # Smaller numbers are likely troop counts
            parent_text = str(span.parent)
            if "killing" in parent_text and "enemy troops" in parent_text:
                troops_killed = int(text.replace(',', ''))
                break
    
    result["troops_killed"] = troops_killed if troops_killed is not None else 0
    
    # Extract troops lost (your casualties)
    troops_lost = None
    for span in defense_strength_spans:
        text = span.get_text(strip=True)
        if re.match(r'^[\d,]+$', text) and len(text) <= 6:  # Smaller numbers are likely troop counts
            parent_text = str(span.parent)
            if "killing" in parent_text and "troops!" in parent_text:
                troops_lost = int(text.replace(',', ''))
                break
    
    result["troops_lost"] = troops_lost if troops_lost is not None else 0
    
    # For Maxed_Hits, set all battle values to 0
    if result["result"] == "Maxed_Hits":
        result["gold_won"] = 0
        result["damage_inflicted"] = 0
        result["damage_taken"] = 0
        result["troops_killed"] = 0
        result["troops_lost"] = 0
    
    return result