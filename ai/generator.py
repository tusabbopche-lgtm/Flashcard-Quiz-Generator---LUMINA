"""Orchestrates item generation for both the offline and LLM backends.

The LLM path chunks the source material, asks the model for items per chunk,
validates every item against the source text, removes duplicates and tops up
when a chunk came back short.
"""

import difflib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai import prompts, rule_based
from ai.llm_client import LLMError, OpenAICompatibleClient
from core import config
from core.preprocessing import chunk_text
from core.text_utils import to_plain_text
from core.validation import (
    deduplicate_items,
    diversify_items,
    estimate_question_difficulty,
    normalize_option,
    normalize_question,
    validate_flashcard_item,
    validate_mcq_item,
)

ProgressFn = Optional[Callable[[float, str], None]]

DIFFICULTY_VALUES = ('easy', 'medium', 'hard')
MAX_TOPUP_ROUNDS = 2


def normalize_difficulty(value: Any) -> str:
    """Map any spelling of a difficulty onto the model enum values."""
    text = str(value or '').strip().lower()
    if text in DIFFICULTY_VALUES:
        return text
    if text.startswith('e'):
        return 'easy'
    if text.startswith('h'):
        return 'hard'
    return 'medium'


def _truncate(text: str, limit: int) -> str:
    text = str(text or '').strip()
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + '...'


def _clean_text_field(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, (list, tuple)):
        value = ' '.join(str(v) for v in value)
    return to_plain_text(value, single_line=True)


def _distribute(total: int, weights: List[int]) -> List[int]:
    """Split ``total`` items across chunks proportionally to their size."""
    if total <= 0 or not weights:
        return [0] * len(weights)
    weight_sum = sum(weights) or 1
    exact = [total * w / weight_sum for w in weights]
    counts = [int(x) for x in exact]
    remainder = total - sum(counts)
    order = sorted(range(len(exact)), key=lambda i: exact[i] - counts[i], reverse=True)
    for i in range(remainder):
        counts[order[i % len(order)]] += 1
    return counts


