"""
Локальный расчёт всех финансовых метрик.

ВСЕ метрики считаются здесь, локально.
LLM получает уже готовые цифры и только интерпретирует их.
"""

from statistics import mean
from typing import Optional
import logging

from data.models import PnLData, PnLRow, CalculatedMetrics, TrendDirection

logger = logging.getLogger(__name__)


def calculate_metrics(data: PnLData) -> CalculatedMetrics:
    """
    Главная функция расчёта всех метрик.
    
    Args:
        data: PnLData с валидированными строками
        
    Returns:
        CalculatedMetrics со всеми посчитанными показателями
    """
    rows = data.rows
    n = len(rows)
    
    logger.info(f"Расчёт метрик для {n} периодов")
    
    # === Базовые средние ===
    revenues = [r.revenue for r in rows]
    avg_revenue = mean(revenues)
    
    # Себестоимость и валовая прибыль
    cogs_values = [r.cogs for r in rows if r.cogs is not None]
    avg_cogs = mean(cogs_values) if cogs_values else None
    
    if avg_cogs is not None:
        avg_gross_profit = avg_revenue - avg_cogs
        avg_gross_margin_pct = (avg_gross_profit / avg_revenue) * 100 if avg_revenue else 0
    else:
        avg_gross_profit = None
        avg_gross_margin_pct = None
    
    # Операционная прибыль
    operating_profits = [_calc_operating_profit(r) for r in rows]
    avg_operating_profit = mean(operating_profits)
    avg_operating_margin_pct = (avg_operating_profit / avg_revenue) * 100 if avg_revenue else 0
    
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
    by_period = []
    for r in rows:
        profit = _calc_operating_profit(r)
        margin = round((profit / r.revenue) * 100, 1) if r.revenue else None
        by_period.append({
            "period": r.period.isoformat(),
            "revenue": r.revenue,
            "profit": profit,
            "margin_pct": margin
        })
    
    metrics = CalculatedMetrics(
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
    
    logger.debug(f"Метрики рассчитаны: avg_revenue={metrics.avg_revenue}, margin={metrics.avg_operating_margin_pct}%")
    
    return metrics


def _calc_operating_profit(row: PnLRow) -> float:
    """
    Операционная прибыль = выручка - все расходы.
    
    Важно: используем `is not None`, чтобы не терять нулевые значения.
    """
    expenses = sum(v for v in [
        row.cogs, 
        row.rent, 
        row.payroll, 
        row.marketing, 
        row.other_expenses
    ] if v is not None)
    
    return row.revenue - expenses


def _calc_trend(values: list[float]) -> tuple[float, TrendDirection]:
    """
    Расчёт тренда: сравниваем последние 3 периода с предыдущими 3.
    
    Возвращает:
        (процент изменения, направление)
    
    ВАЖНО: При менее чем 6 периодах тренд ненадёжен — возвращаем insufficient_data.
    """
    # Минимум 6 периодов для надёжного тренда
    if len(values) < 6:
        logger.debug(f"Недостаточно данных для тренда: {len(values)} периодов (нужно 6+)")
        return 0.0, TrendDirection.INSUFFICIENT_DATA
    
    # Последние 3 vs предыдущие 3
    recent = values[-3:]
    previous = values[-6:-3]
    
    avg_recent = mean(recent)
    avg_previous = mean(previous)
    
    if avg_previous == 0:
        return 0.0, TrendDirection.STABLE
    
    change_pct = ((avg_recent - avg_previous) / avg_previous) * 100
    
    # Определяем направление по порогу ±5%
    if change_pct > 5:
        direction = TrendDirection.GROWING
    elif change_pct < -5:
        direction = TrendDirection.DECLINING
    else:
        direction = TrendDirection.STABLE
    
    logger.debug(f"Тренд: {change_pct:+.1f}% -> {direction.value}")
    
    return change_pct, direction


def _avg_share(rows: list[PnLRow], field: str) -> Optional[float]:
    """
    Средняя доля статьи расходов от выручки ПО ПЕРИОДАМ.
    
    Важно: считаем долю для каждого периода, потом усредняем.
    Это корректнее, чем (среднее расходов / средняя выручка).
    
    Пример:
        Месяц 1: расход=100, выручка=1000 -> доля=10%
        Месяц 2: расход=200, выручка=1000 -> доля=20%
        Средняя доля = 15%
    """
    shares = []
    for r in rows:
        val = getattr(r, field, None)
        if val is not None and r.revenue > 0:
            shares.append(val / r.revenue)
    
    if not shares:
        return None
    
    return round(mean(shares) * 100, 1)


def _detect_anomalies(rows: list[PnLRow]) -> list[str]:
    """
    Поиск аномалий: резкие скачки (>30%) месяц к месяцу.
    
    Returns:
        Список строк с описанием аномалий (максимум 5)
    """
    anomalies = []
    
    if len(rows) < 2:
        return anomalies
    
    # Поля для проверки и их русские названия
    fields = [
        ('revenue', 'Выручка'),
        ('cogs', 'Себестоимость'),
        ('marketing', 'Маркетинг'),
        ('payroll', 'ФОТ'),
        ('rent', 'Аренда')
    ]
    
    # Русские названия месяцев для красивого вывода
    month_names = {
        1: 'январе', 2: 'феврале', 3: 'марте', 4: 'апреле',
        5: 'мае', 6: 'июне', 7: 'июле', 8: 'августе',
        9: 'сентябре', 10: 'октябре', 11: 'ноябре', 12: 'декабре'
    }
    
    for field, name in fields:
        # Собираем пары (период, значение) где значение не None
        values = []
        for r in rows:
            val = getattr(r, field, None)
            if val is not None:
                values.append((r.period, val))
        
        # Ищем скачки
        for i in range(1, len(values)):
            prev_period, prev_val = values[i-1]
            curr_period, curr_val = values[i]
            
            if prev_val == 0:
                continue
            
            change_pct = ((curr_val - prev_val) / prev_val) * 100
            
            # Порог аномалии: ±30%
            if abs(change_pct) > 30:
                direction = "вырос" if change_pct > 0 else "упал"
                month_name = month_names.get(curr_period.month, str(curr_period.month))
                year = curr_period.year
                
                anomaly = f"{name} в {month_name} {year} {direction} на {abs(change_pct):.0f}%"
                anomalies.append(anomaly)
                
                logger.debug(f"Аномалия: {anomaly}")
    
    # Возвращаем максимум 5 аномалий
    return anomalies[:5]

