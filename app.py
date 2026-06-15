import json

import streamlit as st
from langchain_core.callbacks import BaseCallbackHandler

from agents import agent, reset_stream_callback, set_stream_callback
from agents.cache import CACHE_TTL, get_valid_cached_analysis, now_utc

st.set_page_config(
    page_title="Stock Analyst Agent",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 4.25rem;
            padding-bottom: 3rem;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        .stApp,
        .block-container,
        [data-testid="stVerticalBlock"],
        [data-testid="column"],
        [data-testid="stMarkdownContainer"] {
            caret-color: transparent;
            cursor: default;
            user-select: none;
        }
        a[href^="#"],
        a.anchor-link {
            display: none !important;
        }
        .hero-title {
            margin: 0;
            text-align: center;
            font-size: 2.65rem;
            line-height: 1.15;
            font-weight: 800;
            letter-spacing: 0;
            cursor: default;
            user-select: none;
        }
        .hero-subtitle {
            margin-top: 1.05rem;
            margin-bottom: 1.35rem;
            text-align: center;
            color: rgba(250, 250, 250, 0.58);
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0;
            cursor: default;
            user-select: none;
        }
        h1 {
            text-align: center;
        }
        div[data-testid="stCaptionContainer"] {
            text-align: center;
        }
        div[data-testid="stForm"] {
            border: 1px solid rgba(250, 250, 250, 0.14);
            border-radius: 28px;
            padding: 0.75rem 0.85rem;
            background: rgba(255, 255, 255, 0.07);
        }
        div[data-testid="stTextInput"] input {
            caret-color: auto;
            min-height: 52px;
            border-radius: 20px;
            border: 0;
            background: transparent;
            font-size: 1.02rem;
            cursor: text;
            user-select: text;
        }
        div[data-testid="stTextInput"] [data-baseweb="input"],
        div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
            border-color: transparent !important;
            box-shadow: none !important;
            outline: none !important;
        }
        div[data-testid="stTextInput"] input:focus {
            box-shadow: none;
            outline: none;
        }
        div[data-testid="InputInstructions"] {
            display: none;
        }
        .portfolio-builder-scope + div div[data-testid="stFormSubmitButton"] button {
            width: 100%;
            min-height: 52px;
            border-radius: 999px;
            padding: 0.6rem 1.2rem;
            font-size: 1rem;
            font-weight: 800;
            cursor: pointer;
            white-space: nowrap;
        }
        .portfolio-builder-scope + div div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: rgb(255, 75, 75);
            border-color: rgb(255, 75, 75);
            color: white;
        }
        .portfolio-builder-scope + div div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: rgb(255, 92, 92);
            border-color: rgb(255, 92, 92);
            color: white;
        }
        .chat-composer-scope + div div[data-testid="stFormSubmitButton"] button {
            width: 48px;
            min-width: 48px;
            height: 48px;
            min-height: 48px;
            border-radius: 999px;
            padding: 0;
            font-size: 1.35rem;
            font-weight: 800;
            cursor: pointer;
        }
        div[data-testid="stButton"] button {
            min-height: 42px;
            border-radius: 999px;
            font-weight: 600;
            cursor: pointer;
        }
        .portfolio-builder-title {
            margin-top: 1.4rem;
            margin-bottom: 0.25rem;
            text-align: center;
            font-size: 1.1rem;
            font-weight: 800;
            letter-spacing: 0;
        }
        .portfolio-builder-subtitle {
            margin-bottom: 0.65rem;
            text-align: center;
            color: rgba(250, 250, 250, 0.58);
            font-size: 0.84rem;
            font-weight: 600;
        }
        div[data-testid="stExpander"] {
            border-radius: 8px;
            border-color: rgba(250, 250, 250, 0.14);
            background: rgba(255, 255, 255, 0.035);
        }
        [data-testid="stChatMessage"] {
            border-radius: 8px;
            padding: 0.35rem 0.1rem;
            user-select: text;
        }
        [data-testid="stChatMessage"] *,
        [data-testid="stChatMessageContent"] {
            caret-color: transparent;
            user-select: text;
        }
        [data-testid="stChatMessageContent"] h1,
        [data-testid="stChatMessageContent"] h2,
        [data-testid="stChatMessageContent"] h3 {
            letter-spacing: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "conversation_updated_at" not in st.session_state:
    st.session_state.conversation_updated_at = None
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = None
if "user_query_input" not in st.session_state:
    st.session_state.user_query_input = ""
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""
if "pending_display_query" not in st.session_state:
    st.session_state.pending_display_query = ""
if "portfolio_amount" not in st.session_state:
    st.session_state.portfolio_amount = 10000
if "portfolio_language" not in st.session_state:
    st.session_state.portfolio_language = "English"
if "portfolio_holdings_count" not in st.session_state:
    st.session_state.portfolio_holdings_count = 10
if "portfolio_risk" not in st.session_state:
    st.session_state.portfolio_risk = "Balanced"
if "portfolio_horizon" not in st.session_state:
    st.session_state.portfolio_horizon = "1-3yr"
if "portfolio_style" not in st.session_state:
    st.session_state.portfolio_style = "Balanced"
if "portfolio_etf_preference" not in st.session_state:
    st.session_state.portfolio_etf_preference = "Mixed"
if "portfolio_cash_pct" not in st.session_state:
    st.session_state.portfolio_cash_pct = 5
if "portfolio_overweight_sectors" not in st.session_state:
    st.session_state.portfolio_overweight_sectors = []
if "portfolio_avoid_sectors" not in st.session_state:
    st.session_state.portfolio_avoid_sectors = []
if "portfolio_quiz_active" not in st.session_state:
    st.session_state.portfolio_quiz_active = False
if "portfolio_quiz_step" not in st.session_state:
    st.session_state.portfolio_quiz_step = 0
if "portfolio_quiz_answers" not in st.session_state:
    st.session_state.portfolio_quiz_answers = {}


PORTFOLIO_SECTOR_OPTIONS = [
    "Technology",
    "Healthcare",
    "Financial Services",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Industrials",
    "Energy",
    "Utilities",
    "Real Estate",
    "Basic Materials",
    "AI",
    "Semiconductors",
    "Dividend",
    "Broad Market",
]

PORTFOLIO_QUIZ_STEPS = [
    "language",
    "investment_amount",
    "holdings_count",
    "risk",
    "horizon",
    "style",
    "etf_preference",
    "cash_pct",
    "overweight_sectors",
    "avoid_sectors",
]

PORTFOLIO_LANGUAGE_OPTIONS = ["English", "Deutsch", "Українська", "Русский", "Español"]

PORTFOLIO_I18N = {
    "English": {
        "title": "Portfolio Builder",
        "subtitle": "Start the guided quiz or use the full form",
        "start_quiz": "Start guided portfolio quiz",
        "full_form": "Open full portfolio form",
        "language": "Language",
        "select_language": "Select language",
        "question": "Question",
        "of": "of",
        "amount": "Investment amount, USD",
        "amount_question": "How much do you want to invest?",
        "holdings": "Holdings",
        "holdings_question": "How many positions should the portfolio include?",
        "risk": "Risk",
        "risk_question": "What risk level feels right?",
        "horizon": "Horizon",
        "horizon_question": "What is your investment horizon?",
        "style": "Style",
        "style_question": "Which portfolio style do you prefer?",
        "etf": "ETF preference",
        "etf_question": "How much ETF exposure do you want?",
        "cash": "Cash buffer, %",
        "cash_question": "Do you want to keep a cash buffer?",
        "overweight": "Overweight sectors/themes",
        "overweight_question": "Pick sectors/themes to overweight, or leave empty.",
        "avoid": "Avoid sectors/themes",
        "avoid_question": "Pick sectors/themes to avoid, or leave empty.",
        "next": "Next",
        "build": "Build portfolio",
        "none": "none",
        "display_prefix": "Build a stock and ETF portfolio",
        "display_holdings": "holdings",
        "display_risk": "risk",
        "display_horizon": "horizon",
        "display_style": "style",
        "display_etfs": "ETFs",
        "display_cash": "cash",
        "display_overweight": "overweight",
        "display_avoid": "avoid",
    },
    "Deutsch": {
        "title": "Portfolio Builder",
        "subtitle": "Starte den geführten Fragebogen oder nutze das komplette Formular",
        "start_quiz": "Geführten Portfolio-Fragebogen starten",
        "full_form": "Komplettes Portfolio-Formular öffnen",
        "language": "Sprache",
        "select_language": "Sprache auswählen",
        "question": "Frage",
        "of": "von",
        "amount": "Anlagebetrag, USD",
        "amount_question": "Wie viel möchtest du investieren?",
        "holdings": "Positionen",
        "holdings_question": "Wie viele Positionen soll das Portfolio enthalten?",
        "risk": "Risiko",
        "risk_question": "Welches Risikoniveau passt zu dir?",
        "horizon": "Horizont",
        "horizon_question": "Was ist dein Anlagehorizont?",
        "style": "Stil",
        "style_question": "Welchen Portfolio-Stil bevorzugst du?",
        "etf": "ETF-Präferenz",
        "etf_question": "Wie viel ETF-Anteil möchtest du?",
        "cash": "Cash-Puffer, %",
        "cash_question": "Möchtest du einen Cash-Puffer behalten?",
        "overweight": "Sektoren/Themen übergewichten",
        "overweight_question": "Wähle Sektoren/Themen zum Übergewichten oder lasse das Feld leer.",
        "avoid": "Sektoren/Themen vermeiden",
        "avoid_question": "Wähle Sektoren/Themen zum Vermeiden oder lasse das Feld leer.",
        "next": "Weiter",
        "build": "Portfolio erstellen",
        "none": "keine",
        "display_prefix": "Aktien- und ETF-Portfolio erstellen",
        "display_holdings": "Positionen",
        "display_risk": "Risiko",
        "display_horizon": "Horizont",
        "display_style": "Stil",
        "display_etfs": "ETFs",
        "display_cash": "Cash",
        "display_overweight": "Übergewichtung",
        "display_avoid": "vermeiden",
    },
    "Українська": {
        "title": "Конструктор портфеля",
        "subtitle": "Запусти покроковий квіз або скористайся повною формою",
        "start_quiz": "Запустити покроковий квіз",
        "full_form": "Відкрити повну форму портфеля",
        "language": "Мова",
        "select_language": "Оберіть мову",
        "question": "Питання",
        "of": "з",
        "amount": "Сума інвестиції, USD",
        "amount_question": "Скільки ти хочеш інвестувати?",
        "holdings": "Позиції",
        "holdings_question": "Скільки позицій має бути у портфелі?",
        "risk": "Ризик",
        "risk_question": "Який рівень ризику тобі підходить?",
        "horizon": "Горизонт",
        "horizon_question": "Який твій інвестиційний горизонт?",
        "style": "Стиль",
        "style_question": "Який стиль портфеля ти обираєш?",
        "etf": "ETF-перевага",
        "etf_question": "Яку частку ETF ти хочеш?",
        "cash": "Кеш-буфер, %",
        "cash_question": "Чи хочеш залишити кеш-буфер?",
        "overweight": "Сектори/теми для overweight",
        "overweight_question": "Оберіть сектори/теми для overweight або залиште порожнім.",
        "avoid": "Сектори/теми, яких уникати",
        "avoid_question": "Оберіть сектори/теми, яких уникати, або залиште порожнім.",
        "next": "Далі",
        "build": "Зібрати портфель",
        "none": "немає",
        "display_prefix": "Зібрати портфель з акцій та ETF",
        "display_holdings": "позицій",
        "display_risk": "ризик",
        "display_horizon": "горизонт",
        "display_style": "стиль",
        "display_etfs": "ETF",
        "display_cash": "кеш",
        "display_overweight": "overweight",
        "display_avoid": "уникати",
    },
    "Русский": {
        "title": "Конструктор портфеля",
        "subtitle": "Запусти пошаговый квиз или используй полную форму",
        "start_quiz": "Запустить пошаговый квиз",
        "full_form": "Открыть полную форму портфеля",
        "language": "Язык",
        "select_language": "Выберите язык",
        "question": "Вопрос",
        "of": "из",
        "amount": "Сумма инвестиций, USD",
        "amount_question": "Сколько ты хочешь инвестировать?",
        "holdings": "Позиции",
        "holdings_question": "Сколько позиций должно быть в портфеле?",
        "risk": "Риск",
        "risk_question": "Какой уровень риска тебе подходит?",
        "horizon": "Горизонт",
        "horizon_question": "Какой у тебя инвестиционный горизонт?",
        "style": "Стиль",
        "style_question": "Какой стиль портфеля ты предпочитаешь?",
        "etf": "ETF-предпочтение",
        "etf_question": "Какую долю ETF ты хочешь?",
        "cash": "Кеш-буфер, %",
        "cash_question": "Хочешь оставить кеш-буфер?",
        "overweight": "Секторы/темы для overweight",
        "overweight_question": "Выбери секторы/темы для overweight или оставь пустым.",
        "avoid": "Секторы/темы, которых избегать",
        "avoid_question": "Выбери секторы/темы, которых избегать, или оставь пустым.",
        "next": "Далее",
        "build": "Собрать портфель",
        "none": "нет",
        "display_prefix": "Собрать портфель из акций и ETF",
        "display_holdings": "позиций",
        "display_risk": "риск",
        "display_horizon": "горизонт",
        "display_style": "стиль",
        "display_etfs": "ETF",
        "display_cash": "кеш",
        "display_overweight": "overweight",
        "display_avoid": "избегать",
    },
    "Español": {
        "title": "Constructor de cartera",
        "subtitle": "Inicia el cuestionario guiado o usa el formulario completo",
        "start_quiz": "Iniciar cuestionario guiado",
        "full_form": "Abrir formulario completo",
        "language": "Idioma",
        "select_language": "Selecciona idioma",
        "question": "Pregunta",
        "of": "de",
        "amount": "Monto de inversión, USD",
        "amount_question": "¿Cuánto quieres invertir?",
        "holdings": "Posiciones",
        "holdings_question": "¿Cuántas posiciones debe incluir la cartera?",
        "risk": "Riesgo",
        "risk_question": "¿Qué nivel de riesgo prefieres?",
        "horizon": "Horizonte",
        "horizon_question": "¿Cuál es tu horizonte de inversión?",
        "style": "Estilo",
        "style_question": "¿Qué estilo de cartera prefieres?",
        "etf": "Preferencia ETF",
        "etf_question": "¿Cuánta exposición a ETF quieres?",
        "cash": "Reserva en efectivo, %",
        "cash_question": "¿Quieres mantener una reserva en efectivo?",
        "overweight": "Sectores/temas a sobreponderar",
        "overweight_question": "Elige sectores/temas a sobreponderar o déjalo vacío.",
        "avoid": "Sectores/temas a evitar",
        "avoid_question": "Elige sectores/temas a evitar o déjalo vacío.",
        "next": "Siguiente",
        "build": "Construir cartera",
        "none": "ninguno",
        "display_prefix": "Construir una cartera de acciones y ETF",
        "display_holdings": "posiciones",
        "display_risk": "riesgo",
        "display_horizon": "horizonte",
        "display_style": "estilo",
        "display_etfs": "ETF",
        "display_cash": "efectivo",
        "display_overweight": "sobreponderar",
        "display_avoid": "evitar",
    },
}

PORTFOLIO_OPTION_LABELS = {
    "English": {},
    "Deutsch": {
        "Conservative": "Konservativ",
        "Balanced": "Ausgewogen",
        "Aggressive": "Aggressiv",
        "Growth": "Wachstum",
        "Value": "Value",
        "Dividend": "Dividenden",
        "Quality": "Qualität",
        "Defensive": "Defensiv",
        "Mixed": "Gemischt",
        "ETF-heavy": "ETF-lastig",
        "Stocks-only": "Nur Aktien",
        "Technology": "Technologie",
        "Healthcare": "Gesundheit",
        "Financial Services": "Finanzdienstleistungen",
        "Communication Services": "Kommunikation",
        "Consumer Cyclical": "Zyklischer Konsum",
        "Consumer Defensive": "Defensiver Konsum",
        "Industrials": "Industrie",
        "Energy": "Energie",
        "Utilities": "Versorger",
        "Real Estate": "Immobilien",
        "Basic Materials": "Grundstoffe",
        "Semiconductors": "Halbleiter",
        "Dividend": "Dividenden",
        "Broad Market": "Breiter Markt",
    },
    "Українська": {
        "Conservative": "Консервативний",
        "Balanced": "Збалансований",
        "Aggressive": "Агресивний",
        "Growth": "Зростання",
        "Value": "Вартість",
        "Dividend": "Дивідендний",
        "Quality": "Якість",
        "Defensive": "Захисний",
        "Mixed": "Змішано",
        "ETF-heavy": "Більше ETF",
        "Stocks-only": "Тільки акції",
        "Technology": "Технології",
        "Healthcare": "Охорона здоров'я",
        "Financial Services": "Фінансові послуги",
        "Communication Services": "Комунікації",
        "Consumer Cyclical": "Циклічний споживчий сектор",
        "Consumer Defensive": "Захисний споживчий сектор",
        "Industrials": "Промисловість",
        "Energy": "Енергетика",
        "Utilities": "Комунальні послуги",
        "Real Estate": "Нерухомість",
        "Basic Materials": "Базові матеріали",
        "Semiconductors": "Напівпровідники",
        "Dividend": "Дивіденди",
        "Broad Market": "Широкий ринок",
    },
    "Русский": {
        "Conservative": "Консервативный",
        "Balanced": "Сбалансированный",
        "Aggressive": "Агрессивный",
        "Growth": "Рост",
        "Value": "Стоимость",
        "Dividend": "Дивидендный",
        "Quality": "Качество",
        "Defensive": "Защитный",
        "Mixed": "Смешанный",
        "ETF-heavy": "Больше ETF",
        "Stocks-only": "Только акции",
        "Technology": "Технологии",
        "Healthcare": "Здравоохранение",
        "Financial Services": "Финансовые услуги",
        "Communication Services": "Коммуникации",
        "Consumer Cyclical": "Циклический потребсектор",
        "Consumer Defensive": "Защитный потребсектор",
        "Industrials": "Промышленность",
        "Energy": "Энергетика",
        "Utilities": "Коммунальные услуги",
        "Real Estate": "Недвижимость",
        "Basic Materials": "Базовые материалы",
        "Semiconductors": "Полупроводники",
        "Dividend": "Дивиденды",
        "Broad Market": "Широкий рынок",
    },
    "Español": {
        "Conservative": "Conservador",
        "Balanced": "Equilibrado",
        "Aggressive": "Agresivo",
        "Growth": "Crecimiento",
        "Value": "Valor",
        "Dividend": "Dividendos",
        "Quality": "Calidad",
        "Defensive": "Defensivo",
        "Mixed": "Mixto",
        "ETF-heavy": "Más ETF",
        "Stocks-only": "Solo acciones",
        "Technology": "Tecnología",
        "Healthcare": "Salud",
        "Financial Services": "Servicios financieros",
        "Communication Services": "Comunicaciones",
        "Consumer Cyclical": "Consumo cíclico",
        "Consumer Defensive": "Consumo defensivo",
        "Industrials": "Industriales",
        "Energy": "Energía",
        "Utilities": "Servicios públicos",
        "Real Estate": "Bienes raíces",
        "Basic Materials": "Materiales básicos",
        "Semiconductors": "Semiconductores",
        "Dividend": "Dividendos",
        "Broad Market": "Mercado amplio",
    },
}


def portfolio_language() -> str:
    return st.session_state.portfolio_quiz_answers.get("language") or st.session_state.portfolio_language


def pt(key: str, language: str | None = None) -> str:
    language = language or portfolio_language()
    return PORTFOLIO_I18N.get(language, PORTFOLIO_I18N["English"]).get(key, PORTFOLIO_I18N["English"][key])


def po(value: str, language: str | None = None) -> str:
    language = language or portfolio_language()
    return PORTFOLIO_OPTION_LABELS.get(language, {}).get(value, value)


def submit_query():
    st.session_state.pending_query = st.session_state.user_query_input.strip()
    st.session_state.pending_display_query = st.session_state.pending_query
    st.session_state.user_query_input = ""


def set_example_query(text: str):
    st.session_state.user_query_input = text


def submit_portfolio_builder():
    payload = {
        "language": st.session_state.portfolio_language,
        "investment_amount": int(st.session_state.portfolio_amount),
        "currency": "USD",
        "holdings_count": int(st.session_state.portfolio_holdings_count),
        "risk": st.session_state.portfolio_risk,
        "horizon": st.session_state.portfolio_horizon,
        "style": st.session_state.portfolio_style,
        "etf_preference": st.session_state.portfolio_etf_preference,
        "cash_pct": int(st.session_state.portfolio_cash_pct),
        "overweight_sectors": st.session_state.portfolio_overweight_sectors,
        "avoid_sectors": st.session_state.portfolio_avoid_sectors,
    }
    st.session_state.pending_query = (
        "PORTFOLIO_BUILDER_REQUEST "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    language = payload["language"]
    overweight = ", ".join(po(item, language) for item in payload["overweight_sectors"]) or pt("none", language)
    avoid = ", ".join(po(item, language) for item in payload["avoid_sectors"]) or pt("none", language)
    st.session_state.pending_display_query = (
        f"{pt('display_prefix', language)}: "
        f"{payload['language']}, ${payload['investment_amount']:,.0f}, "
        f"{payload['holdings_count']} {pt('display_holdings', language)}, "
        f"{po(payload['risk'], language)} {pt('display_risk', language)}, "
        f"{payload['horizon']} {pt('display_horizon', language)}, "
        f"{po(payload['style'], language)} {pt('display_style', language)}, "
        f"{po(payload['etf_preference'], language)} {pt('display_etfs', language)}, "
        f"{payload['cash_pct']}% {pt('display_cash', language)}, "
        f"{pt('display_overweight', language)}: {overweight}, "
        f"{pt('display_avoid', language)}: {avoid}."
    )


def start_portfolio_quiz(preferences: dict | None = None):
    preferences = preferences or {}
    st.session_state.portfolio_quiz_active = True
    st.session_state.portfolio_quiz_answers = {
        key: value
        for key, value in preferences.items()
        if value not in (None, "", [])
    }
    for index, field in enumerate(PORTFOLIO_QUIZ_STEPS):
        if field not in st.session_state.portfolio_quiz_answers:
            st.session_state.portfolio_quiz_step = index
            break
    else:
        st.session_state.portfolio_quiz_step = len(PORTFOLIO_QUIZ_STEPS) - 1


def answer_portfolio_quiz(field: str, value):
    st.session_state.portfolio_quiz_answers[field] = value
    st.session_state.portfolio_quiz_step += 1


def finish_portfolio_quiz():
    answers = st.session_state.portfolio_quiz_answers
    st.session_state.portfolio_language = answers.get("language") or "English"
    st.session_state.portfolio_amount = int(answers.get("investment_amount") or 10000)
    st.session_state.portfolio_holdings_count = int(answers.get("holdings_count") or 10)
    st.session_state.portfolio_risk = answers.get("risk") or "Balanced"
    st.session_state.portfolio_horizon = answers.get("horizon") or "1-3yr"
    st.session_state.portfolio_style = answers.get("style") or "Balanced"
    st.session_state.portfolio_etf_preference = answers.get("etf_preference") or "Mixed"
    st.session_state.portfolio_cash_pct = int(answers.get("cash_pct") or 0)
    st.session_state.portfolio_overweight_sectors = answers.get("overweight_sectors") or []
    st.session_state.portfolio_avoid_sectors = answers.get("avoid_sectors") or []
    st.session_state.portfolio_quiz_active = False
    st.session_state.portfolio_quiz_step = 0
    submit_portfolio_builder()


conversation_updated_at = st.session_state.conversation_updated_at
if conversation_updated_at and now_utc() - conversation_updated_at > CACHE_TTL:
    st.session_state.conversation = []
    st.session_state.conversation_updated_at = None
    st.session_state.analysis_cache = None

valid_cache = get_valid_cached_analysis(st.session_state.analysis_cache)
if not valid_cache:
    st.session_state.analysis_cache = None


class StreamlitTokenCallback(BaseCallbackHandler):
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.tokens = []

    def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)
        self.placeholder.markdown("".join(self.tokens) + "▌")

    def finish(self, final_text: str):
        self.placeholder.markdown(final_text)


def render_header():
    left, center, right = st.columns([1, 2.35, 1])
    with center:
        st.markdown(
            """
            <div class="hero-title">Stock Analyst Agent</div>
            <div class="hero-subtitle">MULTI-AGENT EQUITY RESEARCH</div>
            """,
            unsafe_allow_html=True,
        )


def render_composer():
    left, center, right = st.columns([0.35, 3.3, 0.35])
    with center:
        st.markdown('<div class="chat-composer-scope"></div>', unsafe_allow_html=True)
        with st.form("query_form", clear_on_submit=False):
            input_col, send_col = st.columns([12, 1])
            with input_col:
                st.text_input(
                    "Ask about a stock",
                    placeholder="Ask about a stock or company",
                    label_visibility="collapsed",
                    key="user_query_input",
                )
            with send_col:
                run = st.form_submit_button("↑", type="primary", on_click=submit_query)

        _, example_col_1, example_col_2, _ = st.columns([0.3, 1.3, 1.3, 0.3])
        with example_col_1:
            st.button(
                "Analyze Tesla stock",
                use_container_width=True,
                on_click=set_example_query,
                args=("Analyze Tesla stock",),
            )
        with example_col_2:
            st.button(
                "Compare NVDA and Apple risks",
                use_container_width=True,
                on_click=set_example_query,
                args=("Compare NVDA and Apple risks",),
            )

    return run


def render_portfolio_builder():
    language = portfolio_language()
    left, center, right = st.columns([0.35, 3.3, 0.35])
    with center:
        st.markdown(
            f"""
            <div class="portfolio-builder-title">{pt("title", language)}</div>
            <div class="portfolio-builder-subtitle">{pt("subtitle", language)}</div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.portfolio_quiz_active:
            render_portfolio_step_quiz()
        else:
            st.button(
                pt("start_quiz", language),
                type="primary",
                use_container_width=True,
                on_click=start_portfolio_quiz,
            )

        with st.expander(pt("full_form", language), expanded=False):
            st.selectbox(
                pt("language", language),
                PORTFOLIO_LANGUAGE_OPTIONS,
                key="portfolio_language",
            )
            st.markdown('<div class="portfolio-builder-scope"></div>', unsafe_allow_html=True)
            with st.form("portfolio_builder_form", clear_on_submit=False):
                amount_col, count_col, cash_col = st.columns([1.15, 1, 1])
                with amount_col:
                    st.number_input(
                        pt("amount", language),
                        min_value=100,
                        max_value=10_000_000,
                        step=500,
                        key="portfolio_amount",
                    )
                with count_col:
                    st.number_input(
                        pt("holdings", language),
                        min_value=3,
                        max_value=25,
                        step=1,
                        key="portfolio_holdings_count",
                    )
                with cash_col:
                    st.slider(
                        pt("cash", language),
                        min_value=0,
                        max_value=20,
                        step=5,
                        key="portfolio_cash_pct",
                    )

                risk_col, horizon_col = st.columns(2)
                with risk_col:
                    st.radio(
                        pt("risk", language),
                        ["Conservative", "Balanced", "Aggressive"],
                        horizontal=True,
                        format_func=lambda value: po(value, language),
                        key="portfolio_risk",
                    )
                with horizon_col:
                    st.radio(
                        pt("horizon", language),
                        ["<6mo", "6-18mo", "1-3yr", "3yr+"],
                        horizontal=True,
                        key="portfolio_horizon",
                    )

                style_col, etf_col = st.columns(2)
                with style_col:
                    st.selectbox(
                        pt("style", language),
                        ["Balanced", "Growth", "Value", "Dividend", "Quality", "Defensive"],
                        format_func=lambda value: po(value, language),
                        key="portfolio_style",
                    )
                with etf_col:
                    st.selectbox(
                        pt("etf", language),
                        ["Mixed", "ETF-heavy", "Stocks-only"],
                        format_func=lambda value: po(value, language),
                        key="portfolio_etf_preference",
                    )

                overweight_col, avoid_col = st.columns(2)
                with overweight_col:
                    st.multiselect(
                        pt("overweight", language),
                        PORTFOLIO_SECTOR_OPTIONS,
                        format_func=lambda value: po(value, language),
                        key="portfolio_overweight_sectors",
                    )
                with avoid_col:
                    st.multiselect(
                        pt("avoid", language),
                        PORTFOLIO_SECTOR_OPTIONS,
                        format_func=lambda value: po(value, language),
                        key="portfolio_avoid_sectors",
                    )

                st.form_submit_button(
                    pt("build", language),
                    type="primary",
                    use_container_width=True,
                    on_click=submit_portfolio_builder,
                )


def render_portfolio_step_quiz():
    answers = st.session_state.portfolio_quiz_answers
    language = answers.get("language") or st.session_state.portfolio_language
    step = min(st.session_state.portfolio_quiz_step, len(PORTFOLIO_QUIZ_STEPS) - 1)
    field = PORTFOLIO_QUIZ_STEPS[step]
    progress = (step + 1) / len(PORTFOLIO_QUIZ_STEPS)

    st.progress(progress)
    st.caption(f"{pt('question', language)} {step + 1} {pt('of', language)} {len(PORTFOLIO_QUIZ_STEPS)}")

    if field == "language":
        st.markdown(pt("select_language", language))
        for label in PORTFOLIO_LANGUAGE_OPTIONS:
            if st.button(label, use_container_width=True):
                answer_portfolio_quiz(field, label)
                st.session_state.portfolio_language = label
                st.rerun()
        return

    if field == "investment_amount":
        value = st.number_input(
            pt("amount_question", language),
            min_value=100,
            max_value=10_000_000,
            step=500,
            value=int(answers.get("investment_amount") or 10000),
            key="portfolio_quiz_amount",
        )
        if st.button(pt("next", language), type="primary", use_container_width=True):
            answer_portfolio_quiz(field, int(value))
            st.rerun()
        return

    if field == "holdings_count":
        st.markdown(pt("holdings_question", language))
        for label, value in [
            ({"English": "Focused: 3-5", "Deutsch": "Fokussiert: 3-5", "Українська": "Фокус: 3-5", "Русский": "Фокус: 3-5", "Español": "Enfocado: 3-5"}.get(language, "Focused: 3-5"), 5),
            ({"English": "Balanced: 8-10", "Deutsch": "Ausgewogen: 8-10", "Українська": "Збалансовано: 8-10", "Русский": "Сбалансировано: 8-10", "Español": "Equilibrado: 8-10"}.get(language, "Balanced: 8-10"), 10),
            ({"English": "Diversified: 12-15", "Deutsch": "Diversifiziert: 12-15", "Українська": "Диверсифіковано: 12-15", "Русский": "Диверсифицированно: 12-15", "Español": "Diversificado: 12-15"}.get(language, "Diversified: 12-15"), 15),
            ({"English": "Broad: 20+", "Deutsch": "Breit: 20+", "Українська": "Широко: 20+", "Русский": "Широко: 20+", "Español": "Amplio: 20+"}.get(language, "Broad: 20+"), 20),
        ]:
            if st.button(label, use_container_width=True):
                answer_portfolio_quiz(field, value)
                st.rerun()
        return

    if field == "risk":
        st.markdown(pt("risk_question", language))
        for label in ["Conservative", "Balanced", "Aggressive"]:
            if st.button(po(label, language), use_container_width=True):
                answer_portfolio_quiz(field, label)
                st.rerun()
        return

    if field == "horizon":
        st.markdown(pt("horizon_question", language))
        for label in ["<6mo", "6-18mo", "1-3yr", "3yr+"]:
            if st.button(label, use_container_width=True):
                answer_portfolio_quiz(field, label)
                st.rerun()
        return

    if field == "style":
        st.markdown(pt("style_question", language))
        for label in ["Balanced", "Growth", "Value", "Dividend", "Quality", "Defensive"]:
            if st.button(po(label, language), use_container_width=True):
                answer_portfolio_quiz(field, label)
                st.rerun()
        return

    if field == "etf_preference":
        st.markdown(pt("etf_question", language))
        for label in ["Mixed", "ETF-heavy", "Stocks-only"]:
            if st.button(po(label, language), use_container_width=True):
                answer_portfolio_quiz(field, label)
                st.rerun()
        return

    if field == "cash_pct":
        st.markdown(pt("cash_question", language))
        for label, value in [("0%", 0), ("5%", 5), ("10%", 10), ("20%", 20)]:
            if st.button(label, use_container_width=True):
                answer_portfolio_quiz(field, value)
                st.rerun()
        return

    if field == "overweight_sectors":
        selected = st.multiselect(
            pt("overweight_question", language),
            PORTFOLIO_SECTOR_OPTIONS,
            default=answers.get("overweight_sectors") or [],
            format_func=lambda value: po(value, language),
            key="portfolio_quiz_overweight",
        )
        if st.button(pt("next", language), type="primary", use_container_width=True):
            answer_portfolio_quiz(field, selected)
            st.rerun()
        return

    if field == "avoid_sectors":
        selected = st.multiselect(
            pt("avoid_question", language),
            PORTFOLIO_SECTOR_OPTIONS,
            default=answers.get("avoid_sectors") or [],
            format_func=lambda value: po(value, language),
            key="portfolio_quiz_avoid",
        )
        if st.button(pt("build", language), type="primary", use_container_width=True):
            answer_portfolio_quiz(field, selected)
            finish_portfolio_quiz()
            st.rerun()


def render_conversation(streaming: bool = False):
    message_count = len(st.session_state.conversation)
    heading_col, count_col = st.columns([5, 1])
    heading_col.subheader("Conversation")
    count_col.caption(f"{message_count} messages")

    with st.container(height=560, border=True):
        for message in st.session_state.conversation:
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(message["content"])

        if streaming:
            with st.chat_message("assistant"):
                return st.empty()

    return None


render_header()
run = render_composer()
render_portfolio_builder()

if st.session_state.conversation:
    clear_col, _ = st.columns([1, 6])
    with clear_col:
        if st.button("Clear", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.conversation_updated_at = None
            st.session_state.analysis_cache = None
            st.rerun()

query = st.session_state.pending_query
display_query = st.session_state.pending_display_query or query
conversation_rendered = False

if query:
    st.session_state.pending_query = ""
    st.session_state.pending_display_query = ""
    prior_conversation = list(st.session_state.conversation)
    st.session_state.conversation.append({"role": "user", "content": display_query})
    assistant_placeholder = render_conversation(streaming=True)
    conversation_rendered = True

    stream_callback = StreamlitTokenCallback(assistant_placeholder)
    previous_callback = set_stream_callback(stream_callback)

    with st.status("Analyzing request...", expanded=True) as status:
        try:
            state = agent.invoke(
                {
                    "user_query": query,
                    "conversation": prior_conversation,
                    "cached_analysis": st.session_state.analysis_cache,
                    "analysis": "",
                    "error": None,
                }
            )
        finally:
            reset_stream_callback(previous_callback)

        if state.get("error"):
            status.update(label="Error", state="error")
            st.error(state["error"])
            st.stop()

        status.update(label="Done", state="complete", expanded=False)

    st.session_state.analysis_cache = state.get("cached_analysis")
    stream_callback.finish(state["analysis"])
    st.session_state.conversation.append({"role": "assistant", "content": state["analysis"]})
    st.session_state.conversation_updated_at = now_utc()
    st.rerun()

elif run:
    st.warning("Ask a question or enter a ticker/company name first.")

if st.session_state.conversation and not conversation_rendered:
    render_conversation()
