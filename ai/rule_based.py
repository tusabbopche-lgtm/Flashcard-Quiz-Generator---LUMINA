"""Deterministic, source-grounded fallback generation.

The offline engine deliberately favours a smaller number of well-grounded,
varied questions over filling a quota with arbitrary cloze deletions. All
question and answer text is taken from the supplied material.
"""

import random
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

STOP_WORDS = set(
    [
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'do', 'does', 'did',
        'will', 'can', 'could', 'should', 'may', 'might', 'this', 'that', 'these', 'those', 'as',
        'from', 'into', 'about', 'than', 'so', 'not', 'while', 'which', 'where', 'when', 'because',
        'although', 'though', 'however', 'therefore', 'thus', 'hence', 'they', 'them', 'their',
        'there', 'its', 'his', 'her', 'our', 'your', 'my', 'it', 'been', 'being', 'also', 'more',
        'most', 'some', 'such', 'other', 'others', 'one', 'two', 'three', 'each', 'every', 'any',
        'all', 'both', 'few', 'many', 'much', 'very', 'too', 'only', 'just', 'even', 'still',
        'again', 'further', 'once', 'here', 'same', 'different', 'own', 'new', 'old', 'first',
        'last', 'next', 'now', 'then', 'over', 'under', 'after', 'before', 'during', 'between',
        'through', 'within', 'without', 'against', 'among', 'per', 'via', 'upon', 'whose', 'whom',
        'what', 'how', 'why', 'whether', 'either', 'neither', 'etc', 'using', 'used', 'use',
    ]
)

TERM_LEAD_STOP = set(
    [
        'all', 'the', 'a', 'an', 'in', 'it', 'this', 'these', 'those', 'they', 'we', 'when', 'while',
        'after', 'before', 'if', 'each', 'every', 'most', 'many', 'some', 'other', 'such', 'there',
        'their', 'its', 'one', 'two', 'both', 'during', 'because', 'although', 'however', 'as', 'by',
        'for', 'from', 'with', 'within', 'without', 'under', 'over', 'between', 'through', 'since',
        'until', 'unlike', 'once', 'often', 'usually', 'now', 'then', 'thus', 'cells', 'living',
        'organisms', 'process', 'study', 'can', 'will', 'may', 'must', 'should', 'according',
        'based', 'given', 'material', 'statement', 'following', 'which', 'what', 'why', 'how',
    ]
)

DIFFICULTY_MAP = {'easy': 'easy', 'medium': 'medium', 'hard': 'hard'}


def _tokenize(text: str) -> List[str]:
    return re.findall(r'[A-Za-z]+', str(text or ''))


def _is_content_word(token: str) -> bool:
    return len(token) > 3 and token.lower() not in STOP_WORDS


def _clean_term(term: str) -> str:
    term = re.sub(r'\s+', ' ', str(term or '')).strip(' .,;:()[]"“”')
    if not term or len(term) > 60:
        return ''
    words = term.lower().split()
    if not words or words[0] in TERM_LEAD_STOP:
        return ''
    if len(words) > 4:
        return ''
    if any(word in STOP_WORDS for word in words[1:]):
        return ''
    return term


def _clean_fragment(text: str, limit: int = 220) -> str:
    text = re.sub(r'\s+', ' ', str(text or '')).strip(' .,;:')
    if len(text) > limit:
        text = text[: max(1, limit - 1)].rstrip(' ,;:') + '…'
    return text


def _difficulty_for(requested: str, fallback: str = 'medium') -> str:
    key = str(requested or '').strip().lower()
    if key in DIFFICULTY_MAP:
        return DIFFICULTY_MAP[key]
    if key.startswith('e'):
        return 'easy'
    if key.startswith('h'):
        return 'hard'
    return fallback


def _split_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', str(text or ''))
    return [s.strip() for s in sentences if len(s.strip()) >= 20]


