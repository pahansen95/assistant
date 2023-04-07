"""TODO: Add module docstring"""
import enum
from abc import ABC, abstractmethod
from typing import AsyncIterable, Iterable, NamedTuple

ANDROGYNOUS_NAMES: tuple[str] = (
  "Alex",
  "Avery",
  "Bailey",
  "Blair",
  "Bobby",
  "Brett",
  "Brook",
  "Cameron",
  "Campbell",
  "Casey",
  "Charlie",
  "Chris",
  "Dakota",
  "Dana",
  "Drew",
  "Eli",
  "Elliot",
  "Emerson",
  "Finley",
  "Frankie",
  "Gale",
  "Harley",
  "Hayden",
  "Hunter",
  "Jackie",
  "Jamie",
  "Jay",
  "Jesse",
  "Jordan",
  "Jules",
  "Kai",
  "Kendall",
  "Kerry",
  "Kim",
  "Kris",
  "Kyle",
  "Lee",
  "Logan",
  "London",
  "Mackenzie",
  "Madison",
  "Max",
  "Morgan",
  "Nicky",
  "Noah",
  "Parker",
  "Pat",
  "Peyton",
  "Phoenix",
  "Quinn",
  "Randy",
  "Reagan",
  "Reese",
  "Riley",
  "River",
  "Robin",
  "Rowan",
  "Ryan",
  "Sage",
  "Sam",
  "Sandy",
  "Sawyer",
  "Shawn",
  "Sidney",
  "Sky",
  "Spencer",
  "Stevie",
  "Terry",
  "Taylor",
  "Toni",
  "Tyler",
  "Val",
  "Whitney",
  "Wren"
)


class AssistantError(Exception):
  """Base class for exceptions in this module."""
  pass

class _LoggingInterface(ABC):
  """A placeholder for the logging function"""
  async def fatal(self, msg: str):
    await self(msg=msg, level="fatal")
  async def critical(self, msg: str):
    await self(msg=msg, level="critical")
  async def error(self, msg: str):
    await self(msg=msg, level="error")
  async def success(self, msg: str):
    await self(msg=msg, level="success")
  async def warning(self, msg: str):
    await self(msg=msg, level="warning")
  async def info(self, msg: str):
    await self(msg=msg, level="info")
  async def debug(self, msg: str):
    await self(msg=msg, level="debug")
  async def trace(self, msg: str):
    await self(msg=msg, level="trace")
  @abstractmethod
  async def __call__(self, msg: str, level: str):
    ...

class _DummyLogger(_LoggingInterface):
  """A dummy logger that does nothing"""
  async def __call__(self, msg: str, level: str):
    pass

_logger = _DummyLogger()

def set_logger(logger: _LoggingInterface):
  """Sets the logger to use for logging"""
  global _logger
  _logger = logger

class PROMPT_MESSAGE_ROLE(enum.Enum):
  USER = "user"
  ASSISTANT = "assistant"
  SYSTEM = "system"

class PROMPT_PERSONALITY(enum.Enum):
  """Influences the response of the LLM"""
  CREATIVE = "creative"
  BALANCED = "balanced"
  RESERVED = "reserved"

class PromptMessage(NamedTuple):
  """A message to prompt the LLM with"""
  content: str
  role: PROMPT_MESSAGE_ROLE

class PromptInterface(ABC):
  """Defines the interface for prompting for a response."""

  @property
  @abstractmethod
  def models(self) -> list[str]:
    """Returns a tuple of the available LLM models"""
    ...
  
  @abstractmethod
  async def __aiter__(
    self,
    messages: Iterable[PromptMessage],
    model: str, # The Specific LLM to use
    personality: PROMPT_PERSONALITY,
  ) -> AsyncIterable[str]:
    """Asynchronously prompt the LLM for a response. Streams the response. Can't retry a stream. Use `__call__` instead."""
    ...

  @abstractmethod
  async def __call__(
    self,
    messages: Iterable[PromptMessage],
    model: str, # The Specific LLM to use
    personality: PROMPT_PERSONALITY,
    max_retry_count: int = 3
  ) -> str:
    """Asynchronously prompt the LLM for a response. Returns the response all at once.
    This is a convenience method that wraps `__aiter__`
    Args:
      messages: The messages to prompt the LLM with.
      personality: The personality to use when prompting the LLM.
      max_retry_count: The maximum number of times to retry prompting the LLM if an error occurs.
    """
    ...

class ResponseError(AssistantError):
  """Raised when the LLM returns an error."""
  def __init__(self, error: str):
    self.error = error

class ResponseIncomplete(AssistantError):
  """Raised when the LLM returns an incomplete response."""
  def __init__(self, reason: str):
    self.reason = reason