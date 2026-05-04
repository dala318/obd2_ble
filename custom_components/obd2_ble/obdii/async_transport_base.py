from abc import ABC, abstractmethod
from typing import Optional

from obdii.transports.transport_base import TransportBase

# from obdii.transports.transport_base import TransportBase

class AsyncTransportBase(TransportBase, ABC):
    """Base class for asynchronous transport implementations."""
    @abstractmethod
    async def async_connect(self) -> None: ...

    @abstractmethod
    async def async_close(self) -> None: ...

    @abstractmethod
    async def async_write_bytes(self, query: bytes) -> None: ...

    @abstractmethod
    async def async_read_bytes(self, expected_seq: bytes = b'>', size: Optional[int] = None) -> bytes: ...

    def _run_coro(self, coro):
        """Run a coroutine in the appropriate event loop."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # If we're here, we're already in an event loop. Run the coroutine directly.
            return loop.run_until_complete(coro)
        except RuntimeError:
            # No running loop, create a new one for this operation.
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

    def connect(self) -> None:
        """Synchronous wrapper for async_connect."""
        self._run_coro(self.async_connect())

    def close(self) -> None:
        """Synchronous wrapper for async_close."""
        self._run_coro(self.async_close())

    def write_bytes(self, query: bytes) -> None:
        """Synchronous wrapper for async_write_bytes."""
        self._run_coro(self.async_write_bytes(query))

    def read_bytes(self, expected_seq: bytes = b'>', size: Optional[int] = None) -> bytes:
        """Synchronous wrapper for async_read_bytes."""
        return self._run_coro(self.async_read_bytes(expected_seq, size))
