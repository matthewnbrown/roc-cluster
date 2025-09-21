# ROC Cluster Management API

A lightweight, high-performance API for managing multiple ROC (Rise of Civilizations) accounts simultaneously. Built with FastAPI for easy frontend integration and designed to handle hundreds of accounts efficiently.

## Features

### Account Management
- Add, update, and remove ROC accounts
- Secure password storage with hashing
- Session management with cookie persistence
- Account metadata retrieval (gold, rank, army info)

### User Actions (Targeting Other Users)
- **Attack** - Attack other players
- **Sabotage** - Sabotage other players
- **Spy** - Gather intelligence on other players
- **Become Officer** - Become an officer of another player
- **Send Credits** - Transfer credits to other players

### Self Actions
- **Get Metadata** - Retrieve current account status
- **Recruiting** - Recruit soldiers and mercenaries
- **Armory Purchase** - Buy weapons and equipment
- **Training Purchase** - Train soldiers
- **Enable Credit Saving** - Activate credit saving mode
- **Purchase Upgrades** - Buy account upgrades

### Job Management
- Create jobs with multiple steps and actions for bulk operations
- **Sequential Execution** (default): Steps run one after another in order
- **Parallel Execution**: All steps run simultaneously for maximum speed
- Asynchronous job execution with status tracking
- Job cancellation and progress monitoring
- View active and completed jobs

## Quick Start

### Installation

#### Option 1: Windows (Recommended for Windows users)

**Using Batch Script:**
```cmd
git clone <repository-url>
cd roc-cluster
install_windows.bat
```

**Using PowerShell Script:**
```powershell
git clone <repository-url>
cd roc-cluster
.\install_windows.ps1
```

#### Option 2: Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd roc-cluster
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
# Try minimal requirements first (recommended)
pip install -r requirements-minimal.txt

# Or full requirements
pip install -r requirements.txt
```

4. Set up environment variables (optional):
```bash
export DATABASE_URL="sqlite:///./data/roc_cluster.db"
export ROC_BASE_URL="https://rocgame.com"
```

### Running the API

#### Option 1: Using the startup script (Recommended)
```bash
python start_api.py
```
**Benefits:**
- Sets default environment variables
- Uses port 8001 to avoid conflicts
- Includes proper error handling
- Automatically creates data directory

#### Option 2: Direct execution
```bash
python main.py
```
**Benefits:**
- Uses your custom configuration
- Runs on port 8000 by default
- Full control over startup parameters

The API will be available at `http://localhost:8000` (or `http://localhost:8001` with start_api.py)

### API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs` (or `http://localhost:8001/docs` with start_api.py)
- **ReDoc**: `http://localhost:8000/redoc` (or `http://localhost:8001/redoc` with start_api.py)

## API Usage Examples

### Create an Account
```bash
curl -X POST "http://localhost:8000/api/v1/accounts/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "player1",
    "email": "player1@example.com",
    "password": "securepassword"
  }'
```

### Attack Another Player
```bash
curl -X POST "http://localhost:8000/api/v1/actions/attack" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "target_id": "enemy_player"
  }'
```

### Job Creation (Replaces Bulk Operations)

#### Individual Account Jobs
```bash
# Create a sequential job (default - steps run one after another)
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sequential Training Job",
    "description": "Purchase training in order",
    "parallel_execution": false,
    "steps": [
      {
        "account_ids": [1],
        "action_type": "recruit",
        "parameters": {
          "soldier_type": "infantry",
          "count": 100
        }
      },
      {
        "account_ids": [1],
        "action_type": "purchase_training",
        "parameters": {
          "training_type": "attack_soldiers",
          "count": 50
        }
      }
    ]
  }'

# Create a parallel job (all steps run simultaneously)
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parallel Multi-Action Job",
    "description": "Execute multiple actions simultaneously",
    "parallel_execution": true,
    "steps": [
      {
        "account_ids": [1],
        "action_type": "recruit",
        "parameters": {
          "soldier_type": "infantry",
          "count": 100
        }
      },
      {
        "account_ids": [2],
        "action_type": "purchase_training",
        "parameters": {
          "training_type": "attack_soldiers",
          "count": 50
        }
      }
    ]
  }'
```

