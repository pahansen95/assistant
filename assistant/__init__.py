"""TODO: Add module docstring"""
import enum
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (AsyncIterable, Callable, Iterable,
                    NamedTuple)

import networkx as nx

from ._misc import *


class AssistantError(Exception):
  """Base class for exceptions in this module."""
  pass

class _CallbackHandler(logging.Handler):
  """A logging handler that hands off the log message to a callback"""
  def __init__(
    self,
    callback: Callable[[logging.LogRecord], None]
  ):
    super().__init__()
    self.callback = callback

  def emit(self, record: logging.LogRecord):
    self.callback(record)

class _MODULE_LOG_LEVELS(enum.IntEnum):
  """The logging levels for the assistant module"""
  ANNOYING = 1
  TRACE = 5
  DEBUG = 10
  INFO = 20
  WARNING = 30
  ERROR = 40
  SUCCESS = 40
  CRITICAL = 50
  FATAL = 50

@dataclass
class _ModuleLogger:
  logger: logging.Logger
  level: _MODULE_LOG_LEVELS

  def __post_init__(self):
    self.logger.setLevel(self.level.value)
  
  def annoying(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.ANNOYING.value, msg)
  annoy = annoying
  
  def trace(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.TRACE.value, msg)
  
  def debug(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.DEBUG.value, msg)
  
  def info(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.INFO.value, msg)

  def warning(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.WARNING.value, msg)
  warn = warning
    
  def error(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.ERROR.value, msg)

  def success(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.SUCCESS.value, msg)

  def critical(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.CRITICAL.value, msg)

  def fatal(self, msg: str):
    self.logger.log(_MODULE_LOG_LEVELS.FATAL.value, msg)

_logging_name = "assistant"
_logger = _ModuleLogger(
  logger=logging.getLogger(_logging_name), # an empty logger
  level=_MODULE_LOG_LEVELS.ANNOYING,
)
# _logger.trace("TEST TRACE")
# _logger.critical("TEST CRITICAL")
# _logger.logger.addHandler(
#   _CallbackHandler(
#     callback=lambda record: print(f"MODULE DEVELOPMENT::{_MODULE_LOG_LEVELS(record.levelno).name.upper()}::{record.msg}", flush=True)
#   )
# )

@dataclass(frozen=True)
class MetaProp:
  name: str
  description: str
  _type: type
  immutable: bool = False

def properties_interface_factory(
  *props: MetaProp,
) -> Callable[[type], type]:
  """A Class decorator that injects into an abstract base class:
    - Abstract Getters & Setters for each property
    - A Mixin class that is a convenience for implementing the abstract base class
  """
  _logger.trace(f"Creating properties interface for {props}")
  # Assert there are no duplicate property names
  assert len(props) == len(set(prop.name for prop in props)), "Duplicate property names"
  
  def _abstract_getter(self):
    raise NotImplementedError("Abstract property getter not implemented")
  
  def _abstract_setter(self, value):
    raise NotImplementedError("Abstract property setter not implemented")
    
  def _getter_factory(_prop_name: str):
    _logger.trace(f"Creating getter for {_prop_name}")
    def _getter(self):
      _logger.annoy(f"Getting property {_prop_name}")
      return getattr(
        self,
        f"_{_prop_name}"
      )
    return _getter

  def _setter_factory(_prop_name: str):
    _logger.trace(f"Creating setter for {_prop_name}")
    def _setter(self, value):
      _logger.annoy(f"Setting property {_prop_name}")
      setattr(
        self,
        f"_{_prop_name}",
        value
      )
    return _setter
  
  def _inject_property_interface(abc_class: type) -> type:
    # Check that the class is an ABC
    _logger.trace(f"Injecting properties into {abc_class.__name__}")
    if not issubclass(abc_class, ABC):
      raise TypeError(f"{abc_class} is not an ABC")
    
    for prop_def in props:      
      # Inject the property into the ABC Class
      setattr(
        abc_class,
        prop_def.name,
        property(
          fget=_abstract_getter,
          fset=_abstract_setter if not prop_def.immutable else None,
          doc=prop_def.description,
        )
      )

      # Set the type hint
      abc_class.__annotations__[prop_def.name] = prop_def._type
    
    # Create the Mixin subclass
    mixin_class = type(
      f"{abc_class.__name__}PropsMixin",
      (),
      {},
    )

    # Inject the properties into the Mixin
    for prop_def in props:
      # Inject the property into the Mixin
      setattr(
        mixin_class,
        prop_def.name,
        property(
          fget=_getter_factory(prop_def.name),
          fset=_setter_factory(prop_def.name) if not prop_def.immutable else None,
          doc=prop_def.description,
        )
      )

      # Set the type hint
      mixin_class.__annotations__[prop_def.name] = prop_def._type

    # Inject the Mixin into the ABC
    setattr(
      abc_class,
      "PropsMixin",
      mixin_class,
    )
    _logger.debug("Returning property Abstract Class")
    return abc_class
  
  _logger.debug("Returning property interface factory")
  return _inject_property_interface


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
  def token_count(self, model: str, *text: str) -> int:
    """Returns the number of tokens in the given text"""
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

