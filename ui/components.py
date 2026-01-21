"""
Gradio UI компоненты для FinRentgen.

Интерфейс:
1. Загрузка файла (CSV/Excel)
2. Контекст бизнеса (опционально)
3. Кнопка анализа
4. Результаты: метрики + инсайты
"""

import gradio as gr
import logging
from pathlib import Path

from ui.styles import CUSTOM_CSS
from core.analyzer import analyze_file
from data.models import AnalysisResult, InsightType

logger = logging.getLogger(__name__)


def create_app() -> gr.Blocks:
    """
    Создание Gradio приложения.
    
    Returns:
        gr.Blocks: готовое приложение
    """
    
    # Путь к примеру файла
    example_file = Path(__file__).parent.parent / "examples" / "sample_pnl_clean.csv"
    
    with gr.Blocks(title="FinRentgen — Финансовый анализ") as app:
        
        # === Header ===
        gr.Markdown("""
        # 📊 FinRentgen
        ### Финансовый рентген вашего бизнеса
        
        Загрузите P&L и получите анализ за 30 секунд
        """)
        
        # === Форма ввода ===
        with gr.Row():
            with gr.Column(scale=2):
                # Загрузка файла
                file_input = gr.File(
                    label="📁 Загрузите файл с P&L",
                    file_types=[".csv", ".xlsx", ".xls"],
                    type="filepath",
                    elem_classes=["file-upload"]
                )
                
                # Ссылка на пример
                if example_file.exists():
                    gr.Markdown(
                        f"[📥 Скачать пример файла]({example_file})",
                        elem_classes=["hint-text"]
                    )
                
                # Контекст бизнеса
                context_input = gr.Textbox(
                    label="💬 Расскажите о бизнесе (опционально)",
                    placeholder="Например: кофейня в центре Москвы, работаем 2 года, 3 сотрудника",
                    lines=2,
                    max_lines=4
                )
                
                # Кнопка анализа
                analyze_btn = gr.Button(
                    "🔍 Анализировать",
                    variant="primary",
                    size="lg",
                    elem_classes=["primary-btn"]
                )
                
                # Предупреждение о времени
                gr.Markdown(
                    "*Анализ может занять до 30 секунд*",
                    elem_classes=["hint-text"]
                )
        
        # === Результаты (скрыты до анализа) ===
        with gr.Column(visible=False, elem_classes=["results-section"]) as results_section:
            
            # Метрики
            gr.Markdown("### 📈 Ключевые показатели")
            
            with gr.Row():
                metric_revenue = gr.Textbox(
                    label="Ср. выручка",
                    interactive=False,
                    elem_classes=["metric-card"]
                )
                metric_margin = gr.Textbox(
                    label="Маржа",
                    interactive=False,
                    elem_classes=["metric-card"]
                )
                metric_profit = gr.Textbox(
                    label="Ср. прибыль",
                    interactive=False,
                    elem_classes=["metric-card"]
                )
                metric_trend = gr.Textbox(
                    label="Тренд выручки",
                    interactive=False,
                    elem_classes=["metric-card"]
                )
            
            # Инсайты
            gr.Markdown("### 💡 Ключевые находки")
            insights_output = gr.Markdown()
            
            # Предупреждения парсера
            warnings_output = gr.Markdown(
                visible=False,
                elem_classes=["warnings-box"]
            )
        
        # === Обработчик ===
        def on_analyze(file_path: str, context: str):
            """Обработчик нажатия кнопки анализа."""
            
            if not file_path:
                gr.Warning("Пожалуйста, загрузите файл")
                return {
                    results_section: gr.update(visible=False)
                }
            
            try:
                logger.info(f"Начало анализа: {file_path}")
                result = analyze_file(file_path, context)
                
                # Форматируем метрики
                revenue_text = f"{result.metrics.avg_revenue:,.0f} ₽"
                margin_text = f"{result.metrics.avg_operating_margin_pct}%"
                profit_text = f"{result.metrics.avg_operating_profit:,.0f} ₽"
                
                # Тренд с эмодзи
                trend_emoji = {
                    "growing": "📈 Растёт",
                    "stable": "➡️ Стабильно",
                    "declining": "📉 Падает",
                    "insufficient_data": "❓ Мало данных"
                }
                trend_text = trend_emoji.get(
                    result.metrics.revenue_trend_direction.value,
                    "➡️ Стабильно"
                )
                
                # Добавляем процент если есть значимый тренд
                if result.metrics.revenue_trend_direction.value in ["growing", "declining"]:
                    trend_text += f" ({result.metrics.revenue_trend_pct:+.1f}%)"
                
                # Форматируем инсайты
                insights_md = _format_insights(result.insights)
                
                # Форматируем предупреждения
                warnings_md = ""
                show_warnings = False
                if result.parsing_warnings:
                    show_warnings = True
                    warnings_md = "⚠️ **Мы исправили данные:**\n"
                    for w in result.parsing_warnings:
                        warnings_md += f"- {w}\n"
                
                logger.info("Анализ успешно завершён")
                
                return {
                    results_section: gr.update(visible=True),
                    metric_revenue: revenue_text,
                    metric_margin: margin_text,
                    metric_profit: profit_text,
                    metric_trend: trend_text,
                    insights_output: insights_md,
                    warnings_output: gr.update(visible=show_warnings, value=warnings_md)
                }
                
            except ValueError as e:
                logger.warning(f"Ошибка валидации: {e}")
                gr.Warning(str(e))
                return {
                    results_section: gr.update(visible=True),
                    metric_revenue: "—",
                    metric_margin: "—",
                    metric_profit: "—",
                    metric_trend: "—",
                    insights_output: f"⚠️ {str(e)}",
                    warnings_output: gr.update(visible=False)
                }
                
            except Exception as e:
                logger.error(f"Ошибка анализа: {e}", exc_info=True)
                return {
                    results_section: gr.update(visible=True),
                    metric_revenue: "—",
                    metric_margin: "—",
                    metric_profit: "—",
                    metric_trend: "—",
                    insights_output: f"❌ Ошибка: {str(e)}",
                    warnings_output: gr.update(visible=False)
                }
        
        # Привязываем обработчик
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


def _format_insights(insights) -> str:
    """
    Форматирование инсайтов в Markdown с HTML-разметкой для стилей.
    """
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
            impact_line = f"\n\n💰 **Потенциал:** {insight.potential_impact}"
        
        parts.append(f"""
<div class="insight-{css_class}">

**{emoji} {insight.title}**

{insight.explanation}

→ *{insight.recommendation}*{impact_line}

</div>
""")
    
    return "\n".join(parts)