#### Cluster-Based Jobs
```bash
# Create a job for all accounts in a cluster
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cluster Recruitment Job",
    "description": "Recruit soldiers across all accounts in cluster 1",
    "parallel_execution": true,
    "steps": [
      {
        "cluster_ids": [1],
        "action_type": "recruit",
        "parameters": {
          "soldier_type": "infantry",
          "count": 100
        }
      }
    ]
  }'

# Create a job for multiple clusters
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Multi-Cluster Training Job",
    "description": "Train soldiers across multiple clusters",
    "parallel_execution": true,
    "steps": [
      {
        "cluster_ids": [1, 2, 3],
        "action_type": "purchase_training",
        "parameters": {
          "training_type": "defense_soldiers",
          "count": 50
        }
      }
    ]
  }'

# Combined account_ids and cluster_ids in same step
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Combined Job",
    "description": "Execute action on specific accounts AND cluster members in one step",
    "parallel_execution": true,
    "steps": [
      {
        "account_ids": [1, 2, 3],
        "cluster_ids": [1, 2],
        "action_type": "recruit",
        "parameters": {
          "soldier_type": "cavalry",
          "count": 50
        }
      }
    ]
  }'

# Multiple accounts and clusters example
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Multi-Target Job",
    "description": "Execute action on multiple accounts and multiple clusters",
    "parallel_execution": true,
    "steps": [
      {
        "account_ids": [1, 2],
        "cluster_ids": [1, 2, 3],
        "action_type": "purchase_training",
        "parameters": {
          "training_type": "defense_soldiers",
          "count": 25
        }
      }
    ]
  }'

# Check job status
curl -X GET "http://localhost:8000/api/v1/jobs/1/status"

# Cancel a job
curl -X POST "http://localhost:8000/api/v1/jobs/1/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "User requested cancellation"}'

# List all jobs
curl -X GET "http://localhost:8000/api/v1/jobs/"

# Get valid action types for job steps
curl -X GET "http://localhost:8000/api/v1/jobs/valid-action-types"
```

**Note:** Replace `8000` with `8001` if using `start_api.py`

### When to Use Sequential vs Parallel Execution

**Sequential Execution** (`parallel_execution: false` - default):
- ✅ Use when steps depend on each other (e.g., training soldiers before buying weapons)
- ✅ Use when you need predictable order of execution
- ✅ Use for actions on the same account to avoid conflicts
- ✅ Use when you want to stop execution if a step fails

**Parallel Execution** (`parallel_execution: true`):
- ✅ Use when steps are independent of each other
- ✅ Use for actions on different accounts
- ✅ Use when you want maximum speed and all steps can run simultaneously
- ✅ Use for bulk operations where order doesn't matter

### Combined Account and Cluster Targeting

The job system supports flexible targeting by combining multiple account IDs and cluster IDs in a single step:

#### How It Works:
1. **Combines all targeting methods** into a unified set of account IDs
2. **Expands clusters** to individual account IDs
3. **Deduplicates accounts** (removes duplicates if an account is in both account_ids and cluster expansion)
4. **Creates separate steps** for each unique account
5. **Maintains execution order** within the expanded steps

#### Examples:

**Cluster-only targeting:**
```json
{
  "cluster_ids": [1, 2],
  "action_type": "recruit"
}
```
*Expands to all accounts in clusters 1 and 2*

**Account-only targeting:**
```json
{
  "account_ids": [1, 2, 3],
  "action_type": "recruit"
}
```
*Executes on specific accounts 1, 2, and 3*

**Combined targeting (NEW!):**
```json
{
  "account_ids": [1, 2, 3],
  "cluster_ids": [1, 2],
  "action_type": "recruit"
}
```

**Expansion Example:**
- account_ids: [1, 2, 3]
- cluster_ids: [1, 2] → expands to accounts [4, 5, 6]
- **Final unified set**: [1, 2, 3, 4, 5, 6] (no duplicates)
- **Creates 6 individual steps** for each account

This powerful combination allows you to target specific accounts AND entire clusters in a single step, making bulk operations incredibly flexible and efficient.

### Action Type Validation

All job steps must use valid action types from the AccountManager.ActionType enum. The system validates action types during job creation and provides helpful error messages.

**Valid Action Types:**

**Actions that require `target_id`:**
- `attack` - Attack other players
- `sabotage` - Sabotage other players  
- `spy` - Gather intelligence on other players
- `become_officer` - Become an officer of another player
- `send_credits` - Transfer credits to other players

**Actions that don't require `target_id`:**
- `recruit` - Recruit soldiers and mercenaries
- `purchase_armory` - Buy weapons and equipment
- `purchase_training` - Train soldiers
- `set_credit_saving` - Set credit saving to 'on' or 'off'
- `buy_upgrade` - Buy account upgrades
- `get_metadata` - Retrieve current account status
- `get_solved_captchas` - Get solved captcha solutions

