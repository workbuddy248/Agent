"""
Configuration settings for the E2E Testing Agent Backend
File: backend/core/config.py
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS Configuration
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Template Configuration
    TEMPLATES_DIR: str = "templates"
    
    # Playwright Configuration
    PLAYWRIGHT_TIMEOUT: int = 30000
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_PROMPT_PATH: str = os.path.join(os.getcwd(), "prompt.md")
    
    # Session Configuration
    SESSION_TIMEOUT: int = 3600  # 1 hour in seconds
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Test Execution Configuration
    TEST_OUTPUT_DIR: str = "test_outputs"
    MAX_CONCURRENT_TESTS: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
