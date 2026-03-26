"""Configuration management for the RAG backend."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "production"] = "development"

    # LLM Configuration (OpenAI-compatible endpoint)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = "sk-your-api-key-here"
    llm_model: str = "gpt-4o-mini"

    # Embedding Model (Self-hosted)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Vector Store Configuration
    faiss_index_path: Path = Field(default=Path("./data/faiss_index"))
    documents_path: Path = Field(default=Path("./data/documents"))
    dataset_path: Path = Field(default=Path("./dataset"))

    # API Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 6969
    api_reload: bool = True
    auto_ingest_on_startup: bool = True  # Auto-ingest dataset on server start
    
    # CORS Configuration
    cors_origins: str = "*"  # Comma-separated origins or "*" for all
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunking_strategy: str = "dynamic"  # "fixed", "dynamic", or "semantic"
    top_k_results: int = 4
    max_tokens: int = 2000
    temperature: float = 0.7

    # Logging
    log_level: str = "INFO"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.faiss_index_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.dataset_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
