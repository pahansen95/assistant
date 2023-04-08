from dataclasses import dataclass, field
import networkx as nx
import networkx.algorithms.dag as dag
from . import EntityProperties, ChatMessage, TranscriptInterface, TranscriptProperties, _logger
from typing import Iterable, AsyncGenerator
from asyncio import Lock
import contextlib


@dataclass
class ChatTranscript(TranscriptProperties.PropsMixin, TranscriptProperties, TranscriptInterface):
  """Log Chat Messages & record the conversation flow."""
  _conversation: nx.DiGraph = field(default_factory=nx.DiGraph)
  """The relationship between messages in the chat. Each node is the hash of a message & each edge is the hash of the message that the node is in response to."""
  _entities: dict[int, EntityProperties] = field(default_factory=dict)
  """All the entities in the chat. The key is the entity's hash & the value is the entity itself."""
  _messages: dict[int, ChatMessage] = field(default_factory=dict)
  """The underlying messages of the chat. The key is the message's hash & the value is the message itself."""
  _lock: Lock = field(default_factory=Lock)
  
  async def __aenter__(self):
    """Acquire the lock on the transcript."""
    await self._lock.acquire()
  
  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Release the lock on the transcript."""
    self._lock.release()

  def message_exists(self, msg: ChatMessage) -> bool:
    """Check if a message exists in the transcript."""
    return hash(msg) in self._messages

  def entity_said(
    self,
    entity: EntityProperties,
    said: str,
    when: float,
    in_response_to: Iterable[ChatMessage] | ChatMessage | None = None,
  ) -> ChatMessage:
    """Records a message from an entity updating the conversational Graph. Returns the message."""
    _logger.trace("Acquiring Transcript lock")
    # check to make sure that in_response_to doesn't have any unknown messages
    if in_response_to is None:
      in_response_to = []
    elif isinstance(in_response_to, ChatMessage):
      in_response_to = [in_response_to]
    
    _logger.trace(f"The response chain is {len(in_response_to)} messages long")
    
    for index, response in enumerate(in_response_to):
      if hash(response) not in self._messages:
        raise ValueError(f"Unknown message at index {index}")

    # create a new message
    message = ChatMessage(
      content=said,
      entity=entity,
      published=when,
    )
    _logger.annoying(f"Creating new message for entity {entity.name}")
    # Check if this message already exists
    if hash(message) in self._messages:
      _logger.annoying("Message already exists")
      # Get the matching message from the existing messages
      message = self._messages[hash(message)]
    else:
      # Add the entity & message to the existing messages
      _logger.trace("Adding message to transcript")
      if hash(entity) not in self._entities:
        _logger.info(f"Adding new entity {entity.name} to transcript")
        self._entities[hash(entity)] = entity
      self._messages[hash(message)] = message
    
    # TODO: Get the youngest message in the conversation

    # Update the Conversation Graph
    _logger.trace("Adding Message to conversation graph")
    self._conversation.add_node(
      message,
    )

    # TODO: Add an edge from the (previous) youngest message to the new message
    
    # Update the conversation graph to reflect the message's relationship to other messages
    _logger.trace("Updating Message relationships in conversation graph")
    for response in in_response_to:
      self._conversation.add_edge(
        response,
        message,
      )

    return message

  def get_message_history(
    self,
    msg: ChatMessage,
    depth: int | None = None,
  ) -> list[ChatMessage]:
    """Get a chain of messages. Optionally up to a certain depth. The msg is at the end of the list."""
    _logger.trace(f"Getting message history up to depth {depth}")
    # For now we just assume the longest path is what we want
    msgs = list(
      dag.dag_longest_path(
        self._conversation.subgraph(
          dag.ancestors(
            self._conversation,
            msg,
          ) | {msg},
        )
      )
    )
    if not isinstance(msgs[0], ChatMessage):
      raise NotImplementedError("The longest path algorithm returned multiple paths. This is not supported yet.")
    if depth is not None:
      if depth == 0:
        _logger.warning("Depth was 0. Returning an empty list")
      msgs = msgs[:min(depth, len(msgs))]
    return msgs
