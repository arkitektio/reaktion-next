from types import TracebackType
from typing import Any, AsyncGenerator, Dict, Optional, Protocol, runtime_checkable
from koil.composition.base import KoiledModel
from rekuest_next.api.schema import Action
from rekuest_next.messages import Assign
from rekuest_next.remote import acall_raw, aiterate_raw


@runtime_checkable
class RPCContract(Protocol):
    """An RPC contract is a protocol that defines how
    to call a function or generator in a blocking or non-blocking way.
    """

    async def aenter(self) -> "RPCContract":
        """Enter the context manager for the RPC contract.
        This method should be implemented by the subclass.
        """
        ...

    async def __aenter__(self) -> "RPCContract": ...

    async def acall_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Optional[Assign] = None,
        reference: str | None = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ): ...

    async def aiterate_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Optional[Assign] = None,
        reference: str | None = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ): ...

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        ...
    

    def __enter__(self) -> "RPCContract":
        ...

    async def aexit(self) -> "RPCContract":
        """Enter the context manager for the RPC contract.
        This method should be implemented by the subclass.
        """
        return self


class DirectContract(KoiledModel):
    """In a direct contract, the function  is called
    without preliminary reserving the node.
    """

    action: Action
    reference: str

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def acall_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Optional[Assign] = None,
        reference: str | None = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ):
        """Call the function or generator in a blocking or non-blocking way.
        This method should be implemented by the subclass.
        """
        return await acall_raw(
            kwargs=kwargs,
            action=self.action,
            parent=parent,
            reference=reference,
            assign_timeout=assign_timeout,
            timeout_is_recoverable=timeout_is_recoverable,
        )

    def aiterate_raw(
        self,
        kwargs: Dict[str, Any],
        parent: Optional[Assign] = None,
        reference: str | None = None,
        assign_timeout: Optional[float] = None,
        timeout_is_recoverable: bool = False,
    ) -> AsyncGenerator[Any, None]:
        """Call the function or generator in a blocking or non-blocking way.
        This method should be implemented by the subclass.
        """
        return aiterate_raw(
            kwargs=kwargs,
            action=self.action,
            parent=parent,
            reference=reference,
            assign_timeout=assign_timeout,
            timeout_is_recoverable=timeout_is_recoverable,
        )
        
    async def aenter(self) -> "DirectContract":
        """Enter the context manager for the direct contract.
        This method should be implemented by the subclass.
        """
        return self
