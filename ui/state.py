"""Helpers for reading and writing the Streamlit session state."""

from typing import Any, Dict, List, Optional

import streamlit as st


VIEWS = ['Home', 'Flashcards', 'Quiz', 'Results', 'Library']
NAV_WIDGET_KEY = 'nav_choice'


class State:
    """Thin wrapper around ``st.session_state`` with the app's key names."""

    # ------------------------------------------------------------------ views
    @staticmethod
    def get_current_view() -> str:
        return st.session_state.get('view', 'Home')

    @staticmethod
    def set_current_view(view: str):
        """Switch the current page.

        The navigation radio is a Streamlit widget, so its key cannot be
        modified after the widget has been created in the same run. The new
        page is therefore queued and applied at the start of the next run.
        """
        st.session_state['view'] = view
        st.session_state['_last_nav'] = view
        st.session_state['pending_nav'] = view

    @staticmethod
    def apply_pending_navigation():
        """Apply a queued navigation. Must run before the nav widget is drawn."""
        pending = st.session_state.pop('pending_nav', None)
        if pending is not None:
            st.session_state[NAV_WIDGET_KEY] = pending

    @staticmethod
    def sync_navigation() -> str:
        """Read the nav widget and update the current page when it changed."""
        requested = st.session_state.get(NAV_WIDGET_KEY)
        if requested and requested != st.session_state.get('_last_nav'):
            st.session_state['_last_nav'] = requested
            st.session_state['view'] = requested
        return State.get_current_view()

    # ------------------------------------------------------------- study set
    @staticmethod
    def get_study_set() -> Optional[Any]:
        return st.session_state.get('study_set')

    @staticmethod
    def set_study_set(study_set: Any):
        st.session_state['study_set'] = study_set
        st.session_state['flashcard_session'] = None
        st.session_state['current_attempt'] = None
        st.session_state['quiz_answers'] = {}
        st.session_state['quiz_index'] = 0
        st.session_state['last_result'] = None

    @staticmethod
    def clear_study_set():
        for key in (
            'study_set',
            'flashcard_session',
            'current_attempt',
            'quiz_answers',
            'quiz_index',
            'last_result',
            'quiz_deadline',
        ):
            st.session_state.pop(key, None)

    # ------------------------------------------------------- flashcard study
    @staticmethod
    def get_flashcard_session():
        return st.session_state.get('flashcard_session')

    @staticmethod
    def set_flashcard_session(session):
        st.session_state['flashcard_session'] = session

    # ------------------------------------------------------------------ quiz
    @staticmethod
    def get_attempt() -> Optional[Dict[str, Any]]:
        return st.session_state.get('current_attempt')

    @staticmethod
    def set_attempt(attempt: Dict[str, Any]):
        st.session_state['current_attempt'] = attempt
        st.session_state['quiz_answers'] = {q['mcq_id']: None for q in attempt.get('questions', [])}
        st.session_state['quiz_index'] = 0

    @staticmethod
    def get_answers() -> Dict[str, Optional[int]]:
        return st.session_state.get('quiz_answers', {})

    @staticmethod
    def set_answer(mcq_id: str, option_index: Optional[int]):
        answers = State.get_answers()
        answers[mcq_id] = option_index
        st.session_state['quiz_answers'] = answers

    @staticmethod
    def get_quiz_index() -> int:
        return st.session_state.get('quiz_index', 0)

    @staticmethod
    def set_quiz_index(index: int):
        st.session_state['quiz_index'] = index

    # --------------------------------------------------------------- results
    @staticmethod
    def get_result() -> Optional[Dict[str, Any]]:
        return st.session_state.get('last_result')

    @staticmethod
    def set_result(result: Dict[str, Any]):
        st.session_state['last_result'] = result

    # -------------------------------------------------------------- warnings
    @staticmethod
    def get_warnings() -> List[str]:
        return st.session_state.get('warnings', [])

    @staticmethod
    def set_warnings(warnings: List[str]):
        st.session_state['warnings'] = list(warnings or [])

    # ------------------------------------------------------------------ init
    @staticmethod
    def init():
        defaults = {
            'study_set': None,
            'current_attempt': None,
            'flashcard_session': None,
            'quiz_answers': {},
            'quiz_index': 0,
            'last_result': None,
            'warnings': [],
            'view': 'Home',
            '_last_nav': 'Home',
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
