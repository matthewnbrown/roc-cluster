import re
from bs4 import BeautifulSoup

def get_clockbar_stats(page_soup: BeautifulSoup | str) -> dict[str, str] | None:
    """ 
    Get the clockbar stats from the page
    Args:
        page_soup (BeautifulSoup | str): page content in BeautifulSoup format or string

    Returns:
        dict[str, str] | None: clockbar stats, None if not found
    """
    
    if isinstance(page_soup, str):
        page_soup = BeautifulSoup(page_soup, 'html.parser')
    else:
        page_soup = page_soup
    
    clock_bar = page_soup.find('div', id='clock_bar')
    if not clock_bar:
        return None
    
    current_user = {
        'username': '',
        'rank': -1,
        'gold': -1,
        'turns': -1,
        'next_turn': '???'
    }
    
    topnav_right = page_soup.find('div', id='topnav_right')
    if topnav_right:
        name_link = topnav_right.find('a')
        if name_link:
            current_user['name'] = name_link.get_text().strip()
        else:
            current_user['name'] = '???'
    else:
        current_user['name'] = '???'
    
    # Get rank
    rank_span = clock_bar.find('span', id='s_rank')
    if rank_span:
        current_user['rank'] = int(rank_span.get_text().strip())
    else:
        current_user['rank'] = -1
    
    # Get gold
    gold_span = clock_bar.find('span', id='s_gold')
    if gold_span:
        gold_text = gold_span.get_text().strip().replace(',', '')
        current_user['gold'] = int(gold_text) if gold_text.isdigit() else -1
    else:
        current_user['gold'] = -1
    
    # Get turns
    turns_span = clock_bar.find('span', id='s_turns')
    if turns_span:
        turns_text = turns_span.get_text().strip().replace(',', '')
        current_user['turns'] = int(turns_text) if turns_text.isdigit() else -1
    else:
        current_user['turns'] = -1
    
    # Get next turn time
    next_turn_span = clock_bar.find('span', id='s_next')
    if next_turn_span:
        current_user['next_turn'] = next_turn_span.get_text().strip()
    else:
        current_user['next_turn'] = '???'
    
    return current_user


def parse_stats_table(soup):
    """Generic function to parse stats table"""
    stats = {}
    
    # Find the stats table
    stats_table = soup.find('table', class_='sep')
    if not stats_table:
        return stats
    
    # Find all rows in the stats table
    rows = stats_table.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            # Extract stat name from first cell
            stat_name_cell = cells[0]
            stat_name_text = stat_name_cell.get_text().strip()
            
            # Extract action points from second cell
            action_points_cell = cells[1]
            action_points_text = action_points_cell.get_text().strip().replace(',', '')
            
            # Extract rank from third cell if it exists
            rank = None
            if len(cells) >= 3:
                rank_cell = cells[2]
                rank_text = rank_cell.get_text().strip()
                if rank_text.startswith('#'):
                    rank = rank_text[1:]  # Remove the # symbol
            
            # Parse stat name and bonus
            if 'Strike:' in stat_name_text:
                stats['strike'] = {
                    'name': 'Strike',
                    'bonus_percent': 0,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': int(rank) if rank and rank.isdigit() else None
                }
            elif 'Defense:' in stat_name_text:
                # Extract bonus percentage if present
                bonus_match = re.search(r'\((\+?\d+%)\)', stat_name_text)
                bonus_percent = 0
                if bonus_match:
                    bonus_percent = int(bonus_match.group(1).replace('+', '').replace('%', ''))
                
                stats['defense'] = {
                    'name': 'Defense',
                    'bonus_percent': bonus_percent,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': int(rank) if rank and rank.isdigit() else None
                }
            elif 'Spy:' in stat_name_text:
                # Extract bonus percentage if present
                bonus_match = re.search(r'\((\+?\d+%)\)', stat_name_text)
                bonus_percent = 0
                if bonus_match:
                    bonus_percent = int(bonus_match.group(1).replace('+', '').replace('%', ''))
                
                stats['spy'] = {
                    'name': 'Spy',
                    'bonus_percent': bonus_percent,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': int(rank) if rank and rank.isdigit() else None
                }
            elif 'Sentry:' in stat_name_text:
                # Extract bonus percentage if present
                bonus_match = re.search(r'\((\+?\d+%)\)', stat_name_text)
                bonus_percent = 0
                if bonus_match:
                    bonus_percent = int(bonus_match.group(1).replace('+', '').replace('%', ''))
                
                stats['sentry'] = {
                    'name': 'Sentry',
                    'bonus_percent': bonus_percent,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': int(rank) if rank and rank.isdigit() else None
                }
            elif 'Kills:' in stat_name_text:
                stats['kills'] = {
                    'name': 'Kills',
                    'bonus_percent': 0,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': None  # Kills don't have ranks
                }
            elif 'Kill Ratio:' in stat_name_text:
                stats['kill_ratio'] = {
                    'name': 'Kill Ratio',
                    'bonus_percent': 0,
                    'action_points': int(action_points_text) if action_points_text.isdigit() else 0,
                    'rank': None  # Kill ratio doesn't have ranks
                }
    
    return stats


