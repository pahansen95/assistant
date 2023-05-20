from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

M = TypeVar("M")

def _msg_hash(author: str, timestamp: int) -> int:
  return hash((
    author,
    timestamp
  ))

class MessageError(Exception):
  pass

class DuplicateMessageError(MessageError):
  pass

class MessageNotFoundError(MessageError):
  pass

@dataclass
class _Message(Generic[M]):
  author: str
  timestamp: int
  message: M

  def __hash__(self) -> int:
    return _msg_hash(self.author, self.timestamp)

@dataclass
class ChatTranscript(Generic[M]):
  log: dict[int, _Message[M]] = field(default_factory=dict)

  def add(self, author: str, timestamp: int, message: M) -> None:
    if _msg_hash(author, timestamp) in self.log:
      raise DuplicateMessageError(author, timestamp)
    self.log[_msg_hash(author, timestamp)] = _Message(author, timestamp, message)
  
  def get(self, author: str, timestamp: int) -> M:
    if _msg_hash(author, timestamp) not in self.log:
      raise MessageNotFoundError(author, timestamp)
    return self.log[_msg_hash(author, timestamp)].message
  
  def remove(self, author: str, timestamp: int) -> None:
    if _msg_hash(author, timestamp) not in self.log:
      raise MessageNotFoundError(author, timestamp)
    del self.log[_msg_hash(author, timestamp)]
  
  def conversation(self) -> list[tuple[str, M]]:
    """Return a list of messages ordered by timestamp."""
    return [
      (
        msg.author,
        msg.message,
      )
      for msg in sorted(
        self.log.values(),
        key=lambda msg: msg.timestamp
      )
    ]