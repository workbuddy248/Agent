from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
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
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = "https://chat-ai.cisco.com"
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_APP_KEY: str = "hackathon-010-team-22"
    CISCO_IDP: str = "https://id.cisco.com/oauth2/default/v1/token"
    AZURE_CLIENT_ID: str = "cG9jLXRyaWFsMjAyNE5vdmVtYmVyMDcf-a96d2526070618ffe287a86f12dcbf"
    AZURE_CLIENT_SECRET: str = "lOyQVkOx4BB712-7kCy0mvgfEyQGyWKwdPhKvbG4XU3mTCMLutrusICO5IqcHsp-"
    AZURE_OPENAI_MODEL: str = "gpt-4.1"
    AZURE_OPENAI_API_VERSION: str = "2024-07-01-preview"
    
    # Alternative: OpenAI Configuration (if not using Azure)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # Test Generation Configuration
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 60
    GENERATION_TEMPERATURE: float = 0.1
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()