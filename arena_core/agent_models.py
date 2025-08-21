# Shared Agent model for arena_core (avoid circular imports)
import os
from dataclasses import dataclass, field

@dataclass
class Agent:
    name: str
    path: str
    score: int = 0
    last_rc: int | None = None
    last_out: str = ""
    last_err: str = ""
    parent: str | None = None
    tags: list = field(default_factory=list)

    def __repr__(self):
        return f"<Agent {self.name} score={self.score}>"

