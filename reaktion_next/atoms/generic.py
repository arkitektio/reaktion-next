import asyncio
from reaktion_next.events import OutEvent, Returns, EventType, InEvent
from reaktion_next.atoms.base import Atom
import logging
from pydantic import Field
from typing import Dict, List
import asyncio

logger = logging.getLogger(__name__)


class FilterAtom(Atom):
    async def filter(self, event: InEvent) -> bool:
        raise NotImplementedError("This needs to be implemented")

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.NEXT:
                    try:
                        result = await self.filter(event)
                        if result is True:
                            await self.transport.put(
                                OutEvent(
                                    handle="return_0",
                                    type=EventType.NEXT,
                                    value=event.value,
                                    source=self.node.id,
                                    caused_by=[event.current_t],
                                )
                            )
                    except Exception as e:
                        logger.error(f"{self.node.id} map failed", exc_info=True)
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.ERROR,
                                source=self.node.id,
                                value=e,
                                caused_by=[event.current_t],
                            )
                        )
                        break

                if event.type == EventType.COMPLETE:
                    # Everything left of us is done, so we can shut down as well
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            value=event.value,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break
                    # We are not raising the exception here but monadicly killing it to the
                    # left
        except asyncio.CancelledError as e:
            logger.debug(f"Atom {self.node} is getting cancelled")
            raise e


class MapAtom(Atom):
    async def map(self, event: InEvent) -> Returns:
        raise NotImplementedError("This needs to be implemented")

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.NEXT:
                    try:
                        result = await self.map(event)
                        if result is None:
                            value = ()
                        elif isinstance(result, list) or isinstance(result, tuple):
                            value = result
                        else:
                            value = (result,)

                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.NEXT,
                                value=value,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    except Exception as e:
                        logger.error(f"{self.node.id} map failed", exc_info=True)
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.ERROR,
                                source=self.node.id,
                                exception=e,
                                caused_by=[event.current_t],
                            )
                        )
                        break

                if event.type == EventType.COMPLETE:
                    # Everything left of us is done, so we can shut down as well
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break
                    # We are not raising the exception here but monadicly killing it to the
                    # left
        except asyncio.CancelledError as e:
            logger.debug(f"Atom {self.node} is getting cancelled")
            raise e


class MergeMapAtom(Atom):
    async def merge_map(self, event: InEvent) -> Returns:
        raise NotImplementedError("This needs to be implemented")

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.NEXT:
                    try:
                        async for result in self.merge_map(event):
                            if result is None:
                                value = ()
                            elif isinstance(result, list) or isinstance(result, tuple):
                                value = result
                            else:
                                value = (result,)
                            await self.transport.put(
                                OutEvent(
                                    handle="return_0",
                                    type=EventType.NEXT,
                                    value=value,
                                    source=self.node.id,
                                    caused_by=[event.current_t],
                                )
                            )

                    except Exception as e:
                        logger.error(f"{self.node.id} map failed")
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.ERROR,
                                source=self.node.id,
                                exception=e,
                                caused_by=[event.current_t],
                            )
                        )
                        break

                if event.type == EventType.COMPLETE:
                    # Everything left of us is done, so we can shut down as well
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break
                    # We are not raising the exception here but monadicly killing it to the
                    # left
        except asyncio.CancelledError as e:
            logger.debug(f"Atom {self.node} is getting cancelled")
            raise e


