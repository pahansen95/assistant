"""Manage communication to/from the assistant.
"""

import asyncio
import contextlib
import enum
from abc import ABC, abstractmethod
from typing import NamedTuple
import json
from os import urandom
from dataclasses import dataclass, field, KW_ONLY

from uri import URI
import zmq
import zmq.asyncio as aiozmq

from .. import AssistantError


class ChannelError(AssistantError):
  """Base class for exceptions in this module."""
  pass

class WrongStateError(ChannelError):
  """Raised when an operation is performed on a channel in an invalid state."""
  pass

class UnsupportedRoleError(ChannelError):
  """Raised when an unsupported role is specified."""
  pass

class BadPeerError(ChannelError):
  """Raised when the peer misbehaves."""
  def __init__(self, msg: '_Message', *args) -> None:
    super().__init__(*args)
    self.msg = msg    

class OutOfOrderError(BadPeerError):
  """Raised when a message is received out of order."""
  pass

class UnknownSessionError(BadPeerError):
  """Raised when a message is received with an unknown session id."""
  pass

class CHANNEL_STATE(enum.Enum):
  """The state of the channel"""
  OFFLINE = enum.auto()
  SETUP = enum.auto()
  ONLINE = enum.auto()
  TEARDOWN = enum.auto()

class CHANNEL_ROLE(enum.Enum):
  """The role of the channel"""
  SERVER = 0
  CLIENT = enum.auto()

class _topic(NamedTuple):
  """A compact representation of a topic & its corresponding queues."""
  topic: str
  inbox: asyncio.Queue | None
  outbox: asyncio.Queue | None

### Contracts ###

class ChannelProperties(ABC):
  """The base set of properties any channel must have.
  """
  @property
  @abstractmethod
  def context(self) -> aiozmq.Context:
    """The channel's underlying ZeroMQ Context"""
    ...
  
  @property
  @abstractmethod
  def socket(self) -> aiozmq.Socket:
    """The channel's underlying ZeroMQ Socket"""
    ...
  
  @property
  @abstractmethod
  def state(self) -> CHANNEL_STATE:
    """The state of the channel"""
    ...
  
  @property
  @abstractmethod
  def topics(self) -> set[str]:
    """The set of topics the channel has registered."""
    ...
  
  @property
  @abstractmethod
  def subscriptions(self) -> set[tuple[str, asyncio.Queue]]:
    """The set of subscribed topics & their corresponding inbox queues"""
    ...
  
  @property
  @abstractmethod
  def publications(self) -> set[tuple[str, asyncio.Queue]]:
    """The set of topics & their corresponding outbox queues"""
    ...
  
  @property
  @abstractmethod
  def role(self) -> CHANNEL_ROLE:
    """The role of the channel"""
    ...
  
  @property
  @abstractmethod
  def url(self) -> URI:
    """The URL of the channel"""
    ...

class ChannelInterface(ABC):
  """The baseline functionality a channel must have.
  A channel allows 1-to-1 communicataion using a pub/sub
  paradigm with a only once delivery guarantee.
  Messages are encoded as JSON Objects.
  Topics are simple unique strings. There is no hierarchy, wildcards or globbing.
  """

  @contextlib.asynccontextmanager
  @abstractmethod
  async def __call__(self) -> 'ChannelInterface':
    """A context manager for setting up & tearing down the channel."""
    ...

  @abstractmethod
  async def setup(self):
    """Setup the caller's end of the channel."""
    ...
  
  @abstractmethod
  async def teardown(self):
    """Teardown the caller's end of the channel."""
    ...
  
  @abstractmethod
  async def register(self, topic: str):
    """Registers a topic with the peer. Allocates new inbox & outbox queues for the topic."""
    ...
  
  @abstractmethod
  async def unregister(self, topic: str):
    """Unregisters a topic with the peer. Deallocates the inbox & outbox queues for the topic."""
    ...

  @abstractmethod
  async def publish(self, topic: str) -> asyncio.Queue:
    """Get the outbox queue for a pre-registerd topic. Callers can then publish messages to the topic by placing them in the queue."""
    ...
  
  @abstractmethod
  async def subscribe(self, topic: str) -> asyncio.Queue:
    """Get the inbox queue for a pre-registerd topic. Callers can then receive messages from the topic by reading from the queue."""
    ...

