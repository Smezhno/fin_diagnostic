# RFC: Финансовый анализатор для SMB (v3)

## Обзор проекта

**Название:** FinRentgen (рабочее)

**Цель:** Веб-приложение, которое анализирует финансовые данные малого бизнеса и выдаёт actionable инсайты.

**Целевой пользователь:** ИП/владелец малого бизнеса в России с оборотом 500К-5М₽/мес, без финансового директора.

**Стадия:** Прототип для customer development интервью.

---

## Волны разработки

### 🌊 Wave 1: Ultra-MVP (10-15 часов)

**Цель:** Минимальный продукт для первых 5-10 кастдев-интервью.

**Включает:**
- ✅ Загрузка файла (CSV, Excel)
- ✅ Парсинг с обработкой грязных данных
- ✅ Локальный расчёт всех метрик
- ✅ Анализ через OpenAI (один провайдер)
- ✅ Вывод инсайтов + ключевые метрики
- ✅ Базовый приятный UI

**НЕ включает:**
- ❌ Авторизация
- ❌ База данных
- ❌ Сохранение сессий
- ❌ Чат
- ❌ Сценарии "что если"
- ❌ Мульти-LLM

**Результат:** Можно показать людям, собрать фидбек, понять что важно.

---

### 🌊 Wave 2: MVP+ (после 5-10 интервью)

**Добавляется по результатам кастдевов:**
- Авторизация (email + пароль)
- Сохранение сессий в SQLite
- История анализов
- Чат с уточнениями
- Сценарии "что если"
- YandexGPT / GigaChat

**Решение о приоритетах — после Wave 1.**

---

## Архитектура Wave 1

### Принципы

1. **Метрики считаются локально** — LLM только интерпретирует готовые цифры
2. **Грязные данные — норма** — парсер готов к реальным Excel
3. **JSON может сломаться** — есть repair-механика
4. **Честное время** — "до 30 секунд" вместо оптимистичных 15
5. **AI-агностичность** — архитектура не завязана жёстко на OpenAI. В Wave 1 один клиент, но интерфейс проектируется под future-мульти-LLM (YandexGPT, GigaChat и др.)

---

### Структура проекта (Wave 1)

```
fin-analyzer/
├── app.py                  # Точка входа, Gradio UI
├── config.py               # Конфигурация
├── .env.example
│
├── core/
│   ├── __init__.py
│   ├── analyzer.py         # Оркестрация анализа
│   └── metrics.py          # ВСЕ расчёты метрик (локально)
│
├── llm/
│   ├── __init__.py
│   ├── client.py           # OpenAI клиент
│   ├── prompts.py          # Промпты
│   └── response_parser.py  # Парсинг + repair JSON
│
├── data/
│   ├── __init__.py
│   ├── parser.py           # Парсинг файлов + очистка
│   ├── cleaner.py          # Очистка грязных данных
│   └── models.py           # Pydantic модели
│
├── ui/
│   ├── __init__.py
│   ├── components.py       # Gradio компоненты
│   └── styles.py           # CSS (ClickUp-like)
│
├── examples/
│   ├── sample_pnl_clean.csv
│   └── sample_pnl_dirty.csv  # С реальными проблемами
│
└── requirements.txt
```

---

## Конфигурация (config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Приложение
    app_name: str = "FinRentgen"
    debug: bool = False
    
    # LLM (Wave 1: только OpenAI)
    openai_api_key: str
    openai_model: str = "gpt-4o"
    
    # Лимиты
    max_file_size_mb: int = 5
    max_rows: int = 100
    min_periods: int = 3
    
    # LLM retry
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Модели данных (data/models.py)

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date
from enum import Enum
from typing import Optional

class InsightType(str, Enum):
    PROBLEM = "problem"          # 🔴
    OBSERVATION = "observation"  # 🟡
    OPPORTUNITY = "opportunity"  # 🟢

class TrendDirection(str, Enum):
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"

class PnLRow(BaseModel):
    """Одна строка P&L (один период)"""
    period: date
    revenue: float = Field(..., gt=0, description="Выручка")
    cogs: Optional[float] = Field(None, ge=0, description="Себестоимость")
    rent: Optional[float] = Field(None, ge=0, description="Аренда")
    payroll: Optional[float] = Field(None, ge=0, description="ФОТ")
    marketing: Optional[float] = Field(None, ge=0, description="Маркетинг")
    other_expenses: Optional[float] = Field(None, ge=0, description="Прочие")

