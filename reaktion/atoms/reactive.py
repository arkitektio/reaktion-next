from fluss.api.schema import FlowNodeFragmentBaseReactiveNode
from .base import Atom
from typing import Dict, Any


class ReactiveAtom(Atom):
    node: FlowNodeFragmentBaseReactiveNode