### Shared Implementation ###

class _id(NamedTuple):
  """A compact representation of a session ID."""
  session: int
  """The session ID as a 64 bit integer."""
  object: int
  """The object's ID as a 64 bit integer. An object can be a peer, topic, message, etc."""

  def to_hex(self) -> str:
    """Converts the ID to a hex string."""
    return f'{self.session:016x}{self.object:016x}'

  @classmethod
  def from_hex(cls, data: str) -> '_id':
    """Converts a hex string to an ID."""
    return cls(
      session=int(data[:16], 16),
      object=int(data[16:], 16),
    )
  
  def increment(self) -> '_id':
    """Increments the object ID."""
    return _id(self.session, self.object + 1)

class _MessageKind(enum.Enum):
  """The kind of channel message being sent"""
  SESSION_JOIN = enum.auto()
  """Informs the other peer that the sender is joining the channel session."""
  SESSION_LEAVE = enum.auto()
  """Informs the other peer that the sender is leaving the channel session."""
  TOPIC_REGISTER = enum.auto()
  """Inform the other peer that the sender is registering a topic."""
  TOPIC_DEREGISTER = enum.auto()
  """Inform the other peer that the sender is unregistering a topic."""
  APPLICATION = enum.auto()
  """Informs the other peer that the sender has sent a message on a topic."""
  ACKNOWLEDGE = enum.auto()
  """Informs the other peer that the sender has received a channel message."""
  ERROR = enum.auto()
  """Informs the other peer that the sender has encountered an error."""

class _Message(NamedTuple):
  """A compact representation a Network Application Message."""
  id: _id
  """The id to uniquely identify the message within the context of a session."""
  kind: _MessageKind
  """The kind of channel message being sent"""
  content: dict[str, str] | None
  """The content of the channel message being sent. Must be JSON (de)serializable."""

  def to_bytes(self) -> bytes:
    """Converts the message to a byte array."""
    return json.dumps({
      'id': self.id.to_hex(),
      'kind': self.kind.name,
      'content': self.content,
    }).encode('utf-8')

  @classmethod
  def from_bytes(cls, data: bytes) -> '_Message':
    """Converts a byte array to a message."""
    data = json.loads(data)
    return cls(
      id=_id.from_hex(data['id']),
      kind=_MessageKind[data['kind']],
      content=data['content']
    )

