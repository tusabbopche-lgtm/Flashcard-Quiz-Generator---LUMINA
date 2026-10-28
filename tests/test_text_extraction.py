from pathlib import Path

import pytest

from core.text_extraction import ExtractionError, extract_text_from_file

SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'samples'


def test_extract_plain_text_utf8():
    content = 'Cells are the basic units of life.'.encode('utf-8')
    assert 'Cells' in extract_text_from_file('notes.txt', content)


def test_extract_plain_text_cp1252_fallback():
    content = 'Caf\xe9 notes about cells'.encode('cp1252')
    text = extract_text_from_file('notes.txt', content)
    assert 'Caf' in text


def test_extract_docx_sample():
    content = (SAMPLES_DIR / 'sample.docx').read_bytes()
    text = extract_text_from_file('sample.docx', content)
    assert 'Mitochondria' in text
    assert 'Powerhouse of the cell' in text


def test_extract_docx_rejects_bad_signature():
    with pytest.raises(ExtractionError):
        extract_text_from_file('notes.docx', b'not a zip file')


def test_extract_pdf_without_text_raises():
    content = (SAMPLES_DIR / 'sample.pdf').read_bytes()
    with pytest.raises(ExtractionError):
        extract_text_from_file('sample.pdf', content)


def test_extract_pdf_rejects_bad_signature():
    with pytest.raises(ExtractionError):
        extract_text_from_file('notes.pdf', b'not a pdf')


def test_unsupported_file_type():
    with pytest.raises(ExtractionError):
        extract_text_from_file('notes.pptx', b'binary')
