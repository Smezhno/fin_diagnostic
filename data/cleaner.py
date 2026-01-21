"""
Очистка грязных данных из файлов пользователей.

Реальные Excel от SMB содержат:
- "1 200 000" и "1,200,000" вместо 1200000
- "—", "нет", "-" вместо пустых значений
- Пустые строки
- Итоги внизу таблицы
- Заголовки на разных языках
- Русские названия месяцев ("Январь 2024", "Март")
"""

import re
from typing import Optional
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


# === Русские названия месяцев ===
RUSSIAN_MONTHS = {
    'январь': 1, 'января': 1, 'янв': 1,
    'февраль': 2, 'февраля': 2, 'фев': 2,
    'март': 3, 'марта': 3, 'мар': 3,
    'апрель': 4, 'апреля': 4, 'апр': 4,
    'май': 5, 'мая': 5,
    'июнь': 6, 'июня': 6, 'июн': 6,
    'июль': 7, 'июля': 7, 'июл': 7,
    'август': 8, 'августа': 8, 'авг': 8,
    'сентябрь': 9, 'сентября': 9, 'сен': 9,
    'октябрь': 10, 'октября': 10, 'окт': 10,
    'ноябрь': 11, 'ноября': 11, 'ноя': 11,
    'декабрь': 12, 'декабря': 12, 'дек': 12,
}