class PnLData(BaseModel):
    """Полный P&L"""
    rows: list[PnLRow]
    business_context: Optional[str] = None
    parsing_warnings: list[str] = Field(default_factory=list)  # Что было исправлено

class CalculatedMetrics(BaseModel):
    """Метрики, посчитанные ЛОКАЛЬНО (не LLM)"""
    
    # Средние за период
    avg_revenue: float
    avg_cogs: Optional[float]
    avg_gross_profit: Optional[float]
    avg_gross_margin_pct: Optional[float]
    avg_operating_profit: float
    avg_operating_margin_pct: float
    
    # Тренды (последние 3 периода vs предыдущие)
    revenue_trend_pct: float  # +10% = растёт
    revenue_trend_direction: TrendDirection
    
    # Доли расходов от выручки (средние)
    cogs_share_pct: Optional[float]
    rent_share_pct: Optional[float]
    payroll_share_pct: Optional[float]
    marketing_share_pct: Optional[float]
    other_share_pct: Optional[float]
    
    # Аномалии
    anomalies: list[str]  # ["Маркетинг в марте вырос на 45%"]
    
    # По периодам (для отображения)
    by_period: list[dict]  # [{period, revenue, profit, margin}, ...]

class Insight(BaseModel):
    """Один инсайт"""
    type: InsightType
    title: str
    explanation: str
    recommendation: str
    potential_impact: Optional[str] = None

class AnalysisResult(BaseModel):
    """Полный результат анализа"""
    metrics: CalculatedMetrics  # Посчитано локально
    insights: list[Insight]     # От LLM
    parsing_warnings: list[str] = Field(default_factory=list)  # Что исправлено
    llm_raw_response: Optional[str] = None  # Для отладки
```

---

## Локальный расчёт метрик (core/metrics.py)

```python
"""
ВСЕ метрики считаются здесь, локально.
LLM получает уже готовые цифры и только интерпретирует их.
"""

from data.models import PnLData, PnLRow, CalculatedMetrics
from statistics import mean, stdev
from typing import Optional

def calculate_metrics(data: PnLData) -> CalculatedMetrics:
    """Главная функция расчёта всех метрик"""
    
    rows = data.rows
    n = len(rows)
    
    # === Базовые средние ===
    revenues = [r.revenue for r in rows]
    avg_revenue = mean(revenues)
    
    # Себестоимость и валовая прибыль
    cogs_values = [r.cogs for r in rows if r.cogs is not None]
    avg_cogs = mean(cogs_values) if cogs_values else None
    
    if avg_cogs is not None:
        avg_gross_profit = avg_revenue - avg_cogs
        avg_gross_margin_pct = (avg_gross_profit / avg_revenue) * 100
    else:
        avg_gross_profit = None
        avg_gross_margin_pct = None
    
    # Операционная прибыль
    operating_profits = [_calc_operating_profit(r) for r in rows]
    avg_operating_profit = mean(operating_profits)
    avg_operating_margin_pct = (avg_operating_profit / avg_revenue) * 100
    
    # === Тренды ===
    revenue_trend_pct, revenue_trend_direction = _calc_trend(revenues)
    
    # === Доли расходов ===
    cogs_share = _avg_share(rows, 'cogs')
    rent_share = _avg_share(rows, 'rent')
    payroll_share = _avg_share(rows, 'payroll')
    marketing_share = _avg_share(rows, 'marketing')
    other_share = _avg_share(rows, 'other_expenses')
    
    # === Аномалии ===
    anomalies = _detect_anomalies(rows)
    
    # === По периодам (для отображения) ===
    by_period = [
        {
            "period": r.period.isoformat(),
            "revenue": r.revenue,
            "profit": _calc_operating_profit(r),
            "margin_pct": round((_calc_operating_profit(r) / r.revenue) * 100, 1) if r.revenue else None
        }
        for r in rows
    ]
    
    return CalculatedMetrics(
        avg_revenue=round(avg_revenue, 0),
        avg_cogs=round(avg_cogs, 0) if avg_cogs else None,
        avg_gross_profit=round(avg_gross_profit, 0) if avg_gross_profit else None,
        avg_gross_margin_pct=round(avg_gross_margin_pct, 1) if avg_gross_margin_pct else None,
        avg_operating_profit=round(avg_operating_profit, 0),
        avg_operating_margin_pct=round(avg_operating_margin_pct, 1),
        revenue_trend_pct=round(revenue_trend_pct, 1),
        revenue_trend_direction=revenue_trend_direction,
        cogs_share_pct=cogs_share,
        rent_share_pct=rent_share,
        payroll_share_pct=payroll_share,
        marketing_share_pct=marketing_share,
        other_share_pct=other_share,
        anomalies=anomalies,
        by_period=by_period
    )


