from core.text_utils import looks_like_legacy_html, to_plain_text


def test_legacy_html_is_reduced_to_readable_text():
    value = '<div class="answer"><p><strong>ATP</strong> is the energy currency.</p></div>'
    assert looks_like_legacy_html(value) is True
    assert to_plain_text(value) == 'ATP is the energy currency.'


def test_escaped_legacy_html_is_decoded_and_cleaned():
    value = '&lt;p class=&quot;answer&quot;&gt;Adenosine triphosphate&lt;/p&gt;'
    assert looks_like_legacy_html(value) is True
    assert to_plain_text(value) == 'Adenosine triphosphate'


def test_plain_text_with_angle_brackets_is_preserved():
    value = 'The condition x < y and y > z must remain unchanged.'
    assert looks_like_legacy_html(value) is False
    assert to_plain_text(value) == value


def test_single_line_and_length_options():
    value = '<p>Line one</p><p>Line two</p>'
    assert to_plain_text(value, single_line=True) == 'Line one Line two'
    assert len(to_plain_text(value, max_length=8)) <= 8
