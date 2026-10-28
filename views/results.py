"""Quiz results: score breakdown and per-question review."""

import streamlit as st

from core import storage
from core.text_utils import to_plain_text
from ui import theme
from ui.state import State


def _topic_performance(attempt, study_set):
    by_id = {mcq.id: mcq for mcq in study_set.mcqs}
    answers = attempt.get('answers', {})
    buckets = {}
    for question in attempt.get('questions', []):
        source = by_id.get(question['mcq_id'])
        topic = to_plain_text(source.concept, max_length=60, single_line=True) if source else 'General'
        topic = topic or 'General'
        total, correct = buckets.get(topic, (0, 0))
        buckets[topic] = (
            total + 1,
            correct + (1 if answers.get(question['mcq_id']) == question['correct_index'] else 0),
        )
    return sorted(
        ((topic, total, correct) for topic, (total, correct) in buckets.items()),
        key=lambda row: (row[2] / row[1] if row[1] else 0, row[0].casefold()),
    )


def _review(attempt, study_set):
    questions = attempt.get('questions', [])
    answers = attempt.get('answers', {})
    by_id = {mcq.id: mcq for mcq in study_set.mcqs}

    for index, question in enumerate(questions, start=1):
        mcq_id = question['mcq_id']
        source = by_id.get(mcq_id)
        options = [
            to_plain_text(option, single_line=True) for option in question['displayed_options']
        ]
        chosen = answers.get(mcq_id)
        correct_index = question['correct_index']
        correct_text = options[correct_index] if 0 <= correct_index < len(options) else ''
        question_text = (
            to_plain_text(source.question, max_length=400, single_line=True) if source else 'Question'
        )
        explanation = to_plain_text(source.explanation, max_length=600) if source else ''

        with st.expander(f'Question {index}', expanded=False):
            st.markdown(
                f'<div class="quiz-question">{theme.esc(question_text)}</div>',
                unsafe_allow_html=True,
            )

            rows = []
            for option_index, option in enumerate(options):
                classes = ['review-option']
                tag = ''
                if option_index == correct_index:
                    classes.append('correct')
                    tag = 'Correct answer'
                if chosen is not None and option_index == chosen and option_index != correct_index:
                    classes.append('wrong')
                    tag = 'Your answer'
                elif chosen is not None and option_index == chosen:
                    tag = 'Your answer'
                tag_html = f'<span class="review-tag">{tag}</span>' if tag else ''
                rows.append(
                    f'<div class="{" ".join(classes)}"><span>{theme.esc(option)}</span>{tag_html}</div>'
                )
            st.markdown(''.join(rows), unsafe_allow_html=True)

            if chosen is None:
                st.warning('Not answered.')
            elif chosen == correct_index:
                st.success('Correct.')
            else:
                st.error(f'Your answer: **{options[chosen] if chosen < len(options) else "Unknown"}**')
                st.info(f'Correct answer: **{correct_text}**')

            if explanation:
                st.caption(explanation)
            if source is not None:
                with st.popover('Source quote'):
                    st.text(to_plain_text(source.source_quote, max_length=300))


def render():
    study_set = State.get_study_set()
    payload = State.get_result()

    if study_set is None:
        theme.page_header('Results', 'Quiz results', 'Generate a study set to see results.')
        theme.empty_state('◉', 'No results yet', 'Create a study set, take a quiz and your score will appear here.')
        return
    if payload is None:
        theme.page_header('Results', 'Quiz results', 'Your score, breakdown and question review appear here.')
        theme.empty_state('◉', 'No quiz submitted', 'Head to the Quiz tab and complete an attempt to see your score.')
        return

    result = payload['result']
    attempt = payload['attempt']
    percent = result['percent']

    st.markdown('<div class="eyebrow">Performance Review</div>', unsafe_allow_html=True)
    st.title('Quiz results')
    st.markdown(
        '<p class="hero-sub">A complete breakdown of this attempt, with the reasoning behind every answer.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2.1], gap='large')
    with left:
        with st.container(border=True):
            st.markdown(
                theme.ring(percent, 'Score', key='result-score', size=176, stroke=13),
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="text-align:center;margin-top:0.4rem;">'
                f'{theme.badge(result.get("band") or "No score", "green" if (percent or 0) >= 75 else "amber")}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{result['correct']} of {result['total']} questions correct")
    with right:
        with st.container(border=True):
            band = result.get('band') or 'Attempt complete'
            if percent is None:
                note = 'This attempt had no questions.'
            elif percent >= 75:
                note = 'Strong recall. Keep the momentum with a harder quiz or a quick deck review.'
            elif percent >= 50:
                note = 'Solid base. Revisit the missed questions and the cards marked for practice.'
            else:
                note = 'Focus on the source quotes for missed questions, then retake a shorter quiz.'
            st.markdown(
                f"""
                <div class="result-hero">
                    <div class="result-copy">
                        <div class="eyebrow" style="margin-bottom:0.2rem;">Overall band</div>
                        <div class="result-band">{theme.esc(band)}</div>
                        <div class="result-note">{theme.esc(note)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Score', f"{percent}%" if percent is not None else '-')
            c2.metric('Correct', result['correct'])
            c3.metric('Incorrect', result['incorrect'])
            c4.metric('Unanswered', result['unanswered'])

    st.markdown('<div style="height:0.65rem"></div>', unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    if b1.button('Try another quiz', width='stretch'):
        State.set_current_view('Quiz')
        st.rerun()
    if b2.button('Study flashcards', width='stretch'):
        State.set_current_view('Flashcards')
        st.rerun()
    if b3.button('Save to library', width='stretch'):
        path = storage.save_study_set(study_set)
        st.success(f'Saved to `{path.name}`.')

    breakdown = _topic_performance(attempt, study_set)
    if breakdown:
        theme.section('01', 'Topic performance', 'Spot the concepts that need another pass.')
        for topic, total, correct in breakdown:
            accuracy = int(round(correct / total * 100)) if total else 0
            label, bar = st.columns([1, 2.4])
            with label:
                st.markdown(f'**{theme.esc(topic)}**')
                st.caption(f'{correct} of {total} correct')
            with bar:
                st.progress(accuracy / 100, text=f'{accuracy}% accuracy')

    theme.section('02', 'Question review', 'Every answer is checked against the source material.')
    _review(attempt, study_set)

    if study_set.attempts:
        theme.section('03', 'Attempt history', 'Compare how this session is progressing.')
        for previous in reversed(study_set.attempts):
            previous_result = previous.result
            if previous_result is None:
                continue
            st.markdown(
                f"- **{previous_result.percent}%** · {previous_result.band} · "
                f"{previous_result.correct}/{previous_result.total} correct · {previous.submitted_at}"
            )
