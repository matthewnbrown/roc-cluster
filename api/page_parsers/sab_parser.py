#!/usr/bin/env python3
"""
BS4 Parser for Ruins of Chaos Sabotage Pages
Parses sab_fail.htm, sab_max.htm, and sab_success.htm files
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, Any


def parse_sabotage_page(html_content: str) -> Dict[str, Any]:
    """
    Parse sabotage page HTML and extract mission data
    
    Returns:
        Dict containing sabotage mission information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        "result": None,
        "target_id": None,
        "target_name": None,
        "targeted_weapon": None,
        "weapon_count": None,
        "weapon_damage_cost": None,
        "damage_to_enemy": None,
        "spies_used": None
    }
    
    # Determine result type based on page content
    if "You have already made 10 sabotages on this target today" in html_content:
        result["result"] = "max_sabbed"
    elif "but is spotted by enemy sentries and forced to flee" in html_content:
        result["result"] = "defended"
    elif "and sabotage" in html_content and "Mithrils" in html_content:
        result["result"] = "success"
    else:
        result["result"] = "unknown"
    
    # Extract target ID from defender_id input or stats.php links
    defender_input = soup.find('input', {'name': 'defender_id'})
    if defender_input:
        result["target_id"] = defender_input.get('value')
    else:
        # Fallback: look for stats.php links
        stats_links = soup.find_all('a', href=re.compile(r'stats\.php\?id=(\d+)'))
        if stats_links:
            match = re.search(r'stats\.php\?id=(\d+)', stats_links[0]['href'])
            if match:
                result["target_id"] = match.group(1)
    
    # Extract target name from stats.php links or player card
    stats_links = soup.find_all('a', href=re.compile(r'stats\.php\?id='))
    if stats_links:
        result["target_name"] = stats_links[0].get_text(strip=True)
    else:
        # Fallback: look for player card name
        player_card = soup.find('div', class_='playercard_name')
        if player_card:
            name_link = player_card.find('a')
            if name_link:
                result["target_name"] = name_link.get_text(strip=True)
    
    # Extract spies used from input field
    spies_input = soup.find('input', {'name': 'sabspies'})
    if spies_input:
        result["spies_used"] = int(spies_input.get('value', 0))
    
    # Extract weapon damage cost
    weapon_cost_match = re.search(r'Your weapon damage cost: ([\d,]+) Gold', html_content)
    if weapon_cost_match:
        result["weapon_damage_cost"] = int(weapon_cost_match.group(1).replace(',', ''))
    
    # Extract mission details based on result type
    if result["result"] == "success":
        # Extract weapon count and type from success message
        success_match = re.search(r'to attempt to sabotage (\d+) (\w+)', html_content)
        if success_match:
            result["weapon_count"] = int(success_match.group(1))
            result["targeted_weapon"] = success_match.group(2)
        
        # Extract damage to enemy (recovery cost)
        damage_match = re.search(r'cost for .*? to recover: ([\d,]+) Gold', html_content)
        if damage_match:
            result["damage_to_enemy"] = int(damage_match.group(1).replace(',', ''))
    
    elif result["result"] == "defended":
        # Extract weapon type from failed attempt
        fail_match = re.search(r'to attempt to sabotage (\d+) (\w+)', html_content)
        if fail_match:
            result["weapon_count"] = int(fail_match.group(1))
            result["targeted_weapon"] = fail_match.group(2)
        
        # No damage to enemy for failed attempts
        result["damage_to_enemy"] = 0
    
    elif result["result"] == "max_sabbed":
        # For max sabotaged, get weapon type from selected option
        weapon_select = soup.find('select', {'name': 'enemy_weapon'})
        if weapon_select:
            selected_option = weapon_select.find('option', selected=True)
            if selected_option:
                result["targeted_weapon"] = selected_option.get_text(strip=True)
        
        # No damage for max sabotaged (can't perform mission)
        result["damage_to_enemy"] = 0
        result["weapon_count"] = 0
    
    return result