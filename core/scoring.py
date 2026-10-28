from typing import Dict, Any, Optional

def compute_band(percent: Optional[float]) -> Optional[str]:
    if percent is None:
        return None
    if percent >= 90:
        return 'Excellent'
    elif percent >= 75:
        return 'Good'
    elif percent >= 60:
        return 'Satisfactory'
    elif percent >= 40:
        return 'Needs Improvement'
    else:
        return 'Needs Significant Revision'

def compute_score(questions, answers: Dict[str, Optional[int]]) -> Dict[str, Any]:
    if not questions or len(questions) == 0:
        return {'total': 0, 'correct': 0, 'incorrect': 0, 'unanswered': 0, 'percent': None, 'band': None}
    total = len(questions)
    correct = 0
    unanswered = 0
    for q in questions:
        mcq_id = q.mcq_id if hasattr(q, 'mcq_id') else q.get('mcq_id')
        correct_idx = q.correct_index if hasattr(q, 'correct_index') else q.get('correct_index')
        selected = answers.get(mcq_id)
        if selected is None:
            unanswered += 1
        elif selected == correct_idx:
            correct += 1
    incorrect = total - correct - unanswered
    if total == 0:
        percent = None
    else:
        percent = round((correct / total) * 100, 1)
    band = compute_band(percent)
    return {'total': total, 'correct': correct, 'incorrect': incorrect, 'unanswered': unanswered, 'percent': percent, 'band': band}

