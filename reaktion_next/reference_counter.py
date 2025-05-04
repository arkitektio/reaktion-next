from typing import Dict
from pydantic import BaseModel, Field
from typing import Set
from rekuest_next.agents.base import Agent


class ReferenceCounter(BaseModel):
    references: Set[str] = Field(default_factory=set)

    def add_reference(self, key: str):
        """Adds a reference to a structure in the reference counter."""
        self.references.add(key)
