"""Flashcard study mode: flip, navigate and mark cards."""

import streamlit as st

from core import storage
from core.flashcard_session import FlashcardSession
from core.text_utils import to_plain_text
from ui import theme
from ui.state import State

STATUS_LABELS = {
    'known': 'Known',
    'practice': 'Needs practice',
    'unmarked': 'Unmarked',
}

STATUS_TONES = {
    'known': 'green',
    'practice': 'amber',
    'unmarked': 'slate',
}

DIFFICULTY_TONES = {
    'easy': 'green',
    'medium': 'violet',
    'hard': 'red',
}


def _ensure_session(study_set):
    session = State.get_flashcard_session()
    if session is None or len(session.original) != len(study_set.flashcards):
        session = FlashcardSession(study_set.flashcards)
        State.set_flashcard_session(session)
    return session


def _status_label(status):
    return STATUS_LABELS.get(status, 'Unmarked')


def _card_html(card, session, current_status):
    status_tone = STATUS_TONES.get(current_status, 'slate')
    difficulty = getattr(card.difficulty, 'value', card.difficulty)
    difficulty_tone = DIFFICULTY_TONES.get(str(difficulty).lower(), 'slate')

    front = to_plain_text(card.front, max_length=300, single_line=True)
    back = to_plain_text(card.back, max_length=600)
    concept = to_plain_text(card.concept, max_length=60, single_line=True)
    explanation_text = to_plain_text(card.explanation, max_length=600)
    source_quote = to_plain_text(card.source_quote, max_length=300)

    if session.flipped:
        explanation = (
            f'<p class="fc-explanation">{theme.esc(explanation_text)}</p>'
            if explanation_text
            else ''
        )
        source = (
            f'<div class="fc-source">'
            f'<div class="fc-source-label">Source quote</div>'
            f'{theme.esc(source_quote)}</div>'
            if source_quote
            else ''
        )
        answer = (
            '<div class="fc-answer">'
            '<div class="fc-kicker">Answer</div>'
            f'<p>{theme.esc(back)}</p>'
            f'{explanation}'
            f'{source}'
            '</div>'
        )
        kicker = 'Recall check'
    else:
        answer = ''
        kicker = 'Prompt'

    return (
        '<div class="flashcard-shell">'
        '<div class="flashcard">'
        '<div>'
        '<div class="fc-top">'
        f'<span class="fc-concept">{theme.esc(concept)}</span>'
        '<span class="fc-pills">'
        f'{theme.badge(str(difficulty).title(), difficulty_tone)}'
        f'{theme.badge(STATUS_LABELS.get(current_status, "Unmarked"), status_tone)}'
        '</span>'
        '</div>'
        f'<div class="fc-kicker">{kicker}</div>'
        f'<div class="fc-front">{theme.esc(front)}</div>'
        '</div>'
        f'{answer}'
        '</div>'
        '</div>'
    )


def render():
    study_set = State.get_study_set()
    if study_set is None:
        theme.page_header(
            'Flashcard Studio',
            'Flashcards',
            'Generate a study set to start rehearsing your deck.',
        )
        theme.empty_state('▤', 'No deck loaded', 'Create a study set from Home, then return here to study.')
        return

    session = _ensure_session(study_set)
    cards = study_set.flashcards
    if not cards:
        st.warning('This study set has no flashcards.')
        return

    counts = session.get_counts()
    mastery = (counts['known'] / counts['total'] * 100) if counts['total'] else 0

    theme.page_header(
        'Flashcard Studio',
        'Build recall, one card at a time',
        'Flip each card, check the source quote, then mark it known or send it to practice.',
        chips=[
            f"{counts['known']} known",
            f"{counts['practice']} for practice",
            f"{counts['unmarked']} unmarked",
        ],
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total', counts['total'])
    col2.metric('Known', counts['known'])
    col3.metric('Needs practice', counts['practice'])
    col4.metric('Unmarked', counts['unmarked'])

    st.markdown('<div style="height:0.65rem"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.7, 1], gap='large')

    with left:
        card = session.current_card()
        if card is None:
            st.success('End of the deck.')
        else:
            with st.container(border=True):
                card_id = getattr(card, 'id', None)
                current_status = session.statuses.get(card_id, 'unmarked')
                st.progress(
                    min(1.0, (session.current_index + 1) / max(len(session.order), 1)),
                    text=f'Card {session.current_index + 1} of {len(session.order)}',
                )
                st.markdown(
                    _card_html(card, session, current_status),
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button('◀ Previous', width='stretch', disabled=session.current_index == 0):
                        session.prev_card()
                        st.rerun()
                with c2:
                    if st.button(
                        'Show answer' if not session.flipped else 'Hide answer', width='stretch'
                    ):
                        session.flip()
                        st.rerun()
                with c3:
                    if st.button(
                        'Next ▶', width='stretch', disabled=session.current_index >= len(session.order) - 1
                    ):
                        session.next_card()
                        st.rerun()

                st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                if m1.button('I know this', width='stretch', key=f'mark_known_{card_id}'):
                    session.mark_status(card_id, 'known')
                    card.status = 'known'
                    st.rerun()
                if m2.button('Needs practice', width='stretch', key=f'mark_practice_{card_id}'):
                    session.mark_status(card_id, 'practice')
                    card.status = 'practice'
                    st.rerun()
                if m3.button('Reset', width='stretch', key=f'mark_unmarked_{card_id}'):
                    session.mark_status(card_id, 'unmarked')
                    card.status = 'unmarked'
                    st.rerun()
                st.caption(f'Status: {_status_label(current_status)}')

    with right:
        with st.container(border=True):
            st.markdown('<div class="assistant-note">Card mastery</div>', unsafe_allow_html=True)
            st.markdown(
                theme.ring(mastery, 'Known', key='deck-mastery', size=144),
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="pulse-row">
                    <div><span class="pulse-dot green"></span>Known <strong>{counts['known']}</strong></div>
                    <div><span class="pulse-dot amber"></span>Practice <strong>{counts['practice']}</strong></div>
                    <div><span class="pulse-dot slate"></span>To review <strong>{counts['unmarked']}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption('A card counts as known only when you can explain it before flipping.')

        with st.expander('Deck tools', expanded=False):
            t1, t2 = st.columns(2)
            if t1.button('Shuffle', width='stretch'):
                session.shuffle()
                st.rerun()
            if t2.button('Reset order', width='stretch'):
                session.reset_order()
                st.rerun()
            if st.button('Save to library', width='stretch'):
                path = storage.save_study_set(study_set)
                st.success(f'Saved to `{path.name}`.')

        with st.expander('Key concepts', expanded=False):
            if study_set.key_concepts:
                for concept in study_set.key_concepts:
                    term = to_plain_text(concept.term, single_line=True)
                    definition = to_plain_text(concept.definition, single_line=True)
                    st.markdown(f'- **{theme.esc(term)}** — {theme.esc(definition)}')
            else:
                st.caption('No key concepts were extracted.')

        with st.expander(f'All {len(cards)} cards', expanded=False):
            for index, item in enumerate(cards, start=1):
                difficulty = getattr(item.difficulty, 'value', item.difficulty)
                front = to_plain_text(item.front, single_line=True)
                back = to_plain_text(item.back, single_line=True)
                st.markdown(f'**{index}. {theme.esc(front)}**')
                st.markdown(f'- {theme.esc(back)}')
                st.caption(
                    f'{_status_label(getattr(item, "status", "unmarked"))} · '
                    f'{str(difficulty).title()}'
                )