# === Синонимы колонок ===
# Ключ — наше стандартное имя, значения — возможные названия в файлах
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
    - "1 200,50" -> 1200.5
    - "—" -> None
    - "" -> None
    - "нет" -> None
    """
    if value is None:
        return None
    
    # Если уже число
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value) if value >= 0 else None
    
    # Приводим к строке и нормализуем
    s = str(value).strip().lower()
    
    # Проверяем на "пустые" значения
    if s in EMPTY_PATTERNS:
        return None
    
    # Убираем пробелы и валюту
    s = re.sub(r'[₽руб\s]', '', s)
    
    # Определяем разделитель дробной части
    # Логика:
    # - Если есть и точка и запятая — запятая скорее разделитель тысяч
    # - Если только запятая и после неё 1-2 цифры — это дробная часть
    # - Иначе запятая — разделитель тысяч
    
    if ',' in s and '.' in s:
        # "1,200.50" или "1.200,50"
        # Определяем по позиции: что ближе к концу — то дробная часть
        comma_pos = s.rfind(',')
        dot_pos = s.rfind('.')
        
        if comma_pos > dot_pos:
            # Запятая ближе к концу — она дробный разделитель (европейский формат)
            s = s.replace('.', '').replace(',', '.')
        else:
            # Точка ближе к концу — она дробный разделитель (US формат)
            s = s.replace(',', '')
    elif ',' in s:
        # Только запятая
        # Если после неё 1-2 цифры в конце — это дробная часть
        if re.search(r',\d{1,2}$', s):
            s = s.replace(',', '.')
        else:
            # Иначе это разделитель тысяч
            s = s.replace(',', '')
    
    # Убираем оставшиеся нечисловые символы кроме точки и минуса
    s = re.sub(r'[^\d.\-]', '', s)
    
    # Проверка на мусор: больше одной точки
    if s.count('.') > 1:
        logger.debug(f"Некорректное число (несколько точек): {value}")
        return None
    
    # Пустая строка после очистки
    if not s or s == '-':
        return None
    
    try:
        result = float(s)
        return result if result >= 0 else None
    except ValueError:
        logger.debug(f"Не удалось преобразовать в число: {value}")
        return None


def normalize_column_name(name: str) -> Optional[str]:
    """
    Сопоставляет название колонки с нашей схемой.
    
    Примеры:
    - "Выручка за месяц" -> "revenue"
    - "ФОТ" -> "payroll"
    - "Себест." -> "cogs"
    - "Неизвестная колонка" -> None
    """
    name_lower = str(name).lower().strip()
    
    for standard_name, synonyms in COLUMN_SYNONYMS.items():
        for synonym in synonyms:
            if synonym in name_lower:
                return standard_name
    
    return None


def parse_russian_date(value) -> Optional[datetime]:
    """
    Парсит дату с русскими названиями месяцев.
    
    Поддерживаемые форматы:
    - "Январь 2024" -> 2024-01-01
    - "Март" -> текущий_год-03-01
    - "2024-01" -> 2024-01-01
    - "01.01.2024" -> 2024-01-01
    
    Returns:
        datetime или None если не удалось распарсить
    """
    if value is None or pd.isna(value):
        return None
    
    s = str(value).strip().lower()
    
    if not s or s in EMPTY_PATTERNS:
        return None
    
    # Пробуем найти русский месяц
    for month_name, month_num in RUSSIAN_MONTHS.items():
        if month_name in s:
            # Ищем год (4 цифры)
            year_match = re.search(r'(\d{4})', s)
            if year_match:
                year = int(year_match.group(1))
            else:
                # Если год не указан — берём текущий
                year = datetime.now().year
            
            return datetime(year, month_num, 1)
    
    # Пробуем стандартные форматы
    formats = [
        '%Y-%m',       # 2024-01
        '%Y-%m-%d',    # 2024-01-15
        '%d.%m.%Y',    # 15.01.2024
        '%d/%m/%Y',    # 15/01/2024
        '%m/%d/%Y',    # 01/15/2024 (US format)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    
    # Последняя попытка — pandas с dateutil
    try:
        result = pd.to_datetime(s, dayfirst=True)
        if pd.notna(result):
            return result.to_pydatetime()
    except Exception:
        pass
    
    return None


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Очистка DataFrame из файла пользователя.
    
    Шаги:
    1. Удаление пустых строк
    2. Нормализация названий колонок
    3. Очистка числовых значений
    4. Удаление строк без выручки (итоги, заголовки)
    5. Парсинг дат
    6. Сортировка по дате
    
    Args:
        df: сырой DataFrame из файла
        
    Returns:
        tuple[DataFrame, list[str]]: очищенный DataFrame и список предупреждений
        
    Raises:
        ValueError: если не найдены обязательные колонки
    """
    warnings = []
    
    # 1. Убираем полностью пустые строки
    original_rows = len(df)
    df = df.dropna(how='all')
    dropped_empty = original_rows - len(df)
    if dropped_empty > 0:
        warnings.append(f"Удалено {dropped_empty} пустых строк")
        logger.debug(f"Удалено {dropped_empty} пустых строк")
    
    # 2. Нормализуем названия колонок
    column_mapping = {}
    unmapped_columns = []
    
    for col in df.columns:
        normalized = normalize_column_name(col)
        if normalized:
            column_mapping[col] = normalized
        else:
            unmapped_columns.append(str(col))
    
    if unmapped_columns:
        warnings.append(f"Нераспознанные колонки: {', '.join(unmapped_columns)}")
        logger.debug(f"Нераспознанные колонки: {unmapped_columns}")
    
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
    
    # 5. Убираем строки без выручки (итоги, заголовки и т.д.)
    original_rows = len(df)
    df = df[df['revenue'].notna() & (df['revenue'] > 0)]
    dropped_no_revenue = original_rows - len(df)
    if dropped_no_revenue > 0:
        warnings.append(f"Удалено {dropped_no_revenue} строк без выручки")
        logger.debug(f"Удалено {dropped_no_revenue} строк без выручки")
    
    # 6. Парсим даты (с поддержкой русских месяцев)
    df['period'] = df['period'].apply(parse_russian_date)
    df['period'] = pd.to_datetime(df['period'], errors='coerce')
    
    # Удаляем строки с нераспознанной датой
    invalid_date_mask = df['period'].isna()
    invalid_date_count = invalid_date_mask.sum()
    
    if invalid_date_count > 0:
        warnings.append(
            f"Удалено {invalid_date_count} строк с нераспознанной датой "
            f"(возможно, строки 'Итого')"
        )
        logger.debug(f"Удалено {invalid_date_count} строк с некорректной датой")
        df = df[~invalid_date_mask]
    
    # 7. Сортируем по дате
    df = df.sort_values('period').reset_index(drop=True)
    
    logger.info(f"Очистка завершена: {len(df)} строк, {len(warnings)} предупреждений")
    
    return df, warnings

