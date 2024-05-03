from typing import Type


class Atom:
    pass


class Plant:
    def __init__(self) -> None:
        self.builders = {}
        pass

    def register_builder(self, atomClass: Type[Atom], type: str) -> None:
        self.builders[type] = atomClass

    def build(self, type: str, **kwargs) -> Atom:
        return self.builders[type](**kwargs)