def _calc_operating_profit(row: PnLRow) -> float:
    """Операционная прибыль = выручка - все расходы"""
    # Важно: используем `is not None`, а не filter(None), 
    # чтобы не терять нулевые значения
    expenses = sum(v for v in [
        row.cogs, row.rent, row.payroll, 
        row.marketing, row.other_expenses
    ] if v is not None)
    return row.revenue - expenses


def _calc_trend(values: list[float]) -> tuple[float, str]:
    """
    Тренд: сравниваем последние 3 периода с предыдущими.
    Возвращает (процент изменения, направление)
    
    ВАЖНО: При менее чем 6 периодах тренд ненадёжен.
    """
    # Минимум 6 периодов для надёжного тренда
    if len(values) < 6:
        return 0.0, "insufficient_data"
    
    # Последние 3 vs предыдущие 3
    recent = values[-3:]
    previous = values[-6:-3]
    
    avg_recent = mean(recent)
    avg_previous = mean(previous)
    
    if avg_previous == 0:
        return 0.0, "stable"
    
    change_pct = ((avg_recent - avg_previous) / avg_previous) * 100
    
    if change_pct > 5:
        direction = "growing"
    elif change_pct < -5:
        direction = "declining"
    else:
        direction = "stable"
    
    return change_pct, direction


def _avg_share(rows: list[PnLRow], field: str) -> Optional[float]:
    """
    Средняя доля статьи расходов от выручки ПО ПЕРИОДАМ.
    
    Важно: считаем долю для каждого периода, потом усредняем.
    Это корректнее, чем (среднее расходов / средняя выручка).
    """
    shares = []
    for r in rows:
        val = getattr(r, field)
        if val is not None and r.revenue:
            shares.append(val / r.revenue)
    if not shares:
        return None
    return round(mean(shares) * 100, 1)


def _detect_anomalies(rows: list[PnLRow]) -> list[str]:
    """
    Поиск аномалий: резкие скачки (>30%) месяц к месяцу.
    """
    anomalies = []
    
    if len(rows) < 2:
        return anomalies
    
    fields = [
        ('revenue', 'Выручка'),
        ('cogs', 'Себестоимость'),
        ('marketing', 'Маркетинг'),
        ('payroll', 'ФОТ'),
        ('rent', 'Аренда')
    ]
    
    for field, name in fields:
        values = [(r.period, getattr(r, field)) for r in rows]
        values = [(p, v) for p, v in values if v is not None]
        
        for i in range(1, len(values)):
            prev_period, prev_val = values[i-1]
            curr_period, curr_val = values[i]
            
            if prev_val == 0:
                continue
                
            change_pct = ((curr_val - prev_val) / prev_val) * 100
            
            if abs(change_pct) > 30:
                direction = "вырос" if change_pct > 0 else "упал"
                anomalies.append(
                    f"{name} в {curr_period.strftime('%B %Y')} {direction} на {abs(change_pct):.0f}%"
                )
    
    return anomalies[:5]  # Максимум 5 аномалий
```

---

## Очистка грязных данных (data/cleaner.py)

```python
"""
Реальные Excel от SMB содержат:
- "1 200 000" и "1,200,000"
- "—", "нет", "-"
- Пустые строки
- Итоги внизу
- Заголовки на разных языках
"""

import re
from typing import Optional
import pandas as pd

# Синонимы колонок
COLUMN_SYNONYMS = {
    'period': ['месяц', 'период', 'date', 'дата', 'month', 'год/месяц'],
    'revenue': ['выручка', 'revenue', 'доход', 'sales', 'продажи', 'оборот'],
    'cogs': ['себестоимость', 'cogs', 'cost of goods', 'закупка', 'себест'],
    'rent': ['аренда', 'rent', 'аренда помещения'],
    'payroll': ['фот', 'зарплаты', 'payroll', 'salaries', 'зп', 'оплата труда'],
    'marketing': ['маркетинг', 'marketing', 'реклама', 'продвижение', 'ads'],
    'other_expenses': ['прочие расходы', 'other', 'прочее', 'другие расходы', 'остальное']
}

