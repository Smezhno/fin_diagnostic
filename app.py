"""
FinRentgen — Финансовый анализатор для малого бизнеса.

Точка входа приложения.

Использование:
    python app.py
    
    Затем откройте http://localhost:7860 в браузере.
"""

import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Уменьшаем шум от библиотек
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("gradio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Запуск приложения."""
    import gradio as gr
    from ui.components import create_app
    from ui.styles import CUSTOM_CSS
    
    logger.info("=" * 50)
    logger.info("🚀 Запуск FinRentgen")
    logger.info("=" * 50)
    
    app = create_app()
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # True для публичной ссылки через Gradio
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        )
    )


if __name__ == "__main__":
    main()

