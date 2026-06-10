---
name: pydantic-settings
description: Pydantic v2 Settings patterns for inp-backend. Use when extending app/core/config.py — env validation, Field() patterns, backward compatibility, and the rule to never read os.getenv outside this file.
---

# Pydantic Settings — `inp-backend`

## File in scope

- `app/core/config.py` — `class Settings(BaseSettings)` and `get_settings()` cache
- `.env.example` — template (tracked)
- `.env` — local dev (gitignored)

## Template

```python
# app/core/config.py
from functools import lru_cache
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # unknown env keys don't crash the app
    )

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # JWT
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32)
    access_token_expire_minutes: int = Field(90, env="ACCESS_TOKEN_EXPIRE_MINUTES", ge=1)
    algorithm: str = Field("HS256", env="ALGORITHM", pattern="^(HS256|HS384|HS512)$")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS", ge=1)

    # CORS
    allowed_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], env="ALLOWED_ORIGINS")

    # Optionals (LLM providers — priority order is in app/services/llm_service.py)
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    openrouter_chat_model: str = Field("deepseek/deepseek-r1-distill-llama-70b", env="OPENROUTER_CHAT_MODEL")
    apifreell_api_key: Optional[str] = Field(default=None, env="APIFREELL_API_KEY")
    apifreell_chat_model: str = Field("deepseek-r1-distill-llama-70b", env="APIFREELL_CHAT_MODEL")
    glm_api_key: Optional[str] = Field(default=None, env="GLM_API_KEY")
    glm_chat_model: str = Field("glm-4.5", env="GLM_CHAT_MODEL")
    vultr_api_key: Optional[str] = Field(default=None, env="VULTR_API_KEY")

    # App
    environment: str = Field("development", env="ENVIRONMENT", pattern="^(development|staging|production)$")
    debug: bool = Field(False, env="DEBUG")
    frontend_url: str = Field("http://localhost:3000", env="FRONTEND_URL")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Conventions

- **All env access goes through `get_settings()`**. Never `os.getenv()` outside this file.
- **Required vs optional**: `Field(...)` for required (raises at startup), `Field(default=None)` for optional.
- **Validation**: `min_length`, `ge`, `le`, `pattern` on the field. Fail fast at boot, not at first request.
- **Lists**: accept CSV string from env, parse in a `field_validator`.
- **Backwards compat**: when adding a new env key, give it a default. When renaming, keep the old key reading.
- **Caching**: `get_settings()` is `@lru_cache`. Don't add mutable state to `Settings`.
- **Logging**: `get_logger(__name__)` from `app/core/logging.py`, never `print()`.

## Adding a new provider key

1. Add to `Settings` with a default of `None` (optional).
2. Add to `.env.example` with a comment.
3. Consume in the service file: `from app.core.config import get_settings; get_settings().<provider>_api_key`.
4. If the key is a secret, never log it, never return it in a response, never include in error messages.

## Don't do

- Don't read `os.environ["..."]` in a service file.
- Don't mutate `Settings` at runtime; treat it as immutable.
- Don't put file paths or computed values in `Settings`; compute at the call site.
