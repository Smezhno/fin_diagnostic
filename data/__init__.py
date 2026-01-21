"""
Data module — парсинг файлов, очистка данных, модели.
"""

from data.models import (
    InsightType,
    TrendDirection,
    PnLRow,
    PnLData,
    CalculatedMetrics,
    Insight,
    AnalysisResult,
)
from data.parser import parse_file, ParseError
from data.cleaner import clean_dataframe, clean_number, normalize_column_name

__all__ = [
    # Models
    "InsightType",
    "TrendDirection",
    "PnLRow",
    "PnLData",
    "CalculatedMetrics",
    "Insight",
    "AnalysisResult",
    # Parser
    "parse_file",
    "ParseError",
    # Cleaner
    "clean_dataframe",
    "clean_number",
    "normalize_column_name",
]