**Note:** The `target_id` parameter is only passed to actions that need it. For actions like `get_metadata`, you don't need to specify a `target_id`.

**Validation:**
```bash
# Get current valid action types
curl -X GET "http://localhost:8000/api/v1/jobs/valid-action-types"
```

If you use an invalid action type, you'll get a clear error message:
```json
{
  "detail": "Invalid action_type 'invalid_action'. Valid types are: attack, sabotage, spy, become_officer, send_credits, recruit, purchase_armory, purchase_training, set_credit_saving, buy_upgrade, get_metadata, get_solved_captchas"
}
```

**Example - get_metadata without target_id:**
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Get Account Metadata",
    "description": "Retrieve metadata for multiple accounts",
    "parallel_execution": true,
    "steps": [
      {
        "account_ids": [1, 2, 3],
        "action_type": "get_metadata"
      }
    ]
  }'
```

## Architecture

### Core Components

1. **AccountManager** - Manages multiple ROC account sessions
2. **ROCAccountManager** - Handles individual account operations
3. **Database Models** - SQLAlchemy models for data persistence
4. **API Endpoints** - FastAPI routers for REST operations

### Database Schema

- **accounts** - Account information and credentials
- **account_logs** - Activity logs for each account
- **account_actions** - Detailed action history and results

### Security Features

- Password hashing with SHA-256
- Session management with secure cookies
- CORS configuration for frontend integration
- Input validation with Pydantic models

## Configuration

The API can be configured through environment variables. Create a `.env` file in your project root or set environment variables directly.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/roc_cluster.db` | Database connection string |
| `ROC_BASE_URL` | `https://rocgame.com` | ROC website base URL |
| `HOST` | `0.0.0.0` | API server host |
| `PORT` | `8000` | API server port |
| `DEBUG` | `False` | Enable debug mode |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | `20` | Number of database connections in pool |
| `DB_MAX_OVERFLOW` | `30` | Additional connections on demand |
| `DB_POOL_RECYCLE` | `3600` | Connection recycle time (seconds) |

### Performance & Concurrency

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_OPERATIONS` | `20` | Max concurrent operations |
| `HTTP_CONNECTION_LIMIT` | `20` | Total HTTP connection pool size |
| `HTTP_CONNECTION_LIMIT_PER_HOST` | `10` | Max connections per host |
| `HTTP_TIMEOUT` | `30` | HTTP request timeout (seconds) |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `` | Optional log file path |

### Example Configuration Files

**Development (.env):**
```bash
DEBUG=True
LOG_LEVEL=DEBUG
MAX_CONCURRENT_OPERATIONS=5
HTTP_CONNECTION_LIMIT=10
DB_POOL_SIZE=5
```

**Production (.env):**
```bash
DEBUG=False
LOG_LEVEL=INFO
MAX_CONCURRENT_OPERATIONS=50
HTTP_CONNECTION_LIMIT=100
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

## Development

### Project Structure
```
roc-cluster/
├── main.py                    # FastAPI application entry point
├── start_api.py              # Alternative startup script with defaults
├── config.py                 # Configuration settings
├── requirements.txt          # Full Python dependencies
├── requirements-minimal.txt  # Minimal dependencies for compatibility
├── install_windows.bat       # Windows batch installation script
├── install_windows.ps1       # Windows PowerShell installation script
├── example_usage.py          # Example API usage script
├── import_users.py           # User import utility
├── CONFIGURATION.md          # Detailed configuration guide
├── TROUBLESHOOTING.md        # Troubleshooting guide
├── data/                     # Database files
│   ├── roc_cluster.db       # Development database
│   └── roc_clusterPROD.db   # Production database
├── api/
│   ├── __init__.py
│   ├── database.py          # Database configuration
│   ├── models.py            # Database and Pydantic models
│   ├── account_manager.py   # Account management logic
│   ├── game_account_manager.py # ROC-specific account operations
│   ├── action_logger.py     # Action logging
│   ├── async_logger.py      # Async logging service
│   ├── captcha.py           # CAPTCHA handling
│   ├── captcha_feedback_service.py # CAPTCHA feedback service
│   ├── credit_logger.py     # Credit transaction logging
│   ├── pagination.py        # API pagination utilities
│   ├── rocurlgenerator.py   # ROC URL generation utilities
│   └── endpoints/
│       ├── __init__.py
│       ├── accounts.py      # Account management endpoints
│       └── actions.py       # Action execution endpoints
└── errors/                   # Error handling utilities
```

### Adding New Actions

