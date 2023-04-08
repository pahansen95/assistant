from dataclasses import dataclass, field
import networkx as nx
from . import EntityProperties, ChatMessage
from typing import Iterable

@dataclass
class ChatTranscript:
  """Log Chat Messages & record the conversation flow."""
  conversation: nx.DiGraph[int] = field(default_factory=nx.DiGraph)
  """The relationship between messages in the chat. Each node is the hash of a message & each edge is the hash of the message that the node is in response to."""
  entities: dict[int, EntityProperties] = field(default_factory=dict)
  """All the entities in the chat. The key is the entity's hash & the value is the entity itself."""
  messages: dict[int, ChatMessage] = field(default_factory=dict)
  """The underlying messages of the chat. The key is the message's hash & the value is the message itself."""
  
  def entity_said(
    self,
    entity: EntityProperties,
    said: str,
    in_response_to: Iterable[ChatMessage] | ChatMessage | None = None,
  ) -> ChatMessage:
    """Records a message from an entity updating the conversational Graph. Returns the message."""
    # check to make sure that in_response_to doesn't have any unknown messages
    if in_response_to is None:
      in_response_to = []
    elif isinstance(in_response_to, ChatMessage):
      in_response_to = [in_response_to]
    
    for index, response in enumerate(in_response_to):
      if hash(response) not in self.messages:
        raise ValueError(f"Unknown message at index {index}")

    # create a new message
    message = ChatMessage(
      content=said,
      entity=entity,
    )
    # Check if this message already exists
    if hash(message) in self.messages:
      # Get the matching message from the existing messages
      message = self.messages[hash(message)]
    else:
      # Add the entity & message to the existing messages
      if hash(entity) not in self.entities:
        self.entities[hash(entity)] = entity
      self.messages[hash(message)] = message
        
    # Update the Conversation Graph
    self.conversation.add_node(
      message,
    )
    
    # Update the conversation graph to reflect the message's relationship to other messages
    for response in in_response_to:
      self.conversation.add_edge(
        response,
        message,
      )

    return message
