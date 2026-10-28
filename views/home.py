"""Landing dashboard: pick the material, generate a study set and get coached."""

import streamlit as st

from ai.llm_client import LLMError
from core import config
from core.pipeline import GenerationError, build_study_set
from core.text_extraction import ExtractionError, extract_text_from_file
from core.validators import validate_upload
from ui import theme
from ui.state import State

SAMPLE_FILES = {
    'Cell biology (10 sentences)': 'biology.txt',
    'American Revolution (1 paragraph)': 'history.txt',
}


def _read_sample(name: str) -> str:
    path = config.SAMPLES_DIR / name
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='replace')


def _status_value(card) -> str:
    status = getattr(card, 'status', 'unmarked')
    return getattr(status, 'value', status) or 'unmarked'


def _deck_counts(study_set):
    counts = {'known': 0, 'practice': 0, 'unmarked': 0, 'total': len(study_set.flashcards)}
    session = State.get_flashcard_session()
    if session is not None and len(session.original) == len(study_set.flashcards):
        counts.update(session.get_counts())
        return counts
    for card in study_set.flashcards:
        status = _status_value(card)
        if status in counts:
            counts[status] += 1
        else:
            counts['unmarked'] += 1
    return counts


def _latest_result(study_set):
    for attempt in reversed(study_set.attempts):
        if attempt.result is not None:
            return attempt.result
    return None


def _score_text(latest):
    if latest is None or latest.percent is None:
        return '—'
    return f'{latest.percent:.0f}%'


def _set_difficulty(study_set):
    settings = getattr(study_set, 'settings', None)
    if settings is None:
        return 'Mixed'
    return str(settings.difficulty).title()


def _mastery(study_set):
    if study_set is None or not study_set.flashcards:
        return None
    counts = _deck_counts(study_set)
    return round((counts['known'] / counts['total']) * 100, 1)


def _hero(study_set):
    st.markdown('<div class="eyebrow">AI Learning Workspace</div>', unsafe_allow_html=True)
    st.title('Flashcard & Quiz Generator')
    st.markdown(
        '<p class="hero-sub">Turn raw notes into a polished study set, rehearse with '
        'adaptive flashcards and prove what you know in a scored quiz.</p>',
        unsafe_allow_html=True,
    )
    engine = config.get_active_engine()
    engine_label = 'Offline rule-based engine' if engine.get('offline') else f"{engine.get('model')} engine"
    chips = [
        engine_label,
        'Grounded generation',
        f'{len(study_set.flashcards)} cards' if study_set else 'Ready when you are',
    ]
    chips_html = ''.join(f'<span class="chip">{theme.esc(chip)}</span>' for chip in chips)
    st.markdown(f'<div class="chip-row">{chips_html}</div>', unsafe_allow_html=True)


def _snapshot(study_set):
    if study_set is None:
        theme.stat_snapshot(
            [
                ('Flashcards', '0', 'Build a deck to start'),
                ('Quiz bank', '0', 'Questions appear here'),
                ('Deck mastery', '—', 'Mark cards as known'),
                ('Last score', '—', 'No attempts yet'),
            ]
        )
        return

    counts = _deck_counts(study_set)
    mastery = _mastery(study_set)
    latest = _latest_result(study_set)
    theme.stat_snapshot(
        [
            ('Flashcards', len(study_set.flashcards), f"{counts['known']} marked as known"),
            ('Quiz bank', len(study_set.mcqs), f'{_set_difficulty(study_set)} difficulty'),
            ('Deck mastery', '—' if mastery is None else f'{mastery:.0f}%', f"{counts['practice']} need practice"),
            ('Last score', _score_text(latest), latest.band if latest else 'No attempts yet'),
        ]
    )


def _assistant_greeting(study_set):
    if study_set is None:
        return (
            'Welcome. Add at least 300 characters of notes and I will help you turn them '
            'into a focused deck. You can also upload a PDF, DOCX or start from a sample.'
        )
    counts = _deck_counts(study_set)
    latest = _latest_result(study_set)
    if latest is not None:
        return (
            f'Your latest quiz landed at <strong>{_score_text(latest)}</strong> '
            f'({theme.esc(latest.band)}). I would review the missed questions, then '
            f'revisit the <strong>{counts["practice"]}</strong> cards marked for practice '
            'before your next attempt.'
        )
    return (
        f'<strong>{theme.esc(study_set.topic)}</strong> is loaded with '
        f'{len(study_set.flashcards)} cards and {len(study_set.mcqs)} questions. '
        'Mark a few cards as known so I can track your mastery, or jump straight into a quiz.'
    )


