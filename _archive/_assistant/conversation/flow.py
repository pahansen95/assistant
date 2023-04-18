from .. import _logger, ENTITY
from . import MemoryInterface, MessagingInterface, RecallError
from dataclasses import dataclass
import asyncio
from collections.abc import Callable

async def _naive_context(
  memory: MemoryInterface,
) -> list[tuple[ENTITY, str]]:
  """Returns the last 3 messages staged in short term memory"""
  return [
    message
    for message in (await asyncio.gather(
      *[
        memory.recall(-1 * i)
        for i in range(3)
      ],
      return_exceptions=True,
    ))
    if not isinstance(message, Exception) 
  ]

async def token_limit_context(
  memory: MemoryInterface,
  token_limit: int,
  calc_token: Callable[[str], int],
) -> list[tuple[ENTITY, str]]:
  """Returns context up to a token limit"""
  context = []
  index = -1
  while sum(calc_token(text) for _, text in context) <= token_limit:
    try:
      context.append(await memory.recall(index))
      index -= 1
    except RecallError:
      break
  
  if sum(calc_token(text) for _, text in context) > token_limit:
    # Truncate the last message to fit the token limit
    entity, text = context.pop()
    reamining_tokens = token_limit - sum(calc_token(text) for _, text in context)
    # Truncate the text to fit the token limit; drop tokens from start to end
    # Do a binary search to find the best truncation point
    truncate_index = 0
    lower = 0
    upper = len(text)
    while True:
      truncate_index = (lower + upper) // 2
      if calc_token(text[truncate_index:]) <= reamining_tokens:
        lower = truncate_index
      else:
        upper = truncate_index
      if upper - lower <= 1:
        break
    context.append((entity, text[truncate_index:]))
  
  context.reverse()
  return context

@dataclass
class InteractiveSession:
  """A basic interactive session with the assistant."""
  user: MessagingInterface
  model: MessagingInterface
  memory: MemoryInterface
  
  async def __call__(
    self,
    max_tokens: int,
    calc_tokens: Callable[[str], int],
  ):
    """An interactive session with the assistant"""
    try:
      while True:
        await _logger.trace("Waiting for user message")
        user_message = await self.user.receive()
        assert isinstance(user_message, str), "User message must be a string"
        if len(user_message) <= 0:
          await _logger.info("User message is empty, skipping...")
          continue
        await _logger.trace("User message received")

        await _logger.trace("Logging user message")
        await self.memory.stage(
          entity=ENTITY.USER,
          message=user_message,
        )
        await _logger.trace("User message logged")

        await _logger.trace("Getting context")
        # context = await _naive_context(self.memory)
        context = await token_limit_context(
          memory=self.memory,
          # token_limit=max_tokens // 2,
          token_limit=max_tokens,
          calc_token=calc_tokens,
        )
        await _logger.trace(f"{context=}")
        await _logger.trace("Context retrieved")
        await _logger.trace("Sending Model a message")
        await self.model.send(
          user_message,
          context=context,
        )
        await _logger.trace("Message sent to model")
        
        await _logger.trace("Waiting for Model's response")
        response = await self.model.receive()
        await _logger.trace("Model response received")
        
        await _logger.trace("Logging Model response")
        await self.memory.stage(
          entity=ENTITY.ASSISTANT,
          message=response,
        )
        await _logger.trace("Model response logged")

        await _logger.trace("Responding to user")
        await self.user.send(response)
        await _logger.trace("User response sent")
    except (asyncio.CancelledError, KeyboardInterrupt):
      await _logger.trace("Interactive session cancelled")
