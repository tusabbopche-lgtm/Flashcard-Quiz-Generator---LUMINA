from core import scoring


def test_scoring_basic():
    questions = [
        type('Q', (), {'mcq_id': '1', 'correct_index': 0})(),
        type('Q', (), {'mcq_id': '2', 'correct_index': 1})(),
        type('Q', (), {'mcq_id': '3', 'correct_index': 2})(),
        type('Q', (), {'mcq_id': '4', 'correct_index': 0})(),
        type('Q', (), {'mcq_id': '5', 'correct_index': 3})(),
        type('Q', (), {'mcq_id': '6', 'correct_index': 1})(),
        type('Q', (), {'mcq_id': '7', 'correct_index': 2})(),
        type('Q', (), {'mcq_id': '8', 'correct_index': 0})(),
        type('Q', (), {'mcq_id': '9', 'correct_index': 1})(),
        type('Q', (), {'mcq_id': '10', 'correct_index': 2})(),
    ]
    answers = {'1': 0, '2': 1, '3': 2, '4': 0, '5': 3, '6': 1, '7': 2, '8': 1, '9': 0, '10': None}
    result = scoring.compute_score(questions, answers)
    assert result['correct'] == 7
    assert result['incorrect'] == 2
    assert result['unanswered'] == 1
    assert result['percent'] == 70.0
    assert result['band'] == 'Satisfactory'


def test_scoring_all_blank():
    questions = [type('Q', (), {'mcq_id': str(i), 'correct_index': 0})() for i in range(3)]
    answers = {str(i): None for i in range(3)}
    result = scoring.compute_score(questions, answers)
    assert result['correct'] == 0
    assert result['unanswered'] == 3
    assert result['percent'] == 0.0
    assert result['band'] == 'Needs Significant Revision'


def test_scoring_total_zero():
    result = scoring.compute_score([], {})
    assert result['percent'] is None
    assert result['band'] is None


def test_bands():
    assert scoring.compute_band(39.9) == 'Needs Significant Revision'
    assert scoring.compute_band(40) == 'Needs Improvement'
    assert scoring.compute_band(59.9) == 'Needs Improvement'
    assert scoring.compute_band(60) == 'Satisfactory'
    assert scoring.compute_band(74.9) == 'Satisfactory'
    assert scoring.compute_band(75) == 'Good'
    assert scoring.compute_band(89.9) == 'Good'
    assert scoring.compute_band(90) == 'Excellent'
    assert scoring.compute_band(100) == 'Excellent'