def parse_soldier_count(soldiers_text):
    """Parse simple soldier count text to get numeric value"""
    # Remove commas and convert to integer
    clean_text = soldiers_text.replace(',', '')
    return int(clean_text) if clean_text.isdigit() else 0


def parse_weapon_troop_distribution(soup):
    """Generic function to parse weapon and troop distribution table"""
    distribution = {}
    
    # Find the weapon and troop distribution table
    tables = soup.find_all('table', class_='sep')
    dist_table = None
    
    for table in tables:
        # Look for the table with "Weapon And Troop Distribution" header
        header = table.find('th', class_='topcap')
        if header and 'Weapon And Troop Distribution' in header.get_text():
            dist_table = table
            break
    
    if not dist_table:
        return distribution
    
    # Find all rows in the distribution table
    rows = dist_table.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 3:
            # Extract category name from first cell
            category_cell = cells[0]
            category_text = category_cell.get_text().strip()
            
            # Extract weapons count from second cell
            weapons_cell = cells[1]
            weapons_text = weapons_cell.get_text().strip().replace(',', '')
            
            # Extract soldiers count from third cell
            soldiers_cell = cells[2]
            soldiers_text = soldiers_cell.get_text().strip().replace('\t', ' ')
            
            # Parse category
            if 'Attack:' in category_text:
                # Parse soldiers text to separate trained and untrained
                trained_soldiers, untrained_soldiers = __parse_soldier_text(soldiers_text)
                distribution['attack'] = {
                    'weapons': int(weapons_text) if weapons_text.isdigit() else 0,
                    'soldiers': trained_soldiers,
                    'untrained': untrained_soldiers
                }
            elif 'Defense:' in category_text:
                # Parse soldiers text to separate trained and untrained
                trained_soldiers, untrained_soldiers = __parse_soldier_text(soldiers_text)
                distribution['defense'] = {
                    'weapons': int(weapons_text) if weapons_text.isdigit() else 0,
                    'soldiers': trained_soldiers,
                    'untrained': untrained_soldiers
                }
            elif 'Spy:' in category_text:
                # Parse soldiers text to get numeric value
                spy_soldiers = parse_soldier_count(soldiers_text)
                distribution['spy'] = {
                    'weapons': int(weapons_text) if weapons_text.isdigit() else 0,
                    'soldiers': spy_soldiers
                }
            elif 'Sentry:' in category_text:
                # Parse soldiers text to get numeric value
                sentry_soldiers = parse_soldier_count(soldiers_text)
                distribution['sentry'] = {
                    'weapons': int(weapons_text) if weapons_text.isdigit() else 0,
                    'soldiers': sentry_soldiers
                }
            elif 'Total Fighting Force:' in category_text:
                # Parse soldiers text to get numeric value
                fighting_soldiers = parse_soldier_count(soldiers_text)
                distribution['total_fighting_force'] = {
                    'weapons': None,
                    'soldiers': fighting_soldiers
                }
            elif 'Total Covert Force:' in category_text:
                # Parse soldiers text to get numeric value
                covert_soldiers = parse_soldier_count(soldiers_text)
                distribution['total_covert_force'] = {
                    'weapons': None,
                    'soldiers': covert_soldiers
                }
    
    return distribution



def __parse_soldier_text(soldiers_text):
    """Parse soldier text to separate trained and untrained soldiers"""
    # Look for pattern like "3,303          (+17,744 Untrained)" with any whitespace
    untrained_match = re.search(r'\((\+?[\d,]+)\s+Untrained\)', soldiers_text)
    
    if untrained_match:
        # Extract untrained count
        untrained_text = untrained_match.group(1).replace(',', '').replace('+', '')
        untrained_soldiers = int(untrained_text) if untrained_text.isdigit() else 0
        
        # Extract trained count (everything before the untrained part)
        trained_text = soldiers_text.split('(')[0].strip().replace(',', '')
        trained_soldiers = int(trained_text) if trained_text.isdigit() else 0
        
        return trained_soldiers, untrained_soldiers
    else:
        # No untrained soldiers, just return the main count
        trained_text = soldiers_text.replace(',', '')
        trained_soldiers = int(trained_text) if trained_text.isdigit() else 0
        return trained_soldiers, 0