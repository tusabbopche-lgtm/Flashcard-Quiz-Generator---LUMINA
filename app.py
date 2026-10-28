"""Flashcard & Quiz Generator — Streamlit entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st

from core import config
from ui import theme
from ui.state import NAV_WIDGET_KEY, VIEWS, State
from views import flashcards, home, library, quiz, results

st.set_page_config(
    page_title='Lumina · Flashcard & Quiz Generator',
    page_icon='✦',
    layout='wide',
    initial_sidebar_state='expanded',
)

theme.inject()
State.init()
State.apply_pending_navigation()

with st.sidebar:
    theme.brand()

    study_set = State.get_study_set()
    st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)

    st.radio(
        'Navigate',
        VIEWS,
        key=NAV_WIDGET_KEY,
        format_func=theme.nav_label,
        label_visibility='collapsed',
    )

    st.markdown('<div class="side-label">Active study set</div>', unsafe_allow_html=True)
    if study_set is not None:
        sub = f'{study_set.subject}' if study_set.subject else 'Ready to study'
        st.markdown(
            f"""
            <div class="side-card">
                <div class="side-card-label">Now learning</div>
                <div class="side-card-title">{theme.esc(study_set.topic)}</div>
                <div class="side-card-meta">
                    {len(study_set.flashcards)} cards · {len(study_set.mcqs)} questions<br>{theme.esc(sub)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="side-card">
                <div class="side-card-label">No active deck</div>
                <div class="side-card-title">Build your first study set</div>
                <div class="side-card-meta">Paste notes or upload a file from Home.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button('+  New study set', key='sidebar_new_set', width='stretch'):
        State.set_current_view('Home')
        st.rerun()

    engine = config.get_active_engine()
    st.markdown('<div class="side-label">Generation engine</div>', unsafe_allow_html=True)
    if engine.get('offline'):
        st.markdown(
            """
            <div class="engine-card">
                <span class="engine-dot"></span>
                <span>Offline · rule-based</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        label = 'local model' if engine.get('local') else 'hosted model'
        st.markdown(
            f"""
            <div class="engine-card">
                <span class="engine-dot remote"></span>
                <span>{theme.esc(engine.get('provider'))} · {theme.esc(engine.get('model'))}
                <br><span style="color:#6F7D94;">{theme.esc(label)}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="side-footer">Local-first · your material stays yours<br>Lumina v1.0</div>',
        unsafe_allow_html=True,
    )

view = State.sync_navigation()

if view == 'Home':
    home.render()
elif view == 'Flashcards':
    flashcards.render()
elif view == 'Quiz':
    quiz.render()
elif view == 'Results':
    results.render()
elif view == 'Library':
    library.render()
else:
    home.render()

warnings = State.get_warnings()
if warnings:
    for warning in warnings:
        st.warning(warning)
    State.set_warnings([])
