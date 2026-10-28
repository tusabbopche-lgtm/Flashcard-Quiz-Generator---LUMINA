import re
from typing import List


def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Drop null/control chars (keep newlines/tabs)
    text = ''.join(ch for ch in text if ord(ch) >= 32 or ch in '\n\t\r')
    # Rejoin hyphenated line breaks
    text = re.sub(r'-\s*\n\s*', '', text)
    # Drop lines that are only page numbers
    lines = text.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\d+$', stripped):
            continue
        filtered_lines.append(line)
    text = '\n'.join(filtered_lines)
    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(text: str, max_size: int = 6000, overlap: int = 300) -> List[str]:
    if len(text) <= max_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end >= len(text):
            chunks.append(text[start:end])
            break
        # Try to break at paragraph or sentence boundary
        # Look back from end
        search_start = max(start + max_size - 500, start)
        # Prefer paragraph break
        para_break = text.rfind('\n\n', search_start, end)
        if para_break > start + 1000:
            end = para_break + 2
        else:
            # Try sentence break
            sent_break = -1
            for punct in ['. ', '! ', '? ', '.\n']:
                idx = text.rfind(punct, search_start, end)
                if idx > sent_break:
                    sent_break = idx + len(punct)
            if sent_break > start + 1000:
                end = sent_break
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap if end - overlap > start else end
    return chunks
