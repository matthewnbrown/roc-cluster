# Market Selloff Automation Script

## Overview

This script automates the process of consolidating value from multiple database accounts to a single main account via marketplace listings.

## Workflow

1. **Login** - Logs in with a main account (not stored in the database)
2. **Create Listing** - Main account creates a marketplace listing for specified gold/credit amount
3. **Iterate** - Pages through all accounts in the database
4. **For each database account:**
   - Gets armory data and calculates selloff value
   - Sells all weapons on the account
   - Purchases the main account's marketplace listing

This effectively transfers wealth from many database accounts to the single main account.

## Usage

```bash
python scripts/automate_market_selloff.py
```

## Interactive Prompts

The script will prompt for:

1. **Main Account Credentials**
   - Username: Your ROC account username (receives the consolidated wealth, not in database)
   - Password: Your ROC account password

2. **API Configuration**
   - API base URL (default: `http://localhost:8000`)

3. **Listing Parameters**
   - Gold amount for listing (default: 10000)
   - Credit price for listing (default: 100)

4. **Pagination Settings**
   - Accounts per page (default: 50)
   - Start from page (default: 1)
   - Max pages to process (default: all pages)

## Example Session

```
============================================================
Market Selloff Automation Script
============================================================

Enter main account credentials (creates the marketplace listing):
Username: my_main_account
Password: ********

API base URL (default: http://localhost:8000): 
Gold amount for listing (default: 10000): 5000
Credit price for listing (default: 100): 100
Accounts per page (default: 50): 25
Start from page (default: 1): 1
Max pages to process (default: all): 5

Initializing main account: my_main_account
✓ Successfully logged in as my_main_account

============================================================
STEP 1: Creating marketplace listing on main account
============================================================
  [DUMMY] Would create market listing: 5000 gold for 100 credits
✓ Created listing: dummy_listing_5000

============================================================
STEP 2: Processing database accounts
============================================================
Each account will sell weapons and buy the listing
Starting to process accounts (page 1, 25 per page)...
------------------------------------------------------------

--- Page 1 (25 accounts) ---

Processing account: user1 (ID: 123)
  → Getting armory data...
  → Selloff value: 3500 gold
  → Selling all weapons...
  ✓ Sold 15 weapons for 3500 gold
  → Purchasing listing dummy_listing_5000...
  ✓ Successfully purchased listing
✓ Successfully processed user1

Processing account: user2 (ID: 124)
  → Getting armory data...
  → Selloff value: 4200 gold
  → Selling all weapons...
  ✓ Sold 18 weapons for 4200 gold
  → Purchasing listing dummy_listing_5000...
  ✗ Can't afford listing dummy_listing_5000
  ✗ Failed to purchase listing
✗ Error processing account user2

...

============================================================
SUMMARY
============================================================
Main account: my_main_account
Listing: 5000 gold for 100 credits
Listing ID: dummy_listing_5000

Database accounts processed: 75
Successful (sold weapons + bought listing): 72
Failed: 3
Pages processed: 3

Cleaned up main account session
```

## Features

- **Main account** - Receives consolidated wealth from database accounts
- **API-based** - Uses the ROC Cluster API for all database account operations
- **Direct HTTP** - Main account uses direct HTTP calls to ROC (not through API)
- **Pagination support** - Can process accounts in pages with configurable size
- **Error handling** - Gracefully handles errors and continues processing
- **Progress tracking** - Shows detailed progress for each step and account
- **Summary report** - Provides a comprehensive summary of results at the end
- **Flexible listing** - Configurable gold amount and credit price for the marketplace listing

## Implementation Notes

### Selloff Value Calculation
- Each database account sells weapons for 70% of their purchase price
- Total selloff value = sum of (weapon_cost * 0.7 * quantity) for all weapons

### Market Listing
- Created on the main account
- Gold amount and credit price are configurable
- **Note:** Market listing creation is currently a dummy implementation (placeholder)
- Multiple database accounts can purchase the same listing
- Main account receives credits from each purchase

### Workflow Details
1. Main account creates a marketplace listing
2. Each database account:
   - Sells all weapons (converts weapons → gold)
   - Uses that gold + existing credits to buy the listing (converts gold+credits → credits for main account)
3. Net result: Weapons from all accounts → Credits on main account

### API Endpoints Used
- `GET /accounts` - Get paginated database accounts
- `GET /actions/account/{account_id}/armory` - Get armory data for database accounts
- `POST /actions/armory-purchase` - Sell weapons on database accounts
- `POST /actions/market-purchase` - Have database accounts purchase listings
- Direct HTTP to ROC (main account only):
  - `POST /login.php` - Login main account
  - `POST /marketpost.php` - Create marketplace listing (future)

## Future Enhancements

- [ ] Implement actual market listing creation (currently dummy)
- [ ] Add retry logic for failed operations
- [ ] Add dry-run mode to preview without executing
- [ ] Add filtering options (e.g., minimum selloff value, minimum account credits)
- [ ] Add option to skip accounts with no weapons
- [ ] Add detailed logging to file
- [ ] Add option to process specific account IDs
- [ ] Add ability to create multiple listings if needed
- [ ] Track total credits earned by main account

## Troubleshooting

### Main account login fails
- Verify credentials are correct
- Check that the ROC website is accessible
- Ensure the account is not locked or suspended
- Note: ROC uses "email" field for username in login form

### Database accounts can't sell weapons
- Check that accounts have weapons in their armory
- Verify weapon IDs are valid in the database
- Check API logs for detailed error messages

### Database accounts can't purchase listing
- Check that accounts have enough credits (need listing credit price)
- After selling weapons, accounts should have gold to contribute
- Verify the listing ID is valid
- Some accounts may fail due to insufficient credits (expected)
- Marketplace mechanics may prevent immediate repurchase

### API connection errors
- Verify the API is running (`http://localhost:8000`)
- Check the API base URL is correct
- Ensure the API server is accessible from the script

## Security Notes

- Passwords are entered via `getpass` (hidden input)
- Main account credentials are not stored anywhere
- Session is cleaned up after script completes
- Consider running this script in a secure environment
- All database account operations go through authenticated API

