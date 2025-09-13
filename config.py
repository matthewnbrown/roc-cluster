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
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./roc_cluster.db")
    
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # ROC Website Settings
    ROC_BASE_URL: str = os.getenv("ROC_BASE_URL", "https://rocgame.com")
    ROC_LOGIN_URL: str = os.getenv("ROC_LOGIN_URL", f"{ROC_BASE_URL}/login")
    ROC_HOME_URL: str = os.getenv("ROC_HOME_URL", f"{ROC_BASE_URL}/home")
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    # Account Management
    MAX_ACCOUNTS_PER_USER: int = int(os.getenv("MAX_ACCOUNTS_PER_USER", "100"))
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    # CORS Settings
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
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
