# Troubleshooting Guide

## Installation Issues

### Windows Build Errors (pydantic-core)

If you encounter build errors like:
```
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

**Solutions:**

1. **Use the minimal requirements file:**
   ```bash
   pip install -r requirements-minimal.txt
   ```

2. **Use the Windows installation script:**
   ```cmd
   install_windows.bat
   ```
   or
   ```powershell
   .\install_windows.ps1
   ```

3. **Install Visual Studio Build Tools:**
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "C++ build tools" workload
   - Restart your terminal and try again

4. **Use conda instead of pip:**
   ```bash
   conda create -n roc-cluster python=3.9
   conda activate roc-cluster
   pip install -r requirements-minimal.txt
   ```

5. **Use pre-compiled wheels:**
   ```bash
   pip install --only-binary=all -r requirements-minimal.txt
   ```

### Python Version Issues

**Minimum Requirements:**
- Python 3.8 or higher
- pip 20.0 or higher

**Check your Python version:**
```bash
python --version
```

**Upgrade pip:**
```bash
python -m pip install --upgrade pip
```

### Virtual Environment Issues

**Create a fresh virtual environment:**
```bash
# Remove old environment
rm -rf .venv  # Linux/Mac
rmdir /s .venv  # Windows

# Create new environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows
```

## Runtime Issues

### Database Connection Errors

**SQLite Issues:**
- Ensure the directory is writable
- Check file permissions
- Try using an absolute path for the database

**PostgreSQL/MySQL Issues:**
- Verify connection string format
- Check if database server is running
- Verify credentials and permissions

### API Server Won't Start

**Port Already in Use:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Kill the process or use a different port
export PORT=8001  # Linux/Mac
set PORT=8001  # Windows
```

**Permission Issues:**
- Run as administrator (Windows)
- Check firewall settings
- Verify network configuration

### Account Management Issues

**Login Failures:**
- Verify ROC website credentials
- Check if ROC website is accessible
- Review network connectivity
- Check for CAPTCHA requirements

**Session Timeouts:**
- Increase session timeout in config
- Implement session refresh logic
- Check cookie persistence

## Performance Issues

### Slow API Responses

**Database Optimization:**
- Add database indexes
- Use connection pooling
- Optimize queries

**Memory Usage:**
- Monitor account manager memory usage
- Implement account cleanup
- Use pagination for large datasets

### High CPU Usage

**Async Operations:**
- Ensure all I/O operations are async
- Use connection pooling
- Implement rate limiting

## Debugging

### Enable Debug Mode

**Environment Variables:**
```bash
export DEBUG=True
export LOG_LEVEL=DEBUG
```

**Or in config.py:**
```python
DEBUG = True
LOG_LEVEL = "DEBUG"
```

### Logging

**View Logs:**
- Check console output
- Review log files (if configured)
- Use structured logging for better debugging

### API Testing

**Use the example script:**
```bash
python example_usage.py
```

**Manual API testing:**
```bash
# Health check
curl http://localhost:8000/health

# List accounts
curl http://localhost:8000/api/v1/accounts/
```

## Common Error Messages

### "Account manager not initialized"
- Restart the API server
- Check database connection
- Verify configuration

### "Account not found"
- Verify account ID exists
- Check database for account records
- Ensure account is active

### "Failed to retrieve metadata"
- Check ROC website connectivity
- Verify account credentials
- Review session status

### "Action failed"
- Check ROC website status
- Verify action parameters
- Review error logs for details

## Getting Help

1. **Check the logs** for detailed error messages
2. **Review the API documentation** at `/docs`
3. **Test with the example script** to isolate issues
4. **Verify your environment** meets the requirements
5. **Check ROC website accessibility** from your network

## Environment-Specific Issues

### Windows
- Use Windows installation scripts
- Install Visual Studio Build Tools
- Check Windows Defender/firewall settings

### Linux
- Ensure proper permissions
- Check SELinux settings
- Verify package dependencies

### macOS
- Use Homebrew for dependencies
- Check Gatekeeper settings
- Verify Xcode command line tools

## Performance Tuning

### For Large Numbers of Accounts (100+)

1. **Database Optimization:**
   ```python
   # Use connection pooling
   engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=30)
   ```

2. **Async Processing:**
   ```python
   # Limit concurrent operations
   semaphore = asyncio.Semaphore(10)  # Max 10 concurrent operations
   ```

3. **Caching:**
   ```python
   # Cache account metadata
   @lru_cache(maxsize=100)
   async def get_cached_metadata(account_id):
       # Implementation
   ```

4. **Rate Limiting:**
   ```python
   # Implement rate limiting for ROC website calls
   rate_limiter = RateLimiter(calls=60, period=60)  # 60 calls per minute
   ```