def clean_flashcard(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalise a flashcard payload into the shape used by the models."""
    if not isinstance(item, dict):
        return None
    front = _clean_text_field(item.get('front'))
    back = _clean_text_field(item.get('back'))
    if len(front) < 5 or not back:
        return None
    quote = _clean_text_field(item.get('source_quote'))
    if len(quote) < 10:
        return None
    concept = _clean_text_field(item.get('concept')) or 'general'
    return {
        'front': _truncate(front, 300),
        'back': _truncate(back, 600),
        'explanation': _truncate(_clean_text_field(item.get('explanation')), 600) or None,
        'concept': _truncate(concept, 60),
        'difficulty': normalize_difficulty(item.get('difficulty')),
        'source_quote': _truncate(quote, 300),
    }


def _clean_option(value: Any) -> str:
    option = to_plain_text(value, max_length=180, single_line=True)
    option = re.sub(r'^[\s\(\[\{]*[A-Da-d1-4][\)\.\:\-]\s+', '', option)
    return option.strip()


def _resolve_correct_index(item: Dict[str, Any], options: List[str]) -> Optional[int]:
    answer = item.get('correct_answer')
    if answer is None:
        answer = item.get('answer')
    if answer is not None and str(answer).strip():
        target = normalize_option(answer)
        matches = [index for index, option in enumerate(options) if normalize_option(option) == target]
        if len(matches) == 1:
            return matches[0]
        best_index = None
        best_ratio = 0.0
        for index, option in enumerate(options):
            ratio = difflib.SequenceMatcher(None, target, normalize_option(option)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        return best_index if best_ratio >= 0.9 else None

    raw_index = item.get('correct_index')
    if isinstance(raw_index, bool):
        return None
    try:
        correct_index = int(raw_index)
    except (TypeError, ValueError):
        return None
    return correct_index if 0 <= correct_index <= 3 else None


def clean_mcq(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalise an MCQ payload into the shape used by the models."""
    if not isinstance(item, dict):
        return None
    question = _clean_text_field(item.get('question'))
    if len(question) < 10:
        return None
    options = item.get('options')
    if not isinstance(options, (list, tuple)) or len(options) != 4:
        return None
    options = [_clean_option(option) for option in options]
    if not all(options):
        return None
    if len({normalize_option(option) for option in options}) != 4:
        return None
    correct_index = _resolve_correct_index(item, options)
    if correct_index is None:
        return None
    quote = _clean_text_field(item.get('source_quote'))
    if len(quote) < 10:
        return None
    explanation = _clean_text_field(item.get('explanation'))
    if len(explanation) < 10:
        return None
    concept = _clean_text_field(item.get('concept')) or 'general'
    question_type = _clean_text_field(item.get('question_type')).lower()
    cleaned = {
        'question': _truncate(question, 400),
        'options': options,
        'correct_index': correct_index,
        'explanation': _truncate(explanation, 600),
        'concept': _truncate(concept, 60),
        'difficulty': normalize_difficulty(item.get('difficulty')),
        'source_quote': _truncate(quote, 300),
    }
    if question_type:
        cleaned['question_type'] = _truncate(question_type, 30)
    return cleaned


def _report(progress: ProgressFn, fraction: float, message: str) -> None:
    if progress is None:
        return
    try:
        progress(min(max(fraction, 0.0), 1.0), message)
    except Exception:  # progress callbacks must never break generation
        pass


def _dedupe_cards(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return deduplicate_items(items, lambda item: item.get('front', ''), threshold=0.9)


def _dedupe_mcqs(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return deduplicate_items(items, lambda item: item.get('question', ''), threshold=0.9)


def generate_offline(
    text: str,
    n_cards: int,
    n_mcqs: int,
    difficulty: str = 'Medium',
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate validated items with the built-in rule-based engine."""
    expected = normalize_difficulty(difficulty)
    raw = rule_based.generate_offline(
        text,
        n_cards=max(n_cards * 2, n_cards),
        n_mcqs=max(n_mcqs * 4, n_mcqs),
        difficulty=difficulty,
        seed=seed,
    )
    flashcards = []
    for item in raw.get('flashcards', []):
        cleaned = clean_flashcard(item)
        if not cleaned:
            continue
        cleaned['difficulty'] = expected
        ok, _reason = validate_flashcard_item(cleaned, text)
        if ok:
            flashcards.append(cleaned)
    mcqs = []
    for item in raw.get('mcqs', []):
        cleaned = clean_mcq(item)
        if not cleaned:
            continue
        cleaned['difficulty'] = expected
        ok, _reason = validate_mcq_item(cleaned, text, expected_difficulty=expected)
        if not ok:
            continue
        if expected == 'hard' and estimate_question_difficulty(cleaned['question']) != 'hard':
            continue
        mcqs.append(cleaned)
    concepts = []
    for item in raw.get('key_concepts', []):
        term = _clean_text_field(item.get('term'))
        definition = _clean_text_field(item.get('definition'))
        if term and definition:
            concepts.append({'term': _truncate(term, 120), 'definition': _truncate(definition, 400)})

    flashcards = _dedupe_cards(flashcards)
    mcqs = diversify_items(
        _dedupe_mcqs(mcqs),
        n_mcqs,
        type_fn=lambda item: item.get('question_type') or '',
    )
    warnings = []
    if len(flashcards) < n_cards:
        warnings.append(f'Only {len(flashcards)} of {n_cards} flashcards could be grounded in the material.')
    if len(mcqs) < n_mcqs:
        warnings.append(f'Only {len(mcqs)} of {n_mcqs} questions could be grounded in the material.')
    return {
        'key_concepts': concepts[:15],
        'flashcards': flashcards[:n_cards],
        'mcqs': mcqs[:n_mcqs],
        'warnings': warnings,
    }


def generate_with_llm(
    text: str,
    client: OpenAICompatibleClient,
    topic: str,
    subject: str,
    n_cards: int,
    n_mcqs: int,
    difficulty: str = 'Medium',
    progress: ProgressFn = None,
) -> Dict[str, Any]:
    """Generate items with an OpenAI-compatible model."""
    warnings: List[str] = []
    chunks = chunk_text(text, config.MAX_CHUNK_SIZE, config.CHUNK_OVERLAP)
    if not chunks:
        return {'key_concepts': [], 'flashcards': [], 'mcqs': [], 'warnings': ['No text to work with.']}

    card_quota = _distribute(n_cards, [len(c) for c in chunks])
    mcq_quota = _distribute(n_mcqs, [len(c) for c in chunks])

    flashcards: List[Dict[str, Any]] = []
    mcqs: List[Dict[str, Any]] = []
    concepts: List[Dict[str, Any]] = []
    rejected = 0

    for index, chunk in enumerate(chunks):
        _report(
            progress,
            0.05 + 0.7 * (index / max(len(chunks), 1)),
            f'Generating items from section {index + 1} of {len(chunks)}...',
        )
        user_prompt = prompts.USER_PROMPT_TEMPLATE.format(
            topic=topic or 'Study material',
            subject=subject or 'General',
            difficulty=difficulty or 'Medium',
            chunk=chunk,
            n_cards=card_quota[index],
            n_mcqs=mcq_quota[index],
        )
        try:
            payload = client.complete_json(prompts.SYSTEM_PROMPT, user_prompt, prompts.REPAIR_PROMPT)
        except LLMError as exc:
            warnings.append(f'Section {index + 1}: {exc}')
            continue

        for item in payload.get('key_concepts', []) or []:
            if isinstance(item, dict):
                term = _clean_text_field(item.get('term'))
                definition = _clean_text_field(item.get('definition'))
                if term and definition:
                    concepts.append({'term': _truncate(term, 120), 'definition': _truncate(definition, 400)})

        for item in payload.get('flashcards', []) or []:
            cleaned = clean_flashcard(item)
            if not cleaned:
                rejected += 1
                continue
            ok, _reason = validate_flashcard_item(cleaned, text)
            if not ok:
                rejected += 1
                continue
            flashcards.append(cleaned)

        for item in payload.get('mcqs', []) or []:
            cleaned = clean_mcq(item)
            if not cleaned:
                rejected += 1
                continue
            ok, _reason = validate_mcq_item(cleaned, text, expected_difficulty=difficulty)
            if not ok:
                rejected += 1
                continue
            mcqs.append(cleaned)

    flashcards = _dedupe_cards(flashcards)
    mcqs = _dedupe_mcqs(mcqs)

    # Top up when the model returned fewer items than requested.
    biggest = max(chunks, key=len)
    for round_index in range(MAX_TOPUP_ROUNDS):
        missing_cards = n_cards - len(flashcards)
        missing_mcqs = n_mcqs - len(mcqs)
        if missing_cards <= 0 and missing_mcqs <= 0:
            break
        _report(
            progress,
            0.78 + 0.1 * (round_index + 1),
            f'Topping up ({missing_cards} cards, {missing_mcqs} questions still needed)...',
        )
        existing = [item.get('front', '') for item in flashcards]
        existing += [item.get('question', '') for item in mcqs]
        topup_prompt = prompts.TOPUP_PROMPT.format(existing='; '.join(existing[:40]) or 'none')
        user_prompt = prompts.USER_PROMPT_TEMPLATE.format(
            topic=topic or 'Study material',
            subject=subject or 'General',
            difficulty=difficulty or 'Medium',
            chunk=biggest,
            n_cards=max(missing_cards, 0),
            n_mcqs=max(missing_mcqs, 0),
        ) + '\n' + topup_prompt
        try:
            payload = client.complete_json(prompts.SYSTEM_PROMPT, user_prompt, prompts.REPAIR_PROMPT)
        except LLMError as exc:
            warnings.append(f'Top-up round {round_index + 1}: {exc}')
            break

        for item in payload.get('flashcards', []) or []:
            cleaned = clean_flashcard(item)
            if not cleaned:
                rejected += 1
                continue
            ok, _reason = validate_flashcard_item(cleaned, text)
            if ok:
                flashcards.append(cleaned)
            else:
                rejected += 1
        for item in payload.get('mcqs', []) or []:
            cleaned = clean_mcq(item)
            if not cleaned:
                rejected += 1
                continue
            ok, _reason = validate_mcq_item(cleaned, text, expected_difficulty=difficulty)
            if ok:
                mcqs.append(cleaned)
            else:
                rejected += 1
        flashcards = _dedupe_cards(flashcards)
        mcqs = _dedupe_mcqs(mcqs)

    if rejected:
        warnings.append(f'{rejected} generated item(s) failed validation and were discarded.')
    if len(flashcards) < n_cards:
        warnings.append(
            f'Only {len(flashcards)} of {n_cards} flashcards could be grounded in the material.'
        )
    if len(mcqs) < n_mcqs:
        warnings.append(
            f'Only {len(mcqs)} of {n_mcqs} questions could be grounded in the material.'
        )

    _report(progress, 0.95, 'Assembling study set...')
    return {
        'key_concepts': _dedupe_concepts(concepts)[:15],
        'flashcards': flashcards[:n_cards],
        'mcqs': mcqs[:n_mcqs],
        'warnings': warnings,
    }


def _dedupe_concepts(concepts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    kept = []
    for concept in concepts:
        key = normalize_question(concept.get('term', ''))
        if key in seen:
            continue
        seen.add(key)
        kept.append(concept)
    return kept


def generate_items(
    text: str,
    topic: str,
    subject: str = '',
    n_cards: int = config.DEFAULT_CARDS,
    n_mcqs: int = config.DEFAULT_MCQ,
    difficulty: str = 'Medium',
    engine: Optional[Dict[str, Any]] = None,
    client: Optional[OpenAICompatibleClient] = None,
    progress: ProgressFn = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate items using the active engine and return ``(items, engine_info)``."""
    engine = engine or config.get_active_engine()
    _report(progress, 0.02, 'Preparing material...')

    if engine.get('offline', True):
        items = generate_offline(text, n_cards, n_mcqs, difficulty, config.get_seed())
        _report(progress, 1.0, 'Done.')
        return items, engine

    items: Dict[str, Any] = {
        'key_concepts': [],
        'flashcards': [],
        'mcqs': [],
        'warnings': [],
    }
    try:
        if client is None:
            if not config.LLM_BASE_URL:
                raise LLMError('No LLM base URL configured; set LLM_BASE_URL in your .env file.')
            client = OpenAICompatibleClient(
                config.LLM_BASE_URL,
                api_key=config.LLM_API_KEY,
                model=config.LLM_MODEL or 'gpt-3.5-turbo',
            )
        items = generate_with_llm(
            text,
            client,
            topic=topic,
            subject=subject,
            n_cards=n_cards,
            n_mcqs=n_mcqs,
            difficulty=difficulty,
            progress=progress,
        )
    except Exception as exc:  # AI failure must not destroy an otherwise usable input
        items['warnings'].append(f'AI generation failed: {exc}')

    missing_cards = n_cards - len(items.get('flashcards', []))
    missing_mcqs = n_mcqs - len(items.get('mcqs', []))
    if missing_cards > 0 or missing_mcqs > 0:
        _report(progress, 0.9, 'Filling gaps with the offline engine...')
        fallback = generate_offline(
            text,
            n_cards=max(n_cards, 1),
            n_mcqs=max(n_mcqs, 1),
            difficulty=difficulty,
            seed=config.get_seed(),
        )
        existing_card_keys = {
            normalize_question(item.get('front', '')) for item in items.get('flashcards', [])
        }
        existing_mcq_keys = {
            normalize_question(item.get('question', '')) for item in items.get('mcqs', [])
        }
        added = 0
        for card in fallback.get('flashcards', []):
            if len(items['flashcards']) >= n_cards:
                break
            key = normalize_question(card.get('front', ''))
            if key and key not in existing_card_keys:
                existing_card_keys.add(key)
                items['flashcards'].append(card)
                added += 1
        for mcq in fallback.get('mcqs', []):
            if len(items['mcqs']) >= n_mcqs:
                break
            key = normalize_question(mcq.get('question', ''))
            if key and key not in existing_mcq_keys:
                existing_mcq_keys.add(key)
                items['mcqs'].append(mcq)
                added += 1
        if not items.get('key_concepts'):
            items['key_concepts'] = fallback.get('key_concepts', [])
        if added:
            items.setdefault('warnings', []).append(
                'The AI returned too few usable items, so the offline engine supplied the rest.'
            )
        elif len(items['flashcards']) < n_cards or len(items['mcqs']) < n_mcqs:
            items.setdefault('warnings', []).append(
                'Not all requested items could be generated from this material.'
            )

    items['flashcards'] = items.get('flashcards', [])[:n_cards]
    items['mcqs'] = items.get('mcqs', [])[:n_mcqs]
    items.setdefault('warnings', [])
    _report(progress, 1.0, 'Done.')
    return items, engine

