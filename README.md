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

### Bulk Operations
- Execute actions across multiple accounts simultaneously
- Parallel processing for improved performance
- Comprehensive error handling and reporting

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd roc-cluster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (optional):
```bash
export DATABASE_URL="sqlite:///./roc_cluster.db"
export SECRET_KEY="your-secret-key"
export ROC_BASE_URL="https://rocgame.com"
```

4. Run the API:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

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

### Bulk Training Purchase
```bash
curl -X POST "http://localhost:8000/api/v1/actions/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": [1, 2, 3],
    "action_type": "purchase_training",
    "parameters": {
      "training_type": "attack_soldiers",
      "count": 100
    }
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

The API can be configured through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./roc_cluster.db` | Database connection string |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT secret key |
| `ROC_BASE_URL` | `https://rocgame.com` | ROC website base URL |
| `HOST` | `0.0.0.0` | API server host |
| `PORT` | `8000` | API server port |
| `DEBUG` | `False` | Enable debug mode |

## Development

### Project Structure
```
roc-cluster/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── api/
│   ├── __init__.py
│   ├── database.py        # Database configuration
│   ├── models.py          # Database and Pydantic models
│   ├── account_manager.py # Account management logic
│   └── endpoints/
│       ├── __init__.py
│       ├── accounts.py    # Account management endpoints
│       └── actions.py     # Action execution endpoints
└── examples/              # Original ROC interaction examples
    ├── rocwebhandler.py
    ├── trainer.py
    ├── buyer.py
    └── models.py
```

### Adding New Actions

1. Add the action method to `ROCAccountManager` class
2. Create a Pydantic request model in `models.py`
3. Add the endpoint in `actions.py`
4. Update the action mapping in `AccountManager.execute_action()`

## Performance Considerations

- **Async Operations**: All I/O operations are asynchronous for better concurrency
- **Connection Pooling**: Database connections are pooled for efficiency
- **Bulk Operations**: Multiple accounts can be processed in parallel
- **Caching**: Account metadata is cached to reduce API calls
- **Rate Limiting**: Built-in rate limiting to prevent abuse

## Error Handling

The API provides comprehensive error handling:
- HTTP status codes for different error types
- Detailed error messages in responses
- Logging for debugging and monitoring
- Graceful degradation for partial failures

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
