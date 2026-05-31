"""
Centralized configuration management using Pydantic Settings.
Provides environment validation, type checking, and backward compatibility.
"""
import os
from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment validation and type checking."""
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    
    # JWT Configuration
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(90, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field("HS256", env="ALGORITHM")
    
    # Session Configuration
    session_secret_key: Optional[str] = Field(None, env="SESSION_SECRET_KEY")
    
    # Stripe Configuration
    stripe_secret_key: Optional[str] = Field(None, env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(None, env="STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: Optional[str] = Field(None, env="STRIPE_PUBLISHABLE_KEY")
    
    # OAuth Configuration
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(None, env="GOOGLE_REDIRECT_URI")
    
    # Application Configuration
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    frontend_url: str = Field("http://localhost:3000", env="FRONTEND_URL")
    
    # CORS Configuration
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost",
            "https://app.insightpilot.co",
            "https://inp-dashboard.netlify.app",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "https://localhost",
            "https://localhost:3000",
        ],
        env="ALLOWED_ORIGINS"
    )
    
    # Database Connection Pool Settings
    db_pool_size: int = Field(5, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or text
    
    # Security Configuration
    enable_security_headers: bool = Field(True, env="ENABLE_SECURITY_HEADERS")
    enable_rate_limiting: bool = Field(True, env="ENABLE_RATE_LIMITING")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(8001, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @validator('allowed_origins', pre=True)
    def parse_origins(cls, v):
        """Parse comma-separated origins string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment values."""
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v.lower() not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v.lower()
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level values."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    Uses LRU cache to avoid re-reading environment variables on every call.
    """
    return Settings()


# Dependency for FastAPI dependency injection
def get_config() -> Settings:
    """FastAPI dependency for injecting configuration."""
    return get_settings()


# Backward compatibility - maintain existing environment loading behavior
def load_environment_variables():
    """
    Load environment variables from .env files with backward compatibility.
    This maintains the existing behavior while adding the new configuration system.
    """
    from dotenv import load_dotenv
    
    possible_env_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),  # project root
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # app directory
        '.env'  # current working directory
    ]
    
    env_found = False
    for env_path in possible_env_paths:
        if os.path.exists(env_path):
            print(f"[config.py] 💡 Found .env file at: {env_path}")
            load_dotenv(dotenv_path=env_path)
            env_found = True
            break
    
    if not env_found:
        print("[config.py] ⚠️ WARNING: No .env file found in any standard location!")
    
    return env_found


# Initialize environment loading on module import for backward compatibility
load_environment_variables()