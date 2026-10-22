from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。

    取值优先级：真实环境变量 > .env 文件 > 这里写的默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-5-5"
    deepseek_api_key: str | None = None

    # 上下文过长时的策略："truncate"（丢掉最早的）或 "summarize"（压成摘要）
    context_strategy: str = "truncate"
    context_token_budget: int = 2000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # 字段值来自环境变量，类型检查器看不到