def _find_definitions(text: str) -> List[Dict[str, str]]:
    patterns = [
        r'([A-Z][A-Za-z]+(?:[ -][A-Za-z]+){0,3})\s+is\s+(?:defined as\s+|called\s+|known as\s+|referred to as\s+|the\s+)?([^.;]{8,240})[.;]',
        r'([A-Z][A-Za-z]+(?:[ -][A-Za-z]+){0,3})\s+are\s+(?:defined as\s+|called\s+|known as\s+|referred to as\s+|the\s+)?([^.;]{8,240})[.;]',
        r'([A-Z][A-Za-z]+(?:[ -][A-Za-z]+){0,3})\s+refers to\s+([^.;]{8,240})[.;]',
        r'([A-Z][A-Za-z]+(?:[ -][A-Za-z]+){0,3})\s+means\s+([^.;]{8,240})[.;]',
    ]
    found: List[Dict[str, str]] = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            term = _clean_term(match.group(1))
            definition = _clean_fragment(match.group(2))
            quote = re.sub(r'\s+', ' ', match.group(0)).strip()
            if not term or len(definition) < 8:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            found.append({'term': term, 'definition': definition, 'quote': quote[:240]})
    return found


def _collect_terms(sentences: List[str]) -> Tuple[Counter, Counter]:
    counts: Counter = Counter()
    proper: Counter = Counter()
    for sentence in sentences:
        for token in _tokenize(sentence):
            if not _is_content_word(token):
                continue
            counts[token] += 1
            if token[0].isupper():
                proper[token] += 1
    return counts, proper


def _term_pool(counts: Counter, proper: Counter, definitions: List[Dict[str, str]]) -> List[str]:
    ordered: List[str] = []
    for item in definitions:
        term = _clean_term(item['term'])
        if term and term.casefold() not in {t.casefold() for t in ordered}:
            ordered.append(term)
    for source in (proper, counts):
        for term, _count in source.most_common():
            clean = _clean_term(term)
            if clean and clean.casefold() not in {t.casefold() for t in ordered}:
                ordered.append(clean)
    return ordered


