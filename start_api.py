#!/usr/bin/env python3
"""
Startup script for the ROC Cluster Management API

This script provides an easy way to start the API server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Start the ROC Cluster Management API"""
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Set default environment variables if not already set
    env_vars = {
        "DATABASE_URL": "sqlite:///./roc_cluster.db",
        "HOST": "0.0.0.0",
        "PORT": "8001",
        "DEBUG": "True",
        "LOG_LEVEL": "INFO"
    }
    
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
    
    # Print startup information
    print("🚀 Starting ROC Cluster Management API")
    print("=" * 50)
    print(f"Host: {os.environ['HOST']}")
    print(f"Port: {os.environ['PORT']}")
    print(f"Debug: {os.environ['DEBUG']}")
    print(f"Database: {os.environ['DATABASE_URL']}")
    print("=" * 50)
    print("📚 API Documentation will be available at:")
    print(f"   - Swagger UI: http://{os.environ['HOST']}:{os.environ['PORT']}/docs")
    print(f"   - ReDoc: http://{os.environ['HOST']}:{os.environ['PORT']}/redoc")
    print("=" * 50)
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host=os.environ['HOST'],
            port=int(os.environ['PORT']),
            reload=os.environ['DEBUG'].lower() == 'true',
            log_level=os.environ['LOG_LEVEL'].lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down ROC Cluster Management API...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
