"""
Конфигурация приложения FinRentgen.
Загружает настройки из переменных окружения / .env файла.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # === Приложение ===
    app_name: str = "FinRentgen"
    debug: bool = False
    
    # === LLM (Wave 1: OpenAI-совместимые API) ===
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"  # Для Grok: https://api.x.ai/v1
    
    # === Лимиты данных ===
    max_file_size_mb: int = 5
    max_rows: int = 100      # Максимум строк для анализа
    min_periods: int = 3     # Минимум периодов для анализа
    
    # === LLM retry ===
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
# Загружается при импорте модуля
settings = Settings()

