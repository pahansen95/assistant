"""
# About
We can leverage the concept of emergent properties to solve a complex problem through the application of a system of simple components.

GPT provides a novel way to generate code from natural language.

Humans have a natural ability to generalize & simplify complex problems into simple components.

If we can split a complex problem into simple components & then provide natural language descriptions of each component then we can leverage the power of GPT to generate code that solves the complex problem.

We can take this a step further by describing the problem solving process as a chain of simple components.

Through this process we can automate the process of solving complex problems.

This is the what I hope to solve (or at least partially solve) with this script

# The Problem & The Solution

The primary goal is to solve a problem.

I have chosen a problem that is neither overly simple nor overly complex:

> How can we simplify concurrent, distributed systems development through a peer-to-peer messaging system that is secure, simple to use & low effort to maintain?

The solution I would like to implement can be summarized as follows:

> Develop a custom L7 application protocol using a Pub/Sub architecture to exchanges messages in a peer-to-peer network environment. Leverage already proven cryptographic solutions like TLS & Symmetric Keys to provide security. Leverage common standards like JSON & Base64 to provide flexibility & interoperability. Leverage existing open source libraries ZeroMQ to reduce maintenance effort. Use Python because it is simple, powerful & easy to learn.

# The Components

A L7 application protocol can be defined within a specification. This specification breaks the complex problem into a series of simple components described in natural language. It defines the external software contracts of the solution as well as the expected behaviours of the solution as a whole. 

# The Process

Designing any type of software can be broken down into a series of steps. Since GPT understands natural language, we can structure the process similiar to an Agile development environment. These are the steps I have identified:

1. Ideation & Pre-Planning
  1. Define the Problem
  2. Propose a Vision for the Solution
  3. Brainstorm & Exhaustively define the solution.
  4. Write a solution specification.
  5. Identify the minimal set of specification components that are required to reach MVP (Minimum Viable Product)
  6. From the MVP components, identify the minimal subset necessary to reach PoC (Proof of Concept).
2. Planning
  1. Generate a project timeline where the first 2 milestones are PoC, MVP & Feature Complete.
  2. For each milestone, identify discrete features & functionality that consitute the milestone.
  3. For each feature or functionality, identify the components that are required to implement it.
  4. Identify the dependencies between these components.
  5. Organize the components into a dependency graph, each layer of the graph represents a sprint.
  6. For each sprint, identify the implementation tasks that are required to complete the sprint.
  7. Identify success criteria for each milestone.
3. Pre-Impementation
  1. For each feature or functionality, design the expected external software interfaces & contracts.
  2. For each component of that feature or functionality, design the internal software interfaces & contracts.
  3. For each component, identify existing libraries that can be leveraged to reduce development effort.
  4. Document in depth every internal & external contracts along with every component, feature & functionality.
4. Implementation
  1. For each sprint, implement the components. Each sprint covers the following:
    - Ensure software executes.
    - Test software for expected behaviour.
    - Produce technical documentation describing the source code.
  2. At the end of the PoC Milestone, evaluate the PoC's effectiveness against success criteria.
    - If the PoC is successful, continue to the MVP Milestone.
    - If the PoC is not successful, re-evaluate the solution & re-plan the project.
  3. At the end of the MVP Milestone, evaluate the MVP's effectiveness against success criteria.
    - If the MVP is successful, continue to the Feature Complete Milestone.
    - If the MVP is not successful then ... (TODO)

Let us commence forth!
"""

from loguru import logger
import openai
import tiktoken
import os
import sys
from typing import Iterable, Callable, Any, TypeVar, AsyncGenerator, AsyncIterable
from dataclasses import dataclass, field
import pathlib
import enum
import functools
import json
import asyncio
import itertools
import re
import datetime
import uuid
import networkx as nx
import time
import random

T = TypeVar("T")

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

model_lookup = {
  "gpt3": {
    "name": "gpt-3.5-turbo",
    "max_tokens": 4096,
    "supported_modes": ["render", "response"],
    "personality": {
      "creative": {
        "description": "Responses are more creative; the model is more curious.",
        "tuning": {
          "temperature": 2.0,
          # "top_p": 0.76, # Wasn't creative enough
          "top_p": 0.95, # Warning! I have observed the model gets "stuck" & never generates a response
        }
      },
      "balanced": {
        "description": "Responses are more balanced; the model is more balanced.",
        "tuning": {
          "temperature": 1.0,
          "top_p": 0.815,
        }
      },
      "reserved": {
        "description": "Responses are more reserved; the model is more straightforward.",
        "tuning": {
          "temperature": 0.5,
          "top_p": 0.68,
        }
      },

    }
  },
}

persona_templates = {
  "sme": """\
You are a Subject Matter Expert (SME).

An SME is...
1. An individual with extensive knowledge in a specific domain or field.
2. An authority in their area of specialization.
3. A professional with in-depth understanding of their discipline.
4. A contributor to the development of best practices within their field.

An SME is responsible for...
1. Consulting and advising organizations, researchers, or project teams.
2. Conducting research and development to advance new theories, technologies, or methodologies.
3. Producing content such as articles, books, white papers, or other publications.
4. Ensuring work aligns with industry standards and best practices through quality assurance processes.

The particulars of your role as an SME are described below:
> {sme_description}
"""
}

string_alnum_lower = lambda s: re.sub(r"[^a-zA-Z0-9]", "", s).lower()

_sme_id = tuple[str, ...]
"""The Identification Key of an SME."""

openapi_concurrent_requests_lock: asyncio.Semaphore
"""Ensures that only a set number of concurrent requests are made to the OpenAI API at any one time."""
total_token_count: int = 0