_logger.trace("Creating properties interface for EntityProperties")
@properties_interface_factory(
  MetaProp(
    name="name",
    description="The name of the entity",
    _type=str,
    immutable=True,
  ),
  MetaProp(
    name="description",
    description="The description of the entity",
    _type=str,
    immutable=True,
  ),
  MetaProp(
    name="uuid",
    description="The UUID of the entity",
    _type=uuid.UUID,
    immutable=True,
  ),
)
class EntityProperties(ABC):
  """Defines the base set of properties that identify an entity."""
  
  def __hash__(self) -> int:
    """A hash of the entity properties to use in things such as set operations."""
    return hash(self.name, self.uuid.bytes)


class EntityInterface(ABC):
  """Defines the interface for an entity."""
  @abstractmethod
  async def think(
    self,
    idea: str,
    context: Iterable[str],
    model: str,
    thinking_personality: str,
  ) -> str:
    """The entity reflects on a thought seeking to improve it."""
    ...
  
  @abstractmethod
  async def respond(
    self,
    chat: Iterable[str],
    context: Iterable[str],
    model: str,
    responding_personality: str,
    reflection_personality: str,
  ) -> str:
    """Respond to the chat. The entity will think of a response, reflect on it & then respond accordingly."""
    ...
  
@dataclass(frozen=True)
class ChatMessage:
  """An immutable message in a chat transcript."""
  content: str
  entity: EntityProperties
  published: float

@properties_interface_factory(
  MetaProp(
    name="conversation",
    description="The conversation as a directed graph.",
    _type=nx.DiGraph,
  ),
  MetaProp(
    name="entities",
    description="The entities that participated in the conversation.",
    _type=set[EntityProperties],
  ),
  MetaProp(
    name="messages",
    description="All the conversation's message buffer.",
    _type=list[ChatMessage],
  ),
)
class TranscriptProperties(ABC):
  """Defines the base set of properties that identify a transcript."""

class TranscriptInterface(ABC):
  """Defines the interface for recording a conversation as a Directed Graph."""

  @abstractmethod
  async def __aenter__(self):
    """Acquire the lock on the transcript."""
    ...
  
  @abstractmethod
  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Release the lock on the transcript."""
    ...

  @abstractmethod
  def message_exists(self, msg: ChatMessage) -> bool:
    """Check if a message exists in the transcript."""
    ...

  @abstractmethod
  def entity_said(
    self,
    entity: EntityProperties,
    said: str,
    when: float,
    in_response_to: Iterable[ChatMessage] | ChatMessage | None = None,
  ):
    """Record that an entity said something."""
    ...
  
  @abstractmethod
  def get_message_history(
    self,
    msg: ChatMessage,
    depth: int,
  ) -> list[ChatMessage]:
    """Get the message history of a message. The msg is at the end of the list."""
    ...