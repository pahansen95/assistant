from . import _logger, PromptInterface, PROMPT_PERSONALITY, PROMPT_MESSAGE_ROLE, PromptMessage, EntityProperties, EntityInterface
from dataclasses import dataclass, field, KW_ONLY
import uuid
from typing import Iterable, Any

_user_msg = lambda content: PromptMessage(content=content, role=PROMPT_MESSAGE_ROLE.USER)
_assistant_msg = lambda content: PromptMessage(content=content, role=PROMPT_MESSAGE_ROLE.ASSISTANT)
_system_msg = lambda content: PromptMessage(content=content, role=PROMPT_MESSAGE_ROLE.SYSTEM)

@dataclass
class ExternalEntity(EntityProperties.PropsMixin, EntityProperties):
  """An external user is an entity that we don't control. We can only responde to them."""
  _name: str
  """The name of the external user."""
  _description: str
  """The description of the external user."""
  _uuid: uuid.UUID
  """The UUID of the external user."""

  def __post_init__(self):
    _logger.debug(f"{self.name=}")
    _logger.debug(f"{self.description=}")
    _logger.debug(f"{self.uuid=}")
  
  def __hash__(self) -> int:
    return hash((self.uuid.hex, self.name))

@dataclass
class InternalEntity(EntityProperties.PropsMixin, EntityProperties, EntityInterface):
  """An entity over which we have control over (ie an assistant). key & persona are optional & don't contribute the entity's identity."""
  _name: str
  """The name of the entity."""
  _description: str
  """The description of the entity."""
  _uuid: uuid.UUID
  """The UUID of the entity."""
  _send: PromptInterface
  """The interface to the LLM that the entity uses to prompt for a response."""
  _: KW_ONLY
  key: tuple[str, ...] | None = field(default=None, kw_only=True)
  """An optional set of strings that uniquely describe the entity's persona"""
  persona: str | None = field(default=None, kw_only=True)
  """The optional persona of the entity. Who is this entity, what are their capabilities, etc..."""
  context: list[str] = field(default_factory=list, kw_only=True)
  """Any contextal information that the entity should track; this is akin to short term memory."""

  def __post_init__(self):
    _logger.debug(f"{self.name=}")
    _logger.debug(f"{self.description=}")
    _logger.debug(f"{self.uuid=}")

  def __hash__(self) -> int:
    return hash((self.uuid.hex, self.name))
    
  def render_iterable(self, header: str, iterable: Iterable[str]) -> str:
    """Convience function for rendering an iterable into a single string"""
    _header = ""
    if header:
      _header += f"# {header}\n"
    return "{header}{context}\n".format(
      header=_header,
      context="\n".join(f"{c}" for c in iterable)
    )

  def render_prompt(
    self,
    chat: Iterable[str],
    context: Iterable[str],
  ) -> list[PromptMessage]:
    """Convience function for rendering the prompt for submission to the model"""
    assert len(chat) > 0, "Chat must have at least one message"
    assert isinstance(chat, list), "Chat must be a list"
    assert all(isinstance(msg, str) for msg in chat), "Chat must be a list of strings"
    assert isinstance(context, list), "Context must be a list"
    assert all(isinstance(msg, str) for msg in context), "Context must be a list of strings"
    return [
      msg
      for msg in [
        _user_msg(f"Your name is {self.name}") if self.name is not None else None,
        _user_msg(self.persona) if self.persona is not None else None,
        _user_msg(self.render_iterable(
          "Here is relevant information to the conversation",
          self.context,
        )) if len(self.context) > 0 else None,
        _user_msg(self.render_iterable(
          "Here are immediate observations you have made",
          context,
        )) if len(context) > 0 else None,
        _user_msg(self.render_iterable(
          "Here is the most recent conversation transcript",
          chat,
        )),
      ] if msg is not None
    ]

  async def thoughts_on(
    self,
    chat: Iterable[str],
    context: Iterable[str],
    model: str,
    personality: str,
  ) -> str:
    """The entity provides it's initial thoughts on a topic, stepping through it's throught process & pointing out any assumptions it makes. (aka single-shot)"""
    raise NotImplementedError
  
  async def reply_to(
    self,
    chat: Iterable[str],
    context: Iterable[str],
    model: str,
    personality: str,
  ) -> str:
    """The entity replies to a specific message without any internal reflection. (aka single-shot)"""
    raise NotImplementedError
    
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
    assert len(chat) > 0, "Chat must have at least one message"
    assert isinstance(chat, list), "Chat must be a list"
    assert all(isinstance(msg, str) for msg in chat), "Chat must be a list of strings"
    assert isinstance(context, list), "Context must be a list"
    assert all(isinstance(msg, str) for msg in context), "Context must be a list of strings"
    rendered_prompt = self.render_prompt(
      chat=chat,
      context=context,
    )
    _logger.debug(f"Entity {self.name} has been asked to respond to the following chat\n{chat[-1]}")
    _logger.trace("Entity {self.name}: render_prompt()\n{prompt}".format(
      self=self,
      prompt='\n'.join(rp.content for rp in rendered_prompt),
    ))    
    
    # Think
    
    # Entity will come up with a response
    initial_response = await self._send(
      messages=rendered_prompt,
      model=model,
      personality=responding_personality,
    )
    _logger.debug(f"Entity {self.name} initial response\n{initial_response}")
    return initial_response

    # Let the entity think about it's response
    # reflective_thought = "Here is the conversation you are replying to:\n{conversation}You want to respond with: {response}. How could you improve your response? ".format(
    #   response=initial_response,
    #   conversation='\n'.join(f'- {c}' for c in chat),
    # )
    reflective_thought = "How can you improve the content quality of your response\n>{response} to\n> {chat}".format(
      response=initial_response,
      chat=chat[-1],
    )
    _logger.debug(f"Entity {self.name} is reflecting on it's response with the following thought\n{reflective_thought}")
    reflection = await self.think(
      thought=reflective_thought,
      # context=context,
      context=[],
      model=model,
      thinking_personality=reflection_personality,
    )
    _logger.debug(f"Entity {self.name} concluded\n{reflection}")
    # Generate another response incorporating the reflection
    _logger.trace(f"Entity {self.name} is revising it's response")
    revised_response = await self._send(
      messages=[
        _user_msg(f"# This is your persona\n{self.persona}"),
        _user_msg("\n".join([
          "Without being verbose, improve the content quality of your response by applying the provided ideas",
          "# Here is the conversation you are replying to:",
          chat[-1],
          "# You want to respond with:",
          initial_response,
          "# You can improve your response by applying these ideas:",
          reflection,
        ])),
      ],
      model=model,
      personality=responding_personality,
    )
    _logger.debug(f"Entity {self.name} revised it's response\n{revised_response}")
    # TODO: Add Heuristics to determine if the response is any good
    return revised_response
  
  async def think(
    self,
    thought: str,
    context: Iterable[str],
    model: str,
    thinking_personality: str,
  ) -> str:
    """The entity reflects on the content of an idea to better understand it or.
    The Entity references the following:
      - It's Persona
      - It's internal context (ie. `entity.context`)
      - Environmental Context (in order provided) (`context` arbitrary textual data to be used as context)
      - The thought to reflect on (`thought`)
    """
    _user_msg = lambda content: PromptMessage(
      content=content,
      role=PROMPT_MESSAGE_ROLE.USER,
    )
    _assistant_msg = lambda content: PromptMessage(
      content=content,
      role=PROMPT_MESSAGE_ROLE.ASSISTANT,
    )
    # generate an initial thought
    _logger.trace(f"Entity: {self.name} is thinking about: {thought}")
    initial_thought = await self._send(
      messages=[
        msg for msg in [
          _user_msg(f"# This is your persona\n{self.persona}") if self.persona is not None else None,
          _user_msg(self.render_context()) if len(self.context) > 0 else None,
          _user_msg("# Here are observations you have made\n{context}".format(context='\n'.join(context))) if len(context) > 0 else None,
          _user_msg(f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
        ] if msg is not None
      ],
      model=model,
      personality=thinking_personality,
    )
    _logger.trace(f"Entity {self.name} is reflecting on it's thought: {initial_thought}")
    # conduct a challenge session
    challenge_session = await self._send(
      messages=[
        _user_msg(f"# This is your persona\n{self.persona}"),
        _user_msg(self.render_context()),
        _user_msg("# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
        _assistant_msg(f"# My Initial Thoughts\n{initial_thought}"),
        _user_msg(f"# Reframe your thoughts, challenge your assumptions, & consider alternative points of view\n{initial_thought}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    _logger.trace(f"Entity {self.name} is challenging it's thoughts: {challenge_session}")
    # reflect on the challenge session & iterate on the initial thought
    reflection = await self._send(
      messages=[
        _user_msg(f"# This is your persona\n{self.persona}"),
        _user_msg(self.render_context()),
        _user_msg("# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
        _assistant_msg(f"# My Initial Thoughts\n{initial_thought}"),
        _user_msg(f"# Reframe your thoughts, challenge your assumptions, & consider alternative points of view\n{initial_thought}"),
        _assistant_msg(f"# My Challenge Session\n{challenge_session}"),
        _user_msg(f"# Reflect on your challenge session & iterate on your original thoughts incorporating ideas & points of view that make it better\n{challenge_session}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    _logger.trace(f"Entity {self.name} summarized it's thought as: {reflection}")
    return reflection

  def to_dict(self):
    return {
      "uuid": self.uuid.hex,
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
