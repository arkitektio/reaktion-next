from pydantic import BaseModel

from fluss_next.api.schema import FlowFragmentGraph


class ReaktionEngine(BaseModel):
    graph: FlowFragmentGraph

    def cause(self, data):
        pass
