import pytest

from core.models import Difficulty, Flashcard, MCQ, QuizResult, StudySet
from core.quiz_engine import QuizEngine


def make_mcq(index, difficulty='medium'):
    return MCQ(
        question=f'Question number {index} about the cell?',
        options=[f'Option {index}A', f'Option {index}B', f'Option {index}C', f'Option {index}D'],
        correct_index=index % 4,
        explanation=f'Explanation for question {index} in the material.',
        concept=f'Concept {index}',
        difficulty=Difficulty(difficulty),
        source_quote='Mitochondria are often referred to as the powerhouse of the cell',
    )


def test_mcq_requires_four_options():
    with pytest.raises(Exception):
        MCQ(
            question='What is the powerhouse of the cell?',
            options=['a', 'b', 'c'],
            correct_index=0,
            explanation='Long enough explanation.',
            concept='Mitochondria',
            difficulty=Difficulty.EASY,
            source_quote='Mitochondria are often referred to as the powerhouse',
        )


def test_mcq_rejects_duplicate_options():
    with pytest.raises(Exception):
        MCQ(
            question='What is the powerhouse of the cell?',
            options=['same', 'SAME', 'other', 'another'],
            correct_index=0,
            explanation='Long enough explanation.',
            concept='Mitochondria',
            difficulty=Difficulty.EASY,
            source_quote='Mitochondria are often referred to as the powerhouse',
        )


def test_flashcard_requires_long_enough_front():
    with pytest.raises(Exception):
        Flashcard(
            front='hi',
            back='answer',
            concept='x',
            difficulty=Difficulty.EASY,
            source_quote='Mitochondria are often referred to as the powerhouse',
        )


def test_quiz_engine_creates_attempt_with_answers():
    mcqs = [make_mcq(i) for i in range(8)]
    attempt = QuizEngine().create_attempt(mcqs, {'n_questions': 5, 'shuffle': False})
    assert len(attempt['questions']) == 5
    assert all(value is None for value in attempt['answers'].values())
    assert attempt['submitted'] is False


def test_quiz_engine_keeps_correct_answer_in_place_when_not_shuffling():
    mcqs = [make_mcq(i) for i in range(3)]
    attempt = QuizEngine().create_attempt(mcqs, {'n_questions': 3, 'shuffle': False})
    for question in attempt['questions']:
        original = next(m for m in mcqs if m.id == question['mcq_id'])
        assert question['correct_index'] == original.correct_index
        assert question['displayed_options'] == original.options


def test_quiz_engine_shuffles_but_keeps_the_right_option():
    mcqs = [make_mcq(i) for i in range(6)]
    attempt = QuizEngine().create_attempt(mcqs, {'n_questions': 6, 'shuffle': True})
    for question in attempt['questions']:
        original = next(m for m in mcqs if m.id == question['mcq_id'])
        assert (
            question['displayed_options'][question['correct_index']]
            == original.options[original.correct_index]
        )


def test_quiz_engine_filters_by_difficulty():
    mcqs = [make_mcq(i, 'easy' if i % 2 == 0 else 'hard') for i in range(6)]
    attempt = QuizEngine().create_attempt(
        mcqs, {'n_questions': 10, 'difficulty': 'Easy', 'shuffle': False}
    )
    assert len(attempt['questions']) == 3


def test_quiz_engine_falls_back_when_filter_matches_nothing():
    mcqs = [make_mcq(i, 'easy') for i in range(4)]
    attempt = QuizEngine().create_attempt(
        mcqs, {'n_questions': 4, 'difficulty': 'Hard', 'shuffle': False}
    )
    assert len(attempt['questions']) == 4


def test_quiz_result_defaults():
    result = QuizResult(total=10, correct=5, incorrect=5, unanswered=0)
    assert result.percent is None
    assert result.band is None


def test_study_set_round_trips_through_json():
    study_set = StudySet(
        topic='Cell biology',
        source_text='Cells are the basic units of life.',
        source_hash='abc123',
        engine={'provider': 'offline', 'model': 'rule-based', 'offline': True},
        settings={'n_cards': 10, 'n_mcqs': 10, 'difficulty': 'Medium'},
        flashcards=[
            Flashcard(
                front='What is the powerhouse of the cell?',
                back='Mitochondria',
                concept='Mitochondria',
                difficulty=Difficulty.EASY,
                source_quote='Mitochondria are often referred to as the powerhouse',
            )
        ],
        mcqs=[make_mcq(0)],
    )
    restored = StudySet(**study_set.model_dump(mode='json'))
    assert restored.topic == 'Cell biology'
    assert restored.flashcards[0].back == 'Mitochondria'
    assert restored.mcqs[0].options[0].startswith('Option')