def _normalise_option(text: str) -> str:
    text = str(text or '').casefold()
    text = re.sub(r'[^\w\s]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _unique_options(correct: str, pool: List[str], limit: int = 3) -> Optional[List[str]]:
    options = [correct]
    seen = {_normalise_option(correct)}
    for candidate in pool:
        candidate = _clean_fragment(candidate, 180)
        if not candidate:
            continue
        key = _normalise_option(candidate)
        if not key or key in seen:
            continue
        if any(
            min(len(key), len(existing)) >= 5 and (key in existing or existing in key)
            for existing in seen
        ):
            continue
        seen.add(key)
        options.append(candidate)
        if len(options) == limit + 1:
            break
    if len(options) != limit + 1:
        return None
    return options


def _pick_distractors(
    rng: random.Random,
    correct: str,
    counts: Counter,
    proper: Counter,
    limit: int = 3,
) -> List[str]:
    correct_len = len(correct)
    pools = [
        [term for term, count in proper.most_common() if term.casefold() != correct.casefold() and count >= 1],
        [term for term, count in counts.most_common() if term.casefold() != correct.casefold() and count >= 2],
        [term for term, count in counts.most_common() if term.casefold() != correct.casefold()],
    ]
    chosen: List[str] = []
    for pool in pools:
        for term in pool:
            if len(chosen) >= limit:
                break
            low = term.casefold()
            if low == correct.casefold() or any(low == c.casefold() for c in chosen):
                continue
            if low in correct.casefold() or correct.casefold() in low:
                continue
            if chosen and abs(len(term) - correct_len) > max(4, correct_len):
                continue
            chosen.append(term)
        if len(chosen) >= limit:
            break
    rng.shuffle(chosen)
    return chosen[:limit]


def _blank_out(sentence: str, term: str) -> str:
    pattern = r'\b' + re.escape(term) + r'\b'
    return re.sub(pattern, '_____', sentence, count=1)


def _comparison_parts(sentence: str) -> Optional[Tuple[str, str, str, str]]:
    match = re.search(r'^(.*?),\s+(?:while|whereas)\s+(.*)$', sentence, re.I)
    if not match:
        return None
    left, right = match.group(1).strip(), match.group(2).strip()

    def first_term(fragment: str) -> Optional[str]:
        proper = re.findall(r'\b[A-Z][A-Za-z]{2,}\b', fragment)
        if proper:
            return proper[0]
        content = [token for token in _tokenize(fragment) if _is_content_word(token)]
        return content[0] if content else None

    left_term = first_term(left)
    right_term = first_term(right)
    if not left_term or not right_term:
        return None
    return left, right, left_term, right_term


def _causal_parts(sentence: str) -> Optional[Tuple[str, str]]:
    match = re.search(r'^(.*?)\s+(?:because|since)\s+(.*)$', sentence, re.I)
    if not match:
        return None
    effect, cause = match.group(1).strip(), match.group(2).strip()
    if len(effect) < 15 or len(cause) < 10:
        return None
    return effect, cause


def _sentence_terms(sentence: str, terms: List[str]) -> List[str]:
    found = []
    lowered = sentence.casefold()
    for term in terms:
        if term.casefold() in lowered and all(term.casefold() != f.casefold() for f in found):
            found.append(term)
    return found


def _make_mcq(
    question: str,
    correct: str,
    distractor_pool: List[str],
    sentence: str,
    concept: str,
    difficulty: str,
    question_type: str,
    rng: random.Random,
    explanation: str,
) -> Optional[Dict[str, Any]]:
    options = _unique_options(correct, distractor_pool)
    if not options:
        return None
    options = [_clean_fragment(option, 180) for option in options]
    if len({_normalise_option(option) for option in options}) != 4:
        return None
    correct = _clean_fragment(correct, 180)
    if correct not in options:
        return None
    rng.shuffle(options)
    return {
        'question': _clean_fragment(question, 400),
        'options': options,
        'correct_index': options.index(correct),
        'explanation': _clean_fragment(explanation, 600),
        'concept': _clean_fragment(concept, 60) or 'concept',
        'difficulty': difficulty,
        'source_quote': _clean_fragment(sentence, 300),
        'question_type': question_type,
    }


def generate_offline(
    text: str,
    n_cards: int = 10,
    n_mcqs: int = 10,
    difficulty: str = 'Medium',
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    sentences = _split_sentences(text)
    if not sentences:
        return {'key_concepts': [], 'flashcards': [], 'mcqs': []}

    requested = _difficulty_for(difficulty, 'medium')
    counts, proper = _collect_terms(sentences)
    definitions = _find_definitions(text)
    terms = _term_pool(counts, proper, definitions)
    definitions = definitions[:15]
    relationship_terms = [item['term'] for item in definitions]
    for term, _count in proper.most_common():
        clean = _clean_term(term)
        if clean and clean.casefold() not in {value.casefold() for value in relationship_terms}:
            relationship_terms.append(clean)
    notion_quotes = [item['quote'] for item in definitions]
    statement_pool = notion_quotes + sentences + [_causal_parts(s)[1] for s in sentences if _causal_parts(s)]

    cards: List[Tuple[int, Dict[str, Any]]] = []
    questions: List[Tuple[int, Dict[str, Any]]] = []
    key_concepts: List[Dict[str, str]] = []
    seen_cards = set()
    seen_questions = set()

    def add_card(priority: int, front: str, back: str, explanation: str, concept: str, quote: str) -> None:
        key = _normalise_option(front)
        if not key or key in seen_cards or len(front) < 5 or not back:
            return
        seen_cards.add(key)
        cards.append(
            (
                priority,
                {
                    'front': _clean_fragment(front, 300),
                    'back': _clean_fragment(back, 600),
                    'explanation': _clean_fragment(explanation, 600),
                    'concept': _clean_fragment(concept, 60) or 'concept',
                    'difficulty': requested,
                    'source_quote': _clean_fragment(quote, 300),
                },
            )
        )

    def add_question(priority: int, item: Optional[Dict[str, Any]]) -> None:
        if not item:
            return
        key = _normalise_option(item['question'])
        if not key or key in seen_questions or len(key) < 8:
            return
        seen_questions.add(key)
        questions.append((priority, item))

    # Definitions make the strongest cards and questions.
    for item in definitions:
        term = item['term']
        definition = item['definition']
        quote = item['quote']
        key_concepts.append({'term': _clean_fragment(term, 120), 'definition': _clean_fragment(definition, 200)})
        if requested == 'hard':
            front = f'How would you apply the concept of {term} in a new situation?'
            priority = 1
        elif requested == 'medium':
            front = f'What does the material say about {term}?'
            priority = 0
        else:
            front = f'What is {term}?'
            priority = 0
        add_card(priority, front, definition, f'{term}: {definition}', term, quote)

    # Comparison cards.
    comparisons = [sentence for sentence in sentences if _comparison_parts(sentence)]
    for sentence in comparisons:
        parts = _comparison_parts(sentence)
        if not parts:
            continue
        _left, _right, left_term, right_term = parts
        if requested != 'easy':
            add_card(
                0,
                f'What is the difference between {left_term} and {right_term}?',
                sentence,
                f'The material contrasts {left_term} and {right_term}.',
                f'{left_term} vs {right_term}',
                sentence,
            )

    # Causal cards.
    causals = []
    for sentence in sentences:
        parts = _causal_parts(sentence)
        if not parts:
            continue
        effect, cause = parts
        causals.append((sentence, effect, cause))
        if requested != 'easy':
            add_card(
                0,
                f'Why {effect[0].lower() + effect[1:]}?',
                cause,
                f'The material gives this reason: {cause}',
                effect.split()[0] if effect.split() else 'cause',
                sentence,
            )

    # Sentence-based recall cards and cloze questions.
    rng.shuffle(sentences)
    for sentence in sentences:
        tokens = [token for token in _tokenize(sentence) if _is_content_word(token)]
        if not tokens:
            continue
        key_term = None
        for token in tokens:
            if token[0].isupper() and proper.get(token, 0) >= 1 and sentence.count(token) == 1:
                key_term = token
                break
        if not key_term:
            key_term = max(tokens, key=len)
        if not key_term or key_term.casefold() not in sentence.casefold():
            continue
        add_card(
            1 if requested in ('medium', 'hard') else 0,
            f'What does the material state about {key_term}?',
            sentence,
            f'Source statement: {sentence}',
            key_term,
            sentence,
        )

        concept_terms = _sentence_terms(sentence, relationship_terms)
        if requested != 'easy' and concept_terms:
            concept_term = concept_terms[0]
            add_question(
                0,
                _make_mcq(
                    f'Which statement best describes {concept_term} in the material?',
                    sentence,
                    [candidate for candidate in sentences if candidate != sentence] + notion_quotes,
                    sentence,
                    concept_term,
                    requested,
                    'concept',
                    rng,
                    f'The material states: {sentence}',
                ),
            )

        word_count = len(re.findall(r"[A-Za-z0-9'\-]+", sentence))
        if requested == 'easy' and (
            word_count > 18 or re.search(r'\b(?:because|while|whereas|therefore)\b', sentence, re.I)
        ):
            continue
        if requested == 'medium':
            continue

        front = _blank_out(sentence, key_term)
        if front == sentence:
            continue
        if '?' not in front:
            front = f'Fill in the blank: {front}'
        distractors = _pick_distractors(rng, key_term, counts, proper)
        if len(distractors) < 3:
            continue
        options = _unique_options(key_term, distractors)
        if not options:
            continue
        rng.shuffle(options)
        add_question(
            1 if requested == 'hard' else 0,
            {
                'question': _clean_fragment(front, 400),
                'options': [_clean_fragment(option, 180) for option in options],
                'correct_index': options.index(key_term),
                'explanation': f'{key_term} completes the statement from the material.',
                'concept': _clean_fragment(key_term, 60),
                'difficulty': requested,
                'source_quote': _clean_fragment(sentence, 300),
                'question_type': 'factual',
            },
        )

    # Meaning-focused multiple choice questions from definitions.
    term_options = [item['term'] for item in definitions]
    definition_options = [item['definition'] for item in definitions]
    for item in definitions:
        term, definition, quote = item['term'], item['definition'], item['quote']
        if requested in ('medium', 'hard'):
            question = f'Which statement best describes {term}?'
            qtype = 'concept'
            priority = 0
        else:
            question = f'Which term is best defined as “{definition}”?'
            qtype = 'definition'
            priority = 1
        add_question(
            priority,
            _make_mcq(
                question,
                definition,
                [d for d in definition_options if _normalise_option(d) != _normalise_option(definition)]
                + statement_pool,
                quote,
                term,
                requested,
                qtype,
                rng,
                f'{term} is described in the material as: {definition}',
            ),
        )

        if requested == 'easy':
            add_question(
                1,
                _make_mcq(
                    f'Which term matches this description: “{definition}”?',
                    term,
                    [t for t in term_options if _normalise_option(t) != _normalise_option(term)]
                    + [t for t in terms if _normalise_option(t) != _normalise_option(term)],
                    quote,
                    term,
                    requested,
                    'definition',
                    rng,
                    f'The material defines {term} as: {definition}',
                ),
            )

        if requested == 'hard':
            add_question(
                0,
                _make_mcq(
                    f'Which statement best explains the role of {term} in this material?',
                    definition,
                    [d for d in definition_options if _normalise_option(d) != _normalise_option(definition)]
                    + statement_pool,
                    quote,
                    term,
                    requested,
                    'application',
                    rng,
                    f'The source explains that {term} is {definition}',
                ),
            )

    # Cause-and-effect questions.
    cause_pool = [cause for _sentence, _effect, cause in causals]
    for sentence, effect, cause in causals:
        if requested == 'easy':
            continue
        causal_question = (
            f'Which statement best explains the cause-and-effect relationship in “{effect}”?'
            if requested == 'hard'
            else f'Which statement best explains why {effect[0].lower() + effect[1:]}?'
        )
        add_question(
            0,
            _make_mcq(
                causal_question,
                cause,
                [c for c in cause_pool if _normalise_option(c) != _normalise_option(cause)]
                + statement_pool,
                sentence,
                effect.split()[0] if effect.split() else 'cause',
                requested,
                'causal',
                rng,
                f'The material explains this by stating: {cause}',
            ),
        )

    # Comparison questions.
    for sentence in comparisons:
        if requested == 'easy':
            break
        parts = _comparison_parts(sentence)
        if not parts:
            continue
        _left, _right, left_term, right_term = parts
        add_question(
            0,
            _make_mcq(
                f'Which statement best describes the difference between {left_term} and {right_term}?',
                sentence,
                [s for s in sentences if _normalise_option(s) != _normalise_option(sentence)],
                sentence,
                f'{left_term} vs {right_term}',
                requested,
                'comparison',
                rng,
                f'The material compares {left_term} and {right_term} in this statement.',
            ),
        )

    # Harder relationship questions that require connecting two ideas.
    if requested == 'hard':
        for sentence in sentences:
            matched = _sentence_terms(sentence, relationship_terms)
            if len(matched) < 2:
                continue
            first, second = matched[0], matched[1]
            add_question(
                0,
                _make_mcq(
                    f'Which statement best explains the relationship between {first} and {second}?',
                    sentence,
                    [s for s in sentences if _normalise_option(s) != _normalise_option(sentence)],
                    sentence,
                    f'{first} and {second}',
                    requested,
                    'application',
                    rng,
                    f'The material connects {first} and {second} in this statement.',
                ),
            )

    # If the requested difficulty produced too few items, fill with the best
    # remaining source-grounded questions rather than returning an empty set.
    questions.sort(key=lambda pair: pair[0])
    cards.sort(key=lambda pair: pair[0])

    unique_questions = []
    for _priority, item in questions:
        unique_questions.append(item)
        if len(unique_questions) >= n_mcqs:
            break
    unique_cards = []
    for _priority, item in cards:
        unique_cards.append(item)
        if len(unique_cards) >= n_cards:
            break

    return {
        'key_concepts': key_concepts[:15],
        'flashcards': unique_cards,
        'mcqs': unique_questions,
    }
