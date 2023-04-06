
from abc import ABC, abstractmethod
import uuid

from .. import ENTITY_KIND

### Contracts ###

class MessageProperties(ABC):
  """The base set of properties any message must have"""
  @property
  @abstractmethod
  def id(self) -> uuid.UUID:
    """A 128 bit UUID for the message"""
    ...
  @property
  @abstractmethod
  def entity_kind(self) -> ENTITY_KIND:
    """The kind of entity this message originated from"""
    ...
  @property
  @abstractmethod
  def entity_id(self) -> uuid.UUID:
    """The 128 bit UUID of the entity this message originated from"""
    ...
  @property
  @abstractmethod
  def content(self) -> str:
    """The content of the message as a UTF-8 string"""
    ...
  @property
  @abstractmethod
  def timestamp(self) -> float:
    """The UTC unix timestamp of when the message was submitted"""
    ...

class MessageInterface(ABC):
  """The baseline functionality a message must have"""
  @abstractmethod
  def to_dict(self) -> dict:
    """Converts the message to a JSON encodable dictionary"""
    ...

class ChatSessionProperties(ABC):
  """The base set of properties any chat session must have"""
  @property
  @abstractmethod
  def id(self) -> uuid.UUID:
    """A 128 bit UUID for the chat session"""
    ...
  @property
  @abstractmethod
  def start_timestamp(self) -> float:
    """The UTC unix timestamp of when the chat session started"""
    ...
  @property
  @abstractmethod
  def latest_timestamp(self) -> float:
    """The UTC unix timestamp of when the chat session was last updated"""
    ...
  @property
  @abstractmethod
  def message_ids(self) -> list[uuid.UUID]:
    """A list of 128 bit UUIDs for the messages in the chat session"""
    ...
  
class ChatSessionInterface(ABC):
  """The baseline functionality a chat session must have"""
  @abstractmethod
  def to_dict(self) -> dict:
    """Converts the chat session to a JSON encodable dictionary"""
    ...
  
  @abstractmethod
  def add_message(self, message: MessageProperties):
    """Adds a message to the chat session"""
    ...
