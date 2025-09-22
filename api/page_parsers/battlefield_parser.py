import re

from bs4 import BeautifulSoup


def parse_battlefield_data(page_content: str | BeautifulSoup):
    f"""Parse the battlefield data from the page
    
    Example Output:
    {
        'current_page': 1,
        'total_pages': 25,
        'total_players': 1246,
        'players': [
            {
                'status_effects': ['online'],
                'rank': 1,
                'id': '123456',
                'is_current_user': False,
                'name': 'Player Name',
                'alliance': 'Alliance Name',
                'soldier_count': 1000,
                'soldier_race': 'Human',
                'gold': 100000
            }
        ]
    }
    """
    if isinstance(page_content, str):
        soup = BeautifulSoup(page_content, 'html.parser')
    else:
        soup = page_content
    
    # Extract page information
    page_info = {}
    page_li = soup.find('li', class_='page_x')
    if page_li:
        page_span = page_li.find('span')
        if page_span:
            page_text = page_span.get_text().strip()
            # Extract "Page 2 of 83 (4,118)" format using string splitting
            try:
                # Split by spaces and extract numbers
                parts = page_text.split()
                if len(parts) >= 5 and parts[0] == 'Page' and parts[2] == 'of' and parts[4].startswith('(') and parts[4].endswith(')'):
                    page_info['current_page'] = int(parts[1])
                    page_info['total_pages'] = int(parts[3])
                    page_info['total_players'] = int(parts[4][1:-1].replace(',', ''))
                else:
                    page_info['current_page'] = 1
                    page_info['total_pages'] = 1
                    page_info['total_players'] = 0
            except (ValueError, IndexError) as e:
                page_info['current_page'] = 1
                page_info['total_pages'] = 1
                page_info['total_players'] = 0
        else:
            page_info['current_page'] = 1
            page_info['total_pages'] = 1
            page_info['total_players'] = 0
    else:
        page_info['current_page'] = '???'
        page_info['total_pages'] = '???'
        page_info['total_players'] = -1
    
    players = []
    
    # Find all player cells
    player_cells = soup.find_all('li', class_=lambda x: x and 'player_cell' in x)
    
    for cell in player_cells:
        player_data = {
            'status_effects': [],
        }
        
        # Extract rank
        rank_div = cell.find('div', class_='player_rank')
        if rank_div:
            player_data['rank'] = int(rank_div.get_text().strip())
        else:
            player_data['rank'] = -1
        
        # Extract player ID from the cell id
        cell_id = cell.get('id', '')
        if 'player_' in cell_id:
            player_data['id'] = cell_id.replace('player_', '')
        else:
            player_data['id'] = '???'
        
        # Check for protect class
        cell_classes = cell.get('class', [])

        if 'protect' in cell_classes:
            player_data['status_effects'].append('protect')

        player_data['is_current_user'] = True if 'hi' in cell_classes else False
        
        # Extract name and online status
        name_link = cell.find('a', href=lambda x: x and 'stats.php?id=' in x)
        if name_link:
            player_data['name'] = name_link.get_text().strip()
            online_status = 'online' if 'online' in name_link.get('class', []) else 'offline'
            player_data['status_effects'].append(online_status)
        else:
            player_data['name'] = '???'
        
        # Extract alliance
        alliance_div = cell.find('div', class_='player_alliance')
        if alliance_div:
            alliance_link = alliance_div.find('a')
            if alliance_link:
                player_data['alliance'] = alliance_link.get_text().strip()
            else:
                player_data['alliance'] = ''
        else:
            player_data['alliance'] = ''
        
        # Extract soldier count and race
        size_div = cell.find('div', class_='player_size')
        if size_div:
            size_text = size_div.get_text().strip()
            # Extract number and race (e.g., "146,321 Humans")
            match = re.match(r'([\d,]+)\s+(\w+)', size_text)
            if match:
                player_data['soldier_count'] = int(match.group(1).replace(',', ''))
                player_data['soldier_race'] = match.group(2)
            else:
                player_data['soldier_count'] = -1
                player_data['soldier_race'] = '???'
        else:
            player_data['soldier_count'] = -1
            player_data['soldier_race'] = '???'
        
        # Extract gold
        gold_div = cell.find('div', class_='player_gold')
        if gold_div:
            gold_text = gold_div.get_text().strip()
            if '??? Gold' in gold_text:
                player_data['gold'] = -1
            else:
                # Handle HTML entities and extract number
                gold_text = gold_text.replace(' Gold', '').strip()
                # Remove HTML entities and commas
                gold_clean = re.sub(r'[^\d]', '', gold_text)
                player_data['gold'] = int(gold_clean) if gold_clean else -1
        else:
            player_data['gold'] = -1
        
        players.append(player_data)
    