# Паттерны для "пустых" значений
EMPTY_PATTERNS = ['-', '—', '–', 'нет', 'н/д', 'n/a', 'na', '']


def clean_number(value) -> Optional[float]:
    """
    Очистка числа из грязных данных.
    
    Примеры:
    - "1 200 000" -> 1200000.0
    - "1,200,000" -> 1200000.0
    - "1200000.50" -> 1200000.5
    - "—" -> None
    - "" -> None
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    
    # Приводим к строке
    s = str(value).strip().lower()
    
    # Проверяем на "пустые" значения
    if s in EMPTY_PATTERNS:
        return None
    
    # Убираем пробелы, валюту
    s = re.sub(r'[₽руб\s]', '', s)
    
    # Определяем разделитель дробной части
    # Если есть и точка и запятая — запятая скорее разделитель тысяч
    if ',' in s and '.' in s:
        s = s.replace(',', '')
    elif ',' in s:
        # Если запятая одна и после неё 1-2 цифры — это дробная часть
        if re.search(r',\d{1,2}$', s):
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    
    # Убираем оставшиеся нечисловые символы кроме точки и минуса
    s = re.sub(r'[^\d.\-]', '', s)
    
    # Если больше одной точки — считаем мусором
    if s.count('.') > 1:
        return None
    
    try:
        result = float(s)
        return result if result >= 0 else None
    except ValueError:
        return None


def normalize_column_name(name: str) -> Optional[str]:
    """
    Сопоставляет название колонки с нашей схемой.
    
    "Выручка за месяц" -> "revenue"
    "ФОТ" -> "payroll"
    """
    name_lower = str(name).lower().strip()
    
    for standard_name, synonyms in COLUMN_SYNONYMS.items():
        for synonym in synonyms:
            if synonym in name_lower:
                return standard_name
    
    return None


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Очистка DataFrame из файла пользователя.
    
    Возвращает:
    - Очищенный DataFrame
    - Список предупреждений (что было исправлено)
    """
    warnings = []
    
    # 1. Убираем полностью пустые строки
    original_rows = len(df)
    df = df.dropna(how='all')
    if len(df) < original_rows:
        warnings.append(f"Удалено {original_rows - len(df)} пустых строк")
    
    # 2. Нормализуем названия колонок
    column_mapping = {}
    unmapped_columns = []
    
    for col in df.columns:
        normalized = normalize_column_name(col)
        if normalized:
            column_mapping[col] = normalized
        else:
            unmapped_columns.append(col)
    
    if unmapped_columns:
        warnings.append(f"Нераспознанные колонки: {', '.join(unmapped_columns)}")
    
    df = df.rename(columns=column_mapping)
    
    # 3. Проверяем обязательные колонки
    if 'revenue' not in df.columns:
        raise ValueError("Не найдена колонка с выручкой (Выручка/Revenue)")
    
    if 'period' not in df.columns:
        raise ValueError("Не найдена колонка с периодом (Месяц/Дата/Period)")
    
    # 4. Очищаем числовые колонки
    numeric_columns = ['revenue', 'cogs', 'rent', 'payroll', 'marketing', 'other_expenses']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
    
    # 5. Убираем строки без выручки (итоги, заголовки)
    original_rows = len(df)
    df = df[df['revenue'].notna() & (df['revenue'] > 0)]
    if len(df) < original_rows:
        warnings.append(f"Удалено {original_rows - len(df)} строк без выручки")
    
    # 6. Парсим даты
    df['period'] = pd.to_datetime(df['period'], dayfirst=True, errors='coerce')
    
    # Логируем строки с нераспознанной датой (вероятно итоги)
    invalid_date_mask = df['period'].isna()
    invalid_date_rows = df[invalid_date_mask]
    if len(invalid_date_rows) > 0:
        # Проверяем, есть ли там revenue (значит это не пустая строка)
        rows_with_revenue = invalid_date_rows[invalid_date_rows['revenue'].notna()]
        if len(rows_with_revenue) > 0:
            warnings.append(
                f"Удалено {len(rows_with_revenue)} строк с нераспознанной датой "
                f"(возможно, строки 'Итого')"
            )
        df = df[~invalid_date_mask]
    
    # 7. Сортируем по дате
    df = df.sort_values('period').reset_index(drop=True)
    
    return df, warnings
```

---

## JSON repair для LLM (llm/response_parser.py)

```python
"""
LLM часто ломают JSON:
- Добавляют текст до/после
- Оборачивают в ```json
- Ломают кавычки
- Путают типы

Этот модуль пытается извлечь валидный JSON.
"""

