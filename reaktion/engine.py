from pydantic import BaseModel

from fluss.api.schema import FlowFragmentGraph


class ReaktionEngine(BaseModel):
    graph: FlowFragmentGraph

    def cause(self, data):
        pass
