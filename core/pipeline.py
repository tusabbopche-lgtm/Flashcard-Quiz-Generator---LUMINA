"""Turns raw study material into a validated :class:`~core.models.StudySet`."""

import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai.generator import generate_items
from ai.llm_client import OpenAICompatibleClient
from core import config
from core.models import (
    Difficulty,
    EngineInfo,
    Flashcard,
    KeyConcept,
    MCQ,
    StudySet,
    StudySettings,
)
from core.preprocessing import normalize_text
from core.validators import validate_input_text, validate_topic

ProgressFn = Optional[Callable[[float, str], None]]


class GenerationError(RuntimeError):
    """Raised when the material cannot be turned into a study set."""


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build_study_set(
    topic: str,
    subject: str = '',
    raw_text: str = '',
    n_cards: int = config.DEFAULT_CARDS,
    n_mcqs: int = config.DEFAULT_MCQ,
    difficulty: str = 'Medium',
    engine: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAICompatibleClient] = None,
    progress: ProgressFn = None,
) -> Tuple[StudySet, List[str]]:
    """Generate and validate a study set from raw material.

    Returns the study set together with any non-fatal warnings.
    """
    ok, reason = validate_topic(topic)
    if not ok:
        raise GenerationError(reason)

    text = normalize_text(raw_text)
    ok, reason = validate_input_text(text, config.MIN_TEXT_CHARS, config.MAX_TEXT_CHARS)
    if not ok:
        raise GenerationError(reason)

    n_cards = max(1, min(int(n_cards), config.MAX_CARDS))
    n_mcqs = max(1, min(int(n_mcqs), config.MAX_MCQ))

    items, engine_info = generate_items(
        text,
        topic=topic,
        subject=subject,
        n_cards=n_cards,
        n_mcqs=n_mcqs,
        difficulty=difficulty,
        engine=engine,
        client=client,
        progress=progress,
    )

    warnings: List[str] = list(items.get('warnings', []))

    flashcards: List[Flashcard] = []
    for item in items.get('flashcards', []):
        try:
            flashcards.append(Flashcard(**item))
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f'Flashcard skipped: {exc}')

    mcqs: List[MCQ] = []
    for item in items.get('mcqs', []):
        try:
            mcqs.append(MCQ(**item))
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f'Question skipped: {exc}')

    concepts: List[KeyConcept] = []
    for item in items.get('key_concepts', []):
        try:
            concepts.append(KeyConcept(**item))
        except Exception:  # pragma: no cover - defensive
            continue

    if not flashcards and not mcqs:
        raise GenerationError(
            'No usable items could be generated from this material. Try a longer or clearer text.'
        )

    study_set = StudySet(
        topic=topic.strip(),
        subject=(subject or None),
        source_text=text,
        source_hash=source_hash(text),
        engine=EngineInfo(
            provider=engine_info.get('provider', 'offline'),
            model=engine_info.get('model', 'rule-based'),
            offline=bool(engine_info.get('offline', True)),
        ),
        settings=StudySettings(
            n_cards=n_cards,
            n_mcqs=n_mcqs,
            difficulty=difficulty,
        ),
        flashcards=flashcards,
        mcqs=mcqs,
        key_concepts=concepts,
    )
    return study_set, warnings
