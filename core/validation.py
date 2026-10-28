import difflib
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple
import re

BAD_OPTIONS = ['all of the above', 'none of the above', 'both a and b']
DIFFICULTY_VALUES = ('easy', 'medium', 'hard')

_META_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'if', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have',
    'had', 'do', 'does', 'did', 'will', 'can', 'could', 'should', 'may', 'might',
    'this', 'that', 'these', 'those', 'as', 'from', 'into', 'about', 'than', 'so',
    'not', 'while', 'which', 'where', 'when', 'because', 'they', 'them', 'their',
    'there', 'its', 'it', 'also', 'more', 'most', 'some', 'such', 'other', 'one',
    'two', 'three', 'each', 'every', 'any', 'all', 'both', 'few', 'many', 'much',
    'very', 'too', 'only', 'just', 'even', 'still', 'same', 'different', 'new',
    'old', 'first', 'last', 'next', 'now', 'then', 'over', 'under', 'after',
    'before', 'during', 'between', 'through', 'within', 'without', 'against',
    'among', 'per', 'via', 'upon', 'whose', 'whom', 'what', 'how', 'why',
    'whether', 'either', 'neither', 'stated', 'material', 'text', 'according',
}


def normalize_question(q: str) -> str:
    q2 = q.lower()
    q2 = re.sub(r'[^\w\s]', '', q2)
    q2 = re.sub(r'\s+', ' ', q2)
    return q2.strip()


