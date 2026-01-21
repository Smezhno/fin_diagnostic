"""
Парсер файлов CSV и Excel.

Функции:
- parse_file(): определяет формат и читает файл в DataFrame
"""

import pandas as pd
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Ошибка при парсинге файла"""
    pass


def parse_file(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Читает файл CSV или Excel и возвращает DataFrame.
    
    Args:
        file_path: путь к файлу (CSV, XLSX, XLS)
        
    Returns:
        pd.DataFrame с сырыми данными
        
    Raises:
        ParseError: если формат не поддерживается или файл не читается
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ParseError(f"Файл не найден: {path}")
    
    suffix = path.suffix.lower()
    
    logger.info(f"Парсинг файла: {path.name} (формат: {suffix})")
    
    try:
        if suffix == ".csv":
            return _parse_csv(path)
        elif suffix in (".xlsx", ".xls"):
            return _parse_excel(path)
        else:
            raise ParseError(
                f"Неподдерживаемый формат файла: {suffix}. "
                f"Поддерживаются: CSV, XLSX, XLS"
            )
    except ParseError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        raise ParseError(f"Не удалось прочитать файл: {e}")


def _parse_csv(path: Path) -> pd.DataFrame:
    """
    Парсит CSV файл.
    
    Пробует разные кодировки и разделители.
    """
    # Пробуем разные кодировки
    encodings = ["utf-8", "cp1251", "latin-1"]
    
    for encoding in encodings:
        try:
            # Сначала пробуем стандартный разделитель (запятая)
            df = pd.read_csv(path, encoding=encoding)
            
            # Если получилась одна колонка — возможно разделитель точка с запятой
            if len(df.columns) == 1 and ";" in df.columns[0]:
                df = pd.read_csv(path, encoding=encoding, sep=";")
            
            logger.debug(f"CSV прочитан с кодировкой {encoding}, колонок: {len(df.columns)}")
            return df
            
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.debug(f"Ошибка с кодировкой {encoding}: {e}")
            continue
    
    raise ParseError("Не удалось определить кодировку CSV файла")


def _parse_excel(path: Path) -> pd.DataFrame:
    """
    Парсит Excel файл.
    
    Берёт первый лист.
    """
    try:
        # Читаем первый лист
        df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
        logger.debug(f"Excel прочитан, колонок: {len(df.columns)}, строк: {len(df)}")
        return df
        
    except Exception as e:
        raise ParseError(f"Не удалось прочитать Excel файл: {e}")

