# Configuration Guide

This document describes all the configurable settings for the ROC Cluster Management API.

## Environment Variables

All configuration can be set via environment variables. Here's a complete list:

### Server Settings
```bash
HOST=0.0.0.0                    # Server host address
PORT=8000                       # Server port
DEBUG=False                     # Enable debug mode
```

### Database Settings
```bash
DATABASE_URL=sqlite:///./data/roc_cluster.db  # Database connection URL

# Database Connection Pooling
DB_POOL_SIZE=20                 # Number of connections to maintain in the pool
DB_MAX_OVERFLOW=30              # Additional connections that can be created on demand
DB_POOL_RECYCLE=3600            # Recycle connections after this many seconds (1 hour)
```

### ROC Website Settings
```bash
ROC_BASE_URL=https://rocgame.com
ROC_LOGIN_URL=https://rocgame.com/login
ROC_HOME_URL=https://rocgame.com/home
```

### Logging
```bash
LOG_LEVEL=INFO                  # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_FILE=                       # Optional log file path
```

### Concurrency Control
```bash
# Maximum number of concurrent operations (prevents resource exhaustion)
MAX_CONCURRENT_OPERATIONS=20
```

### HTTP Connection Limits
```bash
# Total HTTP connection pool size
HTTP_CONNECTION_LIMIT=20
# Maximum connections per host
HTTP_CONNECTION_LIMIT_PER_HOST=10
# DNS cache TTL in seconds
HTTP_DNS_CACHE_TTL=300
# HTTP request timeout in seconds
HTTP_TIMEOUT=30
```

### Captcha Solver Connection Limits
```bash
# Total captcha solver connection pool size
CAPTCHA_CONNECTION_LIMIT=10
# Maximum captcha solver connections per host
CAPTCHA_CONNECTION_LIMIT_PER_HOST=5
# Captcha solver timeout in seconds
CAPTCHA_TIMEOUT=30
```

### Async Service Queue Limits
```bash
# Maximum queue size for async logger
ASYNC_LOGGER_QUEUE_SIZE=1000
# Maximum queue size for captcha feedback service
CAPTCHA_FEEDBACK_QUEUE_SIZE=1000
```

### CORS Settings
```bash
CORS_ORIGINS=*                  # Comma-separated list of allowed origins
```

## Configuration Examples

### Development Environment
```bash
DEBUG=True
LOG_LEVEL=DEBUG
MAX_CONCURRENT_OPERATIONS=5
HTTP_CONNECTION_LIMIT=10
DB_POOL_SIZE=5
```

### Production Environment
```bash
DEBUG=False
LOG_LEVEL=INFO
MAX_CONCURRENT_OPERATIONS=50
HTTP_CONNECTION_LIMIT=100
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

### High-Load Environment
```bash
MAX_CONCURRENT_OPERATIONS=100
HTTP_CONNECTION_LIMIT=200
HTTP_CONNECTION_LIMIT_PER_HOST=50
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=200
ASYNC_LOGGER_QUEUE_SIZE=5000
CAPTCHA_FEEDBACK_QUEUE_SIZE=5000
```

## Performance Tuning Guidelines

### For Small Deployments (< 10 accounts)
- `MAX_CONCURRENT_OPERATIONS=5`
- `HTTP_CONNECTION_LIMIT=10`
- `DB_POOL_SIZE=5`

### For Medium Deployments (10-100 accounts)
- `MAX_CONCURRENT_OPERATIONS=20`
- `HTTP_CONNECTION_LIMIT=20`
- `DB_POOL_SIZE=20`

### For Large Deployments (100+ accounts)
- `MAX_CONCURRENT_OPERATIONS=50`
- `HTTP_CONNECTION_LIMIT=100`
- `DB_POOL_SIZE=50`
- Consider load balancing across multiple instances

## Windows-Specific Recommendations

On Windows, file descriptor limits are often lower. Consider these settings:

```bash
# Conservative settings for Windows
MAX_CONCURRENT_OPERATIONS=10
HTTP_CONNECTION_LIMIT=15
HTTP_CONNECTION_LIMIT_PER_HOST=5
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=15
```

## Monitoring and Troubleshooting

### Key Metrics to Monitor
- Active file descriptors
- Database connection pool usage
- HTTP connection pool usage
- Queue sizes for async services

### Common Issues
1. **"Too many file descriptors"** - Reduce connection limits
2. **Slow performance** - Increase connection limits and pool sizes
3. **Memory usage** - Reduce queue sizes and connection limits
4. **Database timeouts** - Increase DB_POOL_SIZE and DB_MAX_OVERFLOW

### Environment File Setup
Create a `.env` file in your project root with the desired settings:

```bash
# .env file
DEBUG=True
LOG_LEVEL=DEBUG
MAX_CONCURRENT_OPERATIONS=10
HTTP_CONNECTION_LIMIT=20
```

The application will automatically load these environment variables on startup.
