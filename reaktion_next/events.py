from typing import Literal, Tuple, Union, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class EventType(str, Enum):
    NEXT = "NEXT"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


Returns = Tuple[Any, ...]


class BaseInEvent(BaseModel):
    """Base class for all input events"""

    target: str
    """The node that is targeted by the event"""
    handle: str = Field(..., description="The handle of the port")
    """ The handle of the port that emitted the event"""
    current_t: int
    """ The current (in loop) time of the event"""

    @field_validator("handle")
    def validate_handle(cls, v: str | int) -> str:
        if isinstance(v, int):
            v = f"arg_{v}"

        if v.startswith("return_"):
            raise ValueError(f"Handle needs to start with arg_. This is an inevent {v}")
        if not v.startswith("arg_"):
            raise ValueError(
                f"Handle needs to start with arg_. This is an outevent {v} "
            )

        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class NextInEvent(BaseInEvent):
    """An event that is emitted by a node to indicate that it has a new value"""

    type: Literal[EventType.NEXT] = Field(
        default=EventType.NEXT, description="The event type is always NEXT"
    )
    target: str
    """The node that is targeted by the event"""
    handle: str = Field(..., description="The handle of the port")
    """ The handle of the port that emitted the event"""
    value: Returns = Field(..., description="The value of the event")
    """ The attached value of the event"""
    current_t: int
    """ The current (in loop) time of the event"""


class ErrorInEvent(BaseInEvent):
    """An event that is emitted by a node to indicate that it has an error"""

    type: Literal[EventType.ERROR] = Field(
        EventType.ERROR, description="The event type is always ERROR"
    )
    target: str
    """The node that is targeted by the event"""
    handle: str = Field(..., description="The handle of the port")
    """ The handle of the port that emitted the event"""
    exception: Exception = Field(..., description="The exception of the event")
    """ The attached value of the event"""
    current_t: int
    """ The current (in loop) time of the event"""


class CompleteInEvent(BaseInEvent):
    """An event that is emitted by a node to indicate that it has completed its work"""

    type: Literal[EventType.COMPLETE] = Field(
        EventType.COMPLETE, description="The event type is always COMPLETE"
    )
    target: str
    """The node that is targeted by the event"""
    handle: str = Field(..., description="The handle of the port")
    """ The handle of the port that emitted the event"""
    current_t: int
    """ The current (in loop) time of the event"""


InEvent = CompleteInEvent | ErrorInEvent | NextInEvent


class BaseOutEvent(BaseModel):
    source: str
    """ The node that emitted the event """
    handle: str = Field(..., description="The handle of the port")
    """ The handle of the port that emitted the event"""

    caused_by: Optional[Tuple[int, ...]]
    """ The attached value of the event"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("handle", mode="before")
    def validate_handle(cls, v: int | str) -> str:
        if isinstance(v, int):
            v = f"return_{v}"

        if v.startswith("arg_"):
            raise ValueError(f"Handle cannot start with arg_. This is an outevent {v}")
        if not v.startswith("return_"):
            raise ValueError(
                f"Handle needs to start with return_. This is an outevent {v}"
            )

        return v

    def to_state(self) -> dict:
        """Convert the event to a state dictionary"""
        raise NotImplementedError(
            "This method should be implemented by subclasses to convert the event to a state dictionary."
        )


class NextOutEvent(BaseOutEvent):
    value: Optional[Returns] = Field(
        default=None, description="The value of the event (null, exception or any"
    )
    type: Literal[EventType.NEXT] = Field(
        default=EventType.NEXT, description="The event type is always COMPLETE"
    )

    def to_state(self) -> dict[str, Union[str, Returns]]:
        return {
            "source": self.source,
            "handle": self.handle,
            "type": self.type,
            "value": self.value,
        }


class ErrorOutEvent(BaseOutEvent):
    exception: Exception = Field(
        ..., description="The value of the event (null, exception or any"
    )
    type: Literal[EventType.ERROR] = Field(
        default=EventType.ERROR, description="The event type is always COMPLETE"
    )

    def to_state(self) -> dict[str, str | None]:
        return {
            "source": self.source,
            "handle": self.handle,
            "type": self.type,
            "value": str(self.exception)
            if isinstance(self.exception, Exception)
            else self.exception,
        }


class CompleteOutEvent(BaseOutEvent):
    type: Literal[EventType.COMPLETE] = Field(
        default=EventType.COMPLETE, description="The event type is always COMPLETE"
    )

    def to_state(self) -> dict[str, str]:
        return {
            "source": self.source,
            "handle": self.handle,
            "type": self.type,
        }


OutEvent = NextOutEvent | ErrorOutEvent | CompleteOutEvent