class OrderedAtom(Atom):
    runningEvents: Dict[int, asyncio.Task] = Field(default_factory=dict)
    publish_queue: List[int] = Field(default_factory=list)

    async def map(self, event: InEvent) -> Returns:
        raise NotImplementedError("This needs to be implemented")

    async def check_ordered(self):
        tasks_to_remove = []
        for key, task in self.runningEvents.items():
            if task.done():
                exception = task.exception()
                if exception:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=exception,
                            source=self.node.id,
                            caused_by=[key],
                        )
                    )
                else:
                    if key in self.publish_queue:
                        if self.publish_queue[0] == key:
                            await self.transport.put(
                                OutEvent(
                                    handle="return_0",
                                    type=EventType.NEXT,
                                    value=task.result(),
                                    source=self.node.id,
                                    caused_by=[key],
                                )
                            )
                            self.publish_queue.pop(0)
                            tasks_to_remove.append(key)

        for key in tasks_to_remove:
            self.runningEvents.pop(key)

    async def publish_changes(self):
        while True:
            await asyncio.sleep(0.1)
            await self.check_ordered()

    async def run(self):
        publish_task = asyncio.create_task(self.publish_changes())

        try:
            while True:
                event = await self.get()

                if event.type == EventType.NEXT:
                    self.publish_queue.append(event.current_t)
                    self.runningEvents[event.current_t] = asyncio.create_task(
                        self.map(event)
                    )

                if event.type == EventType.COMPLETE:
                    # Everything left of us is done, so we can shut down as well
                    await asyncio.gather(*self.runningEvents.values())
                    await self.check_ordered()

                    publish_task.cancel()
                    try:
                        await publish_task
                    except asyncio.CancelledError:
                        pass
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if event.type == EventType.ERROR:
                    for key, value in self.runningEvents.items():
                        value.cancel()
                        try:
                            await value
                        except asyncio.CancelledError:
                            pass

                    publish_task.cancel()
                    try:
                        await publish_task
                    except asyncio.CancelledError:
                        pass

                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break
                    # We are not raising the exception here but monadicly killing it to the
                    # left
        except asyncio.CancelledError as e:
            publish_task.cancel()
            try:
                await publish_task
            except asyncio.CancelledError:
                pass

            logger.debug(f"Atom {self.node} is getting cancelled")
            raise e


class AsCompletedAtom(Atom):
    runningEvents: Dict[int, asyncio.Task] = Field(default_factory=dict)

    async def map(self, event: InEvent) -> Returns:
        raise NotImplementedError("This needs to be implemented")

    async def check_as_completed(self):
        tasks_to_remove = []
        for key, task in self.runningEvents.items():
            if task.done():
                exception = task.exception()
                if exception:
                    logger.error(f"{self.node.id} map failed with {exception}")
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=exception,
                            source=self.node.id,
                            caused_by=[key],
                        )
                    )

                else:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.NEXT,
                            value=task.result(),
                            source=self.node.id,
                            caused_by=[key],
                        )
                    )
                tasks_to_remove.append(key)

        for key in tasks_to_remove:
            self.runningEvents.pop(key)

    async def publish_changes(self):
        while True:
            await asyncio.sleep(0.1)
            await self.check_as_completed()

    async def run(self):
        publish_task = asyncio.create_task(self.publish_changes())

        try:
            while True:
                event = await self.get()

                if event.type == EventType.NEXT:
                    self.runningEvents[event.current_t] = asyncio.create_task(
                        self.map(event)
                    )

                if event.type == EventType.COMPLETE:
                    # Everything left of us is done, so we can shut down as well
                    await asyncio.gather(*self.runningEvents.values())
                    await self.check_as_completed()
                    publish_task.cancel()
                    try:
                        await publish_task
                    except asyncio.CancelledError:
                        pass
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if event.type == EventType.ERROR:
                    for key, value in self.runningEvents.items():
                        value.cancel()
                        try:
                            await value
                        except asyncio.CancelledError:
                            pass

                    publish_task.cancel()
                    try:
                        await publish_task
                    except asyncio.CancelledError:
                        pass

                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            exception=event.exception,
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )
                    break
                    # We are not raising the exception here but monadicly killing it to the
                    # left
        except asyncio.CancelledError as e:
            publish_task.cancel()
            try:
                await publish_task
            except asyncio.CancelledError:
                pass

            logger.debug(f"Atom {self.node} is getting cancelled")
            raise e
