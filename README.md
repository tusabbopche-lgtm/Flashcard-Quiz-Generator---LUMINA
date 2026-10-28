# Flashcard & Quiz Generator

Turn study material (pasted text, `.txt`, `.pdf` or `.docx`) into flashcards and
multiple-choice questions, study them in a flip-card deck, then test yourself
with a timed quiz that is scored and reviewed question by question.

The app works fully offline with a built-in rule-based engine. If you point it
at an OpenAI-compatible endpoint (Ollama, LM Studio, vLLM, OpenAI, ...) it
switches to LLM-backed generation with grounding checks, de-duplication and
automatic top-up.

## Features

- **Material input** - paste text, upload a file (TXT / PDF / DOCX, max 5 MB) or
  load one of the bundled samples.
- **Two engines** - offline rule-based extraction (no network) or an
  OpenAI-compatible model, selected through `.env`.
- **Grounded generation** - every generated item keeps a verbatim source quote;
  items that cannot be traced back to the material are discarded.
- **Flashcard deck** - flip cards, move forward and back, shuffle, mark cards as
  *known* or *needs practice*, and browse the whole deck.
- **Quiz** - choose the number of questions, difficulty filter, exam or
  practice mode, optional time limit, shuffled options.
- **Scoring** - percentage plus a band (`Excellent`, `Good`, `Satisfactory`,
  `Needs Improvement`, `Needs Significant Revision`) and a per-question review
  with the correct answer, explanation and source quote.
- **Library** - study sets are stored as JSON in `data/study_sets/` and can be
  reopened, downloaded or deleted.

## Requirements

- Python 3.10+
- The packages in `requirements.txt`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

## Run

```bash
streamlit run app.py
```

The app opens on <http://localhost:8501>.

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable        | Purpose                                                        |
| --------------- | -------------------------------------------------------------- |
| `LLM_PROVIDER`  | `offline` (default) or `openai_compatible`                      |
| `LLM_BASE_URL`  | Base URL of the chat-completions endpoint                       |
| `LLM_API_KEY`   | Bearer token, if the endpoint needs one                         |
| `LLM_MODEL`     | Model name passed to the endpoint                               |
| `APP_SEED`      | Optional seed that makes the offline engine reproducible        |

A local endpoint (`localhost` / `127.0.0.1`) is used without an API key, so
Ollama works out of the box:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1
```

## Tests

```bash
pytest
```

The suite covers the offline generator, the LLM client (with a stubbed HTTP
layer), grounding and item validation, preprocessing, text extraction, quiz
scoring and engine, storage, the models and a full Streamlit flow test that
generates a study set and plays a complete quiz.

## Project layout

```
app.py                 Streamlit entry point
ai/
  generator.py         chunk -> generate -> validate -> dedupe -> top up
  llm_client.py        OpenAI-compatible chat-completions client
  prompts.py           system, generation and top-up prompts
  rule_based.py        offline extraction engine
core/
  config.py            limits, paths and engine selection
  flashcard_session.py deck navigation and card status
  models.py            pydantic domain models
  pipeline.py          raw text -> validated StudySet
  preprocessing.py     text normalisation and chunking
  quiz_engine.py       quiz attempt construction
  scoring.py           score and band calculation
  storage.py           JSON persistence for study sets
  text_extraction.py   TXT / PDF / DOCX extraction
  validation.py        grounding, item validation and de-duplication
  validators.py        input, topic and upload validation
ui/state.py            session state helpers
views/                 home, flashcards, quiz, results and library pages
data/samples/          bundled sample material
data/study_sets/       saved study sets (created on demand)
```
