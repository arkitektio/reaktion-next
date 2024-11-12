from pydantic import BaseModel

from fluss_next.api.schema import FlowGraph


class ReaktionEngine(BaseModel):
    graph: FlowGraph

    def cause(self, data):
        pass