import json
import re
from typing import Optional
from pydantic import ValidationError
from data.models import Insight, InsightType

class JSONParseError(Exception):
    """Не удалось распарсить JSON даже после repair"""
    pass


def extract_json(text: str) -> dict:
    """
    Извлекает JSON из ответа LLM.
    
    Пробует:
    1. Прямой парсинг
    2. Извлечение из ```json блока
    3. Поиск { ... } в тексте
    4. Починка частых ошибок
    """
    
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
    
    raise JSONParseError(f"Не удалось извлечь JSON из ответа LLM")


def _repair_json(json_str: str) -> str:
    """Починка частых ошибок в JSON"""
    
    # Trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Single quotes -> double quotes (осторожно)
    # Только если нет двойных кавычек рядом
    json_str = re.sub(r"(?<![\"\\])'([^']*)'(?![\"\\])", r'"\1"', json_str)
    
    # None -> null
    json_str = re.sub(r'\bNone\b', 'null', json_str)
    
    # True/False с маленькой буквы
    json_str = re.sub(r'\bTrue\b', 'true', json_str)
    json_str = re.sub(r'\bFalse\b', 'false', json_str)
    
    return json_str


def parse_insights(raw_response: str) -> list[Insight]:
    """
    Парсит список инсайтов из ответа LLM.
    Валидирует через Pydantic.
    """
    
    try:
        data = extract_json(raw_response)
    except JSONParseError as e:
        # Включаем начало ответа для отладки
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        raise JSONParseError(f"{e}. Начало ответа: {preview}")
    
    if 'insights' not in data:
        preview = raw_response[:300] + "..." if len(raw_response) > 300 else raw_response
        raise JSONParseError(f"В ответе отсутствует поле 'insights'. Ответ: {preview}")
    
    insights = []
    
    for i, item in enumerate(data['insights']):
        try:
            # Нормализуем type
            item_type = item.get('type', '').lower()
            if item_type not in ['problem', 'observation', 'opportunity']:
                item_type = 'observation'  # fallback
            
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
            print(f"[WARNING] Ошибка парсинга инсайта {i}: {e}")
            continue
    
    if not insights:
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        raise JSONParseError(f"Не удалось распарсить ни одного инсайта. Ответ: {preview}")
    
    return insights
```

---

## LLM клиент с retry (llm/client.py)

```python
"""
OpenAI клиент с retry и таймаутами.
"""

from openai import OpenAI
from config import settings
from typing import Optional
import time

class LLMClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_retries = settings.llm_max_retries
        self.timeout = settings.llm_timeout_seconds
    
    def complete(
        self, 
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Запрос к LLM с retry.
        
        Возвращает сырой текст ответа.
        """
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
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
        """
        from llm.response_parser import extract_json, JSONParseError
        
        response = self.complete(messages, temperature, max_tokens)
        
        # Пробуем распарсить
        try:
            extract_json(response)
            return response
        except JSONParseError:
            pass
        
        # Просим починить
        repair_messages = messages + [
            {"role": "assistant", "content": response},
            {"role": "user", "content": 
                "Твой ответ содержит невалидный JSON. "
                "Выдай ТОЛЬКО исправленный JSON, без пояснений и markdown."
            }
        ]
        
        return self.complete(repair_messages, temperature=0.3, max_tokens=max_tokens)
```

---

## Промпты (llm/prompts.py)

```python
SYSTEM_PROMPT = """
Ты — финансовый аналитик для малого бизнеса в России.

КОНТЕКСТ:
- Клиент — владелец малого бизнеса (ИП/ООО) без финансового образования
- Ему нужны простые, понятные, actionable советы
- Он ценит конкретику с цифрами

КРИТИЧЕСКИ ВАЖНО:
- НИКОГДА не выдумывай цифры
- Используй ТОЛЬКО числа из предоставленных данных или посчитанных метрик
- Если данных недостаточно — скажи об этом

ПРАВИЛА:
1. Говори простым языком без жаргона
2. Каждый инсайт = что происходит + почему это важно + что делать
3. Давай конкретные цифры из данных
4. Будь честным — если всё хорошо, так и скажи

ОГРАНИЧЕНИЯ:
- Не давай юридических/налоговых советов
- Не рекомендуй конкретные банки/сервисы
"""

ANALYSIS_PROMPT = """
Проанализируй финансовые данные малого бизнеса.

ИСХОДНЫЕ ДАННЫЕ (таблица P&L):
{table_markdown}

ПОСЧИТАННЫЕ МЕТРИКИ (используй эти цифры, не пересчитывай):
{metrics_json}

КОНТЕКСТ ОТ ПОЛЬЗОВАТЕЛЯ:
{user_context}

ЗАДАЧА:
На основе данных и метрик выдели 3-5 ключевых инсайтов.
Сфокусируйся на:
- Проблемах (где теряются деньги)
- Возможностях (где можно улучшить)
- Аномалиях (резкие изменения)

ФОРМАТ ОТВЕТА — ТОЛЬКО JSON, без текста до и после:
{{
  "insights": [
    {{
      "type": "problem|observation|opportunity",
      "title": "Краткий заголовок (до 10 слов)",
      "explanation": "Что это значит простыми словами (2-3 предложения)",
      "recommendation": "Что конкретно сделать (1-2 предложения)",
      "potential_impact": "Эффект в рублях или процентах (если можно оценить)"
    }}
  ]
}}

ВАЖНО: Ответ должен быть ТОЛЬКО валидным JSON. Никакого текста, markdown, пояснений.
"""
```

---

## Главный анализатор (core/analyzer.py)

```python
"""
Оркестрация анализа:
1. Парсинг файла
2. Расчёт метрик (локально)
3. Запрос к LLM
4. Парсинг ответа
"""

import pandas as pd
from data.parser import parse_file
from data.cleaner import clean_dataframe
from data.models import PnLData, PnLRow, AnalysisResult
from core.metrics import calculate_metrics
from llm.client import LLMClient
from llm.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT
from llm.response_parser import parse_insights
import json

def analyze_file(
    file_path: str, 
    user_context: str = ""
) -> AnalysisResult:
    """
    Полный цикл анализа файла.
    """
    from config import settings
    
    # 1. Парсинг файла
    df = parse_file(file_path)
    
    # 2. Очистка данных
    df, warnings = clean_dataframe(df)
    
    # 3. Применяем лимит строк
    if len(df) > settings.max_rows:
        df = df.tail(settings.max_rows)
        warnings.append(f"Ограничено до последних {settings.max_rows} периодов")
    
    # 4. Проверка минимума периодов
    if len(df) < settings.min_periods:
        raise ValueError(
            f"Недостаточно данных: найдено {len(df)} периодов, "
            f"минимум {settings.min_periods}"
        )
    
    # 5. Конвертация в модель
    pnl_data = dataframe_to_pnl(df, user_context, warnings)
    
    # 6. Расчёт метрик ЛОКАЛЬНО
    metrics = calculate_metrics(pnl_data)
    
    # 7. Формирование промпта
    table_md = dataframe_to_markdown(df)
    metrics_json = metrics.model_dump_json(indent=2)
    
    prompt = ANALYSIS_PROMPT.format(
        table_markdown=table_md,
        metrics_json=metrics_json,
        user_context=user_context or "Не указан"
    )
    
    # 8. Запрос к LLM
    client = LLMClient()
    raw_response = client.complete_with_repair([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])
    
    # 9. Парсинг инсайтов
    insights = parse_insights(raw_response)
    
    return AnalysisResult(
        metrics=metrics,
        insights=insights,
        parsing_warnings=pnl_data.parsing_warnings,
        llm_raw_response=raw_response
    )


def dataframe_to_pnl(
    df: pd.DataFrame, 
    context: str, 
    warnings: list[str]
) -> PnLData:
    """Конвертация DataFrame в PnLData"""
    
    rows = []
    for _, row in df.iterrows():
        rows.append(PnLRow(
            period=row['period'].date(),
            revenue=row['revenue'],
            cogs=row.get('cogs'),
            rent=row.get('rent'),
            payroll=row.get('payroll'),
            marketing=row.get('marketing'),
            other_expenses=row.get('other_expenses')
        ))
    
    return PnLData(
        rows=rows,
        business_context=context,
        parsing_warnings=warnings
    )


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Конвертация DataFrame в markdown таблицу"""
    
    # Форматируем числа
    df_display = df.copy()
    
    for col in df_display.columns:
        if col == 'period':
            df_display[col] = df_display[col].dt.strftime('%Y-%m')
        elif df_display[col].dtype in ['float64', 'int64']:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
            )
    
    return df_display.to_markdown(index=False)
```

---

## UI компоненты (ui/components.py)

```python
"""
Gradio UI с ClickUp-inspired стилями.
"""

import gradio as gr
from ui.styles import CUSTOM_CSS
from core.analyzer import analyze_file
from data.models import AnalysisResult, InsightType

def create_app():
    """Создание Gradio приложения"""
    
    with gr.Blocks(css=CUSTOM_CSS, title="FinRentgen") as app:
        
        # Header
        gr.Markdown("""
        # 📊 FinRentgen
        ### Финансовый рентген вашего бизнеса
        
        Загрузите P&L и получите анализ за 30 секунд
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                # Загрузка файла
                file_input = gr.File(
                    label="Загрузите файл с P&L",
                    file_types=[".csv", ".xlsx", ".xls"],
                    type="filepath"
                )
                
                # Пример для скачивания
                gr.Markdown("[📥 Скачать пример файла](примера пока нет)")
                
                # Контекст
                context_input = gr.Textbox(
                    label="Расскажите о бизнесе (опционально)",
                    placeholder="Например: кофейня в центре Москвы, работаем 2 года",
                    lines=2
                )
                
                # Кнопка
                analyze_btn = gr.Button(
                    "🔍 Анализировать",
                    variant="primary",
                    size="lg"
                )
                
                # Предупреждение о времени
                gr.Markdown(
                    "*Анализ может занять до 30 секунд*",
                    elem_classes=["hint-text"]
                )
        
        # Результаты (скрыты до анализа)
        with gr.Column(visible=False) as results_section:
            
            # Метрики
            gr.Markdown("### 📈 Ключевые показатели")
            with gr.Row():
                metric_revenue = gr.Textbox(label="Ср. выручка", interactive=False)
                metric_margin = gr.Textbox(label="Маржа", interactive=False)
                metric_profit = gr.Textbox(label="Ср. прибыль", interactive=False)
                metric_trend = gr.Textbox(label="Тренд", interactive=False)
            
            # Инсайты
            gr.Markdown("### 📌 Ключевые находки")
            insights_output = gr.Markdown()
            
            # Предупреждения парсера (что было исправлено)
            warnings_output = gr.Markdown(visible=False, elem_classes=["warnings-box"])
        
        # Обработчик
        def on_analyze(file_path, context):
            if not file_path:
                return {
                    results_section: gr.update(visible=False)
                }
            
            try:
                result = analyze_file(file_path, context)
                
                # Форматируем метрики
                revenue_text = f"{result.metrics.avg_revenue:,.0f} ₽"
                margin_text = f"{result.metrics.avg_operating_margin_pct}%"
                profit_text = f"{result.metrics.avg_operating_profit:,.0f} ₽"
                
                trend_emoji = {
                    "growing": "📈 Растёт",
                    "stable": "➡️ Стабильно", 
                    "declining": "📉 Падает",
                    "insufficient_data": "❓ Мало данных"
                }
                trend_text = trend_emoji.get(
                    result.metrics.revenue_trend_direction, 
                    "➡️ Стабильно"
                )
                
                # Добавляем процент если есть значимый тренд
                if result.metrics.revenue_trend_direction in ["growing", "declining"]:
                    trend_text += f" ({result.metrics.revenue_trend_pct:+.1f}%)"
                
                # Форматируем инсайты
                insights_md = format_insights(result.insights)
                
                # Форматируем предупреждения (что исправлено в данных)
                warnings_md = ""
                show_warnings = False
                if result.parsing_warnings:
                    show_warnings = True
                    warnings_md = "⚠️ **Мы исправили данные:**\n"
                    for w in result.parsing_warnings:
                        warnings_md += f"- {w}\n"
                
                return {
                    results_section: gr.update(visible=True),
                    metric_revenue: revenue_text,
                    metric_margin: margin_text,
                    metric_profit: profit_text,
                    metric_trend: trend_text,
                    insights_output: insights_md,
                    warnings_output: gr.update(visible=show_warnings, value=warnings_md)
                }
                
            except Exception as e:
                return {
                    results_section: gr.update(visible=True),
                    insights_output: f"❌ Ошибка: {str(e)}"
                }
        
        analyze_btn.click(
            fn=on_analyze,
            inputs=[file_input, context_input],
            outputs=[
                results_section,
                metric_revenue,
                metric_margin, 
                metric_profit,
                metric_trend,
                insights_output,
                warnings_output
            ]
        )
    
    return app


def format_insights(insights) -> str:
    """Форматирование инсайтов в Markdown"""
    
    type_styles = {
        InsightType.PROBLEM: ("🔴", "problem"),
        InsightType.OBSERVATION: ("🟡", "observation"),
        InsightType.OPPORTUNITY: ("🟢", "opportunity")
    }
    
    parts = []
    
    for insight in insights:
        emoji, css_class = type_styles.get(
            insight.type, 
            ("🟡", "observation")
        )
        
        impact_line = ""
        if insight.potential_impact:
            impact_line = f"\n\n**Потенциал:** {insight.potential_impact}"
        
        parts.append(f"""
<div class="insight-{css_class}">

**{emoji} {insight.title}**

{insight.explanation}

→ *{insight.recommendation}*{impact_line}

</div>
""")
    
    return "\n".join(parts)
```

---

## Точка входа (app.py)

```python
"""
Точка входа приложения.
"""

from ui.components import create_app

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # True для публичной ссылки
    )
