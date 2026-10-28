from types import SimpleNamespace

from core.models import Difficulty
from core.quiz_engine import QuizEngine, filter_mcqs


def make_mcq(index, concept, difficulty=Difficulty.MEDIUM):
    return SimpleNamespace(
        id=f'mcq-{index}',
        options=['Correct', 'Wrong A', 'Wrong B', 'Wrong C'],
        correct_index=0,
        concept=concept,
        difficulty=difficulty,
    )


def test_filter_mcqs_by_topic_and_difficulty():
    mcqs = [
        make_mcq(1, 'Cells', Difficulty.EASY),
        make_mcq(2, 'Cells', Difficulty.HARD),
        make_mcq(3, 'Genetics', Difficulty.EASY),
    ]
    result = filter_mcqs(mcqs, difficulty='Easy', topic='Cells')
    assert [mcq.id for mcq in result] == ['mcq-1']


def test_create_attempt_respects_topic_filter():
    mcqs = [
        make_mcq(1, 'Cells', Difficulty.EASY),
        make_mcq(2, 'Cells', Difficulty.HARD),
        make_mcq(3, 'Genetics', Difficulty.HARD),
    ]
    attempt = QuizEngine().create_attempt(
        mcqs,
        {'n_questions': 10, 'difficulty': 'All', 'topic': 'Genetics', 'shuffle': False},
    )
    assert len(attempt['questions']) == 1
    assert attempt['questions'][0]['mcq_id'] == 'mcq-3'


def test_keeps_correct_answer_after_option_shuffle():
    mcqs = [make_mcq(1, 'Cells')]
    attempt = QuizEngine().create_attempt(
        mcqs,
        {'n_questions': 1, 'difficulty': 'All', 'topic': 'All topics', 'shuffle': True},
    )
    question = attempt['questions'][0]
    assert question['displayed_options'][question['correct_index']] == 'Correct'
