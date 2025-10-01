#!/usr/bin/env python3
"""
BS4 Parser for Ruins of Chaos Send Cards Page
Parses cards.html to extract target and available cards
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, Any


def parse_cards_page(html_content: str) -> Dict[str, Any]:
    """
    Parse cards page HTML and extract target and card data
    
    Returns:
        Dict containing target info and list of available cards
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        "target_id": None,
        "target_name": None,
        "cards": []
    }
    
    # Extract target ID from hidden input
    target_input = soup.find('input', {'name': 'to', 'type': 'hidden'})
    if target_input and target_input.get('value'):
        result["target_id"] = target_input['value']
    
    # Extract target name from the "To:" section
    target_link = soup.find('a', href=re.compile(r'stats\.php\?id=\d+'))
    if target_link:
        result["target_name"] = target_link.get_text(strip=True)
    
    # Check if user has no cards
    no_cards_error = soup.find('span', class_='error')
    if no_cards_error and "don't have any cards" in no_cards_error.get_text():
        return result
    
    # Extract cards from select dropdown
    card_select = soup.find('select', {'name': 'card_type'})
    if card_select:
        # Get all option elements except the first placeholder
        card_options = card_select.find_all('option')
        
        for option in card_options:
            card_value = option.get('value', '')
            
            # Skip the placeholder option
            if not card_value or card_value == "Choose a card...":
                continue
            
            # Parse the option text: "CardName (count available) - Description"
            card_text = option.get_text(strip=True)
            
            match = re.match(r'^(.+?)\s*\((\d+)\s+available\)\s*-\s*(.+)$', card_text)
            
            if match:
                card_name = match.group(1).strip()
                card_count = int(match.group(2))
                card_description = match.group(3).strip()
                
                card_data = {
                    "card_id": card_value,
                    "card_name": card_name,
                    "count": card_count,
                    "description": card_description
                }
                
                result["cards"].append(card_data)
    
    return result