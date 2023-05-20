"""# IPC
Provides Asynchronous IPC functionality through a TCP Backed Duplex.

A Duplex allows for bidirectional communication between two processes.
                                +---------------------------+
                      |   <---  |  [ read  ] <--> [ write ] |   <---  |
[ Parent Process ]  --|         |                           |         |-- [ Child Process ]
                      |   --->  |  [ write ] <--> [ read  ] |   --->  |
                                +---------------------------+

"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Literal

from . import _logger as _module_logger

_logger = _module_logger.getChild("ipc")

@dataclass
class IPCInterface:
  """Represents one end of a 
  """
  reader: asyncio.StreamReader | None
  writer: asyncio.StreamWriter | None
  message_delimiter: bytes = field(default=b'\0\r\n')
  read_chunk_size: int = field(default=4096)
  _read_buffer: bytearray = field(init=False, default=bytearray())

  # # Return self for use in async context managers
  # def __await__(self):
  #   return self

  async def read_debug(self) -> dict:
    """Reads a message from the IPC Stream & logs verbose debug information."""
    _uuid = uuid.uuid4()
    _logger.debug(f"read::{_uuid.hex}::Reading message from IPC...")
    _logger.debug(f"read::{_uuid.hex}::Buffer: {self._read_buffer}")
    _logger.debug(f"read::{_uuid.hex}::Message delimiter: {self.message_delimiter}")
    if self.reader is None:
      raise RuntimeError("IPCInterface has no reader.")
    # read a message from the reader
    while self.message_delimiter not in self._read_buffer:
      # _logger.debug(f"{_uuid.hex}::Delimiter not in buffer")
      # _logger.debug(f"{_uuid.hex}::Buffer: {self._read_buffer}")
      # _logger.debug(f"{_uuid.hex}::Reading from reader...")
      bytes_read = await self.reader.read(self.read_chunk_size)
      # _logger.debug(f"{_uuid.hex}::Read {len(bytes_read)} bytes from reader.")
      self._read_buffer += bytes_read
      # _logger.debug(f"{_uuid.hex}::Buffer: {self._read_buffer}")
    
    _logger.debug(f"read::{_uuid.hex}::Delimiter in buffer")
    message_bytes, self._read_buffer = self._read_buffer.split(self.message_delimiter, 1)

    message = json.loads(message_bytes)
    assert isinstance(message, dict), f"Message must be a dict but got {message.__class__.__name__}."
    if 'user' not in message:
      message['user'] = "user"
    assert {'user', 'content'} <= message.keys(), "Message must contain 'user' and 'content' keys."
    return message

  async def read(self) -> dict:
    return await self.read_debug()

  async def write_debug(self, message: dict) -> None:
    """Writes a message to the IPC Stream & logs verbose debug information."""
    assert isinstance(message, dict), f"Message must be a dict but got {message.__class__.__name__}."
    _uuid = uuid.uuid4()
    _logger.debug(f"write::{_uuid}: Writing message to IPC...")
    _logger.debug(f"write::{_uuid.hex}::Message delimiter: {self.message_delimiter}")
    if self.writer is None:
      raise RuntimeError("IPCInterface has no writer.")
    message_bytes = json.dumps(message).encode("utf-8") + self.message_delimiter
    _logger.debug(f"write::{_uuid.hex}::Message bytes: {message_bytes}")
    self.writer.write(message_bytes)
    _logger.debug(f"write::{_uuid}: Draining writer...")
    await self.writer.drain()
    _logger.debug(f"write::{_uuid}: Writer drained.")

  async def write(self, message: dict) -> None:
    await self.write_debug(message)

@dataclass
class TCPSocketManager:
  """Manages a Uniplex TCP Socket for IPC between two processes."""
  conn: tuple[str, int]
  role: Literal["server", "client"] | None = field(default=None)
  _socket: tuple[asyncio.StreamReader, asyncio.StreamWriter] | asyncio.Server | None = field(init=False, default=None)
  _task: asyncio.Task | None = field(init=False, default=None)
  _ipc: IPCInterface | asyncio.Event | None = field(init=False, default_factory=asyncio.Event)

  async def __aenter__(self) -> IPCInterface:
    """Setup the TCP Socket for IPC between two processes."""
    return await self.setup()
  
  async def __aexit__(self, exc_type, exc_value, traceback) -> None:
    await self.teardown()

  async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Setup the IPCInterface for a new connection to the server."""
    assert self.role == "server", "Role must be server."
    assert isinstance(self._ipc, asyncio.Event), f"IPC must be an Event but got {self._ipc.__class__.__name__}."
    _ipc_ready = self._ipc
    self._ipc = IPCInterface(reader, writer)
    _logger.info(f"New connection from {writer.get_extra_info('peername')}")
    _ipc_ready.set()

  async def _update_role(self):
    """Setup the socket determining the role while we are at it."""
    try:
      try:
        if self.role == "server":
          raise RuntimeError("Role already set to server.")
        _logger.debug(f"Attempting to connect to {self.conn[0]}:{self.conn[1]}")
        self._socket = await asyncio.open_connection(*self.conn)
        _logger.debug("Successfully connected to server.")
        self.role = "client"
      except (OSError, RuntimeError):
        _logger.debug(f"Starting server on {self.conn[0]}:{self.conn[1]}")
        self._socket = await asyncio.start_server(
          self._handle_connection,
          *self.conn,
        )
        _logger.debug("Server started...")
        self.role = "server"
    except:
      _logger.exception("Failed to determine role.")
    
    _logger.info(f"Role set to {self.role}")
  
  async def setup(self) -> IPCInterface:
    """Creates a TCP Socket for IPC between two processes."""
    _logger.debug("Setting up TCP Socket...")
    await self._update_role()
    _logger.debug(f"TCP Socket setup as {self.role}.")
    
    if self.role == "server":
      assert isinstance(self._socket, asyncio.Server), f"Socket must be a Server but got {self._socket.__class__.__name__}."
      assert self._task is None, "Task must be None."
      assert isinstance(self._ipc, asyncio.Event), f"IPC must be an Event but got {self._ipc.__class__.__name__}."
      _ipc_ready = self._ipc
      self._task = asyncio.create_task(self._socket.serve_forever())
      _logger.info(f"Listening on {self.conn[0]}:{self.conn[1]}")
      await _ipc_ready.wait()
    elif self.role == "client":
      assert isinstance(self._socket, tuple), f"Socket must be a tuple but got {type(self._socket).__name__}."
      assert self._task is None, f"Task must be None but got {type(self._task).__name__}."
      self._ipc = IPCInterface(
        reader=self._socket[0],
        writer=self._socket[1],
      )
      _logger.info(f"Connected to {self.conn[0]}:{self.conn[1]}")
    else:
      raise RuntimeError(f"Never should have come here! {self.role}.")
    
    _logger.debug("TCP Socket setup complete.")
    return self._ipc
  
  async def teardown(self):
    """Closes the TCP Socket & resets the Manager's state."""
    _logger.debug("Tearing down TCP Socket...")
    if self.role == "server":
      assert isinstance(self._socket, asyncio.Server), f"Socket must be a Server but got {type(self._socket).__name__}."
      assert self._task is not None, "Task must not be None."
      _logger.debug("Closing server...")
      self._socket.close()
      _logger.debug("Waiting for server to close...")
      await self._socket.wait_closed()
      _logger.debug("Server closed, cancelling task...")
      self._task.cancel()
      _logger.debug("Waiting for task to cancel...")
      await self._task
      _logger.debug("Task cancelled.")
      self._ipc = asyncio.Event()
      self._task = None
    elif self.role == "client":
      assert isinstance(self._socket, tuple), f"Socket must be a tuple but got {self._socket.__class__.__name__}."
      assert self._task is None, "Task must be None."
      _logger.debug("Closing TCP Socket...")
      self._socket[1].close()
      _logger.debug("Waiting for TCP Socket to close...")
      await self._socket[1].wait_closed()
      _logger.debug("TCP Socket closed.")
      self._ipc = asyncio.Event()
      self._socket = None
    else:
      raise RuntimeError(f"Never should have come here! {self.role}.")
    
    _logger.debug("TCP Socket teardown complete.")