"""
LLM клиенты для FinRentgen.

Архитектура AI-агностична:
- LLMClient — абстрактный Protocol (интерфейс)
- OpenAIClient — реализация для OpenAI (Wave 1)
- В Wave 2 добавятся: YandexGPTClient, GigaChatClient

Использование:
    from llm import get_llm_client
    client = get_llm_client()
    response = client.complete(messages)
"""

from typing import Protocol, runtime_checkable
import time
import logging

from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMClient(Protocol):
    """
    Абстрактный интерфейс LLM клиента.
    
    Все реализации (OpenAI, YandexGPT, GigaChat) должны
    реализовывать этот интерфейс.
    """
    
    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Отправляет запрос к LLM и возвращает текстовый ответ.
        
        Args:
            messages: список сообщений [{role, content}, ...]
            temperature: креативность (0.0 - 1.0)
            max_tokens: максимум токенов в ответе
            
        Returns:
            str: текстовый ответ от LLM
        """
        ...
    
    def complete_with_repair(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Запрос с попыткой починить JSON если первый ответ невалидный.
        """
        ...


class OpenAIClient:
    """
    Клиент для OpenAI-совместимых API (OpenAI, Grok, и др.).
    
    Особенности:
    - Retry с exponential backoff
    - Таймауты
    - JSON repair
    - Поддержка custom base_url (для Grok, Azure и др.)
    """
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.openai_model
        self.max_retries = settings.llm_max_retries
        self.timeout = settings.llm_timeout_seconds
        
        logger.info(f"LLM клиент инициализирован (model={self.model}, base_url={settings.openai_base_url})")
    
    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Запрос к OpenAI с retry.
        
        Returns:
            str: сырой текст ответа
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"OpenAI запрос (попытка {attempt + 1}/{self.max_retries + 1})")
                
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout
                )
                
                elapsed = time.time() - start_time
                content = response.choices[0].message.content
                
                logger.info(f"OpenAI ответ получен за {elapsed:.1f}с ({len(content)} символов)")
                
                return content
                
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI ошибка (попытка {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4...
                    logger.debug(f"Ждём {wait_time}с перед повтором")
                    time.sleep(wait_time)
                    continue
                
                logger.error(f"OpenAI: все попытки исчерпаны. Последняя ошибка: {e}")
                raise
        
        raise last_error
    
    def complete_with_repair(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Запрос с попыткой починить JSON если первый ответ невалидный.
        
        Если LLM вернул невалидный JSON, просим его исправить.
        """
        from llm.response_parser import extract_json, JSONParseError
        
        response = self.complete(messages, temperature, max_tokens)
        
        # Пробуем распарсить
        try:
            extract_json(response)
            return response
        except JSONParseError:
            logger.warning("Первый ответ содержит невалидный JSON, просим исправить")
        
        # Просим LLM починить свой ответ
        repair_messages = messages + [
            {"role": "assistant", "content": response},
            {"role": "user", "content": 
                "Твой ответ содержит невалидный JSON. "
                "Выдай ТОЛЬКО исправленный JSON, без пояснений и markdown."
            }
        ]
        
        return self.complete(repair_messages, temperature=0.3, max_tokens=max_tokens)


# === Фабрика клиентов ===

def get_llm_client() -> LLMClient:
    """
    Фабрика для получения LLM клиента.
    
    В Wave 1 возвращает только OpenAIClient.
    В Wave 2 будет выбирать на основе настроек:
    - YANDEX_GPT_API_KEY -> YandexGPTClient
    - GIGACHAT_API_KEY -> GigaChatClient
    - OPENAI_API_KEY -> OpenAIClient (default)
    
    Returns:
        LLMClient: инстанс клиента
    """
    # Wave 1: только OpenAI
    return OpenAIClient()