def _coach_reply(prompt, study_set):
    text = (prompt or '').strip().lower()
    if study_set is None:
        return (
            'I need some material first. Paste your notes on the left, then generate a '
            'study set and I can build a revision plan around it.'
        )

    counts = _deck_counts(study_set)
    latest = _latest_result(study_set)
    mastery = _mastery(study_set) or 0

    if any(word in text for word in ('quiz', 'test', 'exam')):
        if latest is not None:
            return (
                f'Your last score was <strong>{_score_text(latest)}</strong> '
                f'({theme.esc(latest.band)}). Take another quiz with '
                f'{min(10, len(study_set.mcqs))} questions and keep the difficulty on '
                f'{theme.esc(_set_difficulty(study_set))}. '
                'Review every missed question before retrying.'
            )
        return (
            f'You have <strong>{len(study_set.mcqs)} questions</strong> ready. Start with '
            f'{min(10, len(study_set.mcqs))} in practice mode so you get instant feedback, '
            'then switch to exam mode once you are above 75%.'
        )

    if any(word in text for word in ('card', 'flash', 'memor', 'deck')):
        return (
            f'You know <strong>{counts["known"]} of {counts["total"]}</strong> cards '
            f'({mastery:.0f}% mastery). Focus on the {counts["practice"]} cards marked '
            'for practice, and mark a card as known only when you can explain it without '
            'flipping.'
        )

    if any(word in text for word in ('weak', 'revise', 'plan', 'study', 'focus')):
        practice = [card for card in study_set.flashcards if _status_value(card) == 'practice']
        focus = ', '.join(theme.esc(card.concept) for card in practice[:3])
        if practice:
            return (
                f'Priority concepts: <strong>{focus}</strong>. Review those cards first, '
                'then answer the matching questions in practice mode. A 20 minute session '
                'covering 5 cards and 5 questions is a good target.'
            )
        return (
            'Nothing is flagged for practice yet. Flip through the deck, mark two or three '
            'cards as <strong>Needs practice</strong>, then run a short quiz to surface gaps.'
        )

    if any(word in text for word in ('concept', 'summary', 'list')):
        if study_set.key_concepts:
            terms = ', '.join(theme.esc(item.term) for item in study_set.key_concepts[:6])
            return f'The core concepts in this set are <strong>{terms}</strong>. Ask me about any of them.'
        return 'This set does not have extracted key concepts, but every card carries a source quote you can review.'

    return (
        f'Here is your current pulse: <strong>{mastery:.0f}% mastery</strong>, '
        f'{counts["unmarked"]} cards unmarked and {counts["practice"]} flagged for practice. '
        'Ask me about a quiz plan, your weak spots, or how to use the deck.'
    )


