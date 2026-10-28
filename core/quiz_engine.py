import random
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4


def _difficulty_value(mcq: Any) -> str:
    value = getattr(mcq, 'difficulty', None)
    if value is None and isinstance(mcq, dict):
        value = mcq.get('difficulty')
    return str(getattr(value, 'value', value) or '').lower()


def _concept_value(mcq: Any) -> str:
    if isinstance(mcq, dict):
        return str(mcq.get('concept', '') or '')
    return str(getattr(mcq, 'concept', '') or '')


def filter_mcqs(
    mcqs: List[Any],
    difficulty: str = 'All',
    topic: str = 'All topics',
) -> List[Any]:
    filtered = list(mcqs)
    if difficulty and difficulty != 'All':
        wanted = str(difficulty).lower()
        filtered = [mcq for mcq in filtered if _difficulty_value(mcq) == wanted]
    if topic and topic != 'All topics':
        filtered = [mcq for mcq in filtered if _concept_value(mcq).casefold() == str(topic).casefold()]
    return filtered


class QuizEngine:
    def create_attempt(self, mcqs: List[Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        n_questions = int(settings.get('n_questions', min(10, len(mcqs))))
        filtered = filter_mcqs(
            mcqs,
            difficulty=settings.get('difficulty', 'All'),
            topic=settings.get('topic', 'All topics'),
        )
        if not filtered:
            filtered = list(mcqs)
        selected = list(filtered)
        if settings.get('shuffle', True):
            random.shuffle(selected)
        selected = selected[: max(0, n_questions)]

        questions = []
        for mcq in selected:
            options = (
                list(mcq.options)
                if hasattr(mcq, 'options')
                else list(mcq.get('options', []))
            )
            correct_text = (
                mcq.options[mcq.correct_index]
                if hasattr(mcq, 'correct_index')
                else mcq.get('options')[mcq.get('correct_index')]
            )
            displayed = list(options)
            if settings.get('shuffle', True):
                random.shuffle(displayed)
            questions.append(
                {
                    'mcq_id': mcq.id if hasattr(mcq, 'id') else mcq.get('id'),
                    'displayed_options': displayed,
                    'correct_index': displayed.index(correct_text),
                }
            )

        return {
            'id': str(uuid4()),
            'started_at': datetime.utcnow().isoformat() + 'Z',
            'submitted_at': None,
            'settings': settings,
            'questions': questions,
            'answers': {question['mcq_id']: None for question in questions},
            'submitted': False,
        }
