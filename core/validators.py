from typing import Tuple


class ValidationError(Exception):
    pass


def validate_input_text(text: str, min_chars: int = 300, max_chars: int = 50000) -> Tuple[bool, str]:
    if not text or not text.strip():
        return False, "Text is empty"
    length = len(text.strip())
    if length < min_chars:
        return False, f"Text too short (min {min_chars} chars)"
    if length > max_chars:
        return False, f"Text too long (max {max_chars} chars)"
    return True, ""


def validate_topic(topic: str) -> Tuple[bool, str]:
    if not topic or not topic.strip():
        return False, "Topic is required"
    if len(topic.strip()) > 100:
        return False, "Topic too long (max 100 chars)"
    return True, ""


def validate_upload(filename: str, content: bytes, max_bytes: int = 5 * 1024 * 1024) -> Tuple[bool, str]:
    if len(content) > max_bytes:
        return False, "File too large (max 5 MB)"
    name_lower = filename.lower()
    if name_lower.endswith(('.txt', '.pdf', '.docx')):
        # Check content signature
        if name_lower.endswith('.pdf') and not content.startswith(b'%PDF'):
            return False, "File content doesn't match PDF signature"
        if name_lower.endswith('.docx') and not content.startswith(b'PK'):
            return False, "File content doesn't match DOCX signature"
        return True, ""
    return False, "Unsupported file type"
