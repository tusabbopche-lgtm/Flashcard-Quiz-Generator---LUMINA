"""Text cleanup shared by generation and presentation.

Some earlier builds stored presentation HTML inside flashcard answer fields.
The helpers here extract readable text from that legacy markup without
modifying the stored data. They are deliberately conservative so angle
brackets in legitimate code or mathematics are not treated as HTML.
"""

import html
import re
from html.parser import HTMLParser
from typing import Optional

_KNOWN_TAGS = (
    'a|abbr|article|aside|b|blockquote|br|code|dd|del|details|div|dl|dt|em|'
    'figcaption|figure|h[1-6]|hr|i|img|ins|kbd|li|mark|ol|p|pre|q|s|section|'
    'small|span|strong|sub|summary|sup|table|tbody|td|tfoot|th|thead|tr|u|ul'
)

# A lone ``<div>`` can be a literal code snippet; a closing tag, a class
# attribute or a void element is much stronger evidence of real markup.
_HTML_SIGNAL_RE = re.compile(
    r'</(?:' + _KNOWN_TAGS + r')\s*>|'
    r'<(?:br|hr)\s*/?>|'
    r'<\s*(?:' + _KNOWN_TAGS + r')\b[^>]*\b(?:class|style|id)\s*=',
    re.IGNORECASE,
)

_ESCAPED_TAG_RE = re.compile(r'&lt;/?[a-zA-Z][^&]*?&gt;')

_BLOCK_TAGS = {
    'address', 'article', 'aside', 'blockquote', 'dd', 'details', 'div', 'dl',
    'dt', 'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'ol', 'p', 'pre', 'section', 'summary', 'table', 'tbody', 'td', 'tfoot',
    'th', 'thead', 'tr', 'ul',
}
_SKIP_TAGS = {'script', 'style', 'head', 'title'}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == 'br':
            self.parts.append('\n')
        elif tag == 'li':
            self.parts.append('\n• ')
        elif tag in _BLOCK_TAGS:
            self.parts.append('\n')
        elif tag == 'img':
            alt = dict(attrs).get('alt')
            if alt:
                self.parts.append(alt)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._skip_depth:
            return
        if tag == 'br':
            self.parts.append('\n')
        elif tag == 'img':
            alt = dict(attrs).get('alt')
            if alt:
                self.parts.append(alt)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _BLOCK_TAGS:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def _normalize(text: str, single_line: bool) -> str:
    text = str(text or '').replace('\xa0', ' ')
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    if single_line:
        text = re.sub(r'\s+', ' ', text)
    return text.strip()


def looks_like_legacy_html(value) -> bool:
    """Return True when a value contains presentation HTML from old data."""
    text = str(value or '')
    if not text:
        return False
    if _HTML_SIGNAL_RE.search(text):
        return True
    if _ESCAPED_TAG_RE.search(text):
        decoded = html.unescape(text)
        return bool(_HTML_SIGNAL_RE.search(decoded))
    return False


def to_plain_text(value, max_length: Optional[int] = None, single_line: bool = False) -> str:
    """Convert a value to safe, readable text.

    Legacy HTML is reduced to its text content. Modern plain text is only
    whitespace-normalised, so code, equations and angle brackets survive.
    """
    if value is None:
        return ''
    text = str(value)
    if not text.strip():
        return ''

    decoded = html.unescape(text)
    if _HTML_SIGNAL_RE.search(decoded):
        parser = _TextExtractor()
        try:
            parser.feed(decoded)
            parser.close()
            text = ''.join(parser.parts)
        except Exception:
            text = re.sub(r'<[^>]+>', ' ', decoded)
    else:
        text = decoded

    text = _normalize(text, single_line)
    if max_length is not None and len(text) > max_length:
        text = text[: max(1, max_length - 1)].rstrip() + '…'
    return text
