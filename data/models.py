"""
Pydantic модели данных для FinRentgen.

Модели:
- PnLRow: одна строка P&L (один период)
- PnLData: полный P&L со всеми строками
- CalculatedMetrics: метрики, посчитанные локально
- Insight: один инсайт от LLM
- AnalysisResult: полный результат анализа
"""

from pydantic import BaseModel, Field
from datetime import date
from enum import Enum
from typing import Optional


class InsightType(str, Enum):
    """Тип инсайта для цветовой кодировки"""
    PROBLEM = "problem"          # 🔴 Проблема
    OBSERVATION = "observation"  # 🟡 Наблюдение
    OPPORTUNITY = "opportunity"  # 🟢 Возможность


class TrendDirection(str, Enum):
    """Направление тренда выручки"""
    GROWING = "growing"                    # Растёт (>5%)
    STABLE = "stable"                      # Стабильно (-5% до +5%)
    DECLINING = "declining"                # Падает (<-5%)
    INSUFFICIENT_DATA = "insufficient_data"  # Мало данных (<6 периодов)


class PnLRow(BaseModel):
    """
    Одна строка P&L (один период).
    
    Обязательные поля: period, revenue
    Опциональные: все статьи расходов
    """
    period: date
    revenue: float = Field(..., gt=0, description="Выручка (должна быть > 0)")
    
    # Статьи расходов (опциональные)
    cogs: Optional[float] = Field(None, ge=0, description="Себестоимость")
    rent: Optional[float] = Field(None, ge=0, description="Аренда")
    payroll: Optional[float] = Field(None, ge=0, description="ФОТ (зарплаты)")
    marketing: Optional[float] = Field(None, ge=0, description="Маркетинг/реклама")
    other_expenses: Optional[float] = Field(None, ge=0, description="Прочие расходы")


class PnLData(BaseModel):
    """
    Полный P&L — список строк + метаданные.
    """
    rows: list[PnLRow]
    business_context: Optional[str] = None  # Контекст от пользователя
    parsing_warnings: list[str] = Field(default_factory=list)  # Что было исправлено при парсинге


class CalculatedMetrics(BaseModel):
    """
    Метрики, посчитанные ЛОКАЛЬНО (не LLM).
    
    LLM получает эти готовые цифры и только интерпретирует их.
    """
    
    # === Средние за период ===
    avg_revenue: float
    avg_cogs: Optional[float] = None
    avg_gross_profit: Optional[float] = None
    avg_gross_margin_pct: Optional[float] = None
    avg_operating_profit: float
    avg_operating_margin_pct: float
    
    # === Тренды (последние 3 периода vs предыдущие 3) ===
    revenue_trend_pct: float  # Процент изменения (+10% = растёт)
    revenue_trend_direction: TrendDirection
    
    # === Доли расходов от выручки (средние) ===
    cogs_share_pct: Optional[float] = None
    rent_share_pct: Optional[float] = None
    payroll_share_pct: Optional[float] = None
    marketing_share_pct: Optional[float] = None
    other_share_pct: Optional[float] = None
    
    # === Аномалии ===
    anomalies: list[str] = Field(default_factory=list)  # ["Маркетинг в марте вырос на 45%"]
    
    # === По периодам (для отображения) ===
    by_period: list[dict] = Field(default_factory=list)  # [{period, revenue, profit, margin}, ...]


class Insight(BaseModel):
    """
    Один инсайт от LLM.
    
    Структура:
    - type: тип для цветовой кодировки
    - title: краткий заголовок
    - explanation: что это значит
    - recommendation: что делать
    - potential_impact: возможный эффект (опционально)
    """
    type: InsightType
    title: str
    explanation: str
    recommendation: str
    potential_impact: Optional[str] = None


class AnalysisResult(BaseModel):
    """
    Полный результат анализа — всё, что нужно для отображения.
    """
    metrics: CalculatedMetrics      # Посчитано локально
    insights: list[Insight]         # От LLM
    parsing_warnings: list[str] = Field(default_factory=list)  # Что исправлено в данных
    llm_raw_response: Optional[str] = None  # Сырой ответ LLM (для отладки)

