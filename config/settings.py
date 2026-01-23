# config/settings.py
"""
配置管理 - 使用 Pydantic Settings
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # OpenAI 配置
    openai_api_key: str = Field(
        default="sk-xxxxxx",
        alias="OPENAI_API_KEY"
    )
    openai_base_url: str = Field(
        default="https://api.v36.cm/v1",
        alias="OPENAI_BASE_URL"
    )

    # 模型配置
    chat_model: str = "gemini-2.5-flash-thinking"
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.3
    max_tokens: int = 2048

    # 存储配置
    sqlite_db_path: str = "knowledge.db"
    vector_db_path: str = "./chroma_db"

    # Agent 配置
    max_iterations: int = 15
    proficiency_threshold: float = 0.7
    similarity_threshold: float = 0.6

    # MCP 配置
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 8765

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()
