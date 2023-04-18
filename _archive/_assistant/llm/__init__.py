import enum
from typing import AsyncIterator, AsyncIterable
from abc import ABC, abstractmethod
from .. import Error, ENTITY

class LLMError(Error):
  """Base class for LLM errors."""
  ...

class UnknownModelError(LLMError):
  """The requested model is not known."""
  ...

class ReplyError(LLMError):
  """Base class for LLM reply errors."""
  ...

class PromptError(LLMError):
  """Base class for LLM prompt errors."""
  ...

class ReplyTooLong(ReplyError):
  """The Model ran out of tokens while generating the response."""
  ...

class PromptTooLong(PromptError):
  """The Prompt exceeds the model's maximum length."""
  ...

class MODEL_CLASS(enum.Enum):
  GPT3 = "gpt-3.5-turbo"

class ModelInterface(ABC):

  @property
  @abstractmethod
  def max_tokens(self) -> int:
    """Returns the maximum number of tokens the model can process."""
    ...

  @abstractmethod
  def token_length(self, text: str) -> int:
    """Returns the length of the text in tokens."""
    ...
    
  @abstractmethod
  async def prompt(self, prompt: str, context: list[tuple[ENTITY, str]] = []) -> AsyncIterable[str]:
    """Prompts the model for a response with optional context. Returns the response to the API call and a generator to stream the prompt's response."""
    ...

class StreamingReplyInterface(ABC):
  @abstractmethod
  async def __aiter__(self, prompt: str) -> AsyncIterator[str]:
    """Streams the prompt's response.
    Only one caller may iterate over a response.
    """
    ...

def load_llm(
  model: MODEL_CLASS,
  token: str,
  persona: str,
  personality: str | dict,
) -> ModelInterface:
  if model in [MODEL_CLASS.GPT3]:
    # TODO: Check the user has access to the declared model
    from .openai import GPT, PERSONALITIES

    if isinstance(personality, str):
      personality = PERSONALITIES[model.value][personality.lower()]
    
    assert "tuning" in personality, "The provided personality is malformed"
    assert persona, "A non empty persona must be provided"

    return GPT(
      model=model.value,
      token=token,
      personality=personality["tuning"],
      persona=persona,
    )
  else:
    raise UnknownModelError(f"Unknown model: {model}")
    


