from types import SimpleNamespace

from views.flashcards import _card_html


def test_card_html_cleans_legacy_markup_in_every_field():
    card = SimpleNamespace(
        front='<p>What is <b>ATP</b>?</p>',
        back='<div class="answer"><strong>Adenosine triphosphate</strong> is the energy currency.</div>',
        explanation='<em>It carries chemical energy.</em>',
        concept='<span>Energy</span>',
        source_quote='<code>ATP is used as a source of chemical energy.</code>',
        difficulty='easy',
    )
    markdown = _card_html(card, SimpleNamespace(flipped=True), 'unmarked')

    assert 'What is ATP?' in markdown
    assert 'Adenosine triphosphate is the energy currency.' in markdown
    assert '&lt;p&gt;' not in markdown
    assert '&lt;strong&gt;' not in markdown
    assert '<strong>' not in markdown
