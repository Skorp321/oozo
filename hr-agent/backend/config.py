from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model_name: str = Field(env="OPENAI_MODEL_NAME")
    openai_api_base: Optional[str] = Field(env="OPENAI_API_BASE")
    max_tokens: int = Field(default=4000, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    # Embedding Model Configuration
    embedding_model_name: str = Field(default="qwen3-0.6B-embedded", env="EMBEDDING_MODEL_NAME")
    embedding_api_base: Optional[str] = Field(default=None, env="OPENAI_API_BASE")
    embedding_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # File Paths
    docs_path: str = Field(default="../docs", env="DOCS_PATH")
    index_path: str = Field(default="./data/faiss_index", env="INDEX_PATH")
    
    # Document Processing Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")

    # Arize Phoenix / OpenTelemetry Tracing
    phoenix_enabled: bool = Field(default=False, env="PHOENIX_ENABLED")
    phoenix_endpoint: str = Field(default="http://localhost:6006/v1/traces", env="PHOENIX_ENDPOINT")
    phoenix_protocol: str = Field(default="auto", env="PHOENIX_PROTOCOL")
    phoenix_project_name: str = Field(default="hr-agent", env="PHOENIX_PROJECT_NAME")
    phoenix_api_key: Optional[str] = Field(default=None, env="PHOENIX_API_KEY")
    
# Global settings instance
settings = Settings()
