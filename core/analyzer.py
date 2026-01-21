"""
Оркестрация анализа — связывает все компоненты в единый пайплайн.

Пайплайн:
1. Парсинг файла (CSV/Excel)
2. Очистка данных
3. Расчёт метрик (локально)
4. Запрос к LLM
5. Парсинг инсайтов
6. Формирование результата
"""

import pandas as pd
import math
import logging
from typing import Optional

from config import settings
from data.parser import parse_file
from data.cleaner import clean_dataframe
from data.models import PnLData, PnLRow, AnalysisResult
from core.metrics import calculate_metrics
from llm import get_llm_client, SYSTEM_PROMPT, ANALYSIS_PROMPT, parse_insights

logger = logging.getLogger(__name__)


def analyze_file(
    file_path: str,
    user_context: str = ""
) -> AnalysisResult:
    """
    Полный цикл анализа файла.
    
    Args:
        file_path: путь к CSV/Excel файлу
        user_context: контекст от пользователя (опционально)
        
    Returns:
        AnalysisResult с метриками и инсайтами
        
    Raises:
        ValueError: если данных недостаточно
        ParseError: если файл не читается
    """
    logger.info(f"Начало анализа файла: {file_path}")
    
    # 1. Парсинг файла
    logger.debug("Шаг 1: Парсинг файла")
    df = parse_file(file_path)
    
    # 2. Очистка данных
    logger.debug("Шаг 2: Очистка данных")
    df, warnings = clean_dataframe(df)
    
    # 3. Применяем лимит строк
    if len(df) > settings.max_rows:
        logger.info(f"Данные ограничены до последних {settings.max_rows} периодов")
        df = df.tail(settings.max_rows)
        warnings.append(f"Ограничено до последних {settings.max_rows} периодов")
    
    # 4. Проверка минимума периодов
    if len(df) < settings.min_periods:
        raise ValueError(
            f"Недостаточно данных: найдено {len(df)} периодов, "
            f"минимум {settings.min_periods}"
        )
    
    # 5. Конвертация в модель
    logger.debug("Шаг 3: Конвертация в PnLData")
    pnl_data = _dataframe_to_pnl(df, user_context, warnings)
    
    # 6. Расчёт метрик ЛОКАЛЬНО
    logger.debug("Шаг 4: Расчёт метрик")
    metrics = calculate_metrics(pnl_data)
    
    # 7. Формирование промпта
    logger.debug("Шаг 5: Формирование промпта для LLM")
    table_md = _dataframe_to_markdown(df)
    metrics_json = metrics.model_dump_json(indent=2)
    
    prompt = ANALYSIS_PROMPT.format(
        table_markdown=table_md,
        metrics_json=metrics_json,
        user_context=user_context or "Не указан"
    )
    
    # 8. Запрос к LLM
    logger.debug("Шаг 6: Запрос к LLM")
    client = get_llm_client()
    raw_response = client.complete_with_repair([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])
    
    # 9. Парсинг инсайтов
    logger.debug("Шаг 7: Парсинг инсайтов")
    insights = parse_insights(raw_response)
    
    logger.info(f"Анализ завершён: {len(insights)} инсайтов")
    
    return AnalysisResult(
        metrics=metrics,
        insights=insights,
        parsing_warnings=pnl_data.parsing_warnings,
        llm_raw_response=raw_response
    )


def _dataframe_to_pnl(
    df: pd.DataFrame,
    context: str,
    warnings: list[str]
) -> PnLData:
    """Конвертация DataFrame в PnLData."""
    
    rows = []
    for _, row in df.iterrows():
        rows.append(PnLRow(
            period=row['period'].date(),
            revenue=row['revenue'],
            cogs=_safe_float(row.get('cogs')),
            rent=_safe_float(row.get('rent')),
            payroll=_safe_float(row.get('payroll')),
            marketing=_safe_float(row.get('marketing')),
            other_expenses=_safe_float(row.get('other_expenses'))
        ))
    
    return PnLData(
        rows=rows,
        business_context=context,
        parsing_warnings=warnings
    )


def _safe_float(value) -> Optional[float]:
    """Безопасная конвертация в float (обрабатывает NaN)."""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Конвертация DataFrame в markdown таблицу для LLM."""
    
    # Форматируем числа для читаемости
    df_display = df.copy()
    
    for col in df_display.columns:
        if col == 'period':
            df_display[col] = df_display[col].dt.strftime('%Y-%m')
        elif df_display[col].dtype in ['float64', 'int64']:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
            )
    
    return df_display.to_markdown(index=False)