```

---

## Тестовые данные

### examples/sample_pnl_clean.csv

```csv
Месяц,Выручка,Себестоимость,Аренда,ФОТ,Маркетинг,Прочие расходы
2024-01,850000,340000,80000,150000,95000,45000
2024-02,920000,368000,80000,150000,110000,52000
2024-03,780000,312000,80000,150000,125000,48000
2024-04,890000,356000,80000,165000,130000,51000
2024-05,950000,380000,80000,165000,145000,55000
2024-06,870000,348000,85000,165000,160000,53000
```

### examples/sample_pnl_dirty.csv

```csv
Период,Выручка (руб),Себест.,Аренда,ЗП,Реклама,Прочее
Январь 2024,"1 200 000",480000,80000,150000,95 000,45000
Февраль 2024,1300000,520 000,80000,150000,—,52000
Март,1100000,440000,80000,150000,125000,
Апрель 2024,1250000,,80000,165000,130000,51000

Май 2024,1400000,560000,80000,165000,нет,55000
Итого,6250000,2000000,400000,795000,350000,203000
```

---

## Зависимости (requirements.txt)

```
# UI
gradio>=4.0.0

# Data
pandas>=2.0.0
openpyxl>=3.1.0
tabulate>=0.9.0  # для to_markdown

# LLM
openai>=1.0.0

