from core import validation, validators


SOURCE = (
    'Mitochondria are often referred to as the powerhouse of the cell because they generate '
    'most of the cell\'s supply of adenosine triphosphate (ATP), used as a source of chemical energy. '
    'Mitochondria have their own DNA and are believed to have evolved from ancient bacteria. '
    'Ribosomes are responsible for protein synthesis. '
    'Enzymes are biological catalysts that speed up chemical reactions without being consumed in the process.'
)


def valid_mcq(**overrides):
    item = {
        'question': 'Which organelle produces ATP for the cell?',
        'options': ['Mitochondria', 'Ribosomes', 'Enzymes', 'Nucleus'],
        'correct_index': 0,
        'explanation': 'Mitochondria generate most of the cell ATP supply.',
        'concept': 'Mitochondria',
        'difficulty': 'medium',
        'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
    }
    item.update(overrides)
    return item


def valid_flashcard(**overrides):
    item = {
        'front': 'What is the powerhouse of the cell?',
        'back': 'Mitochondria',
        'explanation': 'Described in the material.',
        'concept': 'Mitochondria',
        'difficulty': 'easy',
        'source_quote': 'Mitochondria are often referred to as the powerhouse of the cell',
    }
    item.update(overrides)
    return item


def test_validate_input_text():
    assert validators.validate_input_text('x' * 400)[0] is True
    assert validators.validate_input_text('too short')[0] is False
    assert validators.validate_input_text('')[0] is False
    assert validators.validate_input_text('x' * 60000)[0] is False


def test_validate_topic():
    assert validators.validate_topic('Biology')[0] is True
    assert validators.validate_topic('  ')[0] is False
    assert validators.validate_topic('x' * 200)[0] is False


def test_validate_upload_signature_mismatch():
    ok, reason = validators.validate_upload('notes.pdf', b'not a pdf')
    assert ok is False
    assert 'PDF' in reason
    ok, reason = validators.validate_upload('notes.docx', b'not a docx')
    assert ok is False
    assert 'DOCX' in reason
    ok, reason = validators.validate_upload('notes.exe', b'MZ')
    assert ok is False


def test_validate_upload_size_limit():
    ok, reason = validators.validate_upload('notes.txt', b'x' * 100, max_bytes=10)
    assert ok is False
    assert 'large' in reason


def test_is_grounded_accepts_verbatim_quote():
    assert validation.is_grounded('Mitochondria are often referred to', SOURCE) is True


def test_is_grounded_tolerates_small_edits():
    # A dropped apostrophe must not disqualify an otherwise verbatim quote.
    quote = "they generate most of the cell's supply of adenosine triphosphate"
    assert validation.is_grounded(quote, SOURCE) is True


def test_is_grounded_accepts_near_verbatim_quote():
    quote = 'Enzymes are biological catalysts that speed up chemical reactions without being consumed'
    assert validation.is_grounded(quote, SOURCE) is True


def test_is_grounded_rejects_invented_quote():
    assert validation.is_grounded('The heart pumps blood through arteries', SOURCE) is False


def test_is_grounded_rejects_quote_with_wrong_words():
    assert (
        validation.is_grounded('Photosynthesis occurs inside the nucleus of every living plant cell', SOURCE)
        is False
    )


def test_validate_mcq_item_accepts_valid_item():
    ok, reason = validation.validate_mcq_item(valid_mcq(), SOURCE)
    assert ok is True, reason


def test_validate_mcq_item_rejects_duplicate_options():
    item = valid_mcq(options=['Mitochondria', 'mitochondria', 'Enzymes', 'Nucleus'])
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False
    assert 'distinct' in reason


def test_validate_mcq_item_rejects_three_options():
    ok, reason = validation.validate_mcq_item(valid_mcq(options=['a', 'b', 'c']), SOURCE)
    assert ok is False
    assert '4 options' in reason


def test_validate_mcq_item_rejects_bad_option_phrase():
    item = valid_mcq(options=['Mitochondria', 'All of the above', 'Enzymes', 'Nucleus'])
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False


def test_validate_mcq_item_rejects_ungrounded_quote():
    item = valid_mcq(source_quote='The heart pumps blood through the arteries')
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False
    assert 'Ungrounded' in reason


def test_validate_mcq_item_rejects_short_explanation():
    ok, reason = validation.validate_mcq_item(valid_mcq(explanation='short'), SOURCE)
    assert ok is False
    assert 'Explanation' in reason


def test_validate_flashcard_item():
    ok, reason = validation.validate_flashcard_item(valid_flashcard(), SOURCE)
    assert ok is True, reason
    ok, reason = validation.validate_flashcard_item(valid_flashcard(front='ab'), SOURCE)
    assert ok is False


def test_deduplicate_items_removes_similar_questions():
    items = [
        valid_mcq(),
        valid_mcq(question='Which organelle produces ATP for the cell ?'),
        valid_mcq(question='Which organelle builds proteins in the cell?'),
    ]
    kept = validation.deduplicate_items(items, lambda item: item['question'], threshold=0.85)
    assert len(kept) == 2


def test_normalize_question_strips_punctuation():
    assert validation.normalize_question('  What is ATP?  ') == 'what is atp'


def test_validate_mcq_rejects_answer_in_the_stem():
    item = valid_mcq(question='Which organelle, Mitochondria, produces ATP for the cell?')
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False
    assert 'reveals' in reason


def test_validate_mcq_rejects_near_duplicate_options():
    item = valid_mcq(options=['Mitochondria', 'Mitochondrion', 'Enzymes', 'Nucleus'])
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False
    assert 'distinct' in reason


def test_validate_mcq_rejects_irrelevant_explanation():
    item = valid_mcq(explanation='Bananas grow in tropical climates during summer.')
    ok, reason = validation.validate_mcq_item(item, SOURCE)
    assert ok is False
    assert 'Explanation' in reason


def test_validate_mcq_rejects_difficulty_mismatch():
    item = valid_mcq(question='Which organelle produces ATP for the cell?', difficulty='hard')
    ok, reason = validation.validate_mcq_item(item, SOURCE, expected_difficulty='hard')
    assert ok is False
    assert 'too easy' in reason


def test_fill_in_the_blank_is_estimated_as_easy():
    assert validation.estimate_question_difficulty('Fill in the blank: _____ are the basic units of life.') == 'easy'


def test_diversify_items_round_robins_question_types():
    items = [
        {'question': 'Fact one', 'question_type': 'factual'},
        {'question': 'Fact two', 'question_type': 'factual'},
        {'question': 'Why one', 'question_type': 'causal'},
        {'question': 'Compare one', 'question_type': 'comparison'},
    ]
    result = validation.diversify_items(items, 3, type_fn=lambda item: item['question_type'])
    assert [item['question_type'] for item in result] == ['factual', 'causal', 'comparison']
