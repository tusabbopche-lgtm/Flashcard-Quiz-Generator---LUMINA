import json

import pytest

from core import config, storage
from core.models import Difficulty, EngineInfo, Flashcard, MCQ, StudySet, StudySettings


@pytest.fixture()
def study_set():
    return StudySet(
        topic='Cell biology',
        subject='Biology',
        source_text='Cells are the basic units of life.',
        source_hash='hash',
        engine=EngineInfo(provider='offline', model='rule-based', offline=True),
        settings=StudySettings(n_cards=5, n_mcqs=5, difficulty='Medium'),
        flashcards=[
            Flashcard(
                front='What is the powerhouse of the cell?',
                back='Mitochondria',
                concept='Mitochondria',
                difficulty=Difficulty.EASY,
                source_quote='Mitochondria are often referred to as the powerhouse',
            )
        ],
        mcqs=[
            MCQ(
                question='Which organelle produces ATP for the cell?',
                options=['Mitochondria', 'Ribosomes', 'Enzymes', 'Nucleus'],
                correct_index=0,
                explanation='Mitochondria generate most of the cell ATP supply.',
                concept='Mitochondria',
                difficulty=Difficulty.MEDIUM,
                source_quote='Mitochondria are often referred to as the powerhouse',
            )
        ],
    )


@pytest.fixture()
def study_sets_dir(tmp_path, monkeypatch):
    directory = tmp_path / 'study_sets'
    directory.mkdir()
    monkeypatch.setattr(config, 'STUDY_SETS_DIR', directory)
    return directory


def test_save_and_load_round_trip(study_set, study_sets_dir):
    path = storage.save_study_set(study_set)
    assert path.exists()
    loaded = storage.load_study_set(study_set.id)
    assert loaded is not None
    assert loaded.topic == 'Cell biology'
    assert loaded.flashcards[0].back == 'Mitochondria'
    assert loaded.mcqs[0].options[0] == 'Mitochondria'


def test_load_missing_study_set_returns_none(study_sets_dir):
    assert storage.load_study_set('does-not-exist') is None


def test_load_invalid_id_returns_none(study_sets_dir):
    assert storage.load_study_set('../escape') is None


def test_list_study_sets(study_set, study_sets_dir):
    storage.save_study_set(study_set)
    entries = storage.list_study_sets()
    assert len(entries) == 1
    assert entries[0]['topic'] == 'Cell biology'
    assert entries[0]['n_flashcards'] == 1
    assert entries[0]['n_mcqs'] == 1
    assert entries[0]['n_attempts'] == 0


def test_list_ignores_broken_files(study_set, study_sets_dir):
    storage.save_study_set(study_set)
    (study_sets_dir / 'broken.json').write_text('{not json', encoding='utf-8')
    entries = storage.list_study_sets()
    assert len(entries) == 1


def test_delete_study_set(study_set, study_sets_dir):
    storage.save_study_set(study_set)
    assert storage.delete_study_set(study_set.id) is True
    assert storage.delete_study_set(study_set.id) is False
    assert storage.list_study_sets() == []


def test_export_study_set_is_valid_json(study_set, study_sets_dir):
    payload = json.loads(storage.export_study_set(study_set))
    assert payload['topic'] == 'Cell biology'
    assert payload['flashcards'][0]['back'] == 'Mitochondria'