1. Add the action method to `ROCAccountManager` class
2. Create a Pydantic request model in `models.py`
3. Add the endpoint in `actions.py`
4. Update the action mapping in `AccountManager.execute_action()`

### Additional Utilities

#### Example Usage Script
Test the API with the provided example:
```bash
python example_usage.py
```

#### User Import Utility
Import users from CSV or other formats:
```bash
python import_users.py
```

#### Configuration Files
- **CONFIGURATION.md**: Detailed configuration guide with all environment variables
- **TROUBLESHOOTING.md**: Comprehensive troubleshooting guide
- **requirements-minimal.txt**: Minimal dependencies for compatibility issues

## Performance Considerations

- **Async Operations**: All I/O operations are asynchronous for better concurrency
- **Connection Pooling**: Database connections are pooled for efficiency
- **Job Management**: Asynchronous job execution with status tracking and cancellation
- **Caching**: Account metadata is cached to reduce API calls
- **Rate Limiting**: Built-in rate limiting to prevent abuse

### Performance Tuning Guidelines

#### Small Deployments (< 10 accounts)
```bash
MAX_CONCURRENT_OPERATIONS=5
HTTP_CONNECTION_LIMIT=10
DB_POOL_SIZE=5
```

#### Medium Deployments (10-100 accounts)
```bash
MAX_CONCURRENT_OPERATIONS=20
HTTP_CONNECTION_LIMIT=20
DB_POOL_SIZE=20
```

#### Large Deployments (100+ accounts)
```bash
MAX_CONCURRENT_OPERATIONS=50
HTTP_CONNECTION_LIMIT=100
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

#### Windows-Specific Recommendations
Windows has lower file descriptor limits. Use conservative settings:
```bash
MAX_CONCURRENT_OPERATIONS=10
HTTP_CONNECTION_LIMIT=15
HTTP_CONNECTION_LIMIT_PER_HOST=5
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=15
```

### Monitoring Key Metrics
- Active file descriptors
- Database connection pool usage
- HTTP connection pool usage
- Queue sizes for async services
- Memory usage patterns

## Error Handling

The API provides comprehensive error handling:
- HTTP status codes for different error types
- Detailed error messages in responses
- Logging for debugging and monitoring
- Graceful degradation for partial failures

## Troubleshooting

### Installation Issues

#### Windows Build Errors
If you encounter build errors with pydantic-core or other packages:

1. **Use the Windows installation scripts:**
   ```cmd
   install_windows.bat
   ```
   or
   ```powershell
   .\install_windows.ps1
   ```

2. **Try minimal requirements:**
   ```bash
   pip install -r requirements-minimal.txt
   ```

3. **Install Visual Studio Build Tools:**
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "C++ build tools" workload
   - Restart terminal and try again

4. **Use conda instead of pip:**
   ```bash
   conda create -n roc-cluster python=3.9
   conda activate roc-cluster
   pip install -r requirements-minimal.txt
   ```

#### Python Version Issues
- **Minimum Requirements:** Python 3.8 or higher
- **Check version:** `python --version`
- **Upgrade pip:** `python -m pip install --upgrade pip`

### Runtime Issues

#### API Server Won't Start
**Port already in use:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Use different port
export PORT=8001  # Linux/Mac
set PORT=8001     # Windows
```

#### Database Connection Errors
- Ensure the `data/` directory is writable
- Check file permissions for SQLite database
- For PostgreSQL/MySQL: verify connection string and server status

#### Account Management Issues
- **Login failures:** Verify ROC website credentials and connectivity
- **CAPTCHA issues:** Check captcha solver configuration

### Performance Issues

#### Slow API Responses
- Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
- Optimize database queries and add indexes
- Monitor memory usage and implement cleanup

#### High CPU Usage
- Reduce `MAX_CONCURRENT_OPERATIONS`
- Implement proper rate limiting
- Ensure all I/O operations are async

### Common Error Messages

| Error | Solution |
|-------|----------|
| "Account manager not initialized" | Restart API server, check database connection |
| "Account not found" | Verify account ID exists in database |
| "Failed to retrieve metadata" | Check ROC website connectivity and credentials |
| "Action failed" | Review error logs, check ROC website status |

### Debug Mode
Enable detailed logging:
```bash
export DEBUG=True
export LOG_LEVEL=DEBUG
```

### Getting Help
1. Check the logs for detailed error messages
2. Review API documentation at `/docs`
3. Test with `python example_usage.py`
4. Verify environment meets requirements
5. Check ROC website accessibility

For more detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions, please create an issue in the repository or contact the development team.
