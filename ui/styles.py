"""
CSS стили для FinRentgen UI.

Дизайн: современный, минималистичный, с акцентными цветами для инсайтов.
Вдохновлён финтех-дашбордами.
"""

CUSTOM_CSS = """
/* === Переменные === */
:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-card: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --border: #475569;
    --radius: 12px;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

/* === Основной контейнер === */
.gradio-container {
    background: var(--bg-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* === Заголовки === */
h1, h2, h3 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

h1 {
    font-size: 2rem !important;
    background: linear-gradient(135deg, var(--primary), #8b5cf6) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* === Карточки метрик === */
.metric-card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 20px !important;
    text-align: center !important;
}

.metric-card label {
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

.metric-card input {
    background: transparent !important;
    border: none !important;
    color: var(--text-primary) !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    text-align: center !important;
}

/* === Инсайты === */
.insight-problem {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05)) !important;
    border-left: 4px solid var(--danger) !important;
    border-radius: var(--radius) !important;
    padding: 20px !important;
    margin: 16px 0 !important;
}

.insight-observation {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05)) !important;
    border-left: 4px solid var(--warning) !important;
    border-radius: var(--radius) !important;
    padding: 20px !important;
    margin: 16px 0 !important;
}

.insight-opportunity {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)) !important;
    border-left: 4px solid var(--success) !important;
    border-radius: var(--radius) !important;
    padding: 20px !important;
    margin: 16px 0 !important;
}

/* === Кнопки === */
.primary-btn {
    background: linear-gradient(135deg, var(--primary), #8b5cf6) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px 32px !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(37, 99, 235, 0.4) !important;
}

/* === Загрузка файла === */
.file-upload {
    background: var(--bg-secondary) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    transition: border-color 0.2s !important;
}

.file-upload:hover {
    border-color: var(--primary) !important;
}

/* === Текстовые поля === */
textarea, input[type="text"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    padding: 12px !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: var(--primary) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
}

/* === Предупреждения === */
.warnings-box {
    background: rgba(245, 158, 11, 0.1) !important;
    border: 1px solid var(--warning) !important;
    border-radius: var(--radius) !important;
    padding: 16px 20px !important;
    margin: 16px 0 !important;
    color: var(--text-primary) !important;
}

/* === Текст-подсказка === */
.hint-text {
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-style: italic !important;
}

/* === Секция результатов === */
.results-section {
    background: var(--bg-secondary) !important;
    border-radius: var(--radius) !important;
    padding: 24px !important;
    margin-top: 24px !important;
}

/* === Markdown контент === */
.markdown-body {
    color: var(--text-primary) !important;
}

.markdown-body strong {
    color: var(--text-primary) !important;
}

.markdown-body em {
    color: var(--text-secondary) !important;
}

/* === Таблицы === */
table {
    background: var(--bg-card) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}

th {
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
}

td {
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}

/* === Анимации загрузки === */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* === Прокрутка === */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
}
"""

