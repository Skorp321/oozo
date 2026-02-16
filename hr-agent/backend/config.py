from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = Field(default="dummy_key", env="OPENAI_API_KEY")
    openai_model_name: str = Field(default="model-run-vekow-trunk", env="OPENAI_MODEL_NAME")
    openai_api_base: Optional[str] = Field(default="https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1", env="OPENAI_API_BASE")
    max_tokens: int = Field(default=4000, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    # Embedding Model Configuration
    embedding_model_name: str = Field(default="qwen3-0.6B-embedded", env="EMBEDDING_MODEL_NAME")
    embedding_api_base: Optional[str] = Field(default=None, env="EMBEDDING_API_BASE")
    embedding_api_key: Optional[str] = Field(default="dummy_key", env="EMBEDDING_API_KEY")
    
    # File Paths
    docs_path: str = Field(default="../docs", env="DOCS_PATH")
    index_path: str = Field(default="./data/faiss_index", env="INDEX_PATH")
    
    # Document Processing Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
