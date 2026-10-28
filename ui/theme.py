"""Shared visual language for the app.

Everything here is presentation-only: a global stylesheet plus a few tiny
HTML helpers used by the views. No application state or business logic lives
in this module.
"""

import html as _html
import math
from typing import Iterable, Optional

import streamlit as st


NAV_ICONS = {
    'Home': '⌂',
    'Flashcards': '▤',
    'Quiz': '◎',
    'Results': '◉',
    'Library': '▦',
}


def esc(value) -> str:
    """Escape a value for safe interpolation into custom HTML."""
    return _html.escape(str(value if value is not None else ''))


def nav_label(view: str) -> str:
    return f"{NAV_ICONS.get(view, '•')}   {view}"


def inject():
    st.markdown(f'<style>{CSS}</style>', unsafe_allow_html=True)


def brand():
    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">✦</div>
            <div>
                <div class="brand-name">Lumina</div>
                <div class="brand-sub">AI Learning Studio</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, subtitle: str, chips: Optional[Iterable[str]] = None):
    chip_html = ''
    if chips:
        item = ''.join(f'<span class="chip">{esc(chip)}</span>' for chip in chips)
        chip_html = f'<div class="chip-row">{item}</div>'
    st.markdown(
        f"""
        <div class="page-head">
            <div class="eyebrow">{esc(eyebrow)}</div>
            <h1 class="page-title">{esc(title)}</h1>
            <p class="hero-sub">{esc(subtitle)}</p>
            {chip_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(step: str, title: str, subtitle: str = ''):
    sub = f'<p>{esc(subtitle)}</p>' if subtitle else ''
    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-num">{esc(step)}</div>
            <div>
                <h3>{esc(title)}</h3>
                {sub}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ring(
    percent: Optional[float],
    caption: str = 'Mastery',
    key: str = 'ring',
    size: int = 148,
    stroke: int = 11,
) -> str:
    """Return an SVG progress ring as an HTML string."""
    value = 0.0 if percent is None else max(0.0, min(100.0, float(percent)))
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - value / 100.0)
    gradient_id = 'ring-' + ''.join(ch for ch in key if ch.isalnum() or ch == '-')
    display = '—' if percent is None else f'{value:.0f}%'
    return f"""
    <div class="ring-wrap" style="width:{size}px;height:{size}px;">
        <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
            <defs>
                <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#8B5CF6" />
                    <stop offset="55%" stop-color="#6366F1" />
                    <stop offset="100%" stop-color="#22D3EE" />
                </linearGradient>
            </defs>
            <circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none"
                    stroke="rgba(148,163,184,0.14)" stroke-width="{stroke}" />
            <circle cx="{size / 2}" cy="{size / 2}" r="{radius}" fill="none"
                    stroke="url(#{gradient_id})" stroke-width="{stroke}"
                    stroke-linecap="round" stroke-dasharray="{circumference:.2f}"
                    stroke-dashoffset="{offset:.2f}"
                    style="filter: drop-shadow(0 0 5px rgba(139,92,246,0.55)); transition: stroke-dashoffset .6s ease;" />
        </svg>
        <div class="ring-center">
            <span class="ring-value">{display}</span>
            <span class="ring-caption">{esc(caption)}</span>
        </div>
    </div>
    """


def stat_snapshot(items):
    """Render a responsive row of read-only snapshot cards.

    ``items`` is a sequence of ``(label, value, hint)`` tuples.
    """
    cards = ''.join(
        f"""
        <div class="snap">
            <div class="k">{esc(label)}</div>
            <div class="v">{esc(value)}</div>
            <div class="s">{esc(hint)}</div>
        </div>
        """
        for label, value, hint in items
    )
    st.markdown(f'<div class="snapshot-grid">{cards}</div>', unsafe_allow_html=True)


def badge(text: str, tone: str = 'violet') -> str:
    return f'<span class="badge badge-{esc(tone)}">{esc(text)}</span>'


def empty_state(icon: str, title: str, text: str):
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">{esc(icon)}</div>
            <div class="empty-title">{esc(title)}</div>
            <div class="empty-text">{esc(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #060912;
    --bg-soft: #0A1020;
    --panel: #0E1526;
    --panel-2: #111A2E;
    --line: rgba(148, 163, 184, 0.13);
    --line-strong: rgba(139, 92, 246, 0.34);
    --text: #E8EDF7;
    --muted: #8A97AD;
    --violet: #8B5CF6;
    --indigo: #6366F1;
    --cyan: #22D3EE;
    --green: #34D399;
    --amber: #FBBF24;
    --red: #FB7185;
    --radius: 22px;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    font-family: 'Manrope', 'Inter', 'Segoe UI', sans-serif;
    color: var(--text);
}

.stApp {
    background:
        radial-gradient(1100px 620px at 12% -8%, rgba(124, 58, 237, 0.20), transparent 62%),
        radial-gradient(900px 520px at 92% 2%, rgba(34, 211, 238, 0.09), transparent 58%),
        radial-gradient(800px 500px at 55% 110%, rgba(99, 102, 241, 0.09), transparent 60%),
        linear-gradient(180deg, #070B14 0%, #080D18 52%, #060910 100%);
    background-attachment: fixed;
}

[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"] {
    background: transparent;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"] {
    right: 1rem;
}

#MainMenu, footer {
    visibility: hidden;
}

.block-container {
    padding-top: 2.2rem;
    padding-bottom: 4.5rem;
    max-width: 1440px;
}

/* ------------------------------------------------------------- scrollbars */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.25);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}

/* ---------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A0F1D 0%, #070B14 58%, #050810 100%);
    border-right: 1px solid rgba(139, 92, 246, 0.14);
    min-width: 292px;
    max-width: 292px;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.15rem 0.9rem 2rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--muted);
}

.brand {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    padding: 0.15rem 0.35rem 0.9rem;
}

.brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: linear-gradient(135deg, #8B5CF6, #6366F1 55%, #22D3EE);
    display: grid;
    place-items: center;
    font-size: 1.15rem;
    color: #fff;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.45);
}

.brand-name {
    font-weight: 800;
    letter-spacing: -0.02em;
    font-size: 1.08rem;
    color: #F8FAFC;
}

.brand-sub {
    color: #6F7D94;
    font-size: 0.64rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 700;
}

.side-label {
    margin: 0.7rem 0.45rem 0.45rem;
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #5B6880;
    font-weight: 800;
}

.side-card {
    margin: 0.25rem 0.2rem 0.5rem;
    padding: 0.85rem 0.9rem;
    border-radius: 16px;
    border: 1px solid rgba(139, 92, 246, 0.20);
    background:
        radial-gradient(220px 90px at 100% 0%, rgba(139, 92, 246, 0.16), transparent 70%),
        rgba(14, 21, 38, 0.78);
}

.side-card-label {
    font-size: 0.58rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #7C8AA3;
    font-weight: 800;
}

.side-card-title {
    margin-top: 0.3rem;
    font-size: 0.92rem;
    font-weight: 800;
    color: #F1F5F9;
    letter-spacing: -0.01em;
    line-height: 1.3;
}

.side-card-meta {
    margin-top: 0.28rem;
    font-size: 0.72rem;
    color: #8A97AD;
}

.engine-card {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: 0.2rem;
    padding: 0.65rem 0.75rem;
    border-radius: 13px;
    border: 1px solid var(--line);
    background: rgba(9, 14, 26, 0.7);
    color: #A9B5C8;
    font-size: 0.72rem;
    font-weight: 600;
}

.engine-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px rgba(52, 211, 153, 0.7);
    flex: 0 0 auto;
}

.engine-dot.remote {
    background: var(--violet);
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.7);
}

.side-footer {
    margin: 1.2rem 0.45rem 0;
    padding-top: 0.8rem;
    border-top: 1px solid rgba(148, 163, 184, 0.09);
    color: #4E5B72;
    font-size: 0.66rem;
    letter-spacing: 0.04em;
}

/* ------------------------------------------------------------ sidebar nav */
[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    display: none;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 0.28rem;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    width: 100%;
    margin: 0;
    padding: 0.62rem 0.78rem;
    border-radius: 13px;
    border: 1px solid transparent;
    background: transparent;
    color: #9BA8BD;
    font-weight: 700;
    transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(139, 92, 246, 0.10);
    color: #E8EDF7;
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, rgba(139, 92, 246, 0.24), rgba(99, 102, 241, 0.09));
    border-color: rgba(139, 92, 246, 0.36);
    color: #FFFFFF;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 8px 20px rgba(76, 29, 149, 0.18);
}

[data-testid="stSidebar"] [role="radiogroup"] label p {
    font-size: 0.84rem;
    font-weight: 700 !important;
    letter-spacing: 0.01em;
}

/* ---------------------------------------------------------------- headings */
h1, h2, h3, h4 {
    color: #F8FAFC;
    letter-spacing: -0.02em;
}

.stApp h1 {
    font-weight: 800;
    letter-spacing: -0.035em;
    line-height: 1.12;
    background: linear-gradient(102deg, #FFFFFF 8%, #D8CCFF 52%, #93C5FD 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.page-head {
    animation: rise 0.45s ease both;
}

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #A78BFA;
    margin-bottom: 0.4rem;
}

.eyebrow::before {
    content: '';
    width: 22px;
    height: 1px;
    background: linear-gradient(90deg, #8B5CF6, transparent);
}

.page-title {
    margin: 0;
}

.hero-sub {
    color: #94A3B8;
    font-size: 0.98rem;
    line-height: 1.65;
    max-width: 760px;
    margin: 0.45rem 0 0;
}

.chip-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 1rem 0 1.35rem;
}

.chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.34rem 0.72rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #C4B5FD;
    background: rgba(139, 92, 246, 0.10);
    border: 1px solid rgba(139, 92, 246, 0.22);
    letter-spacing: 0.01em;
}

.chip::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: linear-gradient(135deg, #8B5CF6, #22D3EE);
    box-shadow: 0 0 8px rgba(139, 92, 246, 0.8);
}

.section-head {
    display: flex;
    gap: 0.85rem;
    align-items: flex-start;
    margin: 0.15rem 0 1.05rem;
}

.section-num {
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
    border-radius: 11px;
    display: grid;
    place-items: center;
    font-size: 0.7rem;
    font-weight: 800;
    color: #C4B5FD;
    background: rgba(139, 92, 246, 0.13);
    border: 1px solid rgba(139, 92, 246, 0.26);
}

.section-head h3 {
    margin: 0;
    font-size: 1.02rem;
    font-weight: 800;
    color: #F1F5F9;
    letter-spacing: -0.01em;
}

.section-head p {
    margin: 0.18rem 0 0;
    color: var(--muted);
    font-size: 0.8rem;
    line-height: 1.5;
}

/* --------------------------------------------------------------- snapshots */
.snapshot-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.85rem;
    margin: 0.2rem 0 1.45rem;
}

.snap {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--line);
    background: linear-gradient(160deg, rgba(18, 26, 45, 0.92), rgba(9, 14, 26, 0.94));
    border-radius: 19px;
    padding: 0.95rem 1.05rem;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.snap::after {
    content: '';
    position: absolute;
    right: -34px;
    bottom: -58px;
    width: 124px;
    height: 124px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.20), transparent 70%);
    pointer-events: none;
}

.snap .k {
    color: var(--muted);
    font-size: 0.62rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 800;
}

.snap .v {
    font-size: 1.5rem;
    font-weight: 800;
    color: #F8FAFC;
    margin-top: 0.28rem;
    letter-spacing: -0.03em;
    line-height: 1.15;
}

.snap .s {
    color: #74829A;
    font-size: 0.71rem;
    margin-top: 0.18rem;
    line-height: 1.45;
}

/* ------------------------------------------------------------------ panels */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(160deg, rgba(15, 23, 42, 0.88), rgba(8, 13, 24, 0.93));
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 0.35rem;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.30), inset 0 1px 0 rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    animation: rise 0.5s ease both;
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 0.85rem;
}

/* ------------------------------------------------------------------ inputs */
label,
.stRadio label p,
.stSelectbox label p,
.stTextInput label p,
.stTextArea label p,
.stSlider label p,
.stNumberInput label p,
.stFileUploader label p,
.stCheckbox label p {
    color: #B7C2D4 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
}

.stTextInput div[data-baseweb="input"],
.stTextArea div[data-baseweb="textarea"],
.stNumberInput div[data-baseweb="input"] {
    background: rgba(6, 10, 20, 0.82) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.stTextInput div[data-baseweb="input"]:focus-within,
.stTextArea div[data-baseweb="textarea"]:focus-within,
.stNumberInput div[data-baseweb="input"]:focus-within {
    border-color: rgba(139, 92, 246, 0.62) !important;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.13);
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    color: var(--text) !important;
    background: transparent !important;
    caret-color: #A78BFA;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #55627A !important;
}

div[data-baseweb="select"] > div {
    background: rgba(6, 10, 20, 0.82) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    color: var(--text) !important;
}

div[data-baseweb="select"] svg {
    fill: #8A97AD;
}

div[data-baseweb="popover"] {
    background: #0D1526 !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45) !important;
}

div[data-baseweb="popover"] li {
    color: #D6DFEC !important;
}

div[data-baseweb="popover"] li:hover {
    background: rgba(139, 92, 246, 0.14) !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(6, 10, 20, 0.62) !important;
    border: 1px dashed rgba(139, 92, 246, 0.36) !important;
    border-radius: 18px !important;
}

[data-testid="stFileUploaderDropzone"] button {
    border-radius: 11px !important;
}

[data-baseweb="slider"] [role="slider"] {
    background: linear-gradient(135deg, #A78BFA, #6366F1) !important;
    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.14) !important;
}

[data-baseweb="checkbox"] [data-testid="stCheckbox"] span,
[data-baseweb="checkbox"] div[role="checkbox"] {
    border-radius: 6px !important;
}

/* ------------------------------------------------------------- radio pills */
[data-testid="stRadio"] [role="radiogroup"] {
    flex-wrap: wrap;
    gap: 0.5rem;
}

[data-testid="stRadio"] [role="radiogroup"] > label {
    background: rgba(13, 20, 36, 0.72);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.44rem 0.78rem;
    transition: background 0.16s ease, border-color 0.16s ease;
}

[data-testid="stRadio"] [role="radiogroup"] > label:hover {
    border-color: rgba(139, 92, 246, 0.38);
}

[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(120deg, rgba(139, 92, 246, 0.26), rgba(99, 102, 241, 0.12));
    border-color: rgba(139, 92, 246, 0.5);
    box-shadow: 0 6px 18px rgba(76, 29, 149, 0.16);
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {
    background: transparent;
    border-color: transparent;
    border-radius: 13px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, rgba(139, 92, 246, 0.24), rgba(99, 102, 241, 0.09));
    border-color: rgba(139, 92, 246, 0.36);
}

/* ----------------------------------------------------------------- buttons */
.stButton > button,
.stDownloadButton > button {
    min-height: 2.65rem;
    border-radius: 13px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.82), rgba(15, 23, 42, 0.88));
    color: #E8EDF7;
    font-weight: 700;
    font-size: 0.83rem;
    letter-spacing: 0.01em;
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: rgba(139, 92, 246, 0.55);
    color: #FFFFFF;
    transform: translateY(-1px);
    box-shadow: 0 10px 26px rgba(0, 0, 0, 0.28);
}

.stButton > button:focus:not(:active),
.stDownloadButton > button:focus:not(:active) {
    border-color: rgba(139, 92, 246, 0.65);
    color: #FFFFFF;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(120deg, #7C3AED 0%, #8B5CF6 34%, #6366F1 70%, #22D3EE 135%);
    border: none;
    color: #FFFFFF;
    box-shadow: 0 12px 30px rgba(99, 102, 241, 0.36);
}

.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
    box-shadow: 0 14px 36px rgba(99, 102, 241, 0.50);
}

/* ----------------------------------------------------------------- metrics */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(18, 26, 45, 0.92), rgba(10, 15, 28, 0.92));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.85rem 1rem;
    min-height: 102px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
}

[data-testid="stMetricLabel"] p {
    font-size: 0.64rem !important;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    font-weight: 800 !important;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
}

[data-testid="stMetricDelta"] {
    color: var(--green) !important;
}

/* --------------------------------------------------------------- progress */
.stProgress > div > div {
    background: rgba(148, 163, 184, 0.12);
    border-radius: 999px;
}

.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #8B5CF6, #6366F1 55%, #22D3EE);
    border-radius: 999px;
    box-shadow: 0 0 14px rgba(99, 102, 241, 0.55);
}

.stProgress p {
    color: #94A3B8;
    font-size: 0.74rem;
}

/* --------------------------------------------------------------- expanders */
[data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 16px;
    background: rgba(10, 15, 28, 0.62);
    overflow: hidden;
}

[data-testid="stExpander"] summary {
    font-weight: 700;
    color: #C7D2E5;
}

[data-testid="stExpander"] summary:hover {
    color: #FFFFFF;
}

[data-testid="stExpander"] p,
[data-testid="stExpander"] li {
    color: #B8C4D6;
}

/* ------------------------------------------------------------------ alerts */
[data-testid="stAlert"] {
    border-radius: 16px;
    border: 1px solid var(--line);
    background: rgba(15, 23, 42, 0.78);
}

[data-testid="stAlert"] p {
    color: #D6DFEC;
}

/* ---------------------------------------------------------------- dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 18px;
    overflow: hidden;
}

/* ------------------------------------------------------------------- rings */
.ring-wrap {
    position: relative;
    display: grid;
    place-items: center;
    margin: 0.15rem auto;
}

.ring-wrap svg {
    transform: rotate(-90deg);
}

.ring-center {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.ring-value {
    font-size: 1.45rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.03em;
    line-height: 1;
}

.ring-caption {
    font-size: 0.58rem;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #7C8AA3;
    font-weight: 800;
    margin-top: 0.28rem;
}

/* --------------------------------------------------------------- assistant */
.assistant-head {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.85rem;
}

.orb {
    position: relative;
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    border-radius: 15px;
    background: conic-gradient(from 210deg, #8B5CF6, #6366F1, #22D3EE, #8B5CF6);
    display: grid;
    place-items: center;
    box-shadow: 0 0 28px rgba(139, 92, 246, 0.45);
    animation: pulse 4.5s ease-in-out infinite;
}

.orb::after {
    content: '';
    position: absolute;
    inset: 3px;
    border-radius: 12px;
    background: #0B1120;
}

.orb span {
    position: relative;
    z-index: 1;
    color: #FFFFFF;
    font-size: 1.02rem;
}

.assistant-title {
    font-size: 0.96rem;
    font-weight: 800;
    color: #F1F5F9;
    letter-spacing: -0.01em;
}

.assistant-sub {
    font-size: 0.68rem;
    color: #7C8AA3;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 700;
    margin-top: 0.12rem;
}

.bubble {
    background: linear-gradient(160deg, rgba(139, 92, 246, 0.16), rgba(99, 102, 241, 0.06));
    border: 1px solid rgba(139, 92, 246, 0.22);
    border-radius: 16px 16px 16px 5px;
    padding: 0.8rem 0.9rem;
    color: #DCE5F3;
    font-size: 0.82rem;
    line-height: 1.65;
    margin: 0.55rem 0 0.85rem;
}

.bubble.user {
    background: rgba(148, 163, 184, 0.08);
    border-color: var(--line);
    border-radius: 16px 16px 5px 16px;
    color: #B8C4D6;
}

.bubble strong {
    color: #FFFFFF;
}

.assistant-note {
    color: #6F7D94;
    font-size: 0.68rem;
    line-height: 1.5;
    margin-top: 0.5rem;
}

/* ---------------------------------------------------------------- snapshots */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.22rem 0.55rem;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: 1px solid transparent;
}

.badge-violet { color: #C4B5FD; background: rgba(139, 92, 246, 0.13); border-color: rgba(139, 92, 246, 0.26); }
.badge-green { color: #6EE7B7; background: rgba(52, 211, 153, 0.12); border-color: rgba(52, 211, 153, 0.24); }
.badge-amber { color: #FCD34D; background: rgba(251, 191, 36, 0.12); border-color: rgba(251, 191, 36, 0.24); }
.badge-red { color: #FDA4AF; background: rgba(251, 113, 133, 0.12); border-color: rgba(251, 113, 133, 0.24); }
.badge-slate { color: #A9B5C8; background: rgba(148, 163, 184, 0.10); border-color: rgba(148, 163, 184, 0.18); }

/* -------------------------------------------------------------- flashcards */
.flashcard-shell {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.70), rgba(34, 211, 238, 0.28) 46%, rgba(99, 102, 241, 0.55));
    padding: 1px;
    border-radius: 25px;
    box-shadow: 0 28px 70px rgba(0, 0, 0, 0.42);
    margin: 0.35rem 0 1rem;
}

.flashcard {
    min-height: 288px;
    border-radius: 24px;
    padding: 1.55rem 1.6rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background:
        radial-gradient(900px 260px at 18% 0%, rgba(139, 92, 246, 0.16), transparent 62%),
        linear-gradient(160deg, #0D1526, #080D18 78%);
}

.fc-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.fc-concept {
    color: #A78BFA;
    font-size: 0.66rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 800;
}

.fc-pills {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    flex-wrap: wrap;
}

.fc-kicker {
    color: #6F7D94;
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 800;
    margin-top: 1.15rem;
}

.fc-front {
    font-size: 1.5rem;
    line-height: 1.35;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.025em;
    margin: 0.45rem 0 0.3rem;
}

.fc-answer {
    border-top: 1px solid rgba(148, 163, 184, 0.14);
    padding-top: 1.05rem;
    margin-top: 1.05rem;
}

.fc-answer p {
    color: #CBD5E1;
    font-size: 0.97rem;
    line-height: 1.7;
    margin: 0.2rem 0;
    white-space: pre-line;
    overflow-wrap: anywhere;
}

.fc-explanation {
    color: #8A97AD !important;
    font-size: 0.8rem !important;
    margin-top: 0.55rem !important;
}

.fc-source {
    margin-top: 0.8rem;
    padding: 0.65rem 0.8rem;
    border-left: 2px solid #8B5CF6;
    background: rgba(139, 92, 246, 0.07);
    border-radius: 0 10px 10px 0;
    color: #94A3B8;
    font-size: 0.74rem;
    line-height: 1.55;
    white-space: pre-line;
    overflow-wrap: anywhere;
}

.fc-source-label {
    color: #7C8AA3;
    font-size: 0.58rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 800;
    margin-bottom: 0.18rem;
}

/* ------------------------------------------------------------------- quiz */
.quiz-question {
    font-size: 1.16rem;
    line-height: 1.55;
    font-weight: 700;
    color: #F1F5F9;
    letter-spacing: -0.01em;
    margin: 0.2rem 0 1.1rem;
}

.quiz-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.6rem;
}

/* ---------------------------------------------------------------- results */
.result-hero {
    display: flex;
    align-items: center;
    gap: 1.4rem;
    flex-wrap: wrap;
    padding: 0.35rem 0 0.6rem;
}

.result-copy {
    flex: 1 1 240px;
}

.result-band {
    font-size: 1.45rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #F8FAFC;
    margin: 0.2rem 0 0.25rem;
}

.result-note {
    color: #8A97AD;
    font-size: 0.82rem;
    line-height: 1.6;
}

.review-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.55rem 0.75rem;
    border-radius: 11px;
    border: 1px solid var(--line);
    background: rgba(9, 14, 26, 0.6);
    color: #B8C4D6;
    font-size: 0.82rem;
    margin: 0.35rem 0;
}

.review-option.correct {
    border-color: rgba(52, 211, 153, 0.35);
    background: rgba(52, 211, 153, 0.08);
    color: #A7F3D0;
}

.review-option.wrong {
    border-color: rgba(251, 113, 133, 0.32);
    background: rgba(251, 113, 133, 0.07);
    color: #FECDD3;
}

.review-tag {
    font-size: 0.58rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7C8AA3;
}

/* ----------------------------------------------------------- empty states */
.empty-state {
    padding: 1.7rem 1.4rem;
    text-align: center;
    border: 1px dashed rgba(139, 92, 246, 0.30);
    border-radius: 20px;
    background: radial-gradient(400px 160px at 50% 0%, rgba(139, 92, 246, 0.08), transparent 70%);
}

.empty-icon {
    font-size: 1.5rem;
    color: #A78BFA;
    margin-bottom: 0.4rem;
}

.empty-title {
    font-size: 0.95rem;
    font-weight: 800;
    color: #F1F5F9;
    margin-bottom: 0.25rem;
}

.empty-text {
    font-size: 0.78rem;
    line-height: 1.55;
    color: #8A97AD;
    max-width: 420px;
    margin: 0 auto;
}

/* ------------------------------------------------------------------ extras */
.soft-divider {
    border: none;
    height: 1px;
    margin: 1.15rem 0 1.2rem;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.28), transparent);
}

.input-note {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    margin-top: 0.55rem;
    padding: 0.38rem 0.7rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: rgba(9, 14, 26, 0.64);
    color: #93A1B7;
    font-size: 0.72rem;
    font-weight: 600;
}

.pulse-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem 1rem;
    justify-content: center;
    margin: 0.75rem 0 0.35rem;
    color: #8A97AD;
    font-size: 0.72rem;
}

.pulse-row strong {
    color: #E8EDF7;
    font-weight: 800;
}

.pulse-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    margin-right: 0.25rem;
    vertical-align: middle;
}

.pulse-dot.green { background: var(--green); box-shadow: 0 0 8px rgba(52, 211, 153, 0.6); }
.pulse-dot.amber { background: var(--amber); box-shadow: 0 0 8px rgba(251, 191, 36, 0.55); }
.pulse-dot.slate { background: #64748B; }
.pulse-dot.violet { background: var(--violet); box-shadow: 0 0 8px rgba(139, 92, 246, 0.6); }

/* --------------------------------------------------------------- animation */
@keyframes rise {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 24px rgba(139, 92, 246, 0.38); }
    50% { box-shadow: 0 0 36px rgba(34, 211, 238, 0.45); }
}

@media (max-width: 900px) {
    .snapshot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
    .snapshot-grid { grid-template-columns: 1fr; }
    .block-container { padding-top: 1.4rem; }
    .fc-front { font-size: 1.25rem; }
}
"""
