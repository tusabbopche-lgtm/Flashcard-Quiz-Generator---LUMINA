from typing import List, Any


class FlashcardSession:
    def __init__(self, flashcards: List[Any]):
        self.original = list(flashcards)
        self.order = list(range(len(flashcards)))
        self.current_index = 0
        self.flipped = False
        self.statuses = {f.id if hasattr(f, 'id') else id(f): 'unmarked' for f in flashcards}
    
    def current_card(self):
        if not self.order or self.current_index >= len(self.order):
            return None
        return self.original[self.order[self.current_index]]
    
    def flip(self):
        self.flipped = not self.flipped
        return self.flipped
    
    def reset_flip(self):
        self.flipped = False
    
    def next_card(self):
        if self.current_index < len(self.order) - 1:
            self.current_index += 1
            self.flipped = False
            return True
        return False
    
    def prev_card(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.flipped = False
            return True
        return False
    
    def shuffle(self):
        import random
        random.shuffle(self.order)
        self.current_index = 0
        self.flipped = False
    
    def reset_order(self):
        self.order = list(range(len(self.original)))
        self.current_index = 0
        self.flipped = False
    
    def mark_status(self, card_id: str, status: str):
        self.statuses[card_id] = status
    
    def get_counts(self):
        counts = {'unmarked': 0, 'known': 0, 'practice': 0, 'total': len(self.order)}
        for i in self.order:
            card = self.original[i]
            cid = card.id if hasattr(card, 'id') else id(card)
            st = self.statuses.get(cid, 'unmarked')
            if st == 'known':
                counts['known'] += 1
            elif st == 'practice':
                counts['practice'] += 1
            else:
                counts['unmarked'] += 1
        return counts
