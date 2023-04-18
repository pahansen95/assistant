from .. import ENTITY, Error
from abc import ABC, abstractmethod

class StorageError(Error):
  """Base class for storage errors."""
  ...


class ShortTermMemoryStorageInterface(ABC):
  """The interface for the assistant's short term memory
  It's assumed there is a one to one relationship between short term memory & a conversation.
  """
  
  @abstractmethod
  async def save(self, entity: ENTITY, message: str):
    """Saves a message to short term memory"""
    ...
  
  @abstractmethod
  async def load(self, entity: ENTITY, index: int) -> str:
    """Loads a message from short term memory"""
    ...

class LongTermMemoryStorageInterface(ABC):
  """The interface for the assistant's long term memory"""
  ...