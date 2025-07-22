from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    openai_api_key: str = Field(description="OpenAI API key")
    shopgraph_api_key: str = Field(description="ShopGraph API key")
    otel_endpoint: str | None = Field(None, description="OpenTelemetry endpoint")
    log_level: str = Field("INFO", description="Logging level")
    # Timeout & CB
    default_timeout_s: float = 8.0
    cb_failure_threshold: int = 3
    cb_recovery_s: int = 60
    
    # ReAct Configuration
    react_max_iterations: int = Field(5, description="Maximum iterations for ReAct loop")
    react_confidence_threshold: float = Field(0.7, description="Confidence threshold for ReAct decisions")
    react_enable_dynamic_tool_chaining: bool = Field(True, description="Enable dynamic tool chaining in ReAct")
    react_enable_error_recovery: bool = Field(True, description="Enable error recovery in ReAct loop")

@lru_cache
def get_settings() -> Settings:
    return Settings()

