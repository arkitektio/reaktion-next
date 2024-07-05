import os
from reaktion_next.events import EventType, OutEvent

DIR_NAME = os.path.dirname(os.path.realpath(__file__))


def build_relative(path):
    return os.path.join(DIR_NAME, path)


def expectnext(event: OutEvent):
    if event.type != EventType.NEXT:
        if event.type == EventType.ERROR:
            raise event.value
        else:
            raise Exception(f"Unexpected event: {event}")


def expecterror(event: OutEvent):
    if event.type != EventType.ERROR:
        raise Exception(f"Unexpected event: {event}")
