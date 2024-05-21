from fluss_next.api.schema import ReactiveNodeFragment
from .base import Atom
from typing import Dict, Any


class ReactiveAtom(Atom):
    node: ReactiveNodeFragment