# Config
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

---

## .env.example

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Настройки
DEBUG=false
MAX_FILE_SIZE_MB=5
LLM_MAX_RETRIES=2
LLM_TIMEOUT_SECONDS=60
```

---

## Чеклист Wave 1

### Готово к разработке
- [ ] Структура проекта создана
- [ ] Конфигурация работает
- [ ] Парсер читает CSV и Excel
- [ ] Cleaner обрабатывает грязные данные
- [ ] Метрики считаются локально
- [ ] LLM клиент с retry работает
- [ ] JSON repair работает
- [ ] UI показывает результаты
- [ ] CSS выглядит прилично

### Готово к кастдевам
- [ ] Можно загрузить реальный файл клиента
- [ ] Инсайты релевантные
- [ ] Ошибки обрабатываются понятно
- [ ] Работает локально без проблем

---

## Known Limitations (Wave 1)

⚠️ **Документировано для будущих исправлений:**

1. **JSON repair для апострофов** — регулярка для одинарных кавычек может ломать апострофы в тексте типа "don't". Для русского языка не критично.

2. **OpenAI SDK API** — используется `chat.completions.create()`. Возможна миграция API в новых версиях SDK.

3. **Тренд при <6 периодах** — возвращаем `insufficient_data`. Пользователь видит "Мало данных" вместо ненадёжного тренда.

4. **Числа типа "1.2.3"** — защита добавлена, но edge cases возможны.

---

## Дополнительный CSS для warnings

Добавить в `ui/styles.py`:

```css
/* Предупреждения о данных */
.warnings-box {
    background: rgba(245, 166, 35, 0.1);
    border: 1px solid var(--warning);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 14px;
}

.warnings-box ul {
    margin: 8px 0 0 0;
    padding-left: 20px;
}
```

---

## Что отложено на Wave 2

| Фича | Приоритет после кастдевов |
|------|---------------------------|
| Авторизация | Высокий (если нужно сохранять) |
| Сценарии "что если" | Зависит от фидбека |
| Чат | Зависит от фидбека |
| YandexGPT / GigaChat | Средний |
| Экспорт в PDF | Зависит от фидбека |
| Отраслевые шаблоны | Зависит от фидбека |
| История сессий | После авторизации |

