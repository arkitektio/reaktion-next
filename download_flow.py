from fluss.api.schema import get_flow
from arkitekt import easy


with easy("this"):
    with open("flow.json", "w") as f:
        f.write(get_flow(31).json(by_alias=True))
