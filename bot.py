"""A New and Improved Bot. Integrates with various backends to provide a User Friendly interface to debugging the natural language output of the bot.

Currently supports the following backends:
- Matrix (Most feature complete)

## Notes

### Matrix

- One to One mapping of bots to Matrix users.
- Bots listen & respond to messages in a few places:
  - Direct messages
    - This is an administrative interface to the bot to adjust backend runtime parameters.
  - Rooms bot's have joined
    - This is the primary interface to the bot. Any user (bot or human) can @ the bot & it will respond.
"""

import asyncio
import json
import os
import pathlib
import sys
import uuid
from typing import TypeVar, AsyncGenerator, Iterable, Any
from urllib.parse import quote as url_quote

import aiohttp
import loguru._recattrs
from loguru import logger

import assistant
import assistant.entity as entity
import assistant.openai as openai
import assistant.transcript as transcript

class MatrixClient:
  def __init__(self,
    client_session: aiohttp.ClientSession,
  ) -> None:
    self.client_session = client_session

  async def deserialize_content(self,
    response: aiohttp.ClientResponse,
  ) -> str | dict:
    _type = response.content_type.split(';')
    _props = {
      k: v for k, v in [
        prop.split('=') for prop in _type[1:]
      ]
    }
    _type = _type[0]
    logger.annoy(f'Content Type: {_type}')
    logger.annoy(f'Content Properties: {_props}')

    output = None
    if _type == 'text/plain':
      output = await response.text()
    elif _type == 'application/json':
      output = await response.json()
    else:
      logger.error(f'Unknown Content Type: {_type}')
      raise RuntimeError(f'Unknown Content Type: {_type}')
    logger.annoy(f'Deserialized Content Type: {_type}')
    logger.annoy(f'Deserialized Content: {output}...')
    return output

  async def get_rooms(self,
    client_session: aiohttp.ClientSession,
  ) -> list[str]:
    """Get a list of room IDs the bot is a member of."""
    async with client_session.get(
      "/_matrix/client/v3/joined_rooms",
    ) as response:
      response.raise_for_status()
      data = self.deserialize_content(response)
      return data['joined_rooms']

  async def get_room_id_from_alias(self,
    room_alias: str,
    client_session: aiohttp.ClientSession,
  ) -> str:
    assert room_alias is not None

    async with client_session.get(
      f"/_matrix/client/v3/directory/room/{url_quote('#'+room_alias.lstrip('#'))}",
    ) as response:
      response.raise_for_status()
      data = self.deserialize_content(
        response.headers['Content-Type'],
        await response.read(),
      )
      return data['room_id']

  async def server_event_listener(
    room_id: str,
    event_types: Iterable[str],
    client_session: aiohttp.ClientSession,
  ) -> AsyncGenerator[dict, None]:
    """Listen for events from a Matrix Room."""  
    assert room_id is not None
    assert len(event_types) > 0

    # TODO: Handle events older than the limit
    _filter_def = {
      'room': {
        'rooms': [room_id],
        'timeline': {
          'limit': 100,
          'types': list(set(event_types)),
        },
      },
    }
    # TODO create server side filter
    sync_batches: list[str] = []
    while True:
      async with client_session.get(
        f"/_matrix/client/v3/sync",
        headers={
          'Content-Type': 'application/json',
        },
        params={
          k: v for k, v in {
            'since': sync_batches[-1] if len(sync_batches) > 0 else None,
            'timeout': int(5 * 1000),
            'filter': json.dumps(_filter_def), # TODO: Replace with Server Side Filter ID
          }.items() if v is not None
        },
      ) as response:
        if not (response.status >= 200 and response.status < 300):
          try:
            response.raise_for_status()
          except Exception as e:
            logger.opt(exception=e).error('Sync Error')
          await asyncio.sleep(1)
          continue
        room_data = self.deserialize_content(
          response.headers['Content-Type'],
          await response.read(),
        )['rooms']['join'][room_id]
        room_timeline = room_data['timeline']
        if room_timeline['limited']:
          logger.warning(f"FYI; This isn't the full message history, just the last {_filter_def['room']['timeline']['limit']} messages")
        if 'prev_batch' in room_timeline:
          if room_timeline['prev_batch'] not in sync_batches:
            assert len(sync_batches) == 0
            sync_batches.append(room_timeline['prev_batch'])
        
        for event in room_timeline['events']:
          if event['type'] == 'm.room.message':
            assert {'body', 'msgtype'} <= event['content'].keys(), 'Malformed Message'
            yield event

        sync_batches.append(sync_batches['next_batch'])

  async def send_text_message(
    room_id: str,
    message: str,
    client_session: aiohttp.ClientSession,
  ) -> str:
    """Send a message to a Matrix Room."""
    assert room_id is not None
    assert message is not None

    async with client_session.put(
      f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{uuid.uuid4().hex}",
      headers={
        'Content-Type': 'application/json',
      },
      data=json.dumps({
        'msgtype': 'm.text',
        'body': message,
      }),
    ) as response:
      response.raise_for_status()
      return self.deserialize_content(response)


