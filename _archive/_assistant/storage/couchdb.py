from . import ENTITY, ShortTermMemoryStorageInterface, StorageError
from dataclasses import dataclass
import aiohttp

@dataclass
class CouchDB(ShortTermMemoryStorageInterface):
  """The interface for the assistant's short term memory backed by CouchDB.
  Each data 
  """
  db_session: aiohttp.ClientSession

  async def save(self, entity: ENTITY, message: str):
    """Saves a message to short term memory"""
    ...

  async def load(self, entity: ENTITY, index: int) -> str:
    """Loads a message from short term memory"""
    ...