from pathlib import Path

import pytest

from core.pipeline import GenerationError, build_study_set, source_hash

SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'samples'
BIOLOGY = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')


def test_build_study_set_offline():
    study_set, warnings = build_study_set(
        topic='Cell biology',
        subject='Biology',
        raw_text=BIOLOGY,
        n_cards=10,
        n_mcqs=10,
    )
    assert study_set.topic == 'Cell biology'
    assert study_set.subject == 'Biology'
    assert study_set.engine.offline is True
    assert len(study_set.flashcards) >= 5
    assert len(study_set.mcqs) >= 5
    assert study_set.source_hash == source_hash(study_set.source_text)
    assert isinstance(warnings, list)


def test_build_study_set_rejects_short_material():
    short = (SAMPLES_DIR / 'short.txt').read_text(encoding='utf-8')
    with pytest.raises(GenerationError):
        build_study_set(topic='Short', raw_text=short)


def test_build_study_set_rejects_missing_topic():
    with pytest.raises(GenerationError):
        build_study_set(topic='   ', raw_text=BIOLOGY)


def test_build_study_set_normalizes_the_source_text():
    study_set, _ = build_study_set(
        topic='Cell biology', raw_text='Mitochondria are the powerhouse.   \n\n\n\n' + BIOLOGY
    )
    assert '\n\n\n' not in study_set.source_text


def test_build_study_set_caps_the_requested_counts():
    study_set, _ = build_study_set(
        topic='Cell biology', raw_text=BIOLOGY, n_cards=999, n_mcqs=999
    )
    assert len(study_set.flashcards) <= 30
    assert len(study_set.mcqs) <= 30
