import openai
import tiktoken
import asyncio
from typing import AsyncIterable, Iterable, AsyncGenerator

from . import _logger, PromptInterface, PromptMessage, PROMPT_PERSONALITY, PROMPT_MESSAGE_ROLE, ResponseIncomplete
from dataclasses import dataclass, field, KW_ONLY

OPENAI_MODEL_LOOKUP = {
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

max_openai_api_calls = asyncio.Semaphore(10)

async def count_tokens(model: str, *messages: str):
  """Returns the number of tokens used in a prompt."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    _logger.warning(f"Model {model} not found in TikToken. Using default encoding.")
    encoding = tiktoken.get_encoding("cl100k_base")
  
  return len(encoding.encode(
    "".join(msg for msg in messages)
  ))

async def _streaming_watchdog(
  cancel_task: asyncio.Task,
  timeout: float,
  chunk_recieved: asyncio.Event,
) -> None:
  """Waits for a chunk to be recieved before timing out."""
  _logger.trace("Starting OpenAI Streaming API watchdog...")
  try:
    while True:
      await asyncio.wait_for(chunk_recieved.wait(), timeout)
      chunk_recieved.clear()
  except asyncio.CancelledError:
    _logger.trace("OpenAI Streaming API watchdog cancelled. Stopping watchdog...")
  except asyncio.TimeoutError:
    _logger.warning("OpenAI Streaming API timed out. Cancelling stream...")
    cancel_task.cancel()

async def _safe_stream(
  chunk_timeout: float,
  **acreate_kwargs,
) -> AsyncGenerator[str, None]:
  """Uses the streaming protocol w/ openAI to avoid hanging requests."""
  _logger.trace("Starting streaming API request...")
  acreate_kwargs.pop("stream", None)
  _logger.trace("Acquiring a spot in the api call queue...")
  async with max_openai_api_calls:
    _logger.trace("Acquired a spot in the api call queue. Calling the API...")
    streaming_response = await openai.ChatCompletion.acreate(
      stream=True,
      **acreate_kwargs,
    )
    try:
      _logger.trace("Streaming API request started. Starting watchdog...")
      chunk_recieved = asyncio.Event()
      watchdog_task = asyncio.create_task(
        _streaming_watchdog(
          asyncio.current_task(),
          chunk_timeout,
          chunk_recieved,
        )
      )
      try:
        _logger.trace("Watchdog scheduled. Streaming chunks...")
        async for chunk in streaming_response:
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
          elif chunk['choices'][0]['finish_reason'] == 'stop':
            _logger.trace("OpenAI Streaming API finished. Stopping stream...")
            break
          else:
            raise ResponseIncomplete(chunk['choices'][0]['finish_reason'])
      except asyncio.CancelledError:
        _logger.warning("OpenAI Streaming API cancelled. Stopping stream...")
    finally:
      _logger.trace("Stopping watchdog...")
      watchdog_task.cancel()
      _logger.trace("Closing streaming API request...")
      try:
        await streaming_response.aclose()
      except:
        pass
      _logger.trace("Waiting for watchdog to stop...")
      await watchdog_task

@dataclass
class OpenAIChatCompletion(PromptInterface):
  """A prompt interface that uses the OpenAI Chat Completion API."""
  token: str = field(kw_only=True)
  """The OpenAI API key."""
  model_lookup: dict[str, dict] = field(default_factory=lambda: OPENAI_MODEL_LOOKUP, kw_only=True)
  """Lookup model details by the user friendly name."""

  def __post_init__(self):
    assert self.token
    openai.api_key = self.token
  
  @property
  def models(self) -> list[str]:
    return list(self.model_lookup.keys())

  async def __aiter__(
    self,
    messages: Iterable[PromptMessage],
    model: str, # The Specific LLM to use
    personality: PROMPT_PERSONALITY,
  ) -> AsyncIterable[str]:
    """Asynchronously prompt the LLM for a response. Streams the response. Can't retry a stream. Use `__call__` instead."""
    _logger.trace(f"Streaming response from {model} with personality {personality}...")
    _msgs = [
      {
        "content": msg.content,
        "role": msg.role.value,
      } for msg in messages
    ]
    
    total_tokens = await count_tokens(self.model_lookup[model]["name"], *[m['content'] for m in _msgs])
    if total_tokens <= self.model_lookup[model]['max_tokens'] // 2:
      pass
    elif total_tokens > self.model_lookup[model]['max_tokens'] // 2:
      _logger.warning(f"Prompt exceeds 50% of maximum number of tokens for model {model}.")
    elif total_tokens >= int(9 * self.model_lookup[model]['max_tokens'] / 10):
      _logger.warning(f"Prompt exceeds 90% the number of tokens for model {model}.")
    elif total_tokens >= self.model_lookup[model]['max_tokens']:
      _logger.error(f"Prompt exceeds maximum number of tokens for model {model}.")
      raise RuntimeError(f"Prompt exceeds maximum number of tokens for model {model}.")

    _logger.trace(f"Starting stream...")
    async for response in _safe_stream(
      chunk_timeout=1, # Chunks should be recieved within milliseconds
      model=self.model_lookup[model]["name"],
      messages=_msgs,
      **self.model_lookup[model]["personality"][personality.value]["tuning"],
    ):
      yield response
    
  async def __call__(
    self,
    messages: Iterable[PromptMessage],
    model: str, # The Specific LLM to use
    personality: PROMPT_PERSONALITY,
    max_retry_count: int = 3
  ) -> str:
    """Asynchronously prompt the LLM for a response. Returns the response."""
    _logger.info(f"Prompting {model} with {personality.value} personality...")
    retry_count = 0
    while True:
      _logger.trace(f"Attempt {retry_count}/{max_retry_count}...")
      try:
        response = ""
        chunk_generator = self.__aiter__(messages, model, personality)
        async for chunk in chunk_generator:
          response += chunk
        return response
      except (openai.OpenAIError, openai.APIError, asyncio.TimeoutError):
        if retry_count >= max_retry_count:
          raise
        retry_count += 1
        _logger.warning(f"Retrying Prompt {retry_count}/{max_retry_count}...")
        continue
