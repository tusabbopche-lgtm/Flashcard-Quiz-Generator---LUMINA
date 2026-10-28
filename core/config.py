import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MIN_TEXT_CHARS = 300
MAX_TEXT_CHARS = 50000
WARN_TEXT_CHARS = 40000
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MIN_CARDS = 5
MAX_CARDS = 30
DEFAULT_CARDS = 10
MIN_MCQ = 5
MAX_MCQ = 30
DEFAULT_MCQ = 10
MAX_CHUNK_SIZE = 6000
CHUNK_OVERLAP = 300

DATA_DIR = PROJECT_ROOT / 'data'
SAMPLES_DIR = DATA_DIR / 'samples'
STUDY_SETS_DIR = DATA_DIR / 'study_sets'
STUDY_SETS_DIR.mkdir(parents=True, exist_ok=True)


def get_llm_settings():
    """Read the LLM settings from the environment at call time."""
    return {
        'provider': (os.getenv('LLM_PROVIDER', '') or '').strip().lower() or None,
        'base_url': (os.getenv('LLM_BASE_URL', '') or '').strip() or None,
        'api_key': (os.getenv('LLM_API_KEY', '') or '').strip() or None,
        'model': (os.getenv('LLM_MODEL', '') or '').strip() or None,
    }


def get_active_engine():
    """Describe the engine that will be used for generation."""
    settings = get_llm_settings()
    provider = settings['provider']
    base_url = settings['base_url']
    api_key = settings['api_key']
    model = settings['model']

    if provider == 'openai_compatible':
        if base_url and ('localhost' in base_url or '127.0.0.1' in base_url):
            return {
                'provider': 'openai_compatible',
                'model': model or 'local',
                'offline': False,
                'local': True,
            }
        if api_key:
            return {
                'provider': 'openai_compatible',
                'model': model or 'gpt-3.5-turbo',
                'offline': False,
                'local': False,
            }
    return {'provider': 'offline', 'model': 'rule-based', 'offline': True}


def get_seed():
    """Deterministic seed for the offline engine, when configured."""
    raw = os.getenv('APP_SEED', '') or ''
    if not raw.strip():
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
