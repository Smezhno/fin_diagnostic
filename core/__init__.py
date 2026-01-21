"""
Core module — расчёт метрик и оркестрация анализа.
"""

from core.metrics import calculate_metrics
from core.analyzer import analyze_file

__all__ = [
    "calculate_metrics",
    "analyze_file",
]
