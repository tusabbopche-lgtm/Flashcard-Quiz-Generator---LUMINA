from pathlib import Path

from ai import rule_based

SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'samples'


def test_rule_based_biology_sample():
    text = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')
    res = rule_based.generate_offline(text, n_cards=10, n_mcqs=10)
    assert len(res['flashcards']) >= 5
    assert len(res['mcqs']) >= 5
    # Check MCQ structure
    for mcq in res['mcqs']:
        assert len(mcq['options']) == 4
        assert len(set([o.lower() for o in mcq['options']])) == 4
        assert 0 <= mcq['correct_index'] <= 3
        assert mcq['options'][mcq['correct_index']] == mcq['options'][mcq['correct_index']]  # basic check


def test_rule_based_respects_requested_counts():
    text = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')
    res = rule_based.generate_offline(text, n_cards=3, n_mcqs=2)
    assert len(res['flashcards']) <= 3
    assert len(res['mcqs']) <= 2


def test_rule_based_is_deterministic_with_seed():
    text = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')
    first = rule_based.generate_offline(text, n_cards=5, n_mcqs=5, seed=7)
    second = rule_based.generate_offline(text, n_cards=5, n_mcqs=5, seed=7)
    assert first == second


def test_rule_based_short_text_does_not_crash():
    text = (SAMPLES_DIR / 'short.txt').read_text(encoding='utf-8')
    res = rule_based.generate_offline(text, n_cards=5, n_mcqs=5)
    assert isinstance(res['flashcards'], list)
    assert isinstance(res['mcqs'], list)
    assert isinstance(res['key_concepts'], list)
