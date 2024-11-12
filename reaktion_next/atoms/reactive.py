from fluss_next.api.schema import ReactiveNode
from .base import Atom
from typing import Dict, Any


class ReactiveAtom(Atom):
    node: ReactiveNode
