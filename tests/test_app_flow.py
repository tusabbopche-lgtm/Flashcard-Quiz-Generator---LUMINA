from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / 'data' / 'samples'
BIOLOGY = (SAMPLES_DIR / 'biology.txt').read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def app():
    return AppTest.from_file(str(PROJECT_ROOT / 'app.py'), default_timeout=120)


def test_home_page_renders(app):
    app.run()
    assert not app.exception
    assert any('Flashcard' in title.value for title in app.title)


def test_generate_flashcards_and_take_a_quiz(app):
    app.run()
    app.text_area(key='home_text').set_value(BIOLOGY)
    app.text_input(key='home_topic').set_value('Cell biology')
    app.run()
    assert not app.exception

    generate = [button for button in app.button if 'Generate' in button.label]
    assert generate
    generate[0].click()
    app.run()

    assert not app.exception
    metrics = {(metric.label, metric.value) for metric in app.metric}
    assert ('Total', '10') in metrics
    assert app.radio(key='nav_choice').value == 'Flashcards'

    # The flashcard deck can be flipped and marked.
    show_answer = [button for button in app.button if button.label == 'Show answer']
    assert show_answer
    show_answer[0].click()
    app.run()
    assert not app.exception

    known = [button for button in app.button if button.label == 'I know this']
    assert known
    known[0].click()
    app.run()
    assert not app.exception
    metrics = {(metric.label, metric.value) for metric in app.metric}
    assert ('Known', '1') in metrics

    # Run a quiz from start to finish.
    app.radio(key='nav_choice').set_value('Quiz')
    app.run()
    assert not app.exception

    start = [button for button in app.button if 'Start quiz' in button.label]
    assert start
    start[0].click()
    app.run()
    assert not app.exception
    assert any('Question 1 of' in header.value for header in app.subheader)

    for _ in range(30):
        options = [radio for radio in app.radio if radio.label == 'Choose an answer']
        assert options, 'the quiz should always show an answer radio'
        options[0].set_value(options[0].options[0])
        app.run()
        assert not app.exception
        submit = [button for button in app.button if 'Submit quiz' in button.label]
        if submit:
            submit[0].click()
            app.run()
            break
        nxt = [button for button in app.button if 'Next' in button.label]
        assert nxt
        nxt[0].click()
        app.run()
    else:  # pragma: no cover - guards against an endless quiz
        pytest.fail('The quiz never reached the submit button')

    assert not app.exception
    assert any('Quiz results' in title.value for title in app.title)
    metrics = {(metric.label, metric.value) for metric in app.metric}
    assert 'Score' in {label for label, _ in metrics}
    correct = int(dict(metrics)['Correct'])
    incorrect = int(dict(metrics)['Incorrect'])
    unanswered = int(dict(metrics)['Unanswered'])
    assert correct + incorrect + unanswered == 10
