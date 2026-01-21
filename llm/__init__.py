"""
LLM module — интеграция с языковыми моделями.

AI-агностичная архитектура:
- LLMClient: абстрактный интерфейс
- get_llm_client(): фабрика для получения клиента
- OpenAIClient: реализация для OpenAI (Wave 1)

Использование:
    from llm import get_llm_client
    client = get_llm_client()
    response = client.complete([
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ])
"""

from llm.client import LLMClient, OpenAIClient, get_llm_client
from llm.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT
from llm.response_parser import parse_insights, extract_json, JSONParseError

__all__ = [
    # Client
    "LLMClient",
    "OpenAIClient", 
    "get_llm_client",
    # Prompts
    "SYSTEM_PROMPT",
    "ANALYSIS_PROMPT",
    # Parser
    "parse_insights",
    "extract_json",
    "JSONParseError",
]