@dataclass
class Entity:
  """A Contributor to a Conversation. key & persona are optional & don't contribute the entity's identity."""
  uuid: uuid.UUID
  """The UUID of the entity."""
  name: str
  """The name of the entity."""
  key: tuple[str, ...] | None = None
  """An optional set of strings that uniquely describe the entity's persona"""
  persona: str | None = None
  """The optional persona of the entity. Who is this entity, what are their capabilities, etc..."""
  context: list[str] = field(default_factory=list)
  """Any contextal information that the entity should track; this is akin to short term memory."""

  def __hash__(self) -> int:
    return hash((self.uuid.hex, self.name))
  
  def render_context(self) -> str:
    return "# You remember the following\n{context}".format(
      context="\n".join(f"- {c}" for c in self.context)
    )
  
  async def respond(
    self,
    chat: Iterable[str],
    context: Iterable[str],
    model: str,
    responding_personality: str,
    reflection_personality: str,
  ) -> str:
    """The entity responds as part of a conversation. The latest message in the conversation is the last item in the chat list.
    The Entity knows the following:
    - Entity's name
    - Entity's persona
    - Entity's Short Term Memory (ie. `entity.context`)
    - Environmental Context (in order provided) (`context` arbitrary textual data to be used as context)
    - Chat Transcript (in order provided) (`chat` should be ordered with the oldest message first)
    """
    _user_msg = functools.partial(
      ChatMessage,
      entity=self,
      role=CHAT_ROLE.USER,
    )
    # Entity will come up with a response
    initial_response = await _parse_and_retry_chat(
      messages=[
        _user_msg(content=f"Your name is {self.name}"),
        _user_msg(content=f"# This is your persona\n{self.persona}"),
        _user_msg(content=self.render_context()),
        _user_msg(content="# Here are observations you have made\n{context}".format(context='\n'.join(f'- {c}' for c in context))),
        _user_msg(content="# Here is the conversation so far\n"),
        *[
          _user_msg(content=c)
          for c in chat
        ],
      ],
      model=model,
      personality=responding_personality,
      max_retry_count=3,
    )
    logger.trace(f"Entities {self.name} initial response: {initial_response}")
    # Let the entity think about it's response
    # reflective_thought = "Here is the conversation you are replying to:\n{conversation}You want to respond with: {response}. How could you improve your response? ".format(
    #   response=initial_response,
    #   conversation='\n'.join(f'- {c}' for c in chat),
    # )
    reflective_thought = "How can you improve the content quality of your response\n>{response} to\n> {chat}".format(
      response=initial_response,
      chat=chat[-1],
    )
    reflection = await self.think(
      thought=reflective_thought,
      # context=context,
      context=[],
      model=model,
      thinking_personality=reflection_personality,
      summary_personality=responding_personality,
    )
    logger.trace(f"Entities {self.name} reflection on it's thought: {reflection}")
    # Generate another response incorporating the reflection
    revised_response = await _parse_and_retry_chat(
      messages=[
        _user_msg(content=f"# This is your persona\n{self.persona}"),
        _user_msg(content="\n".join([
          "Without being verbose, improve the content quality of your response by applying the provided ideas",
          "# Here is the conversation you are replying to:",
          chat[-1],
          "# You want to respond with:",
          initial_response,
          "# You can improve your response by applying these ideas:",
          reflection,
        ])),
        # _user_msg(content=f"Without being verbose, improve the content quality of your response by applying the provided ideas\n> {initial_response}\nto\n> {chat}\nby applying these ideas:\n> {reflection}"),
        # _user_msg(content=f"Your name is {self.name}"),
        # _user_msg(content=f"# This is your persona\n{self.persona}"),
        # _user_msg(content=self.render_context()),
        # _user_msg(content="# You thought about how to respond & concluded:\n{reflection}".format(reflection=reflection)),
        # _user_msg(content="# Here are observations you have made:\n{context}".format(context='\n'.join(f'- {c}' for c in context))),
        # _user_msg(content="# Here is the conversation so far..."),
        # *[
        #   _user_msg(content=c)
        #   for c in chat
        # ],
      ],
      model=model,
      personality=responding_personality,
      max_retry_count=3,
    )
    logger.trace(f"Entities {self.name} revised response: {revised_response}")
    # TODO: Add Heuristics to determine if the response is any good
    return revised_response
  
  async def think(
    self,
    thought: str,
    context: Iterable[str],
    model: str,
    thinking_personality: str,
  ) -> str:
    """The entity reflects on a thought seeking to improve it.
    The Entity references the following:
      - It's Persona
      - It's internal context (ie. `entity.context`)
      - Environmental Context (in order provided) (`context` arbitrary textual data to be used as context)
      - The thought to reflect on (`thought`)
    """
    _user_msg = functools.partial(
      ChatMessage,
      entity=self,
      role=CHAT_ROLE.USER,
    )
    _assistant_msg = functools.partial(
      ChatMessage,
      entity=self,
      role=CHAT_ROLE.ASSISTANT,
    )
    # generate an initial thought
    logger.trace(f"Entity: {self.name} is thinking about: {thought}")
    initial_thought = await _parse_and_retry_chat(
      messages=[
        _user_msg(content=f"# This is your persona\n{self.persona}"),
        _user_msg(content=self.render_context()),
        _user_msg(content="# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(content=f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    logger.trace(f"Entity {self.name} is reflecting on it's thought: {initial_thought}")
    # conduct a challenge session
    challenge_session = await _parse_and_retry_chat(
      messages=[
        _user_msg(content=f"# This is your persona\n{self.persona}"),
        _user_msg(content=self.render_context()),
        _user_msg(content="# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(content=f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
        _assistant_msg(content=f"# My Initial Thoughts\n{initial_thought}"),
        _user_msg(content=f"# Reframe your thoughts, challenge your assumptions, & consider alternative points of view\n{initial_thought}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    logger.trace(f"Entity {self.name} is challenging it's thoughts: {challenge_session}")
    # reflect on the challenge session & iterate on the initial thought
    reflection = await _parse_and_retry_chat(
      messages=[
        _user_msg(content=f"# This is your persona\n{self.persona}"),
        _user_msg(content=self.render_context()),
        _user_msg(content="# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(content=f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
        _assistant_msg(content=f"# My Initial Thoughts\n{initial_thought}"),
        _user_msg(content=f"# Reframe your thoughts, challenge your assumptions, & consider alternative points of view\n{initial_thought}"),
        _assistant_msg(content=f"# My Challenge Session\n{challenge_session}"),
        _user_msg(content=f"# Reflect on your challenge session & iterate on your original thoughts incorporating ideas & points of view that make it better\n{challenge_session}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    logger.trace(f"Entity {self.name} summarized it's thought as: {reflection}")
    return reflection

  def to_dict(self):
    return {
      "uuid": self.uuid.hes,
      "name": self.name,
      "key": list(self.key) if self.key is not None else None,
      "persona": self.persona if self.persona is not None else None,
      "context": self.context,
    }

  @classmethod
  def from_dict(cls, d: dict[str, Any]):
    return cls(
      uuid=uuid.UUID(d["uuid"]),
      name=d["name"],
      key=tuple(d["key"]) if d["key"] is not None else None,
      persona=d["persona"] if d["persona"] is not None else None,
      context=d["context"],
    )

async def reduce_thoughts(
  entity: Entity,
  thoughts: Iterable[str],
  context: Iterable[str],
  model: str,
  thinking_personality: str,
  summary_personality: str,
) -> str:
  """Reduces a set of thoughts into a single salient summary.
  Currently, this is niave implementation that produces salient summaries for each thought & then concatenates them.
  There is a TODO to use embeddings to group thoughts first before further reduction."""
  entity_thoughts = list(thoughts)
  assert len(entity_thoughts) > 0, f"Cannot reduce 0 thoughts (entity: {entity.name})"
  initial_thoughts = await asyncio.gather(*[
    entity.think(
      thought=thought,
      context=context,
      model=model,
      thinking_personality=thinking_personality,
      summary_personality=summary_personality,
    )
    for thought in entity_thoughts
  ])
  reduced_thought = await entity.think(
    thought="\n".join(initial_thoughts),
    context=context,
    model=model,
    thinking_personality=thinking_personality,
    summary_personality=summary_personality,
  )
  return reduced_thought

class CHAT_ROLE(enum.Enum):
  SYSTEM: str = "system"
  USER: str = "user"
  ASSISTANT: str = "assistant"

@dataclass
class ChatMessage:
  """Represents a chat message. A message's identity is determined by its speaking entity & content."""
  entity: Entity
  """The posting Entity."""
  role: CHAT_ROLE
  """The role expected by the OpenAI API"""
  content: str
  """The actual content of the message."""

  def __hash__(self) -> int:
    return hash((self.entity, self.content))

  def to_dict(self):
    return {
      "entity": self.entity.uuid.hex,
      "role": self.role.value,
      "content": self.content,
    }

  @classmethod
  def from_dict(cls, d: dict[str, Any]):
    return cls(
      entity=uuid.UUID(d["entity"]),
      role=CHAT_ROLE(d["role"]),
      content=d["content"],
    )

@dataclass
class ChatTranscript:
  """Log Chat Messages & record the conversation flow."""
  conversation: nx.DiGraph = field(default_factory=nx.DiGraph)
  """Relational data between speakers, message & conversation flow."""
  entities: set[Entity] = field(default_factory=set)
  """All the entities in the chat."""
  messages: list[ChatMessage] = field(default_factory=list)
  """The underlying messages of the chat."""

  def __post_init__(self):
    self.conversation.add_node("root", role=CHAT_ROLE.SYSTEM)
  
  def entity_said(
    self,
    entity: Entity,
    said: str,
    in_response_to: Iterable[ChatMessage] | ChatMessage | None = None,
  ) -> ChatMessage:
    """Records a message from an entity updating the conversational Graph. Returns the message."""
    # create a new message
    message = ChatMessage(
      entity=entity,
      role=CHAT_ROLE.USER if entity.persona is None else CHAT_ROLE.ASSISTANT,
      content=said,
    )
    # Add the entity to the transcript's set of entities
    self.entities.add(entity)
    # Add the message to the transcript's list of messages
    self.messages.append(message)
    # Add the message to the conversation graph
    self.conversation.add_node(message, role=message.role)
    # Update the conversation graph to reflect the message's relationship to other messages
    if in_response_to is not None:
      if isinstance(in_response_to, ChatMessage):
        in_response_to = [in_response_to]
      for response in in_response_to:
        self.conversation.add_edge(message, response)
    else:
      self.conversation.add_edge(message, "root")

    return message
  
def count_tokens(model: str, *messages: str | ChatMessage):
  """Returns the number of tokens used in a prompt."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    logger.warning(f"Model {model} not found in TikToken. Using default encoding.")
    encoding = tiktoken.get_encoding("cl100k_base")
  
  return len(encoding.encode(
    "\n".join(
      msg if isinstance(msg, str) else msg.content
      for msg in messages
    )
  ))

class _StreamStopped(Exception):
  """Raised when the stream is stopped."""
  def __init__(self, reason: str):
    self.reason = reason

async def _yield_chunks(
  streaming_response: AsyncIterable[dict],
  chunk_recieved: asyncio.Event,
) -> AsyncGenerator[str, None]:
  async for chunk in streaming_response:
    # Get the reply from the response
    # TODO: Support multiple choices
    if chunk["choices"][0]["delta"] != {}:
      if "content" in chunk["choices"][0]["delta"]:
        if chunk["choices"][0]["delta"]["content"]:
          chunk_recieved.set()
          yield chunk["choices"][0]["delta"]["content"]
        continue # Skip to the next chunk if there is no content
      elif "role" in chunk["choices"][0]["delta"]:
        continue # Skip to the next chunk
    # Check if the model finished it's reply
    if chunk["choices"][0]["finish_reason"] == None:
      continue
    else:
      raise _StreamStopped(chunk['choices'][0]['finish_reason'])

async def _gather_response(
  streaming_response: AsyncIterable[dict],
  chunk_recieved: asyncio.Event,
  stream_complete: asyncio.Event,
) -> tuple[str, str]:
  response = ""
  try:
    async for chunk in _yield_chunks(streaming_response, chunk_recieved):
      response += chunk
      chunk_recieved.clear()
  except _StreamStopped as stop_reason:
    # Make sure the watchdog doesn't timeout
    stream_complete.set()
    chunk_recieved.set()
    return response, stop_reason.reason

async def _streaming_watchdog(
  timeout: float,
  chunk_recieved: asyncio.Event,
  stream_complete: asyncio.Event,
) -> None:
  """Waits for a chunk to be recieved before timing out."""
  try:
    while not stream_complete.is_set():
      await asyncio.wait_for(chunk_recieved.wait(), timeout)
  except asyncio.TimeoutError:
    raise asyncio.TimeoutError("OpenAI Streaming API timed out.")

async def safe_openai_request(
  chunk_timeout: float,
  max_retries: int,
  **acreate_kwargs,
) -> tuple[str, str]:
  """Uses the streaming protocol w/ openAI to avoid hanging requests."""
  global total_token_count
  prompt_tokens = count_tokens(acreate_kwargs["model"], *[msg["content"] for msg in acreate_kwargs["messages"]])
  acreate_kwargs.pop("stream", None)
  retry_count = 0
  while retry_count < max_retries:
    global openapi_concurrent_requests_lock
    async with openapi_concurrent_requests_lock:
      streaming_response = await openai.ChatCompletion.acreate(
        stream=True,
        **acreate_kwargs,
      )
      total_token_count += prompt_tokens
      chunk_recieved = asyncio.Event()
      stream_complete = asyncio.Event()
      try:
        results = await asyncio.gather(
          _gather_response(streaming_response, chunk_recieved, stream_complete),
          _streaming_watchdog(chunk_timeout, chunk_recieved, stream_complete),
        )
        total_token_count += count_tokens(acreate_kwargs["model"], results[0][0])
        return results[0]
      except asyncio.TimeoutError:
        logger.warning("OpenAI Streaming API timed out. Retrying...")
        retry_count += 1
        continue

async def chat(
  messages: Iterable[ChatMessage],
  model: str,
  personality: dict,
) -> str:
  """Submits a chat for completion to the OpenAI Chat API."""
  _msgs = [
    {
      "role": m.role.value,
      "content": m.content,
    } for m in messages
  ]
  # logger.trace(
  #   "Submitting the following chat completion to OpenAI API...\n{msgs}".format(
  #     msgs="\n".join([msg["content"] for msg in _msgs])
  #   )
  # )
  while True:
    logger.trace("Submitting chat to OpenAI...")
    try:
      # response = await asyncio.wait_for(
      #   openai.ChatCompletion.acreate(
      #     model=model,
      #     # messages=list(map(lambda m: m.to_dict(), messages)),
      #     messages=_msgs,
      #     stream=False,
      #     temperature=personality["tuning"]["temperature"],
      #     top_p=personality["tuning"]["top_p"],
      #   ),
      #   timeout=90, # Prevents the bot from hanging
      # )
      response, stop_reason = await safe_openai_request(
        chunk_timeout=2, # Chunks should be recieved within milliseconds
        max_retries=3,
        model=model,
        messages=_msgs,
        temperature=personality["tuning"]["temperature"],
        top_p=personality["tuning"]["top_p"],
      )
      logger.trace("Response received.")
      if stop_reason != "stop":
        logger.warning(f"Expected stop reason 'stop', got {response['choices'][0]['finish_reason']}.")
      return response
    except openai.error.APIError as e:
      logger.opt(exception=e).warning(f"OpenAI API Error. Will try again.")
    except asyncio.TimeoutError:
      logger.warning("OpenAI API timed out. Will try again")

def load_persona(name: str, dir: str) -> ChatMessage:
  """Loads a persona from a file."""
  logger.trace(f"Loading persona {name} from {dir}")
  try:
    persona_path = pathlib.Path(dir) / f"{name}.md"
    return persona_path.read_text()
  except FileNotFoundError:
    logger.error(f"Persona {name} not found in {dir}.")
    raise FileNotFoundError(f"Persona {name} not found in {dir}.")

def load_api_token():
  """Loads the OpenAI API Token from the environment."""
  try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
  except KeyError:
    logger.critical("No OpenAI Token found.")
    raise RuntimeError("No OpenAI Token found.")

class ParseError(Exception):
  """Raised when a response cannot be parsed."""
  def __init__(self, msg: str, error: str, *args) -> None:
    self.msg: str = msg
    self.error: str = error
    super().__init__(*args)

async def _parse_and_retry_chat(
  messages: list[ChatMessage],
  model: str,
  personality: str,
  parse_response: Callable[[str], T] = lambda s: s,
  max_retry_count: int = 0,
) -> T:
  """Convience function that wraps a chat session with GPT. Handles retries up to max_retry_count. Parses the raw model output with parse_response."""
  # type check the arguments
  assert isinstance(messages, list)
  assert all(isinstance(m, ChatMessage) for m in messages), f"All messages must be ChatMessage instances but got some of type {set(map(type, messages)) - set([ChatMessage])}."
  assert isinstance(model, str)
  assert isinstance(personality, str)
  assert isinstance(parse_response, Callable)
  assert isinstance(max_retry_count, int)
  retry_count = 0
  _messages = list(messages)
  # Get the number of tokens used in the prompt.
  total_tokens = count_tokens(model_lookup[model]['name'], *_messages)
  if total_tokens < model_lookup[model]['max_tokens'] // 2:
    pass
  elif total_tokens > model_lookup[model]['max_tokens'] // 2:
    logger.warning(f"Prompt exceeds 50% of maximum number of tokens for model {model}.")
  elif total_tokens >= int(9 * model_lookup[model]['max_tokens'] / 10):
    logger.warning(f"Prompt exceeds 90% the number of tokens for model {model}.")
  elif total_tokens >= model_lookup[model]['max_tokens']:
    logger.error(f"Prompt exceeds maximum number of tokens for model {model}.")
    raise RuntimeError(f"Prompt exceeds maximum number of tokens for model {model}.")
  while True:
    response = await chat(
      messages=_messages,
      model=model_lookup[model]["name"],
      personality=model_lookup[model]["personality"][personality]
    )
    assert isinstance(response, str), f"Expected response to be a string but got {response.__class__.__name__}."
    try:
      parsed_response = parse_response(response)
      if parsed_response is None:
        raise RuntimeError(f"Function {parse_response.__name__} returned {None.__class__.__name__}")
      return parsed_response
    except ParseError as pe:
      logger.warning(f"Failed to parse response: {pe.error}")
      logger.trace(f"Bad Response: {response}")
      if retry_count > max_retry_count:
        logger.error(f"Failed to parse response after {max_retry_count} retries.")
        raise RuntimeError("Failed to parse response.")
      retry_count += 1
      error_message = ChatMessage(
        role=CHAT_ROLE.USER,
        content=f"Please fix your response, {pe.msg}: {pe.error}",
      )
      if not messages[-1].content.startswith("Please fix your response"):
        messages.append(error_message)
      else:
        messages[-1] = error_message

def _parse_json_list(
  response: str,
  item_types: tuple[type] | type,
) -> list:
  if not isinstance(item_types, tuple):
    item_types = (item_types,)
  try:
    result = json.loads(response)
    if not isinstance(result, list):
      raise TypeError(f"Expected a list but got {type(result).__name__}.")
    all_wrong_types = [
      f"bad type {type(r).__name__} at index {i}"
      for i, r in enumerate(result)
      if not isinstance(result[i], item_types)
    ]
    if len(all_wrong_types) > 0:
      raise TypeError(f"Expected a list of {', '.join([t.__name__ for t in item_types])} but found the following errors: {', '.join(all_wrong_types)}.")
    return result
  except TypeError as te:
    raise ParseError("invalid JSON detected", te) from te
  except json.JSONDecodeError as jde:
    raise ParseError("invalid JSON detected", jde.msg) from jde

async def generate_sme_descriptions(
  problem_statement: str,
  vision_statement: str,
  get_persona: Callable[..., ChatMessage],
) -> dict[_sme_id, str]:
  """Generate a list of descriptions for potential SMEs that can contribute to the solutioning process."""
  # type check the arguments
  assert isinstance(problem_statement, str)
  assert isinstance(vision_statement, str)
  assert callable(get_persona)

  problem_statement_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=problem_statement,
  )
  vision_statement_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=vision_statement,
  )

  # Based on the problem and vision provided, generate a list of domain areas that are relevant to the problem.
  domain_excpetation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array of strings in plain text. Do not use markdown or any other formatting.",
  )
  tightly_relevant_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Generate a list of 30 technical fields, research domains & areas of expertise that are tightly correlated to the problem statement.",
  )
  loosely_relevant_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Generate a list of 30 technical fields, research domains & areas of expertise that are loosely correlated to the problem statement.",
  )
  domain_fields_parse_response = functools.partial(
    _parse_json_list,
    item_types=str,
  )
  domain_fields = list(itertools.chain.from_iterable(await asyncio.gather(
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="balanced",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="balanced",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, loosely_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=domain_fields_parse_response,
    ),
  )))


  domain_fields = list(set(map(string_alnum_lower, domain_fields)))
    
  logger.info(f"Domain fields: {domain_fields}")

  # Group these domain areas into clusters of related fields.
  cluster_request_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Please group the following fields into clusters based on how closely they are related to each other. Fields may be used more than once if neccesary. These are the following fields:\n{', '.join(domain_fields)}",
  )
  cluster_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array where each item is itself a JSON array of strings. Do not use markdown or any other formatting.",
  )
  cluster_parse_response = functools.partial(
    _parse_json_list,
    item_types=list,
  )
  clusters = await _parse_and_retry_chat(
    messages=[cluster_request_message, cluster_expectation_message],
    persona=get_persona("jack-of-all-trades"),
    model="gpt3",
    personality="balanced",
    parse_response=cluster_parse_response,
  )
  logger.info(f"Clusters: {clusters}")

  # For each cluster generate a natural language description of such an SME.
  sme_description_messages: list[ChatMessage] = [
    ChatMessage(
      role=CHAT_ROLE.USER,
      content=f"I will provide a clustering of related domain fields. Please write a natural language description of a Subjet Matter Expert. When writing a description for a subject matter expert (SME), include three key components. First, briefly describe the SME's field or domain of specialization to establish their area of expertise. Next, highlight their key technical skills, tools, methodologies, and knowledge areas to emphasize their proficiency within the field. Finally, emphasize the expert's unique strengths and qualities, focusing on what sets them apart in their discipline. By incorporating these three elements, you'll create a concise and informative description that showcases the SME's expertise, technical capabilities, and personal strengths. This description should not include any information related to their personal life or their personality. The description should be salient & succinct. Here are the related domain fields you should consider: \n{', '.join(cluster)}",
    )
    for cluster in clusters
  ]
  sme_description_example = f"""
  The expert is a Marine Biologist specializing in coral reef ecosystems and conservation. They are proficient in underwater survey techniques, statistical analysis of ecological data, and remote sensing technologies for marine habitats. With a strong understanding of the taxonomy and ecology of coral reef species, including fish, invertebrates, and coral, they possess strong observational and research skills. Their adaptability to different fieldwork environments and ability to synthesize complex ecological data make them invaluable for practical conservation applications.
  """
  sme_description_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"My expectation is you will respond in plain text with only the requested description. Use plain text, do not use markdown or any other formatting. Here is an example of a description of an SME:\n{sme_description_example}",
  )
  sme_descriptions = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[sme_description_message, sme_description_expectation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=lambda s: s,
    )
    for sme_description_message in sme_description_messages
  ])
  for sme_description in sme_descriptions:
    logger.info(f"Generated SME Description...\n{sme_description}")
  
  # Scope down the SMEs to only those most relevant to the problem.
  sme_descriptions_as_markdown_list = "\n".join(f"{i+1}. {sme_description}" for i, sme_description in enumerate(sme_descriptions))
  relevant_sme_request_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Please select the 10 most relevant SMEs for our problem statement:\n{sme_descriptions_as_markdown_list}",
  )
  relevant_sme_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array of integers. Each integer should be the list number corresponding of the SME you selected. Do not use markdown or any other formatting.",
  )
  relevant_sme_parse_response = functools.partial(
    _parse_json_list,
    item_types=int,
  )
  relevant_sme: list[int] = await _parse_and_retry_chat(
    messages=[
      problem_statement_message,
      relevant_sme_request_message,
      relevant_sme_expectation_message,
    ],
    persona=get_persona("jack-of-all-trades"),
    model="gpt3",
    personality="balanced",
    parse_response=relevant_sme_parse_response,
  )
  selected_smes = [sme_descriptions[i-1] for i in relevant_sme]
  for selected_sme in selected_smes:
    logger.info(f"Selected sme...\n{selected_sme}")
  
  # Generate a unique identifier for each SME that describes their area of expertise.
  sme_id_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you MUST respond with only the JSON array of strings. The array SHOULD have a length of between five and ten inclusive. Each item in the list MUST be less or equal to three words. You MUST NOT use markdown or any syntax other than JSON.",
  )
  sme_id_responses = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[
        ChatMessage(
          role=CHAT_ROLE.USER,
          content=f"Given the provided description of the SME please provide a salient set of descriptors that describes their core domain of competency:\n{selected_sme}",
        ),
        sme_id_expectation_message,
      ],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=functools.partial(
        _parse_json_list,
        item_types=str,
      ),
    )
    for selected_sme in selected_smes
  ])
  assert isinstance(sme_id_responses, list)
  assert all(isinstance(sme_id_response, list) for sme_id_response in sme_id_responses)
  assert all(isinstance(sme_id, str) for sme_id_response in sme_id_responses for sme_id in sme_id_response)
  for sme_id_response in sme_id_responses:
    logger.info(f"Generated SME ID...\n{sme_id_response}")
  
  assert len(sme_id_responses) == len(selected_smes)
  return {
    tuple(set(
      string_alnum_lower(sme_id)
      for sme_id in sme_ids
    )): sme_description
    for sme_ids, sme_description in zip(sme_id_responses, selected_smes)
  }

async def think_tank(
  smes: list[Entity],
  problem_statement: str,
  vision_statement: str,
  get_persona: Callable[[str], str],
  model: str,
) -> ...:
  """A Think tank is a group of Subject Matter Experts (SMEs) who sit down together and discuss the problem, the vision, and the solution through a series of sessions.
  
  The first session is focused on exploring the problem space. The goal of this part of the discussion is to understand the problem. The SMEs should ask questions to clarify the problem. They should also ask questions to understand the problem from different perspectives.

  The second session is to brainstorm ideas for solutions that meet the vision. Ideas can be new or existing. They can be simple or complex. They can be good or bad. The goal is to generate as many ideas as possible. The more ideas, the better.

  It is also important to note that the brainstorming session is not a discussion of what solution specifically to use or how to implement it. The goal is to generate ideas, not to evaluate them. The evaluation of ideas is done later.

  The brainstorming session is facilitated by a moderator who ensures that the discussion stays on track. The moderator should be a neutral party who is not an SME. 

  Additional members should be present to offer points of view outside from outside the problem space. These members are called "Observers". Observers do not contribute the same amount as SMEs but offer valuable insights.

  The third session is to evaluate the ideas generated in the brainstorming session. The goal of this session is to determine which ideas are worth pursuing. The evaluation process is called "Prioritization". The SMEs should evaluate each idea based on criteria such as:

  - Does the idea meet the vision?
  - Is the idea realistic?
  - Is the idea pragmatic?
  - How much effort is required to implement the idea?
  - How much effort is required to maintain & support the idea?

  Finally the fourth session is to select the best ideas to implement. The SMEs should select the ideas that best match the vision, is the most realistic, is the most pragmatic, requires the least effort to implement, and requires the least effort to maintain & support. This is the output of the Think Tank.
  """
  # Type check all the arguments
  assert isinstance(smes, list)
  assert len(smes) >= 3, f"There must be at least three SMEs, but there are only {len(smes)}"
  assert all(isinstance(sme, Entity) for sme in smes)
  assert isinstance(problem_statement, str)
  assert isinstance(vision_statement, str)
  assert callable(get_persona)
  assert isinstance(model, str)

  # Create a Salient Summary Entity; this isn't really a contributor but a utility to optimize tokenization
  knowledge_synthesis = Entity(
    uuid=uuid.uuid5(uuid.NAMESPACE_DNS, "salience"),
    name="Salience",
    key=("salience", "summary", "knowledgesynthesizer"),
    persona=get_persona("knowledge-synthesizer"),
  )
  knowledge_synthesis.context.append(
    "the information to summarize will be subsequently provided. I shouldn't need to ask for it. I also shouldn't summarize or otherwise include information about myself."
  )

  # Create a Moderator Entity
  moderator = Entity(
    uuid=uuid.uuid5(uuid.NAMESPACE_DNS, "moderator"),
    name="Moderator",
    key=("moderator", "jackofalltrades"),
    persona=get_persona("jack-of-all-trades"),
  )

  # Create some contextual data
  context = {
    "problem_statement": f"the problem statement is: {problem_statement}",
    "vision_statement": f"the vision statement is: {vision_statement}",
    "ground_rules": "these are the ground rules for the discussion\n{rules}".format(
      rules="\n".join([
      "Rule 1: Respect and appreciate differing opinions and perspectives, even if you disagree.",
      "Rule 2: Stay focused on the problem statement and vision statement and avoid going off-topic."
      ])
    )
  }

  # Start new transcript
  transcript = ChatTranscript()

  ### Session 1: Problem Space Exploration ###
  """
  The Goal of session 1 is to explore the problem space. The SMEs should ask questions to clarify the problem. They should also ask questions to understand the problem from different perspectives.
  """

  # Ask for initial thoughts on the problem statement & the vision statement
  sme_thought = "What are my initial thoughts on the customer's problem statement and vision statement?"

  logger.info("Asking SMEs for their initial thoughts on the problem statement and vision statement...")
  sme_responses = await asyncio.gather(*[
    sme.think(
      thought=sme_thought,
      context=list(context.values()),
      model=model,
      thinking_personality="balanced",
      summary_personality="reserved",
    )
    for sme in smes
  ])

  moderator_thought = "How would I summarize the SME's intial thoughts on the problem statement and vision statement?"
  logger.info("Generating a summarization of the SME's initial thoughts on the problem statement and vision statement...")
  initial_thoughts_summary = await moderator.think(
    thought=moderator_thought,
    context=[
      *context.values(),
      *[
        f"{sme.name}'s initial thoughts are:\n{sme_response}"
        for sme, sme_response in zip(smes, sme_responses)
      ],
    ],
  )
  context["initial_thoughts"] = f"Everyone's initial thoughts on the problem & vision is summarized as:\n{initial_thoughts_summary}"

  # Ask the SMEs to discuss the problem space. They should think through how to begin approaching the problem. What challenges might they run into? What second or third order problems might they also need to solve? Are there any assumptions that they need to verify? What questions do they keep coming back to?
  sme_thought = "How would I approach the problem? What challenges might I run into? What second or third order problems might I also need to solve? Are there any assumptions that I need to verify? What questions do I keep coming back to?"
  sme_povs = await asyncio.gather(*[
    sme.think(
      thought=sme_thought,
      context=list(context.values()),
      model=model,
      thinking_personality="balanced",
      summary_personality="reserved",
    )
    for sme in smes
  ])
  # TODO: Salient summary & inject into SME internal context

  # Ask one SME to describe the problem space in their own words. Have the other SMEs ask questions to clarify the description. Do this at least three times, each time with a different SME.
  for sme in random.choices(smes, k=3):
    moderator_question = "Can you describe the problem space in your own words?"
    sme_response = ...
    for other_sme in list(smes - set(sme)):
      moderator_question = f"What questions do you have for {sme.name} & their description of the problem space?"
      other_sme_questions = ...
      sme_answers = ...
  
  # Take the descriptions, questions & answers. Summarize the problem space.
  moderator_thought = "How would I summarize the problem space?"
  #TODO Log the problem space summary in the chat transcript

  # In a round robin fashion, have each SME add or remove one item from the summary. Do this at least twice.
  for _ in range(2):
    for sme in tuple(smes):
      moderator_question = "Select one thing to add, remove or adjust in the description of the problem space. Please walk us through your thought process."
      sme_response = ...
      moderator_thought = "How would I update the problem space summary based on {sme.name}'s response?"
      # TODO: Log the updated problem space summary in the chat transcript

  ### Session 4: Prioritization & Selection ###
  """
  The Goal of session 4 is to prioritize the ideas generated & select those ideas that best implement the vision.
  """

  ### PreSession ###

  # 1. Introductions and preliminary questioning
  intro_message: ChatMessage = transcript.entity_said(
    entity=moderator,
    said="""Everyone, thank you for joining us today. My name is {moderator_name} and I will be facilitating this session. Let's start by introducing ourselves and sharing our areas of expertise.""".format(
      moderator_name=moderator.name,
    ),
  )
  # Ask the SMEs to introduce themselves and share their expertise
  logger.info("Asking SMEs to introduce themselves and share their expertise")
  sme_responses: list[str] = await asyncio.gather(
    *[
      sme.respond(
        chat=[
          intro_message.content,
        ],
        context=[
          context["problem_statement"],
          context["vision_statement"],
        ],
        model=model,
        responding_personality="balanced",
        reflection_personality="reserved",
      )
      for sme in smes
    ],
  )
  assert len(sme_responses) == len(smes)
  for sme, sme_response in zip(smes, sme_responses):
    logger.info(f"SME {sme.name} replied to the moderator:\n{sme_response}")
  # Record the SME responses in the transcript
  for sme, sme_response in zip(smes, sme_responses):
    transcript.entity_said(
      entity=sme,
      said=sme_response,
      in_response_to=intro_message,
    )
  # Have the SMEs internally reflect on each other's PoVs. Record any thoughts in the entity's short term memory.
  logger.info("Asking SMEs to reflect on each other's PoVs; reducing reflection to a single final thought.")
  sme_reflections = await asyncio.gather(
    *[
      sme.think(
        thought="\n".join([
          sme_pov
          for pov_owner, sme_pov
          in zip(smes, sme_responses)
          if pov_owner != sme
        ]),
        context=[
          # The problem & vision statement
          context["problem_statement"],
          context["vision_statement"],
          # The SME's PoV
          next(sme_pov for pov_owner, sme_pov in zip(smes, sme_responses) if pov_owner == sme),
        ],
        model=model,
        thinking_personality="balanced",
        summary_personality="reserved",
      )
      # reduce_thoughts(
      #   entity=sme,
      #   thoughts=[
      #     sme_pov
      #     for pov_owner, sme_pov
      #     in zip(smes, sme_responses)
      #     if pov_owner != sme
      #   ],
      #   context=[
      #     # The problem & vision statement
      #     context["problem_statement"],
      #     context["vision_statement"],
      #     # The SME's PoV
      #     next(sme_pov for pov_owner, sme_pov in zip(smes, sme_responses) if pov_owner == sme),
      #   ],
      #   model=model,
      #   thinking_personality="creative",
      #   summary_personality="reserved",
      # )
      for sme in smes
    ],
  )
  # Commit the thoughts to the SME's short term memory
  for sme, sme_reflection in zip(smes, sme_reflections):
    logger.info(f"SME {sme.name} reflected on all the others SMEs' PoVs:\n{sme_reflection}")
    sme.context.append(sme_reflection)

  return 

  # 2. Setting ground rules for discussion
  transcript.entity_said(
    entity=moderator,
    said="Thank you for sharing your expertise. Before we dive into the discussion, let's set some ground rules to ensure a productive and respectful conversation.",
  )




  ### OLD ###

  _name_to_message = lambda id: ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Your name is {sme_names[id]}.",
  )

  def _contextual_transcript_from_messages(messages: list[tuple[str, str]]) -> ChatMessage:
    """Generate a contextual transcript from a list of messages ordered in time (oldest to newest)"""
    # assert messages has the right types & has a length of at least 1
    assert isinstance(messages, list)
    assert all(isinstance(message, tuple) for message in messages)
    assert all(isinstance(speaker, str) for message in messages for speaker in message)
    assert all(isinstance(message, str) for message in messages for message in message)
    return ChatMessage(
      role=CHAT_ROLE.USER,
      content="Here is the contextual chat transcript:\n{transcript}".format(
        transcript="\n".join(
          f"{speaker} said: {message}"
          for speaker, message in messages
        ),
      ),
    )

  # Template the Persona's from the SMEs
  sme_persona_messages: dict[_sme_id, ChatMessage] = {
    sme_id: ChatMessage(
      role=CHAT_ROLE.USER,
      content=persona_templates['sme'].format(
        sme_description=sme_desc,
      ),
    )
    for sme_id, sme_desc in sme_descriptions.items()
  }
  _chat_response = tuple[str | None, str]
  _chat_history = list[_chat_response]
  # Track the individual SMEs responses
  sme_chat_history: dict[_sme_id, _chat_history] = {
    sme_id: []
    for sme_id in sme_descriptions.keys()
  }
  moderator_chat_history: _chat_history = []
  """Tracks the response from an individual SME. The key is the SME's ID. The value is a tuple of two messages: the first (optional) message is the message the SME is responding to, the second (required) message is the response from the SME."""

  # Generate a response from the SMEs based on the problem statement & vision statement.
  contextual_header_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="You are participating in a think tank as an SME. I will give contextual information for the session & the session's most recent conversational transcript."
  )
  contextual_info_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="This is the contextual information for the session:\nProblem Statment:\n{problem_statement}\nVision Statement:\n{vision_statement}\n".format(
      problem_statement=problem_statement,
      vision_statement=vision_statement,
    )
  )
  no_contextual_chat_history_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="There is no previous chat history for this session.",
  )
  moderator_asks_preliminary_questions_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Thank you for joining us on today's session. I will be today's moderator. To start I would like to cover some preliminary items. First, I would like to ask each of you to briefly introduce your areas of expertise & your strengths. Second, please restate the problem statement as you understand it. Third, please restate the vision statement as you understand it. Lastly please tell us your initial thoughts on the customer's problem & vision statement.",
  )
  moderator_chat_history.append((None, moderator_asks_preliminary_questions_message.content))
  
  responses = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[
        _name_to_message(sme_id),
        contextual_header_message,
        contextual_info_message, no_contextual_chat_history_message,
        moderator_asks_preliminary_questions_message,
      ],
      persona=sme_persona_message,
      model="gpt3",
      personality="balanced",
      parse_response=lambda s: s,
    )
    for sme_id, sme_persona_message in sme_persona_messages.items()
  ])
  for response in responses:
    logger.info(f"Generated response...\n{response}")
  
  # Log the responses in the chat history
  for sme_id, response in zip(sme_descriptions.keys(), responses):
    assert isinstance(response, str), f"Expected response to be str but got {type(response).__name__}"
    sme_chat_history[sme_id].append((None, response))
  
  # Ask each SME to provide their thoughts on another SME's response
  async def _get_sme_opinion_on_all_other_responses(sme_id: _sme_id) -> dict[_sme_id, ChatMessage]:
    sme_opinions = await asyncio.gather(*[
      _parse_and_retry_chat(
        messages=[
          _name_to_message(sme_id),
          contextual_header_message,
          contextual_info_message,
          _contextual_transcript_from_messages([
            ("moderator", moderator_asks_preliminary_questions_message.content),
            (sme_names[sme_id], sme_chat_history[sme_id][-1][1]),
            (sme_names[other_sme_id], sme_chat_history[other_sme_id][-1][1]),
          ]),
          ChatMessage(
            role=CHAT_ROLE.USER,
            content=f"Consider {sme_names[other_sme_id]}'s response to my earlier question. Can you talk through your thoughts on their point of view of the customer's problem statement & vision statement?",
          ),
        ],
        persona=sme_persona_messages[sme_id],
        model="gpt3",
        personality="balanced",
        parse_response=lambda s: s,
      )
      for other_sme_id in filter(
        lambda other_sme_id: other_sme_id != sme_id,
        sme_descriptions.keys(),
      )
    ])
    return {
      other_sme_id: opinion
      for other_sme_id, opinion in zip(
        filter(
          lambda other_sme_id: other_sme_id != sme_id,
          sme_descriptions.keys(),
        ),
        sme_opinions,
      )
    }

  sme_opinions: list[dict] = await asyncio.gather(*[
    _get_sme_opinion_on_all_other_responses(sme_id)
    for sme_id in list(sme_descriptions.keys())[0:1]
  ])
  # Assert that all opions are dicts with _sme_id keys & str values
  assert all(
    isinstance(sme_opinion, dict)
    and all(
      isinstance(key, tuple)
      and isinstance(value, str)
      for key, value in sme_opinion.items()
    )
    for sme_opinion in sme_opinions
  )
  moderator_chat_history.append((None, "Can provide your thoughts on SME's response to my earlier question?"))

  for sme_id, opinions in zip(sme_descriptions.keys(), sme_opinions):
    # assert that the opinions is a dict whoses keys are the _sme_ids for all other SMEs & the values are str
    assert isinstance(opinions, dict)
    assert all(
      isinstance(key, tuple)
      and key != sme_id
      for key in opinions.keys()
    )
    assert all(
      isinstance(value, str)
      for value in opinions.values()
    )
    for other_sme_id, opinion_on in opinions.items():
      # log the opinions to stderr
      logger.info(f"{sme_names[sme_id]}'s opinion on {sme_names[other_sme_id]} is...\n{opinion_on}")
      # Update the chat history
      sme_chat_history[sme_id].append((moderator_chat_history[-1][1], opinion_on))
  
  # Log the chat transcript for each SME up till now
  for sme_id in list(sme_descriptions.keys())[0:1]:
    chat_transcript = [f"# Chat transcript for {sme_names[sme_id]}\n"]
    for message_pair in sme_chat_history[sme_id]:
      if message_pair[0] is not None:
        chat_transcript.append(f"## Someone Said\n{message_pair[0]}\n")
      chat_transcript.append(f"## {sme_names[sme_id]}\n{message_pair[1]}\n")
    logger.trace("\n".join(chat_transcript))

async def main(*args, **kwargs) -> int:
  """Main entry point for the program."""
  global openapi_concurrent_requests_lock
  openapi_concurrent_requests_lock = asyncio.Semaphore(kwargs["openai-concurrent"])
  cache_dir = pathlib.Path(kwargs["cache"])
  personas_dir = pathlib.Path(kwargs["personas"])
  if not cache_dir.exists():
    logger.info(f"Creating cache directory {cache_dir}")
    cache_dir.mkdir(parents=True)
  if not personas_dir.exists():
    logger.info(f"Creating personas directory {personas_dir}")
    personas_dir.mkdir(parents=True)
  
  # Find available personas
  personas = list(map(lambda p: p.stem, personas_dir.glob("*.md")))
  logger.info(f"Found {len(personas)} personas: {', '.join(personas)}")
  _load_persona = functools.partial(load_persona, dir=personas_dir)
  
  load_api_token()

  # Load the Problem & Vision Statement
  problem_statement_path = pathlib.Path(os.environ["CI_PROJECT_DIR"]) / "docs" / "ipc" / "problem-statement.md"
  vision_statement_path = pathlib.Path(os.environ["CI_PROJECT_DIR"]) / "docs" / "ipc" / "vision-statement.md"

  problem_statement = problem_statement_path.read_text()
  vision_statement = vision_statement_path.read_text()
  
  if kwargs['phase-gen-smes']:
    # Generate a set of SMEs that will contribute to the problem solving process.
    logger.trace("Generating SME Descriptions...")
    sme_descriptions = await generate_sme_descriptions(
      problem_statement,
      vision_statement,
      get_persona=_load_persona,
    )
    # Cache the SME Descriptions
    logger.trace("Caching SME Descriptions...")
    sme_descriptions_path = cache_dir / "sme-descriptions.json"
    # Backup the old SMEs if they exist
    if sme_descriptions_path.exists():
      backup_path = sme_descriptions_path.parent / f"{sme_descriptions_path.stem}-{datetime.datetime.now().isoformat()}{sme_descriptions_path.suffix}"
      logger.trace(f"Backing up old SME Descriptions to {backup_path}")
      sme_descriptions_path.rename(backup_path)
    # lambda that strips all non-alphanumeric characters from a string
    sme_descriptions_path.write_text(json.dumps(
      {
        "|".join(sme_ids): sme_desc
        for sme_ids, sme_desc in sme_descriptions.items()
      }
    ))
    logger.info(f"Saved SME Descriptions to {sme_descriptions_path}")
  else:
    # Load the SME Descriptions
    logger.trace("Loading SME Descriptions...")
    sme_descriptions_path = cache_dir / "sme-descriptions.json"
    if not sme_descriptions_path.exists():
      logger.error(f"No SME Descriptions found at {sme_descriptions_path}; please run with --phase-gen-smes")
      return 1
    sme_descriptions = {
      tuple(sme_ids.split("|")): sme_desc
      for sme_ids, sme_desc in json.loads(sme_descriptions_path.read_text()).items()
    }
    logger.info(f"Loaded SME Descriptions from {sme_descriptions_path}")
    for sme_ids, sme_desc in sme_descriptions.items():
      logger.trace(f"{sme_ids}: {sme_desc}")

  # Sanity check the SME Descriptions
  assert isinstance(sme_descriptions, dict)
  assert all(
    isinstance(sme_ids, tuple) and isinstance(sme_desc, str)
    for sme_ids, sme_desc in sme_descriptions.items()
  )
  assert all(
    isinstance(sme_id, str)
    for sme_ids in sme_descriptions.keys()
    for sme_id in sme_ids
  )

  logger.info(f"Found {len(sme_descriptions)} SMEs")

  # deterministically generate names for the SMEs. So long as the SMEs don't change, the names will be the same.
  assert len(sme_descriptions) <= len(ANDROGYNOUS_NAMES), "Too many SMEs to generate names for!"
  sme_human_names = {
    sme_ids: tuple(ANDROGYNOUS_NAMES)[i]
    for i, sme_ids in enumerate(sme_descriptions)
  }
  assert len(sme_human_names) == len(sme_descriptions)
  logger.info(f"SME Human Names: {list(sme_human_names.values())}")

  # Create UUIDs for each SME based off the hash of their keys
  sme_uuids = {
    sme_ids: uuid.uuid5(uuid.NAMESPACE_DNS, "|".join(sme_ids))
    for sme_ids in sme_descriptions
  }
  assert len(sme_uuids) == len(sme_descriptions)

  # Create the SME Entities
  sme_entities = [
    Entity(
      uuid=sme_uuids[sme_key],
      name=sme_human_names[sme_key],
      key=sme_key,
      persona=sme_descriptions[sme_key],
      context=[],
    )
    for sme_key in sme_descriptions
  ]
  assert len(sme_entities) == len(sme_descriptions)

  # Move on to the Think Tank phase
  if kwargs['phase-think-tank']:
    _ = await think_tank(
      sme_entities[0:3], # For now limit the number of SMEs to reduce costs
      problem_statement,
      vision_statement,
      get_persona=_load_persona,
      model=kwargs["model"],
    )

  return 0

def _parse_kwargs(*args: str, **kwargs: str) -> dict:
  _kwargs = {
    "help": False,
    "verbose": False,
    "cache": f"{os.environ['CI_PROJECT_DIR']}/meta/chain/",
    "personas": f"{os.environ['CI_PROJECT_DIR']}/meta/personas/",
    "phase-gen-smes": False,
    "phase-think-tank": False,
    "model": "gpt3",
    "openai-concurrent": 10,
  }
  for arg in args:
    if arg.startswith("-"):
      try:
        key, value = arg.split("=")
      except ValueError:
        key = arg
        value = True
      _kwargs[key.lstrip('-').lower()] = value
  return _kwargs

def _parse_args(*args: str, **kwargs: str) -> list:
  _args = []
  for arg in args:
    if not arg.startswith("-"):
      _args.append(arg)
  return _args

def _help():
  print(f"""
Usage: {sys.argv[0]} [OPTIONS] [SUBCMD] [ARGS...]

About:
  ...

Args:
  SUBCMD:
    The subcommand to run.
  ARGS:
    The arguments to pass to the subcommand.

Options:
  -h, --help
    Print this help message and exit.
  --cache=DIRECTORY
    The path to a directory to save chat log. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/chain/
  --personas=DIRECTORY
    The path to a directory containing persona files. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/personas/
  --verbose
    Enable verbose logging.
  --openai-concurrent=INT
    The maximum number of concurrent calls to make to the OpenAI API. Defaults to 10.
  --phase-gen-smes
    Generate SME Descriptions and save them to the cache directory.
  --phase-think-tank
    Run the Think Tank phase of the process.
  
  Subcommands:
    prompt:
      Run a single-shot conversation with a persona.
      About: 
    chat:
      Have a chat conversation with a persona.
    think-tank:
      Run the Think Tank phase of the process.
  """)

if __name__ == "__main__":
  _rc = 255
  try:
    logger.remove()
    _args = _parse_args(*sys.argv[1:])
    _kwargs = _parse_kwargs(*sys.argv[1:])
    if _kwargs["verbose"]:
      logger.add(sys.stderr, level="TRACE")
    else:
      logger.add(sys.stderr, level="INFO")
    if _kwargs["help"]:
      _help()
      _rc = 0
    else:
      start = time.monotonic()
      _rc = asyncio.run(main(*_args, **_kwargs))
      finish = time.monotonic()
      logger.success(f"This session consumed ~{total_token_count // 1000} units of 1000 tokens (~{total_token_count} tokens) in {finish - start:.2f}s. This is a rate of ~{int((total_token_count // 1000) / ((finish - start) / 60))} token-units/minute.")
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled Exception raised during runtime...")
    logger.error(f"This session consumed ~{total_token_count // 1000} units of 1000 tokens (~{total_token_count} tokens).")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)
