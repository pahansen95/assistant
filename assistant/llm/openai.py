import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import AsyncGenerator, AsyncIterable, AsyncIterator

import openai
import tiktoken

from .. import ENTITY, _logger
from . import ModelInterface, ReplyError, PromptTooLong, StreamingReplyInterface

PERSONALITIES = {
  "gpt-3.5-turbo": {
    "creative": {
      "name": "creative",
      "description": "Responses are creative; the model is curious & constantly changes it's opinion.",
      "tuning": {
        "temperature": 2.0, # Double the default sampling temperature; The higher the temperature, the more random the samples.
        "top_p": 0.95, # 2 sigma; Model considers the top 95% of the (next token) distribution
      }
    },
    "balanced": {
      "name": "balanced",
      "description": "Responses are moderate; the model is consistent but can change it's opinion.",
      "tuning": {
        "temperature": 1.0, # The default sampling temperature
        "top_p": 0.815, # somewhere between 1 and 2 sigma; Model considers the top 81.5% of the (next token) distribution
      }
    },
    "reserved": {
      "name": "reserved",
      "description": "Responses are reserved; the model hardly every deviates from it's opinion.",
      "tuning": {
        "temperature": 0.5, # Half the default sampling temperature; The lower the temperature, the less random the samples.
        "top_p": 0.68, # 1 sigma; Model Considers the top 68% of the (next token) distribution
      }
    },
  },
}

MAX_TOKENS = {
  "gpt-3.5-turbo": 4096,
}

def _entity_to_role(entity: ENTITY) -> str:
  """Converts an entity to the role OpenAI expects."""
  assert isinstance(entity, ENTITY)
  if entity == ENTITY.USER:
    return "user"
  elif entity == ENTITY.ASSISTANT:
    return "assistant"
  else:
    raise ValueError(f"Unknown entity: {entity}")
  
def token_length(text: str, model: str) -> int:
  """Returns the number of tokens used in a prompt."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    encoding = tiktoken.get_encoding("cl100k_base")
  
  return len(encoding.encode(text))


@dataclass
class _TextReply(StreamingReplyInterface):
  response: AsyncIterable[dict]
  cleanup: Coroutine | None = field(default=None)
  __reply_buffer: list[str] = field(default_factory=list, init=False)
  __lock_streaming_iter: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
  __reply_already_streamed: bool = field(default=False, init=False)
  __reply_error: Exception = field(default=None, init=False)

  async def __streaming_reply(self) -> AsyncGenerator[str, None]:
    async for chunk in self.response:
      # Get the reply from the response
      # TODO: Support multiple choices
      if chunk["choices"][0]["delta"] != {}:
        if "content" in chunk["choices"][0]["delta"]:
          self.__reply_buffer.append(
            chunk["choices"][0]["delta"]["content"]
          )
        elif "role" in chunk["choices"][0]["delta"]:
          await _logger.trace("checking role & skip to next chunk...")
          if chunk["choices"][0]["delta"]["role"] != "assistant":
            await _logger.warning(f"Expected role 'assistant', got {chunk['choices'][0]['delta']['role']}.")
          continue # Skip to the next chunk
        yield self.__reply_buffer[-1]
      # Check if the model finished it's reply
      if chunk["choices"][0]["finish_reason"] == None:
        continue
      elif chunk["choices"][0]["finish_reason"] == "stop":
        break
      else:
        self.__reply_error = ReplyError(f"Model couldn't finish it's reply b/c '{chunk['choices'][0]['finish_reason']}'")
        break
  
  async def __aiter__(self) -> AsyncIterator[str]:
    # If the reply has already been streamed, return the buffer
    if self.__reply_already_streamed:
      for reply in self.__reply_buffer:
        yield reply
    else: # Otherwise, stream the reply
      # Make sure only one caller is streaming the reply
      async with self.__lock_streaming_iter:
        if self.__reply_already_streamed: # Check again in case another caller was waiting on the lock
          for reply in self.__reply_buffer:
            yield reply
        # Stream the reply
        try:
          async for reply in self.__streaming_reply():
            yield reply
        finally:
          if self.cleanup is not None:
            await self.cleanup()
          self.__reply_already_streamed = True
    
    # If the reply errored, raise the error
    if self.__reply_error:
      raise self.__reply_error

@dataclass
class GPT(ModelInterface):
  model: str
  token: str
  personality: dict
  persona: str

  @property
  def max_tokens(self) -> int:
    return MAX_TOKENS[self.model]

  def token_length(self, text: str) -> int:
    return token_length(text, self.model)

  async def prompt(
    self,
    prompt: str,
    context: list[tuple[ENTITY, str]] = [],
  ) -> StreamingReplyInterface:
    messages = [
      {
        "role": "user",
        "content": f"Take on the following persona: {self.persona}",
      },
      *[
        {
          "role": _entity_to_role(entity),
          "content": text,
        } for entity, text in context
      ],
      {
        "role": "user",
        "content": prompt,
      }
    ]
    token_count = sum(token_length(message["content"], self.model) for message in messages)
    if token_count > MAX_TOKENS[self.model] // 2:
      await _logger.warning(f"Prompt is half the max token count for model {self.model}. This may cause the model to fail to reply.")
    elif token_count >= MAX_TOKENS[self.model]:
      raise PromptTooLong(f"Prompt is longer than the max token count for model {self.model}.")

    response = await openai.ChatCompletion.acreate(
      model=self.model,
      messages=messages,
      stream=True,
      temperature=self.personality["temperature"],
      top_p=self.personality["top_p"],
    )
    async def _cleanup():
      await response.aclose()
    return _TextReply(
      response=response,
      cleanup=_cleanup,
    )
