from pathlib import Path

from ai import generator
from core import config

SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'samples'
BIOLOGY = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')


class StubClient:
    """Minimal stand-in for OpenAICompatibleClient."""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def complete_json(self, system_prompt, user_prompt, repair_prompt=''):
        self.calls.append(user_prompt)
        if not self.payloads:
            return {'flashcards': [], 'mcqs': [], 'key_concepts': []}
        return self.payloads.pop(0)


def test_normalize_difficulty():
    assert generator.normalize_difficulty('Easy') == 'easy'
    assert generator.normalize_difficulty('MEDIUM') == 'medium'
    assert generator.normalize_difficulty('hard') == 'hard'
    assert generator.normalize_difficulty('') == 'medium'
    assert generator.normalize_difficulty(None) == 'medium'


def test_clean_flashcard_truncates_and_normalizes():
    cleaned = generator.clean_flashcard(
        {
            'front': '  What   is ATP?  ',
            'back': 'Adenosine triphosphate',
            'explanation': 'x' * 900,
            'concept': 'ATP',
            'difficulty': 'Hard',
            'source_quote': 'y' * 900,
        }
    )
    assert cleaned['front'] == 'What is ATP?'
    assert len(cleaned['explanation']) <= 600
    assert len(cleaned['source_quote']) <= 300
    assert cleaned['difficulty'] == 'hard'


def test_clean_flashcard_rejects_incomplete_items():
    assert generator.clean_flashcard({'front': 'hi', 'back': 'x'}) is None
    assert generator.clean_flashcard({'front': 'long enough front', 'back': ''}) is None
    assert generator.clean_flashcard({'front': 'long enough front', 'back': 'x', 'source_quote': 'short'}) is None


def test_clean_mcq_rejects_bad_options():
    base = {
        'question': 'Which organelle produces ATP for the cell?',
        'options': ['Mitochondria', 'Ribosomes', 'Enzymes', 'Nucleus'],
        'correct_index': 0,
        'explanation': 'Mitochondria generate ATP.',
        'concept': 'Mitochondria',
        'difficulty': 'medium',
        'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
    }
    assert generator.clean_mcq(base) is not None
    assert generator.clean_mcq(dict(base, options=['a', 'b', 'c'])) is None
    assert generator.clean_mcq(dict(base, options=['a', 'A', 'c', 'd'])) is None
    assert generator.clean_mcq(dict(base, correct_index=9)) is None
    assert generator.clean_mcq(dict(base, explanation='short')) is None


def test_generate_offline_returns_model_ready_items():
    items = generator.generate_offline(BIOLOGY, n_cards=8, n_mcqs=8, difficulty='Medium', seed=1)
    assert len(items['flashcards']) <= 8
    assert len(items['mcqs']) <= 8
    for card in items['flashcards']:
        assert card['difficulty'] == 'medium'
        assert len(card['source_quote']) >= 10
    for mcq in items['mcqs']:
        assert len(mcq['options']) == 4
        assert 0 <= mcq['correct_index'] <= 3


def test_generate_offline_is_deterministic_with_a_seed():
    first = generator.generate_offline(BIOLOGY, 5, 5, 'Medium', seed=42)
    second = generator.generate_offline(BIOLOGY, 5, 5, 'Medium', seed=42)
    assert first == second


