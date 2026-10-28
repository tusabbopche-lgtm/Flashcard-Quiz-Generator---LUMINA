from core.flashcard_session import FlashcardSession
from core.models import Difficulty, Flashcard


def make_card(index):
    return Flashcard(
        front=f'Flashcard question number {index}?',
        back=f'Answer {index}',
        concept=f'Concept {index}',
        difficulty=Difficulty.MEDIUM,
        source_quote='Mitochondria are often referred to as the powerhouse of the cell',
    )


def test_session_starts_on_first_card():
    cards = [make_card(i) for i in range(3)]
    session = FlashcardSession(cards)
    assert session.current_card() is cards[0]
    assert session.current_index == 0
    assert session.flipped is False


def test_flip_toggles_state():
    session = FlashcardSession([make_card(0)])
    assert session.flip() is True
    assert session.flipped is True
    assert session.flip() is False


def test_next_and_previous_navigation():
    cards = [make_card(i) for i in range(3)]
    session = FlashcardSession(cards)
    assert session.next_card() is True
    assert session.current_card() is cards[1]
    assert session.prev_card() is True
    assert session.current_card() is cards[0]


def test_navigation_stops_at_the_edges():
    session = FlashcardSession([make_card(i) for i in range(2)])
    assert session.prev_card() is False
    session.next_card()
    assert session.next_card() is False


def test_next_resets_flip():
    session = FlashcardSession([make_card(i) for i in range(2)])
    session.flip()
    session.next_card()
    assert session.flipped is False


def test_shuffle_keeps_all_cards():
    cards = [make_card(i) for i in range(6)]
    session = FlashcardSession(cards)
    session.shuffle()
    assert sorted(session.order) == list(range(6))
    assert session.current_index == 0


def test_reset_order_restores_original_order():
    session = FlashcardSession([make_card(i) for i in range(4)])
    session.shuffle()
    session.reset_order()
    assert session.order == [0, 1, 2, 3]


def test_mark_status_and_counts():
    cards = [make_card(i) for i in range(3)]
    session = FlashcardSession(cards)
    session.mark_status(cards[0].id, 'known')
    session.mark_status(cards[1].id, 'practice')
    counts = session.get_counts()
    assert counts == {'unmarked': 1, 'known': 1, 'practice': 1, 'total': 3}


def test_empty_session_returns_none():
    session = FlashcardSession([])
    assert session.current_card() is None
    assert session.get_counts()['total'] == 0