def _assistant_panel(study_set):
    with st.container(border=True):
        st.markdown(
            """
            <div class="assistant-head">
                <div class="orb"><span>✦</span></div>
                <div>
                    <div class="assistant-title">Study copilot</div>
                    <div class="assistant-sub">Context-aware guidance</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        reply = st.session_state.get('assistant_reply')
        if reply:
            asked = st.session_state.get('assistant_asked', '')
            if asked:
                st.markdown(f'<div class="bubble user">{theme.esc(asked)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bubble">{reply}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="bubble">{_assistant_greeting(study_set)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="assistant-note">Quick actions</div>', unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        with q1:
            if st.button('Review deck', key='assistant_deck', width='stretch'):
                State.set_current_view('Flashcards')
                st.rerun()
        with q2:
            if st.button('Take a quiz', key='assistant_quiz', width='stretch'):
                State.set_current_view('Quiz')
                st.rerun()

        prompt = st.text_input(
            'Ask your study coach',
            key='assistant_prompt',
            placeholder='e.g. Build me a revision plan',
            label_visibility='collapsed',
        )
        if st.button('Get guidance', key='assistant_ask', width='stretch'):
            if prompt.strip():
                st.session_state['assistant_asked'] = prompt.strip()
                st.session_state['assistant_reply'] = _coach_reply(prompt, study_set)
                st.rerun()

        st.markdown(
            '<div class="assistant-note">Guidance is generated locally from your study set.</div>',
            unsafe_allow_html=True,
        )


def _mastery_panel(study_set):
    with st.container(border=True):
        st.markdown('<div class="assistant-note">Deck pulse</div>', unsafe_allow_html=True)
        mastery = _mastery(study_set)
        st.markdown(theme.ring(mastery, 'Mastery', key='home-mastery', size=150), unsafe_allow_html=True)
        if study_set is None:
            st.caption('Generate a study set to unlock progress tracking.')
            return
        counts = _deck_counts(study_set)
        latest = _latest_result(study_set)
        st.markdown(
            f"""
            <div class="pulse-row">
                <div><span class="pulse-dot green"></span>Known <strong>{counts['known']}</strong></div>
                <div><span class="pulse-dot amber"></span>Practice <strong>{counts['practice']}</strong></div>
                <div><span class="pulse-dot slate"></span>Unmarked <strong>{counts['unmarked']}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if latest is not None:
            st.caption(f"Last quiz: {latest.percent:.0f}% · {latest.band}")
        else:
            st.caption('No quiz attempts yet — take one to benchmark yourself.')


def _builder(study_set):
    with st.container(border=True):
        theme.section('01', 'Source material', 'Paste notes, upload a document or load a sample.')
        source = st.radio(
            'Material source',
            ['Paste text', 'Upload a file', 'Use a sample'],
            horizontal=True,
            key='home_source',
            label_visibility='collapsed',
        )

        text = ''
        if source == 'Paste text':
            text = st.text_area(
                'Paste your notes or an article',
                height=250,
                key='home_text',
                placeholder='Paste at least 300 characters of study material…',
            )
        elif source == 'Upload a file':
            uploaded = st.file_uploader(
                'TXT, PDF or DOCX (max 5 MB)',
                type=['txt', 'pdf', 'docx'],
                key='home_upload',
            )
            if uploaded is not None:
                content = uploaded.getvalue()
                ok, reason = validate_upload(uploaded.name, content, config.MAX_UPLOAD_BYTES)
                if not ok:
                    st.error(reason)
                else:
                    try:
                        text = extract_text_from_file(uploaded.name, content)
                        st.caption(f'Extracted {len(text):,} characters from {uploaded.name}.')
                    except ExtractionError as exc:
                        st.error(f'Could not read the file: {exc}')
        else:
            sample_label = st.selectbox('Sample', list(SAMPLE_FILES.keys()), key='home_sample')
            text = _read_sample(SAMPLE_FILES[sample_label])
            st.caption(f'{len(text):,} characters loaded from the sample file.')

        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)
        theme.section('02', 'Study set details', 'Name the set and tune how much practice it contains.')
        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input('Topic *', key='home_topic', placeholder='e.g. Cell biology')
            subject = st.text_input('Subject (optional)', key='home_subject', placeholder='e.g. Biology')
        with col2:
            difficulty = st.selectbox('Difficulty', ['Easy', 'Medium', 'Hard'], key='home_difficulty')
            n_cards = st.slider(
                'Flashcards', config.MIN_CARDS, config.MAX_CARDS, config.DEFAULT_CARDS, key='home_n_cards'
            )
            n_mcqs = st.slider(
                'Quiz questions', config.MIN_MCQ, config.MAX_MCQ, config.DEFAULT_MCQ, key='home_n_mcqs'
            )

        char_count = len(text.strip())
        if char_count:
            if char_count < config.MIN_TEXT_CHARS:
                st.warning(f'Only {char_count:,} characters - at least {config.MIN_TEXT_CHARS:,} are needed.')
            elif char_count > config.WARN_TEXT_CHARS:
                st.warning(f'{char_count:,} characters is a lot; generation may take a while.')
            else:
                st.markdown(
                    f'<div class="input-note"><span class="pulse-dot green"></span>'
                    f'{char_count:,} characters of material ready</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="input-note"><span class="pulse-dot slate"></span>'
                'Add material to unlock generation</div>',
                unsafe_allow_html=True,
            )

        generate = st.button('Generate study set', type='primary', width='stretch')

    if not generate:
        return

    if not text.strip():
        st.error('Add some material first.')
        return

    progress_bar = st.progress(0.0, text='Preparing…')
    status = st.empty()

    def on_progress(fraction, message):
        progress_bar.progress(min(max(fraction, 0.0), 1.0), text=message)
        status.caption(message)

    try:
        study_set, warnings = build_study_set(
            topic=topic.strip() or 'Untitled topic',
            subject=subject.strip(),
            raw_text=text,
            n_cards=n_cards,
            n_mcqs=n_mcqs,
            difficulty=difficulty,
            progress=on_progress,
        )
    except GenerationError as exc:
        progress_bar.empty()
        status.empty()
        st.error(str(exc))
        return
    except LLMError as exc:
        progress_bar.empty()
        status.empty()
        st.error(f'The language model could not be used: {exc}')
        return
    except Exception as exc:  # pragma: no cover - defensive
        progress_bar.empty()
        status.empty()
        st.error(f'Unexpected error: {exc}')
        return

    progress_bar.empty()
    status.empty()
    State.set_study_set(study_set)
    State.set_warnings(warnings)
    State.set_current_view('Flashcards')
    st.success(
        f'Created {len(study_set.flashcards)} flashcards and {len(study_set.mcqs)} quiz questions.'
    )
    st.rerun()


def render():
    study_set = State.get_study_set()

    current_id = study_set.id if study_set is not None else None
    if st.session_state.get('assistant_for') != current_id:
        st.session_state['assistant_for'] = current_id
        st.session_state.pop('assistant_reply', None)
        st.session_state.pop('assistant_asked', None)
        st.session_state.pop('assistant_prompt', None)

    _hero(study_set)
    _snapshot(study_set)

    left, right = st.columns([1.72, 1], gap='large')
    with left:
        _builder(study_set)
    with right:
        _assistant_panel(study_set)
        _mastery_panel(study_set)