async def bot_loop(
  # ...
) -> int:
  """Main loop for the bot."""
  client: aiohttp.ClientSession = ...
  rooms = await self.get_rooms(client_session)

  """Development Notes
  > K.I.S.S. - Keep It Simple Stupid
  
  - Each room represents a "namespace" for a bot to operate in.
    - Conversations are scoped to the room.
    - Memory, Context & State are scoped to their respective rooms.
  - Runtime Configurables are intrinsic to the bot itself & not scoped to a room. Any runtime changes will affect the bot's behavior in all rooms.
  """

  async with client as client_session:
    ...

async def main(*args, **kwargs) -> int:
  """Main entry point for the bot."""
  persona_dir = pathlib.Path(kwargs["personas"])
  if not persona_dir.exists():
    logger.error(f"Personas directory {persona_dir} does not exist.")
    return 1

  if kwargs["model"] in openai.OPENAI_MODEL_LOOKUP:
    model_interface = openai.OpenAIChatCompletion(
      token=os.environ["OPENAI_API_KEY"],
    )
  else:
    logger.error(f"Unknown model: {kwargs['model']}")
    return 1
  
  if args[0] == "discord":
    logger.info("Starting Discord Bot...")
    return await bot_loop(
      model_interface=model_interface,
      persona_dir=persona_dir,
      guild_ids=list(map(int, kwargs["guild-ids"].split(","))),
    )
  else:
    logger.error(f"Unknown subcommand: {args[0]}")
    return 255


