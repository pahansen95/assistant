from .. import _logger, ENTITY, Error
from abc import ABC, abstractmethod
from typing import Any

class MemoryError(Error):
  """Base class for memory errors."""
  ...

class RecallError(MemoryError):
  """Failed to recall a message from short term memory."""
  ...

class MessagingInterface(ABC):
  """An interface for sending messages to & recieving messages from an entity."""
  
  @abstractmethod
  async def send(self, message: str, context: list[ENTITY, str]):
    """Prompts the entit for a message"""
    pass

  @abstractmethod
  async def receive(self) -> str:
    """Recieves a message from the entity"""
    pass

class MemoryInterface(ABC):
  """An interface for managing chat messages over the duration of a conversation"""

  @abstractmethod
  async def stage(self, entity: ENTITY, message: str):
    """Puts a message in short term memory."""
    ...
  
  @abstractmethod
  async def commit(self):
    """Commits all short term memory to long term memory"""
    ...
  
  @abstractmethod
  async def recall(self, index: int, entity: ENTITY = None) -> tuple[ENTITY, str]:
    """Lookup a message in short term memory by index & optionally entity"""
    ...

  @abstractmethod
  async def forget(self):
    """Drop all of short term memory"""
    ...
  
  # TODO Long term memory

class ConversationInterface(ABC):
  """An interface for conversing between entities"""
  
  @abstractmethod
  async def __call__(self, **kwargs) -> str:
    """The loop that handles the conversation"""
    ...


