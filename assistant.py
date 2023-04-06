"""
An assistant PoC for ideation & workflow automation
"""
import asyncio
import json
import os
import pathlib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterable, Any

from loguru import logger

from _assistant.conversation import MessagingInterface
from _assistant.conversation.flow import InteractiveSession
from _assistant.conversation.memory import EphemeralMemory
from _assistant.llm import MODEL_CLASS, ModelInterface, load_llm
from _assistant import _logger, _LoggingInterface, ENTITY

# patch the module's logger
class _Logger(_LoggingInterface):
  async def __call__(self, msg: str, level: str):
    if level in ["trace", "debug"]:
      logger.trace(msg)
    elif level in ["info"]:
      logger.info(msg)
    elif level in ["warning"]:
      logger.warning(msg)
    elif level in ["error", "fatal", "critical"]:
      logger.error(msg)
    elif level in ["success"]:
      logger.success(msg)
    else:
      raise ValueError(f"Unknown log level: {level}")

_logger = _Logger()


class Subcommand(ABC):
  @abstractmethod
  async def __call__(self, *args: str, **kwargs: str):
    ...

_commmon_args = {}
_common_kwargs = {
  "help": {
    "default_value_factory": lambda *_, **__: False,
    "empty_value_factory": lambda *_, **__: True,
    "casting_factory": lambda x: x.lower() in ["true", "1", "yes"],
    "description": "Print this help message and exit.",
  },
  "verbose": {
    "default_value_factory": lambda *_, **__: False,
    "empty_value_factory": lambda *_, **__: True,
    "casting_factory": lambda x: x.lower() in ["true", "1", "yes"],
    "description": "Enable verbose logging.",
  },
  "quiet": {
    "default_value_factory": lambda *_, **__: False,
    "empty_value_factory": lambda *_, **__: True,
    "casting_factory": lambda x: x.lower() in ["true", "1", "yes"],
    "description": "Suppress all output to stderr.",
  },
  "cache": {
    "default_value_factory": lambda *_, **__: os.environ.get('ASSISTANT_CHAT_LOGS', f"{os.getcwd()}/.cache/assistant_chat_logs"),
    "casting_factory": str,
    "description": "Where the chat log is stored",
  },
  "token": {
    "default_value_factory": lambda *_, **__: os.environ.get('OPENAI_API_KEY', None),
    "casting_factory": str,
    "description": "The OpenAI API key to use for the chat session.",
  },
}

def _get_llm_class(model: str) -> MODEL_CLASS:
  try:
    return MODEL_CLASS[model.upper()]
  except KeyError:
    raise ValueError(f"Unknown model: {model}")

def _load_persona(persona: str) -> str:
  if persona.startswith("@"):
    persona_path = pathlib.Path(persona[1:])
    if not persona_path.exists():
      raise ValueError(f"Persona file not found: {persona_path}")
    return persona_path.read_text()
  return persona

def _load_personality(personality: str) -> str | dict:
  if personality.startswith("@"):
    personality_path = pathlib.Path(personality[1:])
    if not personality_path.exists():
      raise ValueError(f"Personality file not found: {personality_path}")
    return json.loads(personality_path.read_text())
  return personality

_chat_args = {}
_chat_kwargs = {
  "model": {
    "default_value_factory": lambda *_, **__: "gpt3",
    "casting_factory": _get_llm_class,
    "description": "The model to use for the chat session.",
  },
  "personality": {
    "default_value_factory": lambda *_, **__: "balanced",
    "casting_factory": _load_personality,
    "description": "The personality to use for the chat session. Prepend with @ to load a custom personality object from a file.",    
  },
  "persona": {
    "default_value_factory": lambda *_, **__: "You are a helpful assistant.",
    "casting_factory": _load_persona,
    "description": "The persona to use for the chat session. Prepend with @ to load from a file.",    
  },
}

@dataclass
class User(MessagingInterface):
  input_reader: Any
  output_writer: Any
  
  async def send(self, message: str):
    self.output_writer.write(message)
    self.output_writer.flush()
  
  async def receive(self) -> str:
    print("\n\n>", end=" ", flush=True)
    return self.input_reader.readline()

@dataclass
class Model(MessagingInterface):  
  llm: ModelInterface
  __response: AsyncIterable[str] | None = field(default=None, init=False)

  async def send(self, message: str, context: list[tuple[ENTITY, str]]):
    logger.trace(f"{message=}")
    logger.trace(f"{context=}")
    self.__response = await self.llm.prompt(
      prompt=message,
      context=context if context else [],
    )

  async def receive(self) -> str:
    if self.__response is None:
      raise ValueError("No response available")
    
    message = ""
    async for tokens in self.__response:
      message += tokens
    return message

