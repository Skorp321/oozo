from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = Field(default="dummy_key", env="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL_NAME")
    max_tokens: int = Field(default=4000, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    # Embedding Model Configuration
    embedding_model_name: str = Field(default="./models/multilingual-e5-large", env="EMBEDDING_MODEL_NAME")
    
    # File Paths
    docs_path: str = Field(default="../docs", env="DOCS_PATH")
    index_path: str = Field(default="./data/faiss_index", env="INDEX_PATH")
    logs_path: str = Field(default="./data/logs/qa_logs.jsonl", env="LOGS_PATH")
    
    # Document Processing Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # API Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 