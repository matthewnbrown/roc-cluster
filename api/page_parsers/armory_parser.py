from bs4 import BeautifulSoup
import re
from .common import get_clockbar_stats, parse_stats_table, parse_weapon_troop_distribution

def parse_armory_data(armory_page: str | BeautifulSoup):
    """Parse armory data from both files"""
    
    if isinstance(armory_page, BeautifulSoup):
        armory_soup = armory_page
    else:
        armory_soup = BeautifulSoup(armory_page, 'html.parser')
    
    # Parse weapons from main armory file
    weapons = __parse_weapon_data(armory_soup, is_repair_page=False)
    
    # Parse stats and distribution from main armory file
    stats = parse_stats_table(armory_soup)
    weapon_troop_dist = parse_weapon_troop_distribution(armory_soup)
    
    # Calculate total sell value
    total_sell_value = __calculate_total_sell_value(weapons)
    
    return {
        'current_user': get_clockbar_stats(armory_soup),
        'total_sell_value': total_sell_value,
        'weapons': weapons,
        'stats': stats,
        'weapon_troop_dist': weapon_troop_dist
    }

def __calculate_total_sell_value(weapons):
    """Calculate total sell value from all weapons"""
    total = 0
    for weapon in weapons:
        total += weapon['owned_count'] * weapon['sell_value']
    return total

def __parse_weapon_data(soup, is_repair_page=False):
    """Parse weapon data from armory page"""
    weapons = []
    
    # Parse inventory weapons (owned weapons)
    inventory_items = soup.find_all('li', class_=lambda x: x and 'inventory' in x and 'typeheader' not in x)
    
    for item in inventory_items:
        weapon_data = {}
        
        # Extract weapon ID from the item id (e.g., "inv_weapon3" -> "3")
        item_id = item.get('id', '')
        if 'inv_weapon' in item_id:
            weapon_data['id'] = item_id.replace('inv_weapon', '')
        else:
            continue
        
        # Extract weapon name
        name_h3 = item.find('h3')
        if name_h3:
            weapon_data['name'] = name_h3.get_text().strip()
        else:
            continue
        
        # Extract owned count
        amount_span = item.find('span', class_='amount')
        if amount_span:
            amount_text = amount_span.get_text().strip().replace(',', '')
            weapon_data['owned_count'] = int(amount_text) if amount_text.isdigit() else 0
        else:
            weapon_data['owned_count'] = 0
        
        # Extract sell value
        sellvalue_span = item.find('span', class_='sellvalue')
        if sellvalue_span:
            sellvalue_text = sellvalue_span.get_text().strip().replace(',', '')
            weapon_data['sell_value'] = int(sellvalue_text) if sellvalue_text.isdigit() else 0
        else:
            weapon_data['sell_value'] = 0
        
        # Extract strength (for repair page, this shows damaged strength)
        strength_span = item.find('span', class_='strength')
        if strength_span:
            strength_text = strength_span.get_text().strip()
            # Extract number from strength text (e.g., "2,995.527 Strength" -> 2995.527)
            strength_match = re.search(r'([\d,]+\.?\d*)', strength_text)
            if strength_match:
                weapon_data['current_strength'] = float(strength_match.group(1).replace(',', ''))
            else:
                weapon_data['current_strength'] = 0
        else:
            weapon_data['current_strength'] = 0
        
        # Initialize repair data
        weapon_data['repair_cost'] = 0
        weapon_data['repair_value'] = 0
        weapon_data['cost'] = 0
        
        weapons.append(weapon_data)
    
    # Parse buy weapons to get cost and full strength
    buy_weapons = soup.find_all('li', class_=lambda x: x and 'weapon' in x and 'typeheader' not in x)
    
    for weapon in buy_weapons:
        # Extract weapon ID from the item id (e.g., "weapon3" -> "3")
        weapon_id = weapon.get('id', '')
        if 'weapon' in weapon_id and 'type' not in weapon_id:
            weapon_id_num = weapon_id.replace('weapon', '')
        else:
            continue
        
        # Find corresponding weapon in our list
        existing_weapon = None
        for w in weapons:
            if w['id'] == weapon_id_num:
                existing_weapon = w
                break
        
        if not existing_weapon:
            # Create new weapon entry for weapons not in inventory
            existing_weapon = {
                'id': weapon_id_num,
                'name': '',
                'owned_count': 0,
                'sell_value': -1,
                'current_strength': 0,
                'repair_cost': 0,
                'repair_value': 0,
                'cost': -1
            }
            weapons.append(existing_weapon)
        
        # Extract weapon name
        name_h3 = weapon.find('h3')
        if name_h3:
            existing_weapon['name'] = name_h3.get_text().strip()
        
        # Extract cost
        cost_span = weapon.find('span', class_='cost')
        if cost_span:
            cost_text = cost_span.get_text().strip()
            # Extract number from cost text (e.g., "200,000 Gold" -> 200000)
            cost_match = re.search(r'([\d,]+)', cost_text)
            if cost_match:
                existing_weapon['cost'] = int(cost_match.group(1).replace(',', ''))
        
        # Extract full strength
        strength_span = weapon.find('span', class_='strength')
        if strength_span:
            strength_text = strength_span.get_text().strip()
            # Extract number from strength text (e.g., "3,000 Attack" -> 3000)
            strength_match = re.search(r'([\d,]+)', strength_text)
            if strength_match:
                existing_weapon['full_strength'] = int(strength_match.group(1).replace(',', ''))
            else:
                existing_weapon['full_strength'] = 0
        else:
            existing_weapon['full_strength'] = 0
        
        # Extract repair cost if this is a repair page
        if is_repair_page:
            repair_input = weapon.find('input', class_='repair')
            if repair_input:
                repair_value = repair_input.get('value', '0')
                existing_weapon['repair_value'] = float(repair_value)
                
                # Extract repair cost from label text
                repair_label = weapon.find('label', class_='repaircost')
                if repair_label:
                    repair_text = repair_label.get_text().strip()
                    # Extract number from repair text (e.g., "Repair for 323,622 Gold" -> 323622)
                    repair_match = re.search(r'([\d,]+)', repair_text)
                    if repair_match:
                        existing_weapon['repair_cost'] = int(repair_match.group(1).replace(',', ''))
    
    return weapons
