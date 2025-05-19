from pydantic import BaseModel, Field
from typing import Set


class ReferenceCounter(BaseModel):
    references: Set[str] = Field(default_factory=set)

    def add_reference(self, key: str):
        """Adds a reference to a structure in the reference counter."""
        if isinstance(key, int):
            key = str(key)
        self.references.add(key)
