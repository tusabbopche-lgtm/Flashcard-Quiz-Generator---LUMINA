"""Persistence for study sets on the local filesystem."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import config
from core.models import StudySet


def study_set_path(study_set_id: str) -> Path:
    safe_id = ''.join(ch for ch in str(study_set_id) if ch.isalnum() or ch in '-_')
    if not safe_id:
        raise ValueError('Invalid study set id')
    return config.STUDY_SETS_DIR / f'{safe_id}.json'


def save_study_set(study_set: StudySet) -> Path:
    """Write the study set to disk atomically and return its path."""
    path = study_set_path(study_set.id)
    payload = study_set.model_dump(mode='json')
    config.STUDY_SETS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        'w', encoding='utf-8', dir=str(config.STUDY_SETS_DIR), delete=False, suffix='.tmp'
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return path


def load_study_set(study_set_id: str) -> Optional[StudySet]:
    """Load a study set by id, returning ``None`` when it does not exist."""
    try:
        path = study_set_path(study_set_id)
    except ValueError:
        return None
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return None
    try:
        return StudySet(**payload)
    except Exception:
        return None


def list_study_sets() -> List[Dict[str, Any]]:
    """Return metadata for every saved study set, newest first."""
    entries: List[Dict[str, Any]] = []
    if not config.STUDY_SETS_DIR.exists():
        return entries
    for path in config.STUDY_SETS_DIR.glob('*.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        entries.append(
            {
                'id': payload.get('id', path.stem),
                'topic': payload.get('topic', 'Untitled'),
                'subject': payload.get('subject'),
                'created_at': payload.get('created_at', ''),
                'n_flashcards': len(payload.get('flashcards', []) or []),
                'n_mcqs': len(payload.get('mcqs', []) or []),
                'n_attempts': len(payload.get('attempts', []) or []),
                'engine': payload.get('engine', {}),
                'path': str(path),
            }
        )
    entries.sort(key=lambda item: item.get('created_at', ''), reverse=True)
    return entries


def delete_study_set(study_set_id: str) -> bool:
    """Delete a saved study set. Returns ``True`` when a file was removed."""
    try:
        path = study_set_path(study_set_id)
    except ValueError:
        return False
    if not path.exists():
        return False
    path.unlink()
    return True


def export_study_set(study_set: StudySet) -> str:
    """Return the study set as a pretty-printed JSON document."""
    return json.dumps(study_set.model_dump(mode='json'), ensure_ascii=False, indent=2)
