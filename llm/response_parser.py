"""
Парсинг и починка JSON-ответов от LLM.

LLM часто ломают JSON:
- Добавляют текст до/после
- Оборачивают в ```json
- Ломают кавычки
- Путают типы (None вместо null)

Этот модуль пытается извлечь валидный JSON.
"""

import json
import re
from typing import Optional
import logging

from pydantic import ValidationError
from data.models import Insight, InsightType

logger = logging.getLogger(__name__)


class JSONParseError(Exception):
    """Не удалось распарсить JSON даже после repair"""
    pass


def extract_json(text: str) -> dict:
    """
    Извлекает JSON из ответа LLM.
    
    Пробует по порядку:
    1. Прямой парсинг
    2. Извлечение из ```json блока
    3. Поиск { ... } в тексте
    4. Починка частых ошибок
    
    Args:
        text: сырой ответ от LLM
        
    Returns:
        dict с распарсенным JSON
        
    Raises:
        JSONParseError: если не удалось извлечь JSON
    """
    if not text or not text.strip():
        raise JSONParseError("Пустой ответ от LLM")
    
    # 1. Прямой парсинг
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 2. Извлечение из markdown code block
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 3. Поиск JSON объекта в тексте
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        json_str = json_match.group(0)
        
        # 3.1 Прямой парсинг найденного
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 3.2 Починка частых ошибок
        json_str = _repair_json(json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    raise JSONParseError("Не удалось извлечь JSON из ответа LLM")


def _repair_json(json_str: str) -> str:
    """
    Починка частых ошибок в JSON.
    
    Исправляет:
    - Trailing commas: {a: 1,} -> {a: 1}
    - Single quotes: {'a': 1} -> {"a": 1}
    - Python None -> null
    - Python True/False -> true/false
    """
    # Trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Single quotes -> double quotes (осторожно с апострофами)
    # Только если нет двойных кавычек рядом
    json_str = re.sub(r"(?<![\"\\])'([^']*)'(?![\"\\])", r'"\1"', json_str)
    
    # Python None -> null
    json_str = re.sub(r'\bNone\b', 'null', json_str)
    
    # Python True/False -> true/false
    json_str = re.sub(r'\bTrue\b', 'true', json_str)
    json_str = re.sub(r'\bFalse\b', 'false', json_str)
    
    return json_str


def parse_insights(raw_response: str) -> list[Insight]:
    """
    Парсит список инсайтов из ответа LLM.
    
    Args:
        raw_response: сырой текст ответа от LLM
        
    Returns:
        list[Insight]: список валидированных инсайтов
        
    Raises:
        JSONParseError: если не удалось распарсить
    """
    logger.debug(f"Парсинг ответа LLM ({len(raw_response)} символов)")
    
    try:
        data = extract_json(raw_response)
    except JSONParseError as e:
        # Включаем начало ответа для отладки
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        logger.error(f"Не удалось извлечь JSON: {e}. Ответ: {preview}")
        raise JSONParseError(f"{e}. Начало ответа: {preview}")
    
    if 'insights' not in data:
        preview = raw_response[:300] + "..." if len(raw_response) > 300 else raw_response
        logger.error(f"В ответе отсутствует поле 'insights': {preview}")
        raise JSONParseError(f"В ответе отсутствует поле 'insights'. Ответ: {preview}")
    
    insights = []
    
    for i, item in enumerate(data['insights']):
        try:
            # Нормализуем type
            item_type = item.get('type', '').lower()
            if item_type not in ['problem', 'observation', 'opportunity']:
                logger.warning(f"Неизвестный тип инсайта '{item_type}', используем observation")
                item_type = 'observation'
            
            insight = Insight(
                type=InsightType(item_type),
                title=item.get('title', 'Без названия'),
                explanation=item.get('explanation', ''),
                recommendation=item.get('recommendation', ''),
                potential_impact=item.get('potential_impact')
            )
            insights.append(insight)
            
        except (ValidationError, KeyError) as e:
            # Пропускаем битый инсайт, но логируем
            logger.warning(f"Ошибка парсинга инсайта {i}: {e}")
            continue
    
    if not insights:
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        logger.error(f"Не удалось распарсить ни одного инсайта: {preview}")
        raise JSONParseError(f"Не удалось распарсить ни одного инсайта. Ответ: {preview}")
    
    logger.info(f"Успешно распарсено {len(insights)} инсайтов")
    return insights

