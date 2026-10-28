from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Status(str, Enum):
    UNMARKED = "unmarked"
    KNOWN = "known"
    PRACTICE = "practice"


class Flashcard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    front: str = Field(min_length=5, max_length=300)
    back: str = Field(min_length=1, max_length=600)
    explanation: Optional[str] = None
    concept: str = Field(min_length=1, max_length=60)
    difficulty: Difficulty
    source_quote: str = Field(min_length=10, max_length=300)
    status: Status = Status.UNMARKED


class MCQ(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question: str = Field(min_length=10, max_length=400)
    options: List[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=10, max_length=600)
    concept: str = Field(min_length=1, max_length=60)
    difficulty: Difficulty
    source_quote: str = Field(min_length=10, max_length=300)

    @field_validator("options")
    @classmethod
    def check_options(cls, v):
        if len(v) != 4:
            raise ValueError("Must have exactly 4 options")
        for opt in v:
            if not opt or not str(opt).strip():
                raise ValueError("Options cannot be empty")
        # Check distinct case-insensitively
        normalized = [str(o).strip().lower() for o in v]
        if len(set(normalized)) != 4:
            raise ValueError("Options must be distinct")
        return [str(o).strip() for o in v]


class KeyConcept(BaseModel):
    term: str
    definition: str


class StudySettings(BaseModel):
    n_cards: int
    n_mcqs: int
    difficulty: str


class EngineInfo(BaseModel):
    provider: str
    model: str
    offline: bool


class QuizAttemptSettings(BaseModel):
    n_questions: int
    difficulty: str
    shuffle: bool = False
    mode: str = "exam"
    timer_minutes: int = 0


class QuizQuestion(BaseModel):
    mcq_id: str
    displayed_options: List[str] = Field(min_length=4, max_length=4)
    correct_index: int


class QuizResult(BaseModel):
    total: int
    correct: int
    incorrect: int
    unanswered: int
    percent: Optional[float] = None
    band: Optional[str] = None


class QuizAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    submitted_at: Optional[str] = None
    settings: QuizAttemptSettings
    questions: List[QuizQuestion]
    answers: Dict[str, Optional[int]] = Field(default_factory=dict)
    result: Optional[QuizResult] = None


class StudySet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = Field(min_length=1, max_length=100)
    subject: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_text: str
    source_hash: str
    engine: EngineInfo
    settings: StudySettings
    flashcards: List[Flashcard] = Field(default_factory=list)
    mcqs: List[MCQ] = Field(default_factory=list)
    key_concepts: List[KeyConcept] = Field(default_factory=list)
    attempts: List[QuizAttempt] = Field(default_factory=list)
