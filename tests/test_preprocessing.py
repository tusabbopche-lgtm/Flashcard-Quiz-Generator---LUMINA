from pathlib import Path

from core import preprocessing

SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'samples'


def test_normalize_removes_control_characters():
    text = 'Hello\x00 world\x07 again'
    assert '\x00' not in preprocessing.normalize_text(text)
    assert '\x07' not in preprocessing.normalize_text(text)


def test_normalize_joins_hyphenated_line_breaks():
    text = 'photo-\nsynthesis converts light'
    assert 'photosynthesis' in preprocessing.normalize_text(text)


def test_normalize_drops_page_numbers_only_lines():
    text = 'First line\n12\nSecond line'
    result = preprocessing.normalize_text(text)
    assert '12' not in result.splitlines()
    assert 'First line' in result


def test_normalize_collapses_whitespace():
    assert preprocessing.normalize_text('a    b\t\tc') == 'a b c'


def test_normalize_handles_empty_input():
    assert preprocessing.normalize_text('') == ''
    assert preprocessing.normalize_text(None) == ''


def test_chunk_text_returns_single_chunk_for_short_text():
    chunks = preprocessing.chunk_text('short text', max_size=6000, overlap=300)
    assert chunks == ['short text']


def test_chunk_text_splits_long_text():
    text = ('Sentence number %d about biology. ' % 0) + ('Filler sentence about cells. ' * 400)
    chunks = preprocessing.chunk_text(text, max_size=1000, overlap=100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1400 for chunk in chunks)


def test_chunk_text_preserves_all_content():
    text = ' '.join(f'word{i}' for i in range(2000))
    chunks = preprocessing.chunk_text(text, max_size=500, overlap=50)
    joined = ''.join(chunks)
    for word in ('word0', 'word999', 'word1999'):
        assert word in joined


def test_chunk_biology_sample():
    text = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')
    chunks = preprocessing.chunk_text(text)
    assert len(chunks) == 1
    assert 'Mitochondria' in chunks[0]
