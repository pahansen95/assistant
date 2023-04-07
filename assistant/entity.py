from . import _logger, PromptInterface, PROMPT_PERSONALITY, PROMPT_MESSAGE_ROLE, PromptMessage
from dataclasses import dataclass, field, KW_ONLY
import uuid
from typing import Iterable, Any
 
@dataclass
class Entity:
  """A Contributor to a Conversation. key & persona are optional & don't contribute the entity's identity."""
  uuid: uuid.UUID
  """The UUID of the entity."""
  name: str
  """The name of the entity."""
  _send: PromptInterface
  """The interface to the LLM that the entity uses to prompt for a response."""
  _: KW_ONLY
  key: tuple[str, ...] | None = field(default=None)
  """An optional set of strings that uniquely describe the entity's persona"""
  persona: str | None = field(default=None)
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
    _user_msg = lambda content: PromptMessage(
      content=content,
      role=PROMPT_MESSAGE_ROLE.USER,
    )
    # Entity will come up with a response
    initial_response = await self._send(
      messages=[
        _user_msg(f"Your name is {self.name}"),
        _user_msg(f"# This is your persona\n{self.persona}"),
        _user_msg(self.render_context()),
        _user_msg("# Here are observations you have made\n{context}".format(context='\n'.join(f'- {c}' for c in context))),
        _user_msg("# Here is the conversation so far\n"),
        *[
          _user_msg(c)
          for c in chat
        ],
      ],
      model=model,
      personality=responding_personality,
    )
    await _logger.trace(f"Entities {self.name} initial response: {initial_response}")
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
    )
    await _logger.trace(f"Entities {self.name} reflection on it's thought: {reflection}")
    # Generate another response incorporating the reflection
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
    await _logger.trace(f"Entities {self.name} revised response: {revised_response}")
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
    _user_msg = lambda content: PromptMessage(
      content=content,
      role=PROMPT_MESSAGE_ROLE.USER,
    )
    _assistant_msg = lambda content: PromptMessage(
      content=content,
      role=PROMPT_MESSAGE_ROLE.ASSISTANT,
    )
    # generate an initial thought
    await _logger.trace(f"Entity: {self.name} is thinking about: {thought}")
    initial_thought = await self._send(
      messages=[
        _user_msg(f"# This is your persona\n{self.persona}"),
        _user_msg(self.render_context()),
        _user_msg("# Here are observations you have made\n{context}".format(context='\n'.join(context))),
        _user_msg(f"# Ruminate on the following, itemize your thoughts & explain your reasoning\n{thought}"),
      ],
      model=model,
      personality=thinking_personality,
    )
    await _logger.trace(f"Entity {self.name} is reflecting on it's thought: {initial_thought}")
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
    await _logger.trace(f"Entity {self.name} is challenging it's thoughts: {challenge_session}")
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
    await _logger.trace(f"Entity {self.name} summarized it's thought as: {reflection}")
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