@dataclass
class Chat(Subcommand):
  args_def: dict = field(default_factory=lambda: _chat_args)
  kwargs_def: dict = field(default_factory=lambda: _chat_kwargs)

  async def __call__(self, *args: str, **kwargs: str):
    """Start an interactive session with the assistant"""

    llm: ModelInterface = load_llm(
      model=MODEL_CLASS[kwargs["model"].upper()],
      token=kwargs["token"],
      personality=kwargs["personality"],
      persona=kwargs["persona"],
    )

    model = Model(llm=llm)
    memory = EphemeralMemory()

    user = User(
      input_reader=sys.stdin,
      output_writer=sys.stdout,
    )

    conversation = InteractiveSession(
      user=user,
      model=model,
      memory=memory,
    )

    task = asyncio.create_task(
      conversation(
        max_tokens=llm.max_tokens,
        calc_tokens=llm.token_length,
      )
    )
    try:
      await task
    except KeyboardInterrupt:
      logger.info("User requested to exit the chat session...")
      logger.trace("Cancelling the chat session...")
      task.cancel()

def init_cache(cache: str):
  cache_path = pathlib.Path(cache)
  if not cache_path.exists():
    cache_path.mkdir(parents=True, exist_ok=True)

def main(
  args: list[str],
  kwargs: dict,
  remainder: list[str],
  raw_argv: list[str],
) -> int:
  if len(args) == 0:
    logger.error("No subcommand provided")
    return 1
  subcmd_class = {
    "chat": Chat,
  }.get(args[0], None) 

  if subcmd_class is None:
    logger.error(f"Unknown subcommand: {args[0]}")
    return 1
  
  subcmd = subcmd_class()
  subcmd_kwargs = _parse_kwargs(
    argv=raw_argv,
    kwarg_defs=subcmd.kwargs_def,
  )
  
  try:
    init_cache(kwargs["cache"])
    asyncio.run(subcmd(*args[1:], **kwargs, **subcmd_kwargs))
  except Exception as e:
    logger.opt(exception=e).error(f"Error encountered while running '{args[0]}'")
    return 1
  return 0


def _parse_kwargs(
  argv: list[str],
  kwarg_defs: dict[str, dict],
) -> dict:
  _kwargs = {}
  _parsed_kwargs = {}
  for arg in argv:
    if arg.startswith("-"):
      try:
        key, value = arg.split("=")
      except ValueError:
        key, value = arg, None
      _parsed_kwargs[key.lstrip('-').lower()] = value
  for key in kwarg_defs:
    if key in _parsed_kwargs:
      if _parsed_kwargs[key] is None:
        _kwargs[key] = kwarg_defs[key]["empty_value_factory"]()
      else:
        _kwargs[key] = kwarg_defs[key]["casting_factory"](
          _parsed_kwargs[key]
        )
    elif "default_value_factory" in kwarg_defs[key]:
      _kwargs[key] = kwarg_defs[key]["default_value_factory"]()
    else:
      logger.warning(f"No Value could be loaded for {key}")
  
  return _kwargs

def _parse_args(argv: list[str]) -> list:
  return [
    arg
    for arg in argv
    if not arg.startswith("-")
  ]

def _split_args(argv: list[str], split_on: str) -> tuple[list, list]:
  try:
    return argv[:argv.index(split_on)], argv[argv.index(split_on)+1:]
  except ValueError:
    return argv, []

def _setup_logging(verbose: bool, quiet: bool):
  logger.remove()
  
  if quiet:
    sys.stderr = open(os.devnull, "w")
  
  if verbose:
    logger.add(sys.stderr, level="TRACE")
  else:
    logger.add(sys.stderr, level="ERROR")

def _help():
  print(f"""
Usage: {sys.argv[0]} [OPTIONS] [CMD] [ARGS...]

About:
  Entrypoint to the assistant application.

Options:
  -h, --help
    Print this help message and exit.
  --verbose
    Enable verbose logging.
  --quiet
    Suppress all output to stderr.
  --cache=DIRECTORY
    Where the application's stateful data is stored.
Commands:
  chat
    Start an interactive session with the assistant
  """)

if __name__ == "__main__":
  _rc = 255
  try:
    _argv, _remainder = _split_args(argv=sys.argv[1:], split_on="--")
    _args = _parse_args(argv=_argv)
    _kwargs = _parse_kwargs(argv=_argv, kwarg_defs=_common_kwargs)
    _setup_logging(verbose=_kwargs["verbose"], quiet=_kwargs["quiet"])
    
    # TODO Generate the help message from the subcommands
    if _kwargs["help"]:
      _help()
      _rc = 0
    else:
      _rc = main(args=_args, kwargs=_kwargs, remainder=_remainder, raw_argv=sys.argv[1:])
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled error during runtime...")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)
