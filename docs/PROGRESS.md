# Progress log

## Status

Feature complete. The Streamlit app runs end to end: material -> study set ->
flashcard deck -> quiz -> scored results -> saved library.

## Completed

- `core/config.py` - limits, paths, engine selection (offline / OpenAI-compatible)
- `core/models.py` - pydantic models for flashcards, MCQs, study sets and attempts
- `core/scoring.py` - score calculation and performance bands
- `core/preprocessing.py` - text normalisation and chunking
- `core/text_extraction.py` - TXT / PDF / DOCX extraction with signature checks
- `core/validation.py` - grounding checks, item validation, de-duplication
- `core/validators.py` - input, topic and upload validation
- `core/flashcard_session.py` - deck navigation, shuffle and card status
- `core/quiz_engine.py` - quiz attempt construction with shuffling
- `core/pipeline.py` - raw text -> validated `StudySet`
- `core/storage.py` - JSON persistence in `data/study_sets/`
- `ai/prompts.py` - system, generation, repair and top-up prompts
- `ai/rule_based.py` - offline extraction engine (definitions, cloze cards, MCQs)
- `ai/llm_client.py` - OpenAI-compatible client with JSON repair
- `ai/generator.py` - chunk, generate, validate, de-duplicate and top up
- `ui/state.py` - session state helpers and navigation handling
- `views/` - home, flashcards, quiz, results and library pages
- `app.py` - Streamlit entry point
- `tests/` - 98 tests, including a full app flow test

## Fixes made in this session

- `tests/test_rule_based.py` raised `FileNotFoundError` because the sample path
  was relative to the working directory; it now resolves from `__file__`.
- The project had no `pytest.ini`, so pytest picked up a global config from the
  home directory and the project root was never added to `sys.path`. Added
  `pytest.ini` (`pythonpath = .`, `testpaths = tests`) and a `conftest.py`.
- `core/validation.py::is_grounded` only accepted verbatim quotes: the fuzzy
  window was longer than the quote, so the similarity ratio could never reach
  the threshold. Replaced with a normalisation + token-order check plus a
  bounded fuzzy fallback.
- `ai/rule_based.py` produced weak distractors (`while`, `which`) and terms such
  as `DNA and`; term and distractor selection were rewritten.
- `core/config.py` resolved `data/` against the working directory; paths are
  now anchored to the project root.
- `views/*` used the deprecated `use_container_width` argument; switched to
  `width='stretch'`.

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```
