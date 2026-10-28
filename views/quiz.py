"""Quiz setup and question flow."""

import time

import streamlit as st

from core.models import QuizAttempt, QuizAttemptSettings, QuizQuestion, QuizResult
from core.quiz_engine import QuizEngine, filter_mcqs
from core.scoring import compute_score
from core.text_utils import to_plain_text
from ui import theme
from ui.state import State

DIFFICULTY_CHOICES = ['All', 'Easy', 'Medium', 'Hard']


def _key_part(value):
    return ''.join(char if char.isalnum() else '_' for char in str(value)).strip('_').lower()


def _topics(mcqs):
    topics = sorted(
        {
            to_plain_text(mcq.concept, max_length=60, single_line=True)
            for mcq in mcqs
            if to_plain_text(mcq.concept, max_length=60, single_line=True)
        },
        key=str.casefold,
    )
    return ['All topics'] + topics


def _setup(study_set):
    theme.page_header(
        'Quiz Lab',
        'Test what you actually know',
        'Pick the length, difficulty and mode. Answers are scored instantly and every '
        'question is reviewed against its source quote.',
        chips=[f'{len(study_set.mcqs)} questions available', 'Timed or untimed', 'Practice feedback'],
    )

    mcqs = study_set.mcqs
    if not mcqs:
        st.warning('This study set has no quiz questions.')
        return

    theme.stat_snapshot(
        [
            ('Question bank', len(mcqs), 'Ready to draw from'),
            ('Difficulty', study_set.settings.difficulty.title(), 'Set when generated'),
            ('Attempts', len(study_set.attempts), 'Saved in this session'),
            ('Timer', 'Optional', 'Set a limit below'),
        ]
    )

    with st.container(border=True):
        theme.section('01', 'Quiz settings', 'A short focused quiz usually beats a long unfocused one.')

        c1, c2, c3 = st.columns(3)
        with c1:
            topic = st.selectbox('Topic', _topics(mcqs), key='quiz_topic')
        with c2:
            difficulty = st.selectbox('Difficulty', DIFFICULTY_CHOICES, key='quiz_difficulty')
        with c3:
            mode = st.radio('Mode', ['exam', 'practice'], horizontal=True, key='quiz_mode')

        available = filter_mcqs(mcqs, difficulty=difficulty, topic=topic)
        if not available:
            st.warning('No questions match this topic and difficulty. Choose another combination.')
            return

        c4, c5, c6 = st.columns([1.1, 1, 1])
        with c4:
            n_questions = st.slider(
                'Questions',
                1,
                len(available),
                min(10, len(available)),
                key=f"quiz_n_questions_{_key_part(topic)}_{_key_part(difficulty)}",
            )
        with c5:
            shuffle = st.checkbox('Shuffle questions and options', value=True, key='quiz_shuffle')
        with c6:
            timer_minutes = st.number_input(
                'Time limit (minutes, 0 = none)',
                min_value=0,
                max_value=180,
                value=0,
                step=5,
                key='quiz_timer',
            )

        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)
        st.caption(
            f'{len(available)} question(s) match this filter. Exam mode hides feedback until '
            'you submit; practice mode reveals the answer as soon as you choose.'
        )
        if st.button('Start quiz', type='primary', width='stretch'):
            settings = {
                'n_questions': n_questions,
                'difficulty': difficulty,
                'topic': topic,
                'shuffle': shuffle,
                'mode': mode,
                'timer_minutes': int(timer_minutes),
            }
            attempt = QuizEngine().create_attempt(mcqs, settings)
            State.set_attempt(attempt)
            if timer_minutes:
                st.session_state['quiz_deadline'] = time.time() + int(timer_minutes) * 60
            else:
                st.session_state.pop('quiz_deadline', None)
            st.rerun()