def test_generate_items_uses_the_offline_engine(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', '')
    items, engine = generator.generate_items(BIOLOGY, 'Cell biology', 'Biology', 5, 5)
    assert engine['offline'] is True
    assert items['flashcards']


def test_generate_with_llm_keeps_grounded_items():
    payload = {
        'key_concepts': [{'term': 'Mitochondria', 'definition': 'The powerhouse of the cell.'}],
        'flashcards': [
            {
                'front': 'What is the powerhouse of the cell?',
                'back': 'Mitochondria',
                'explanation': 'Stated in the material.',
                'concept': 'Mitochondria',
                'difficulty': 'easy',
                'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
            },
            {
                'front': 'Where does the heart pump blood to?',
                'back': 'The lungs',
                'explanation': 'Not in the material at all.',
                'concept': 'Heart',
                'difficulty': 'easy',
                'source_quote': 'The heart pumps blood through the arteries of the body',
            },
        ],
        'mcqs': [
            {
                'question': 'Which organelle generates ATP for the cell?',
                'options': ['Mitochondria', 'Ribosomes', 'Enzymes', 'Nucleus'],
                'correct_index': 0,
                'explanation': 'Mitochondria generate most of the ATP.',
                'concept': 'Mitochondria',
                'difficulty': 'medium',
                'source_quote': 'they generate most of the cell supply of adenosine triphosphate',
            }
        ],
    }
    client = StubClient([payload])
    items = generator.generate_with_llm(
        BIOLOGY, client, 'Cell biology', 'Biology', n_cards=5, n_mcqs=5
    )
    assert len(items['flashcards']) == 1
    assert items['flashcards'][0]['back'] == 'Mitochondria'
    assert len(items['mcqs']) == 1
    assert items['key_concepts'][0]['term'] == 'Mitochondria'
    assert any('validation' in warning for warning in items['warnings'])


def test_generate_with_llm_tops_up_when_short():
    good_card = {
        'front': 'What is the powerhouse of the cell?',
        'back': 'Mitochondria',
        'explanation': 'Stated in the material.',
        'concept': 'Mitochondria',
        'difficulty': 'easy',
        'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
    }
    second_card = dict(
        good_card,
        front='Which organelle contains its own DNA?',
        back='Mitochondria',
        source_quote='Mitochondria have their own DNA and are believed to have evolved',
    )
    client = StubClient([{'flashcards': [good_card], 'mcqs': []}, {'flashcards': [second_card], 'mcqs': []}])
    items = generator.generate_with_llm(
        BIOLOGY, client, 'Cell biology', 'Biology', n_cards=2, n_mcqs=0
    )
    assert len(items['flashcards']) == 2


def test_generate_with_llm_survives_client_errors():
    class BrokenClient(StubClient):
        def complete_json(self, system_prompt, user_prompt, repair_prompt=''):
            from ai.llm_client import LLMError

            raise LLMError('endpoint down')

    items = generator.generate_with_llm(
        BIOLOGY, BrokenClient([]), 'Cell biology', 'Biology', n_cards=5, n_mcqs=5
    )
    assert items['flashcards'] == []
    assert items['warnings']


def test_clean_mcq_accepts_answer_text_and_strips_option_prefixes():
    item = {
        'question': 'Which organelle produces ATP for the cell?',
        'options': ['A) Mitochondria', 'B) Ribosomes', 'C) Enzymes', 'D) Nucleus'],
        'correct_answer': 'Mitochondria',
        'explanation': 'Mitochondria generate most of the cell ATP supply.',
        'concept': 'Mitochondria',
        'difficulty': 'medium',
        'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
    }
    cleaned = generator.clean_mcq(item)
    assert cleaned['correct_index'] == 0
    assert cleaned['options'][0] == 'Mitochondria'


def test_generation_cleans_legacy_html_fields():
    card = generator.clean_flashcard(
        {
            'front': '<p>What is <b>ATP</b>?</p>',
            'back': '<div class="answer"><strong>Energy currency</strong></div>',
            'explanation': '<em>Used by cells.</em>',
            'concept': '<span>ATP</span>',
            'difficulty': 'easy',
            'source_quote': '<p>ATP is used as a source of chemical energy.</p>',
        }
    )
    assert card['front'] == 'What is ATP?'
    assert card['back'] == 'Energy currency'
    assert '<' not in card['concept']
    assert '<' not in card['source_quote']


def test_hard_offline_questions_are_actually_hard():
    from core.validation import estimate_question_difficulty

    items = generator.generate_offline(BIOLOGY, 5, 5, 'Hard', seed=3)
    assert items['mcqs']
    for mcq in items['mcqs']:
        assert mcq['difficulty'] == 'hard'
        assert estimate_question_difficulty(mcq['question']) == 'hard'


def test_generate_items_falls_back_when_llm_fails():
    class BrokenClient(StubClient):
        def complete_json(self, system_prompt, user_prompt, repair_prompt=''):
            from ai.llm_client import LLMError

            raise LLMError('endpoint down')

    items, _engine = generator.generate_items(
        BIOLOGY,
        'Cell biology',
        'Biology',
        n_cards=5,
        n_mcqs=5,
        engine={'provider': 'openai_compatible', 'model': 'test', 'offline': False},
        client=BrokenClient([]),
    )
    assert items['flashcards']
    assert items['mcqs']
    assert any('offline engine' in warning.lower() for warning in items['warnings'])