def _parse_kwargs(*args: str, **kwargs: str) -> dict:
  _kwargs = {
    "help": False,
    "verbose": False,
    "debug": False,
    "trace": False,
    "annoy": False,
    "quiet": False,
    "modules": False,
    "cache": f"{os.environ['CI_PROJECT_DIR']}/meta/chain/",
    "personas": f"{os.environ['CI_PROJECT_DIR']}/meta/personas/",
    "model": "gpt3",
    "openai-concurrent": "10",
    "guild-ids": "1093645046986850346",
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
Usage: {sys.argv[0]} [GLOBAL OPTIONS] [SUBCMD] [SUBCMD OPTIONS] [ARGS...]
About:
  ...

Global Options:
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
  
Subcommands:
  discord
    About:
      Uses Discord for the front end.
    
    Options:
      --guild-ids=INT,INT,...
        The guild ids to run the bot in. Defaults to 1093645046986850346.
  """)

def _setup_logging(**_kwargs):
  # Set custom log levels w/ loguru. We'll use the same levels as the assistant package
  # The lower the lever, the less important the message is.
  # Lower levels should have duller colors & higher levels should have brighter colors.
  pallete = {
    "red": 0xcc0000,
    "green": 0x00cc00,
    "blue": 0x0000cc,
    "yellow": 0xcccc00,
    "cyan": 0x00cccc,
    "magenta": 0xcc00cc,
    "white": 0xcccccc,
    "black": 0x000000,
    "light-gray": 0xeeeeee,
    "gray": 0xbcbcbc,
    "dark-gray": 0x999999,
  }
  fmt_color = lambda c='white', b=True, u=False: f"<fg #{pallete[c.lower()]:06x}>{'<b>' if b else ''}{'<u>' if u else ''}"
  # Update loguru's log levels
  logger.level(
    name="USER_CRITICAL",
    no=assistant._MODULE_LOG_LEVELS.CRITICAL.value,
    color=fmt_color(c="red"),
    icon="💀",
  )
  logger.level(
    name="USER_ERROR",
    no=assistant._MODULE_LOG_LEVELS.ERROR.value,
    color=fmt_color(c="red"),
    icon="‼️"
  )
  logger.level(
    name="USER_SUCCESS",
    no=assistant._MODULE_LOG_LEVELS.SUCCESS.value,
    color=fmt_color(c="green"),
    icon="✅"
  )
  logger.level(
    name="USER_WARNING",
    no=assistant._MODULE_LOG_LEVELS.WARNING.value,
    color=fmt_color(c="yellow"),
    icon="⚠️"
  )
  logger.level(
    name="USER_INFO",
    no=assistant._MODULE_LOG_LEVELS.INFO.value,
    color=fmt_color(c="white"),
    icon="❕"
  )
  logger.level(
    name="USER_DEBUG",
    no=assistant._MODULE_LOG_LEVELS.DEBUG.value,
    color=fmt_color(c="light-gray", b=False),
    icon="🐛"
  )
  logger.level(
    name="USER_TRACE",
    no=assistant._MODULE_LOG_LEVELS.TRACE.value,
    color=fmt_color(c="gray", b=False),
    icon="🐞"
  )
  logger.level(
    name="USER_ANNOYING",
    no=assistant._MODULE_LOG_LEVELS.ANNOYING.value,
    color=fmt_color(c="dark-gray", b=False),
    icon="💤"
  )
  # Update loguru's log level shortcuts
  logger.annoying = lambda msg, *args, **kwargs: logger.log("USER_ANNOYING", msg)
  logger.annoy = lambda msg, *args, **kwargs: logger.log("USER_ANNOYING", msg)
  logger.trace = lambda msg, *args, **kwargs: logger.log("USER_TRACE", msg)
  logger.debug = lambda msg, *args, **kwargs: logger.log("USER_DEBUG", msg)
  logger.info = lambda msg, *args, **kwargs: logger.log("USER_INFO", msg)
  logger.warning = lambda msg, *args, **kwargs: logger.log("USER_WARNING", msg)
  logger.warn = lambda msg, *args, **kwargs: logger.log("USER_WARNING", msg)
  logger.error = lambda msg, *args, **kwargs: logger.log("USER_ERROR", msg)
  logger.success = lambda msg, *args, **kwargs: logger.log("USER_SUCCESS", msg)
  logger.critical = lambda msg, *args, **kwargs: logger.log("USER_CRITICAL", msg)
  logger.fatal = lambda msg, *args, **kwargs: logger.log("USER_CRITICAL", msg)
  
  ### Patch Loguru's RecordLevel to strip the `USER_` prefix
  def _patched_init(self, name: str, no: int, icon: str):
    self.name = name.removeprefix("USER_")
    self.no = no
    self.icon = icon
  setattr(
    loguru._recattrs.RecordLevel,
    "__init__",
    _patched_init,
  )
  ###

  # Set the log levels
  script_log_level = assistant._MODULE_LOG_LEVELS.WARNING
  assistant_module_log_level = None
  if _kwargs["verbose"]:
    script_log_level=assistant._MODULE_LOG_LEVELS.INFO
    assistant_module_log_level = assistant._MODULE_LOG_LEVELS.INFO
  elif _kwargs["debug"]:
    script_log_level=assistant._MODULE_LOG_LEVELS.DEBUG
    assistant_module_log_level = assistant._MODULE_LOG_LEVELS.DEBUG
  elif _kwargs["trace"]:
    script_log_level=assistant._MODULE_LOG_LEVELS.TRACE
    assistant_module_log_level = assistant._MODULE_LOG_LEVELS.TRACE
  elif _kwargs["annoy"]:
    script_log_level=assistant._MODULE_LOG_LEVELS.ANNOYING
    assistant_module_log_level = assistant._MODULE_LOG_LEVELS.ANNOYING
  
  if not _kwargs["quiet"]:
    # Custome logger based off the loguru default
    custom_fmt = (
      "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
      "<level>{level: ^10}</level> | "
      "{level.icon: ^2} | "
      "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.add(
      sys.stderr,
      level=f"USER_{script_log_level.name.upper()}",
      format=custom_fmt,
    )
  
    if _kwargs['modules'] and assistant_module_log_level:
      # Update the assistant module's log level
      assistant_logger = logging.getLogger(assistant._logging_name)
      assistant_logger.setLevel(assistant_module_log_level.value)
      assistant_logger.addHandler(
        assistant._CallbackHandler(_log_record_with_loguru)
      )
    
if __name__ == "__main__":
  _rc = 255
  try:
    logger.remove()
    _args = _parse_args(*sys.argv[1:])
    _kwargs = _parse_kwargs(*sys.argv[1:])
    _setup_logging(**_kwargs)
    if _kwargs["help"]:
      _help()
      _rc = 0
    else:
      _rc = asyncio.run(main(*_args, **_kwargs))
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled Exception raised during runtime...")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)

