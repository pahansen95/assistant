"""All things chat related. Chats are the basis of the knoweldge base."""
from dataclasses import dataclass

from .. import ENTITY_KIND
from . import (ChatSessionInterface, ChatSessionProperties, MessageInterface,
               MessageProperties)
import uuid


@dataclass
class Message(MessageProperties, MessageInterface):
  """A message sent from one entity to another"""
  id: uuid.UUID
  """A 128 bit UUID for the message"""
  entity_kind: ENTITY_KIND
  """The kind of entity this message originated from"""
  entity_id: uuid.UUID
  """The 128 bit UUID of the entity this message originated from"""
  content: str
  """The content of the message as a UTF-8 string"""
  timestamp: float
  """The UTC unix timestamp of when the message was submitted"""

  def to_dict(self) -> dict:
    """Converts the message to a JSON encodable dictionary"""
    return {
        "id": self.id.hex,
        "entity_kind": self.entity_kind.value,
        "entity_id": self.entity_id.hex,
        "content": self.content,
        "timestamp": self.timestamp,
    }

@dataclass
class ChatSession(ChatSessionProperties, ChatSessionInterface):
  id: uuid.UUID
  """A 128 bit UUID for the chat session"""
  start_timestamp: float
  """The UTC unix timestamp of when the chat session started"""
  latest_timestamp: float
  """The UTC unix timestamp of when the chat session was last updated"""
  message_ids: list[uuid.UUID]
  """A list of 128 bit UUIDs for the messages in the chat session"""

  def to_dict(self) -> dict:
    """Converts the chat session to a JSON encodable dictionary"""
    return {
        "id": self.id.hex,
        "start_timestamp": self.start_timestamp,
        "latest_timestamp": self.latest_timestamp,
        "message_ids": [message_id.hex for message_id in self.message_ids],
    }
  
  def add_message(self, message: Message):
    """Adds a message to the chat session"""
    self.message_ids.append(message.id)
    self.latest_timestamp = message.timestamp
