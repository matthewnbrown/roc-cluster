"""
Configuration settings for ROC Cluster Management API
"""

import os
from typing import Optional

class Settings:
    """Application settings"""
    
    # API Settings
    API_TITLE: str = "ROC Cluster Management API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Lightweight API for managing multiple ROC accounts"
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

    
    # ROC Website Settings
    ROC_BASE_URL: str = os.getenv("ROC_BASE_URL", "https://rocgame.com")
    ROC_LOGIN_URL: str = os.getenv("ROC_LOGIN_URL", f"{ROC_BASE_URL}/login")
    ROC_HOME_URL: str = os.getenv("ROC_HOME_URL", f"{ROC_BASE_URL}/home")
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/roc_cluster.db")
    USE_IN_MEMORY_DB: bool = os.getenv("USE_IN_MEMORY_DB", "False").lower() == "true"
    IN_MEMORY_DB_URL: str = "sqlite:///:memory:"
    
    # Auto-save settings for in-memory database
    AUTO_SAVE_INTERVAL: int = int(os.getenv("AUTO_SAVE_INTERVAL", "300"))
    AUTO_SAVE_ENABLED: bool = os.getenv("AUTO_SAVE_ENABLED", "True").lower() == "true"
    AUTO_SAVE_BACKGROUND: bool = os.getenv("AUTO_SAVE_BACKGROUND", "True").lower() == "true"
    AUTO_SAVE_MEMORY_SNAPSHOT: bool = os.getenv("AUTO_SAVE_MEMORY_SNAPSHOT", "True").lower() == "true" 
    
    # Database Connection Pooling
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "1000"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "-1"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
    
    # Concurrency Control
    MAX_CONCURRENT_OPERATIONS: int = int(os.getenv("MAX_CONCURRENT_OPERATIONS", "100"))
    
    # HTTP Connection Limits - Optimized for high concurrency
    HTTP_CONNECTION_LIMIT: int = int(os.getenv("HTTP_CONNECTION_LIMIT", "40"))
    HTTP_CONNECTION_LIMIT_PER_HOST: int = int(os.getenv("HTTP_CONNECTION_LIMIT_PER_HOST", "40"))
    HTTP_DNS_CACHE_TTL: int = int(os.getenv("HTTP_DNS_CACHE_TTL", "300"))  # 5 minutes
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))  # seconds
    
    # Captcha Solver Settings
    CAPTCHA_SOLVER_URL: str = os.getenv("CAPTCHA_SOLVER_URL", "http://localhost:8001/api/v1/solve")
    CAPTCHA_REPORT_URL: str = os.getenv("CAPTCHA_REPORT_URL", "http://localhost:8001/api/v1/feedback")
    
    # Captcha Solver Connection Limits
    CAPTCHA_CONNECTION_LIMIT: int = int(os.getenv("CAPTCHA_CONNECTION_LIMIT", "50"))
    CAPTCHA_CONNECTION_LIMIT_PER_HOST: int = int(os.getenv("CAPTCHA_CONNECTION_LIMIT_PER_HOST", "50"))
    CAPTCHA_TIMEOUT: int = int(os.getenv("CAPTCHA_TIMEOUT", "30"))  # seconds
    
    # Async Service Queue Limits
    ASYNC_LOGGER_QUEUE_SIZE: int = int(os.getenv("ASYNC_LOGGER_QUEUE_SIZE", "1000"))
    CAPTCHA_FEEDBACK_QUEUE_SIZE: int = int(os.getenv("CAPTCHA_FEEDBACK_QUEUE_SIZE", "1000"))
    
    # CORS Settings
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Page Data Service
    USE_PAGE_DATA_SERVICE: bool = os.getenv("USE_PAGE_DATA_SERVICE", "False").lower() == "true"
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with proper formatting"""
        if cls.DATABASE_URL.startswith("sqlite"):
            return cls.DATABASE_URL
        elif cls.DATABASE_URL.startswith("postgresql"):
            return cls.DATABASE_URL
        elif cls.DATABASE_URL.startswith("mysql"):
            return cls.DATABASE_URL
        else:
            return f"sqlite:///./{cls.DATABASE_URL}"

# Global settings instance
settings = Settings()
