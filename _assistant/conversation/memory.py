from dataclasses import dataclass, field
import pathlib
import aiofiles
import json
import mmap

from .. import _logger, ENTITY
from . import MemoryInterface, RecallError

@dataclass
class EphemeralMemory(MemoryInterface):
  """A chat log that is buffered in system memory only for the duration of the conversation."""
  __buffer: list[tuple[ENTITY, str]] = field(default_factory=list, init=False)

  async def stage(self, entity: ENTITY, message: str):
    await _logger.trace(f"Logging message from {entity.name} to buffer")
    self.__buffer.append((entity, message))
  
  async def commit(self):
    await _logger.trace("Saving short term memory to long term memory")
    raise NotImplementedError("Long term memory is not yet supported")

  async def recall(self, index: int, entity: ENTITY = None) -> tuple[ENTITY, str]:
    if entity is None:
      await _logger.trace(f"Looking up message at index {index} in buffer")
      try:
        return self.__buffer[index]
      except IndexError:
        raise RecallError(f"Couldn't recall a message that is {index} old.")
    
    await _logger.trace(f"Looking up message from {entity.name} in buffer")
    try:
      return next(filter(lambda x: x[0] == entity, self.__buffer))
    except IndexError:
      raise RecallError(f"Couldn't recall a message from {entity.name} that is {index} old.")
  
  async def forget(self):
    await _logger.trace("Clearing buffer")
    self.__buffer.clear()

@dataclass
class PersistentMemory(MemoryInterface):
  """A chat log that is buffered to & from a file."""
  file: str
  __mmap: mmap.mmap = field(default=None, init=False)
  __seperator: bytes = field(default=b"\x00\x00\x00\x00", init=False)
  __mmap_size: int = field(default=4*1024**1, init=False) # 4kb
  __mmap_offset: int = field(default=0, init=False)
  __head: int = field(init=False)
  __tail: int = field(init=False)
  """The index where 0 is the last message & -1 is the first message in the file."""

  def __post_init__(self):
    _file = pathlib.Path(self.file)
    if not _file.parent.exists():
      raise FileNotFoundError(f"Couldn't find directory {self.file.parent}")
    if not _file.exists():
      _file.touch()

    # Open the last 4kb of the file in read/write mode
    self.__mmap_offset = max(0, _file.stat().st_size - self.__mmap_size)
    self.__mmap = mmap.mmap(
      _file.open("r+b").fileno(),
      self.__mmap_size,
      offset=self.__mmap_offset,
    )
    # find the index of the first seperator
    try:
      self.__head = self.__mmap.find(self.__seperator)
    except ValueError:
      self.__head = 0
    # find the index of the last seperator
    try:
      self.__tail = self.__mmap.rfind(self.__seperator)
    except ValueError:
      self.__tail = 0
  
  def __next_item(self) -> tuple[ENTITY, str]:
    """Return the next item in the buffer."""
    # Find the next seperator
    try:
      next_seperator = self.__mmap.find(self.__seperator, self.__head)
    except ValueError:
      raise StopIteration("No more items in buffer")
    # Get the item from the buffer
    item = json.loads(self.__mmap[self.__head:next_seperator].decode("utf-8"))
    # Update the head
    self.__head = next_seperator + len(self.__seperator)
    # Return the item
    return item
  
  def __last_item(self) -> tuple[ENTITY, str]:
    """Return the last item in the buffer."""
    # Find the last seperator
    try:
      last_seperator = self.__mmap.rfind(self.__seperator, self.__tail)
    except ValueError:
      raise StopIteration("No more items in buffer")
    # Get the item from the buffer
    item = json.loads(self.__mmap[last_seperator:self.__tail].decode("utf-8"))
    # Update the tail
    self.__tail = last_seperator
    # Return the item
    return item

  async def stage(self, entity: ENTITY, message: str):
    await _logger.trace(f"Logging message from {entity.name} to buffer")
    # Write the message to the file
    self.__mmap[self.__tail:] = json.dumps([
      entity.value,
      message
    ]).encode("utf-8")
    self.__mmap[self.__tail + len(message):] = self.__seperator
    self.__tail += len(message) + len(self.__seperator)    
    self.__mmap.flush()
  
  async def commit(self):
    await _logger.trace("Saving short term memory to long term memory")
    raise NotImplementedError("Long term memory is not yet supported")

  async def recall(self, index: int, entity: ENTITY = None) -> tuple[ENTITY, str]:
    """Lookup a message by index & optionally entity."""
    if entity is None:
      await _logger.trace(f"Looking up message at index {index} in buffer")
      try:
        return self.__buffer[index]
      except IndexError:
        raise RecallError(f"Couldn't recall a message that is {index} old.")
    
    await _logger.trace(f"Looking up message from {entity.name} in buffer")
    try:
      return next(filter(lambda x: x[0] == entity, self.__buffer))
    except IndexError:
      raise RecallError(f"Couldn't recall a message from {entity.name} that is {index} old.")
  
  async def forget(self):
    await _logger.trace("Clearing buffer")
    self.__buffer.clear()
