from bs4 import BeautifulSoup

def parse_recon_data(page_content: str | BeautifulSoup):
    """Parse all data from the recon"""
    if isinstance(page_content, str):
        soup = BeautifulSoup(page_content, 'html.parser')
    else:
        soup = page_content

    data = {}
    
    target_link = soup.find('a', class_='online')
    if target_link:
        data['username'] = target_link.get_text().strip()
        data['target_id'] = target_link.get('href', '').split('id=')[-1] if 'id=' in target_link.get('href', '') else '???'
        data['is_online'] = True
    else:
        # Check for offline user
        target_link = soup.find('a', href=lambda x: x and 'stats.php?id=' in x)
        if target_link:
            data['username'] = target_link.get_text().strip()
            data['target_id'] = target_link.get('href', '').split('id=')[-1] if 'id=' in target_link.get('href', '') else '???'
            data['is_online'] = False
        else:
            data['username'] = '???'
            data['target_id'] = '???'
            data['is_online'] = False
    
    # Treasury
    gold_elem = soup.find('span', id='gold')
    data['gold'] = gold_elem.get_text().strip() if gold_elem else '???'
    
    # Military Division
    military_data = {}
    military_ids = ['sa', 'da', 'sp', 'se', 'siege', 'skill', 'turns']
    for mid in military_ids:
        elem = soup.find('td', id=mid)
        if elem:
            military_data[mid] = elem.get_text().strip()
        else:
            military_data[mid] = '???'
    data['military'] = military_data
    
    # Troops
    troops_data = {}
    troop_ids = ['attack_soldiers', 'attack_mercs', 'defense_soldiers', 'defense_mercs', 
                 'untrained_soldiers', 'untrained_mercs', 'spies', 'sentries']
    for tid in troop_ids:
        elem = soup.find('td', id=tid)
        if elem:
            troops_data[tid] = elem.get_text().strip()
        else:
            troops_data[tid] = '???'
    data['troops'] = troops_data
    
    # Weapons table
    weapons = []
    tables = soup.find_all('table', class_='sep')
    weapons_table = None
    for table in tables:
        if table.find('th', string='Weapons'):
            weapons_table = table
            break
    
    if weapons_table:
        rows = weapons_table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                weapon = {
                    'name': cells[0].get_text().strip(),
                    'type': cells[1].get_text().strip(),
                    'quantity': cells[2].get_text().strip(),
                    'strength': cells[3].get_text().strip()
                }
                weapons.append(weapon)
    data['weapons'] = weapons
    
    return data