@dataclass
class Channel(ChannelProperties, ChannelInterface):
  """A channel for communicating with external systems such as an entity"""
  url: URI
  """The URL of the channel"""
  context: aiozmq.Context
  """The channel's underlying ZeroMQ Context used to manage the socket"""
  role: CHANNEL_ROLE
  """The role of the channel"""
  _: KW_ONLY
  state: CHANNEL_STATE = field(default=CHANNEL_STATE.OFFLINE)
  """The state of the channel"""
  __topics: list[_topic] = field(default_factory=list, init=False)
  """The set of topics the channel has registered."""
  __socket: aiozmq.Socket = field(default=None, init=False)
  """The channel's underlying ZeroMQ Socket"""
  __session_id: int = field(init=False)
  """The session id of the channel"""
  __last_message_id: int = field(init=False)
  """The last message id of the channel"""
  __self_id: int = field(init=False, default_factory=lambda: int.from_bytes(urandom(8)))
  """A 64 bit random number used to fingerprint us channel"""
  __peer_id: int = field(init=False)
  """The peer's id as a 64 bit number"""

  @property
  def socket(self) -> aiozmq.Socket:
    """The channel's underlying ZeroMQ Socket"""
    if self.__socket is None:
      raise WrongStateError("Socket has not been initialized")
    return self.__socket

  @property
  def topics(self) -> set[str]:
    """The set of topics the channel has registered."""
    return set(topic.topic for topic in self.__topics)
  
  @property
  def subscriptions(self) -> set[tuple[str, asyncio.Queue]]:
    """The set of subscribed topics & their corresponding inbox queues"""
    return set((topic, topic.inbox) for topic in self.__topics.values() if topic.inbox)
  
  @property
  def publications(self) -> set[tuple[str, asyncio.Queue]]:
    """The set of topics & their corresponding outbox queues"""
    return set((topic, topic.outbox) for topic in self.__topics.values() if topic.outbox)
  
  async def __send_message_to_peer(
    self,
    kind: _MessageKind,
    content: dict[str, str]
  ):
    """Sends a message to the peer accross the channel"""
    if self.state in (CHANNEL_STATE.OFFLINE):
      raise WrongStateError("Cannot Send & Receive on an offline channel")
    
    if self.state in (CHANNEL_STATE.ONLINE):
      assert self.__session_id is not None and self.__last_message_id is not None
    
    self.__last_message_id += 1
    await self.__socket.send(_Message(
      id=_id(
        session=self.__session_id,
        object=self.__last_message_id
      ),
      kind=kind,
      content=content
    ).to_bytes())
  
  async def __recv_message_from_peer(self) -> _Message:
    """Recieves a message from the peer accross the channel"""
    if self.state in (CHANNEL_STATE.OFFLINE):
      raise WrongStateError("Cannot Receive on an offline channel")
    
    if self.state in (CHANNEL_STATE.ONLINE):
      assert self.__session_id is not None and self.__last_message_id is not None
    
    peer_msg = _Message.from_bytes(await self.__socket.recv())
    
    # Enforce session id & message id ordering
    if self.state in (CHANNEL_STATE.ONLINE):
      if peer_msg.id.session != self.__session_id:
        raise UnknownSessionError(peer_msg)
      if peer_msg.id.object != self.__last_message_id + 1:
        raise OutOfOrderError(peer_msg)
    
    return peer_msg
  
  async def __send_message_to_peer_and_recv_ack(
    self,
    kind: _MessageKind,
    content: dict[str, str]
  ) -> _Message:
    """Sends a message to the peer accross the channel & recieves the expected response"""
    valid_response_kinds: set[_MessageKind] = set()
    if kind in (_MessageKind.JOIN, _MessageKind.LEAVE, _MessageKind.TOPIC_REGISTER, _MessageKind.TOPIC_UNREGISTER, _MessageKind.TOPIC_MESSAGE):
      valid_response_kinds.add(_MessageKind.ACKNOWLEDGE)
    await self.__send_message_to_peer(kind, content)
    try:
      response = await self.__recv_message_from_peer()
    except BadPeerError as e:
      if isinstance(e, OutOfOrderError):
        response = e.msg
        await self.__send_message_to_peer(
          _MessageKind.ERROR,
          {
            "error": f"Peer sent an out of order message",
            "got": response.id.object,
            "expected": self.__last_message_id + 1,
            "id": response.id,
          }
        )
      elif isinstance(e, UnknownSessionError):
        response = e.msg
        await self.__send_message_to_peer(
          _MessageKind.ERROR,
          {
            "error": f"Peer sent a message for an unknown session",
            "got": response.id.session,
            "expected": self.__session_id,
            "id": response.id,
          }
        )
      else:
        raise e
    
    if response.kind not in valid_response_kinds:
      if response.kind == _MessageKind.ERROR:
        raise BadPeerError(f"Peer sent an error message: {response.content['error']}")
      # Send peer an error message
      await self.__send_message_to_peer(
        _MessageKind.ERROR,
        {
          "error": f"Peer sent an invalid response message",
          "got": response.kind,
          "expected": list(valid_response_kinds),
          "id": response.id,
        }
      )
      raise BadPeerError(f"Peer sent an invalid response message: {response.kind}")
    return response
  
  async def __inbound_network_loop(self):
    """Main loop for handling inbound network messages"""
    assert self.state == CHANNEL_STATE.ONLINE
    ...
  
  async def __outbound_network_loop(self):
    """Main loop for handling outbound network messages"""
    assert self.state == CHANNEL_STATE.ONLINE
    ...
  
  async def setup(self):
    """Sets up the channel"""
    assert self.state == CHANNEL_STATE.OFFLINE
    self.state = CHANNEL_STATE.SETUP
    self.__socket: aiozmq.Socket = self.context.socket(zmq.PAIR)
    if self.role == CHANNEL_ROLE.SERVER:
      self.__socket.bind(self.url)
    elif self.role == CHANNEL_ROLE.CLIENT:
      self.__socket.connect(self.url)
    else:
      raise UnsupportedRoleError(f"Unsupported role: {self.role}")
    if self.role == CHANNEL_ROLE.SERVER:
      # Wait until a JOIN message is recieved from a peer
      # Generate a new session id & send an ACKNOWLEDGE message to the peer
      peer_msg = await self.__recv_message_from_peer()
      if peer_msg.kind != _MessageKind.JOIN: # Handle error case
        # Send peer an error message
        self.__session_id = peer_msg.id.session
        self.__last_message_id = peer_msg.id.object
        await self.__send_message_to_peer(
          _MessageKind.ERROR,
          {
            "error": "Unknown Peer has sent us a message",
            "got": peer_msg.kind,
            "expected": [_MessageKind.JOIN],
            "id": peer_msg.id.to_hex(),
          }
        )
        self.__session_id = None
        self.__last_message_id = None
        raise BadPeerError("Unknown Peer has sent us a message")
      self.__session_id = int.from_bytes(urandom(8))
      self.__last_message_id = 0 # The Joing Message is always the first message in a session
      self.__peer_id = _id.from_hex(peer_msg.content["id"]).object
      await self.__send_message_to_peer(
        _MessageKind.ACKNOWLEDGE,
        {"id": _id(session=self.__session_id, object=self.__self_id).to_hex()},
      )   
    elif self.role == CHANNEL_ROLE.CLIENT:
      # Initialize the session id & last message id & inform the Server we wish to JOIN.
      # The server will send the correct session & message id values in the ACKNOWLEDGE message it sends back to us.
      self.__session_id = 0
      self.__last_message_id = 0
      ack_msg = await self.__send_message_to_peer_and_recv_ack(
        _MessageKind.JOIN,
        {"id": _id(session=self.__session_id, object=self.__self_id).to_hex()}
      )
      self.__peer_id = _id.from_hex(ack_msg.content["id"]).object
      self.__session_id = ack_msg.id.session
      self.__last_message_id = ack_msg.id.object
    
    self.state = CHANNEL_STATE.ONLINE

  async def teardown(self):
    """Tears down the channel"""
    assert self.state == CHANNEL_STATE.ONLINE
    self.state = CHANNEL_STATE.TEARDOWN
    if self.role == CHANNEL_ROLE.SERVER:
      await self.__send_message_to_peer(_MessageKind.LEAVE, {"id": _id(session=self.__session_id, object=self.__self_id).to_hex()})
      self.__session_id = None
      self.__last_message_id = None
      self.__peer_id = None
    elif self.role == CHANNEL_ROLE.CLIENT:
      await self.__send_message_to_peer_and_recv_ack(_MessageKind.LEAVE, {"id": _id(session=self.__session_id, object=self.__self_id).to_hex()})
      self.__session_id = None
      self.__last_message_id = None
      self.__peer_id = None
    self.__socket.close()
    self.state = CHANNEL_STATE.OFFLINE
  
  async def register(self, topic: str):
    """Registers a topic with the peer allocating a new inbox and outbox"""
    assert self.state == CHANNEL_STATE.ONLINE
    if not any(t["topic"] == topic for t in self.__topics):
      await self.__send_message_to_peer_and_recv_ack(_MessageKind.TOPIC_REGISTER, {"topic": topic})
      self.__topics.append(_topic(
        topic=topic,
        inbox=asyncio.Queue(),
        outbox=asyncio.Queue(),
      ))
  
  async def unregister(self, topic: str):
    """Unregisters a topic with the peer deallocating the inbox and outbox"""
    assert self.state == CHANNEL_STATE.ONLINE
    await self.__send_message_to_peer_and_recv_ack(_MessageKind.TOPIC_UNREGISTER, {"topic": topic})

  async def publish(self, topic: str) -> asyncio.Queue:
    """Get the outbox for a topic to publish messages to"""
    assert self.state == CHANNEL_STATE.ONLINE
    if topic not in self.__outboxes:
      self.__outboxes[topic] = asyncio.Queue()
      await self.register(topic)
    return self.__outboxes[topic]
  
  async def subscribe(self, topic: str) -> asyncio.Queue:
    """Get the inbox for a topic to recieve messages from"""
    ...