def normalize_option(value: Any) -> str:
    """Normalise an option for duplicate and leakage checks."""
    text = str(value or '').casefold()
    text = re.sub(r'^[\s\(\[\{]*[a-d1-4][\)\.\:\-]\s*', '', text)
    text = re.sub(r'[^\w\s]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _content_words(text: str) -> set:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]+", str(text or '').casefold())
    return {word for word in words if len(word) >= 3 and word not in _META_STOP_WORDS}


def _normalize_for_match(text: str) -> str:
    """Lower-case, strip punctuation and collapse whitespace for comparison."""
    text = str(text or '').lower()
    for smart in ('\u2018', '\u2019'):
        text = text.replace(smart, "'")
    for smart in ('\u201c', '\u201d'):
        text = text.replace(smart, '"')
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = re.sub(r"[^\w\s']", ' ', text)
    text = re.sub(r"['\u2019]", '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _tokens_appear_in_order(quote_tokens, source_tokens) -> bool:
    """True when the quote's words that exist in the source also occur in order."""
    cursor = 0
    for token in quote_tokens:
        try:
            index = source_tokens.index(token, cursor)
        except ValueError:
            continue
        cursor = index + 1
    return True


def _fuzzy_ratio(quote: str, source: str, threshold: float) -> float:
    """Best similarity between the quote and any window of the same length."""
    if not quote or not source:
        return 0.0
    first = quote.split()[0]
    positions = []
    index = source.find(first)
    while index != -1 and len(positions) < 200:
        positions.append(index)
        index = source.find(first, index + 1)
    best = 0.0
    for position in positions:
        for offset in range(-10, 3):
            start = max(0, position + offset)
            candidate = source[start:start + len(quote)]
            if not candidate:
                continue
            ratio = difflib.SequenceMatcher(None, quote, candidate).ratio()
            if ratio > best:
                best = ratio
                if best >= threshold:
                    return best
    return best


def is_grounded(source_quote: str, source_text: str, threshold: float = 0.85) -> bool:
    """Check that a quote really comes from the source material.

    A quote is accepted when it appears verbatim, when its words appear in the
    source in the same order and close together (small edits such as a dropped
    apostrophe are tolerated), or when it is close to a verbatim span.
    """
    if not source_quote or not source_text:
        return False
    if str(source_quote).strip() in str(source_text):
        return True

    quote = _normalize_for_match(source_quote)
    source = _normalize_for_match(source_text)
    if not quote or not source:
        return False
    if quote in source:
        return True

    quote_tokens = [token for token in quote.split() if len(token) >= 3]
    if quote_tokens:
        source_token_list = source.split()
        source_token_set = set(source_token_list)
        matched = sum(1 for token in quote_tokens if token in source_token_set)
        coverage = matched / len(quote_tokens)
        if coverage >= threshold and _tokens_appear_in_order(quote_tokens, source_token_list):
            return True

    return _fuzzy_ratio(quote, source, threshold) >= threshold


def classify_question(question: str) -> str:
    """Best-effort question-type label used for diversity and analytics."""
    text = str(question or '').casefold()
    if any(term in text for term in ('which term', 'defined as', 'definition of')):
        return 'definition'
    if any(term in text for term in ('calculate', 'how many', 'how much', 'numeric value')):
        return 'calculation'
    if any(term in text for term in ('code', 'function', 'variable', 'program', 'snippet', 'output of')):
        return 'code'
    if any(term in text for term in ('differ', 'difference', 'compare', 'contrast', 'whereas', 'unlike')):
        return 'comparison'
    if 'cause-and-effect' not in text and any(
        term in text for term in ('why ', 'because', 'cause', 'effect', 'result of', 'leads to', 'due to')
    ):
        return 'causal'
    if any(
        term in text
        for term in (
            'if ', 'scenario', 'a student', 'would', 'best explains', 'apply', 'application',
            'relationship', 'cause-and-effect',
        )
    ):
        return 'application'
    if any(term in text for term in ('what is', 'what are', 'which statement best describes')):
        return 'concept'
    if any(term in text for term in ('which', 'where', 'when', 'who', 'how')):
        return 'factual'
    return 'other'


def estimate_question_difficulty(question: str) -> str:
    """Rough cognitive-demand estimate, independent of word count alone."""
    text = str(question or '').strip()
    qtype = classify_question(text)
    words = re.findall(r"[A-Za-z0-9'\-]+", text)
    if 'fill in the blank' in text.casefold():
        return 'easy' if len(words) <= 22 else 'medium'
    clause_markers = len(re.findall(r'\b(?:and|but|while|whereas|because|therefore|then)\b', text, re.I))
    if qtype in ('application', 'comparison') or (qtype == 'calculation' and len(words) > 18):
        return 'hard'
    if qtype in ('causal', 'code') and (len(words) > 18 or clause_markers >= 1):
        return 'medium'
    if qtype == 'concept' and (clause_markers >= 2 or len(words) > 28):
        return 'hard'
    if qtype in ('definition', 'factual') and len(words) <= 24:
        return 'easy'
    return 'medium'


def _has_answer_leak(question: str, correct_option: str) -> bool:
    qn = normalize_question(question)
    an = normalize_option(correct_option)
    return len(an) >= 3 and an in qn


def _explanation_is_relevant(explanation: str, item: Dict[str, Any], correct_option: str) -> bool:
    explanation_words = _content_words(explanation)
    if not explanation_words:
        return False
    context = ' '.join(
        str(item.get(field, '') or '')
        for field in ('concept', 'question', 'source_quote')
    ) + ' ' + str(correct_option)
    return bool(explanation_words & _content_words(context))


def validate_mcq_item(
    item: Dict[str, Any],
    source_text: str,
    expected_difficulty: Optional[str] = None,
) -> Tuple[bool, str]:
    try:
        question = str(item.get('question', '') or '').strip()
        if len(question) < 10:
            return False, 'Question is missing or too short'
        if len(re.findall(r'[A-Za-z0-9]+', question)) < 3:
            return False, 'Question is too vague'
        if re.search(r'\b(select all|choose all|all that apply)\b', question, re.I):
            return False, 'Single-answer question cannot ask for multiple selections'

        options = item.get('options', [])
        if not isinstance(options, list) or len(options) != 4:
            return False, 'MCQ must have exactly 4 options'
        for opt in options:
            if not opt or not str(opt).strip():
                return False, 'Options cannot be empty'
        norm_opts = [normalize_option(o) for o in options]
        if any(not opt for opt in norm_opts):
            return False, 'Options cannot be empty'
        if len(set(norm_opts)) != 4:
            return False, 'Options must be distinct'
        for i, first in enumerate(norm_opts):
            for second in norm_opts[i + 1:]:
                if min(len(first), len(second)) >= 6:
                    ratio = difflib.SequenceMatcher(None, first, second).ratio()
                    if ratio >= 0.87:
                        return False, 'Options must be distinct'
                if min(len(first), len(second)) >= 5 and (
                    first in second or second in first
                ):
                    return False, 'Options must be distinct'
        for opt in norm_opts:
            if opt in BAD_OPTIONS or opt in ['a and b']:
                return False, 'Bad option pattern'

        ci = item.get('correct_index')
        if not isinstance(ci, int) or isinstance(ci, bool) or ci < 0 or ci > 3:
            return False, 'Invalid correct_index'
        correct_option = options[ci]
        if _has_answer_leak(question, correct_option):
            return False, 'Question reveals the correct answer'

        exp = str(item.get('explanation', '') or '').strip()
        if len(exp) < 10:
            return False, 'Explanation too short'
        if not _explanation_is_relevant(exp, item, correct_option):
            return False, 'Explanation is not relevant to the answer'

        if not str(item.get('concept', '') or '').strip():
            return False, 'Missing concept'
        difficulty = str(item.get('difficulty', '') or '').strip().lower()
        if not difficulty:
            return False, 'Missing difficulty'
        if difficulty not in DIFFICULTY_VALUES:
            return False, 'Invalid difficulty'
        if expected_difficulty:
            expected = str(expected_difficulty).strip().lower()
            if expected in DIFFICULTY_VALUES:
                if difficulty != expected:
                    return False, 'Difficulty does not match the requested level'
                estimated = estimate_question_difficulty(question)
                if expected == 'hard' and estimated == 'easy':
                    return False, 'Question is too easy for the requested level'
                if expected == 'easy' and estimated == 'hard':
                    return False, 'Question is too complex for the requested level'

        sq = str(item.get('source_quote', '') or '').strip()
        if len(sq) < 10:
            return False, 'Invalid source_quote'
        if not is_grounded(sq, source_text):
            return False, 'Ungrounded source_quote'
        return True, ''
    except Exception as e:
        return False, str(e)


def validate_flashcard_item(item: Dict[str, Any], source_text: str) -> Tuple[bool, str]:
    try:
        front = item.get('front', '')
        back = item.get('back', '')
        if not front or len(str(front).strip()) < 5:
            return False, 'Invalid front'
        if not back or len(str(back).strip()) < 1:
            return False, 'Invalid back'
        if not str(item.get('concept', '') or '').strip():
            return False, 'Missing concept'
        difficulty = str(item.get('difficulty', '') or '').strip().lower()
        if not difficulty:
            return False, 'Missing difficulty'
        if difficulty not in DIFFICULTY_VALUES:
            return False, 'Invalid difficulty'
        sq = item.get('source_quote', '')
        if not sq or len(str(sq).strip()) < 10:
            return False, 'Invalid source_quote'
        if not is_grounded(str(sq).strip(), source_text):
            return False, 'Ungrounded source_quote'
        return True, ''
    except Exception as e:
        return False, str(e)


def _text_similarity(first: str, second: str) -> float:
    a = normalize_question(first)
    b = normalize_question(second)
    if not a or not b:
        return 0.0
    sequence = difflib.SequenceMatcher(None, a, b).ratio()
    a_words = set(a.split())
    b_words = set(b.split())
    union = a_words | b_words
    jaccard = (len(a_words & b_words) / len(union)) if union else 0.0
    return max(sequence, jaccard)


def deduplicate_items(
    items: List[Dict[str, Any]],
    key_fn,
    threshold: float = 0.85,
) -> List[Dict[str, Any]]:
    kept = []
    for item in items:
        is_dup = False
        value = key_fn(item)
        for existing in kept:
            if _text_similarity(value, key_fn(existing)) > threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(item)
    return kept


def diversify_items(
    items: List[Dict[str, Any]],
    limit: int,
    type_fn=None,
) -> List[Dict[str, Any]]:
    """Round-robin questions by type so a set is not all one format."""
    if limit <= 0:
        return []
    get_type = type_fn or (lambda item: item.get('question_type') or classify_question(item.get('question', '')))
    buckets: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for item in items:
        buckets.setdefault(get_type(item), []).append(item)
    ordered: List[Dict[str, Any]] = []
    while len(ordered) < limit and any(buckets.values()):
        for key in list(buckets.keys()):
            if buckets[key] and len(ordered) < limit:
                ordered.append(buckets[key].pop(0))
            if not buckets[key]:
                buckets.pop(key, None)
    return ordered