def _submit(attempt, study_set):
    questions = attempt.get('questions', [])
    answers = State.get_answers()
    result = compute_score(questions, answers)
    attempt['answers'] = dict(answers)
    attempt['submitted_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    attempt['result'] = result
    attempt['submitted'] = True
    State.set_result({'result': result, 'attempt': attempt})

    study_set.attempts.append(
        QuizAttempt(
            id=attempt['id'],
            started_at=attempt['started_at'],
            submitted_at=attempt['submitted_at'],
            settings=QuizAttemptSettings(**attempt['settings']),
            questions=[
                QuizQuestion(
                    mcq_id=q['mcq_id'],
                    displayed_options=q['displayed_options'],
                    correct_index=q['correct_index'],
                )
                for q in questions
            ],
            answers=dict(answers),
            result=QuizResult(**result),
        )
    )
    st.session_state.pop('quiz_deadline', None)
    State.set_current_view('Results')
    st.rerun()


def _run(attempt, study_set):
    questions = attempt.get('questions', [])
    if not questions:
        st.warning('The quiz has no questions.')
        return

    index = State.get_quiz_index()
    index = max(0, min(index, len(questions) - 1))
    question = questions[index]
    answers = State.get_answers()
    mode = attempt.get('settings', {}).get('mode', 'exam')

    theme.page_header(
        'Quiz in progress',
        'Stay in the flow',
        'Answer at your own pace. You can move back and forth before submitting.',
        chips=[f'Question {index + 1} of {len(questions)}', f'{mode.title()} mode'],
    )

    header = st.columns([2.2, 1])
    with header[0]:
        st.subheader(f'Question {index + 1} of {len(questions)}')
        answered = sum(1 for value in answers.values() if value is not None)
        st.progress(
            (index + 1) / max(len(questions), 1),
            text=f'{answered} of {len(questions)} answered',
        )
    with header[1]:
        deadline = st.session_state.get('quiz_deadline')
        if deadline:
            remaining = max(0, int(deadline - time.time()))
            st.metric('Time left', f'{remaining // 60}:{remaining % 60:02d}')
            if remaining == 0:
                st.warning('Time is up - the quiz was submitted automatically.')
                _submit(attempt, study_set)
                return
        else:
            st.metric('Mode', mode.title())

    mcq_id = question['mcq_id']
    source = None
    for mcq in study_set.mcqs:
        if mcq.id == mcq_id:
            source = mcq
            break

    options = question['displayed_options']
    stored = answers.get(mcq_id)

    options = [to_plain_text(option, single_line=True) for option in options]
    with st.container(border=True):
        difficulty = getattr(source.difficulty, 'value', source.difficulty) if source else 'medium'
        concept = to_plain_text(source.concept, max_length=60, single_line=True) if source else 'Quiz'
        question_text = (
            to_plain_text(source.question, max_length=400, single_line=True) if source else 'Question'
        )
        st.markdown(
            f"""
            <div class="quiz-meta">
                <span class="fc-concept">{theme.esc(concept)}</span>
                <span class="fc-pills">
                    {theme.badge(str(difficulty).title(), 'violet')}
                    {theme.badge('Answered' if stored is not None else 'Unanswered',
                                  'green' if stored is not None else 'slate')}
                </span>
            </div>
            <div class="quiz-question">{theme.esc(question_text)}</div>
            """,
            unsafe_allow_html=True,
        )

        choice = st.radio(
            'Choose an answer',
            options,
            index=stored if stored is not None else None,
            key=f'quiz_opt_{mcq_id}',
        )
        selected = stored
        if choice is not None:
            selected = options.index(choice)
            State.set_answer(mcq_id, selected)

        if mode == 'practice' and selected is not None and source is not None:
            correct_text = to_plain_text(source.options[source.correct_index], single_line=True)
            explanation = to_plain_text(source.explanation, max_length=600)
            picked = options[selected]
            if picked == correct_text:
                st.success('Correct.')
            else:
                st.error(f'The correct answer is **{correct_text}**.')
            if explanation:
                st.info(explanation)
            with st.popover('Source quote'):
                st.text(to_plain_text(source.source_quote, max_length=300))

    nav = st.columns([1, 1, 2])
    with nav[0]:
        if st.button('◀ Previous', width='stretch', disabled=index == 0):
            State.set_quiz_index(index - 1)
            st.rerun()
    with nav[1]:
        if index < len(questions) - 1:
            if st.button('Next ▶', width='stretch'):
                State.set_quiz_index(index + 1)
                st.rerun()
        else:
            if st.button('Submit quiz', type='primary', width='stretch'):
                _submit(attempt, study_set)
                return
    with nav[2]:
        answered = sum(1 for value in answers.values() if value is not None)
        st.caption(f'Answered {answered} of {len(questions)} questions.')

    if st.button('Exit without submitting', key='quiz_exit'):
        State.set_current_view('Home')
        st.rerun()


def render():
    study_set = State.get_study_set()
    if study_set is None:
        theme.page_header(
            'Quiz Lab',
            'Quiz',
            'Generate a study set to unlock the quiz engine.',
        )
        theme.empty_state('◎', 'No quiz bank yet', 'Create a study set from Home and come back to test yourself.')
        return

    attempt = State.get_attempt()
    if attempt is None:
        _setup(study_set)
        return

    _run(attempt, study_set)
