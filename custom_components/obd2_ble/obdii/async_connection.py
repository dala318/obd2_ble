import logging
from typing import Awaitable, Callable, List, Optional, Tuple, Type, Union
from types import TracebackType
import inspect

from obdii.basetypes import MISSING
from obdii.connection import Connection
from obdii.protocol import Protocol

from obdii.command import Command
from obdii.modes import ModeAT
from obdii.protocols.protocol_base import ProtocolBase
from obdii.response import Context, Response, ResponseBase
from obdii.utils.bits import bytes_to_string, filter_bytes
from obdii.utils.helper import debug_responsebase  #, setup_logging


from .async_transport_base import AsyncTransportBase

_LOGGER: logging.Logger = logging.getLogger(__package__)


class AsyncConnection(Connection):
    """
    Asynchronous version of Connection for async OBDII operations.

    This class provides the same interface as Connection but with async methods
    for non-blocking I/O operations. It inherits all sync functionality from
    Connection and overrides transport resolution to use async transports.
    """

    def __init__(
        self,
        transport: AsyncTransportBase,
        protocol: Protocol = Protocol.AUTO,
        auto_connect: bool = False,
        smart_query: bool = False,
        early_return: bool = False,
        # *,
        # log_handler: logging.Handler = MISSING,
        # log_formatter: logging.Formatter = MISSING,
        # log_level: int = logging.INFO,
        # log_root: bool = False,
        **kwargs,
    ) -> None:
        """
        Initialize async connection settings and optionally auto-connect.

        Parameters
        ----------
        transport: :class:`~obdii.transports.transport_base.AsyncTransportBase`
            An asynchronous transport instance implementing :class:`~obdii.transports.transport_base.AsyncTransportBase`.
        protocol: :class:`Protocol`
            The protocol to use for communication.
        auto_connect: :class:`bool`
            If True, connect to the adapter immediately.
        smart_query: :class:`bool`
            If True, send repeat command when the same command is issued again.
        early_return: :class:`bool`
            If set to true, the ELM327 will return immediately after sending the specified number of responses specified in the command (expected_bytes). Works only with ELM327 v1.3 and later.

        log_handler: :class:`logging.Handler`
            Custom log handler for the logger.
        log_formatter: :class:`logging.Formatter`
            Formatter to use with the given log handler.
        log_level: :class:`int`
            Logging level for the logger.
        log_root: :class:`bool`
            Whether to set up the root logger.

        **kwargs: :class:`dict`
            Additional keyword arguments forwarded to the transport's constructor.
        """
        # Call parent init but override transport resolution
        # super().__init__(
        #     transport, protocol, False, smart_query, early_return,
        #     log_handler=log_handler, log_formatter=log_formatter,
        #     log_level=log_level, log_root=log_root, **kwargs
        # )
        self.transport = self._resolve_async_transport(transport, **kwargs)

        self.protocol = protocol
        self.smart_query = smart_query
        self.early_return = early_return

        self.protocol_handler = ProtocolBase.get_handler(Protocol.UNKNOWN)
        self.supported_protocols: List[Protocol] = []
        self.last_command: Optional[Command] = None

        self.init_sequence: List[Union[Command, Callable[[], Union[None, Awaitable[None]]]]] = [
            ModeAT.RESET,
            ModeAT.ECHO_OFF,
            ModeAT.HEADERS_ON,
            ModeAT.SPACES_ON,
            # self._auto_protocol,
            self._aauto_protocol,
        ]
        self.init_completed = False

        # 0x06 to 0x09, 0x01 to 0x05, 0x0A to 0x0C
        self.protocol_preferences = [
            Protocol.ISO_15765_4_CAN,
            Protocol.ISO_15765_4_CAN_B,
            Protocol.ISO_15765_4_CAN_C,
            Protocol.ISO_15765_4_CAN_D,
            Protocol.SAE_J1850_PWM,
            Protocol.SAE_J1850_VPW,
            Protocol.ISO_9141_2,
            Protocol.ISO_14230_4_KWP,
            Protocol.ISO_14230_4_KWP_FAST,
            Protocol.SAE_J1939_CAN,
            Protocol.USER1_CAN,
            Protocol.USER2_CAN,
        ]

        # if log_handler or log_formatter or log_level:
        #     setup_logging(log_handler, log_formatter, log_level, log_root)

        # if auto_connect:
        #     # Use asyncio to run the async connect
        #     import asyncio
        #     try:
        #         asyncio.get_running_loop()
        #         # We're in an async context, can't auto-connect
        #         _LOGGER.warning("Cannot auto-connect in async context. Call aconnect() manually.")
        #     except RuntimeError:
        #         # No running loop, we can create one
        #         asyncio.run(self.aconnect(**kwargs))

    def _resolve_async_transport(
        self,
        transport: Union[str, Tuple[str, Union[str, int]], AsyncTransportBase],
        **kwargs,
    ) -> AsyncTransportBase:
        """Resolves a user-supplied transport instance into an async transport."""
        if isinstance(transport, AsyncTransportBase):
            return transport
        raise TypeError(
            f"AsyncConnection requires an AsyncTransportBase instance, not {type(transport)}."
        )

    async def aconnect(self, **kwargs) -> None:
        """
        Asynchronously establishes a connection to the device using the configured transport and runs the initialization sequence.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments forwarded to the transport's connect method.
        """
        _LOGGER.info(f"Attempting to connect to {repr(self.transport)}.")
        try:
            _LOGGER.debug(f"Connecting with parameters: {kwargs}")
            await self.transport.async_connect(**kwargs)
            _LOGGER.debug("Transport connected, running initialization sequence.")
            await self._ainitialize_connection()
            self.init_completed = True
            _LOGGER.info(f"Successfully connected to {repr(self.transport)}.")
        except Exception as e:
            await self.transport.async_close()
            _LOGGER.error(f"Failed to connect to {repr(self.transport)}: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    async def _ainitialize_connection(self) -> None:
        """Asynchronously initializes the connection using the init sequence."""
        for command in self.init_sequence:
            if isinstance(command, Command):
                _LOGGER.debug(f"Running init command: {command}")
                await self.aquery(command)
            elif callable(command):
                # Try to await if it's a coroutine function, otherwise call directly
                if inspect.iscoroutinefunction(command):
                    _LOGGER.debug(f"Running async command: {command.__name__}")
                    await command()
                else:
                    _LOGGER.debug(f"Running sync command: {command.__name__}")
                    command()
            else:
                _LOGGER.error(f"Invalid type in init_sequence: {type(command)}")
                raise TypeError(f"Invalid command type: {type(command)}")

    def is_connected(self) -> bool:
        """
        Checks if the transport connection is open.

        Returns
        -------
        :class:`bool`
            True if the connection is active.
        """
        return self.transport.is_connected()

    async def aquery(self, command: Command) -> Response:
        """
        Asynchronously send a command and wait for the response.

        Parameters
        ----------
        command: :class:`Command`
            Command to send.

        Returns
        -------
        :class:`Response`
            Parsed response from the adapter.
        """
        effective = command
        send_repeat = False

        if self.smart_query and self.last_command:
            if effective == ModeAT.REPEAT:
                effective = self.last_command
            send_repeat = effective == self.last_command

        if send_repeat:
            query = ModeAT.REPEAT.build()
        else:
            query = effective.build(self.early_return)

        context = Context(effective, self.protocol)

        _LOGGER.debug(f">>> Send: {query}")

        await self.transport.async_write_bytes(query)
        self.last_command = effective

        return await self._await_for_response(context)

    async def _await_for_response(self, context: Context) -> Response:
        """
        Asynchronously wait for a raw response from the transport and parses it using the protocol handler.

        Parameters
        ----------
        context: :class:`Context`
            Context to use for parsing.

        Returns
        -------
        :class:`Response`
            Parsed response or raw fallback response.
        """
        raw = await self.transport.async_read_bytes()

        messages = [line for line in raw.splitlines() if line]

        response_base = ResponseBase(context, raw, messages)

        _LOGGER.debug(f"<<< Read:\n{debug_responsebase(response_base).strip()}")

        try:
            return self.protocol_handler.parse_response(response_base)
        except NotImplementedError:
            if self.init_completed:
                _LOGGER.warning(f"Unsupported Protocol used: {self.protocol.name}")
            return Response(**vars(response_base))

    async def _aset_protocol_to(self, protocol: Protocol) -> int:
        """
        Asynchronously sets the protocol to the specified value.
        Returns the protocol number if successful.
        """
        await self.aquery(ModeAT.SET_PROTOCOL(protocol.value))
        response = await self.aquery(ModeAT.DESC_PROTOCOL_N)

        line = bytes_to_string(filter_bytes(response.raw, b'\r', b'>'))
        protocol_number = self._parse_protocol_number(line)

        return protocol_number

    async def _aget_supported_protocols(self) -> List[Protocol]:
        """
        Asynchronously attempts to find supported protocol(s).
        """
        supported_protocols = []
        excluded_protocols = {Protocol.UNKNOWN, Protocol.AUTO}

        for protocol in Protocol:
            if protocol in excluded_protocols:
                continue

            protocol_number = await self._aset_protocol_to(protocol)
            if protocol_number == protocol.value:
                supported_protocols.append(protocol)

        if not supported_protocols:
            _LOGGER.warning("No supported protocols detected.")
            return [Protocol.UNKNOWN]

        return supported_protocols

    async def _aauto_protocol(self, protocol: Protocol = MISSING) -> None:
        """
        Asynchronously sets the protocol for communication.
        Automatically detects the best supported protocol if AUTO is specified.
        """
        protocol = protocol or self.protocol
        unwanted_protocols = {Protocol.AUTO, Protocol.UNKNOWN}

        protocol_number = await self._aset_protocol_to(protocol)

        if Protocol(protocol_number) in unwanted_protocols:
            self.supported_protocols = await self._aget_supported_protocols()
            supported_protocols = self.supported_protocols

            if supported_protocols:
                priority_dict = {
                    protocol: idx
                    for idx, protocol in enumerate(self.protocol_preferences)
                }
                supported_protocols.sort(
                    key=lambda p: priority_dict.get(p, len(self.protocol_preferences))
                )

                protocol_number = await self._aset_protocol_to(supported_protocols[0])
            else:
                protocol_number = -1

        self.protocol = Protocol(protocol_number)
        self.protocol_handler = ProtocolBase.get_handler(self.protocol)
        if protocol not in unwanted_protocols and protocol != self.protocol:
            _LOGGER.warning(f"Requested protocol {protocol.name} cannot be used.")
        _LOGGER.info(f"Protocol set to {self.protocol.name}.")

    async def aclose(self) -> None:
        """
        Asynchronously closes the transport connection.
        """
        await self.transport.async_close()
        _LOGGER.info("Connection closed.")

    async def __aenter__(self):
        """
        Support usage as an async context manager.

        Returns
        -------
        :class:`AsyncConnection`
            The connection instance itself.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Close the connection when exiting the async context.
        """
        await self.aclose()
