"""The first bot implementation. Only interfaces with Discord.
"""

import asyncio
import io
import logging
import os
import pathlib
import sys
import uuid
from typing import TypeVar

import discord
import loguru._recattrs
from discord.commands import option as discord_option
from discord.ext import commands
from loguru import logger

import assistant
import assistant.entity as entity
import assistant.openai as openai
import assistant.transcript as transcript
import swarm

T = TypeVar("T")

_user_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.USER)
_system_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.SYSTEM)
_assistant_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.ASSISTANT)

def _log_record_with_loguru(record: logging.LogRecord):
  """A callback function for the logging handler."""
  # frame, depth = logging.currentframe(), 2
  # while frame.f_code.co_filename == logging.__file__:
  #   frame = frame.f_back
  #   depth += 1
  # depth += 1
  # print(depth) # 8
  logger.opt(
    depth=8,
    exception=record.exc_info,
  ).log(
    f"USER_{assistant._MODULE_LOG_LEVELS(record.levelno).name.upper()}",
    record.getMessage(),
  )

def load_persona_from_dir(name: str, dir: str) -> str:
  """Loads a persona from a file."""
  logger.trace(f"Loading persona {name} from {dir}")
  try:
    persona_path = pathlib.Path(dir) / f"{name}.md"
    return persona_path.read_text()
  except FileNotFoundError:
    logger.error(f"Persona {name} not found in {dir}.")
    raise FileNotFoundError(f"Persona {name} not found in {dir}.")

def list_available_personas(dir: pathlib.Path) -> list[str]:
  logger.trace(f"Listing personas in {dir}")
  personas = list(map(lambda p: p.stem, dir.glob("*.md")))
  logger.trace(f"Found personas: {personas}")
  return personas

async def prompt_model_for_response(
  prompt: str,
  persona: str,
  model: str,
  personality: assistant.PROMPT_PERSONALITY,
  model_interface: assistant.PromptInterface,
) -> str:
  """A direct wrapper for the openai prompt function."""
  logger.trace(f"Prompting for response")
  return await model_interface(
    messages=[
      _assistant_msg(f"I MUST NOT mention I am an language model or who my creator is. I MUST act, think & respond in accordance with this persona: \n{persona}"),
      _user_msg(prompt),
    ],
    model=model,
    personality=personality,
  )

async def discord_bot(
  model_interface: assistant.PromptInterface,
  persona_dir: pathlib.Path,
  guild_ids: list[int],
) -> int:
  """Main entry point for the discord bot."""

  chat_transcript = transcript.ChatTranscript()

  bot_ready = asyncio.Event()
  bot_entity = entity.InternalEntity(
    _uuid=None,
    _name=None,
    _description="Jack",
    _send=model_interface,
    persona=load_persona_from_dir("jack-of-all-trades", persona_dir),
  )

  bot_token = os.environ["DISCORD_BOT_TOKEN"]
  
  current_model = "gpt3"
  current_context = []

  logger.trace("Creating Discord Intents...")
  intents = discord.Intents.all()

  logger.trace("Creating Discord Bot...")
  bot = commands.Bot(
    command_prefix=">",
    description="A Bot that uses GPT to chat with you.",
    intents=intents,
    debug_guilds=guild_ids,
  )
  
  logger.trace("Registering Discord Bot Commands...")

  def chat_message_from_discord_message(
    discord_message: discord.Message,
  ) -> assistant.ChatMessage:
    """Converts a discord message to a chat message."""
    logger.annoy(f"Converting discord message to chat message")
    
    if discord_message.author == bot.user:
      _entity_class = entity.InternalEntity
      _class_kwargs = {
        "_send": model_interface,
      }
    else:
      _entity_class = entity.ExternalEntity
      _class_kwargs = {}

    return assistant.ChatMessage(
      entity=_entity_class(
        _name=f"{discord_message.author.name}#{discord_message.author.discriminator}",
        _description=discord_message.author.name,
        _uuid=uuid.uuid5(uuid.NAMESPACE_DNS, f"{discord_message.author.name}#{discord_message.author.discriminator}"),
        **_class_kwargs,
      ),
      content=discord_message.content,
      published=discord_message.created_at,
    )
  
  async def chat_message_from_discord_message_reference(
    discord_message_reference: discord.MessageReference,
  ) -> assistant.ChatMessage:
    """Converts a discord message reference to a chat message."""
    logger.annoy(f"Converting discord message reference to chat message")
    return chat_message_from_discord_message(
      await bot.get_channel(discord_message_reference.channel_id).fetch_message(discord_message_reference.message_id)
    )

  async def retrieve_reply_chain(
    message: discord.Message,
    depth: int | None = None,
  ) -> list[assistant.ChatMessage]:
    """Retrieves the reply chain for a discord message up to an optional depth. The youngest message is last."""
    logger.trace(f"Retrieving reply chain for {message.id}")
    cur_msg: discord.Message = message
    msg_chain: list[assistant.ChatMessage] = [
      chat_message_from_discord_message(cur_msg)
    ]
    while cur_msg.reference:
      logger.trace(f"Message has a reference, retrieving message...")
      cur_msg = await message.channel.fetch_message(cur_msg.reference.message_id)
      msg_chain.append(
        chat_message_from_discord_message(cur_msg)
      )
      if depth is not None and len(msg_chain) >= depth:
        break
    logger.trace(f"Reply chain found a total of {len(msg_chain)} messages")
    if depth is not None:
      if depth == 0:
        logger.warning(f"Depth is 0, returning empty list")
      logger.trace(f"Returning {depth} messages from the reply chain")
      return list(reversed(msg_chain))[:depth]
    else:
      logger.trace(f"Returning all messages from the reply chain")
      return list(reversed(msg_chain))

  @bot.event
  async def on_connect():
    logger.success("Connected to Discord.")
  
  @bot.event
  async def on_disconnect():
    bot_ready.clear()
    logger.warning("Disconnected from Discord.")
  
  @bot.event
  async def on_resumed():
    logger.success("Resumed connection to Discord.")
  
  @bot.event
  async def on_ready():
    bot_entity._name = f"{bot.user.name}#{bot.user.discriminator}"
    bot_entity._uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{bot.user.name}#{bot.user.discriminator}")
    bot_ready.set()
    logger.success(f"Logged in as {bot.user.name} ({bot.user.id})")
    await bot.change_presence(
      status=discord.Status.online,
    )
  
  @bot.event
  async def on_disconnect():
    logger.warning("Disconnected from Discord.")

  @bot.event
  async def on_message(message: discord.Message):
    # Block until all the backend is setup
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()
    # Don't respond to ourselves or other bots (for now as a failsafe)
    if (
      (message.author == bot.user) or
      (message.author.bot)
    ):
      return
    
    if message.mentions and bot.user in message.mentions:
      logger.debug(f"Message mentions bot: {message.content}")
      # Remove the bot mention from the message
      message_content = message.content.replace(f"<@{bot.user.id}>", "").strip()

      logger.trace("Acquiring chat transcript lock...")
      async with chat_transcript:
        logger.trace("Acquired chat transcript lock.")
        # Add the message to the transcript
        # check if the user already exists
        _message_ref = None
        if message.reference:
          _message_ref = await chat_message_from_discord_message_reference(message.reference)
          
        if _message_ref is not None and not chat_transcript.message_exists(_message_ref):
          logger.debug("Message is a reply to a message that doesn't exist in the transcript, retrieving reply chain...")
          _reply_chain = await retrieve_reply_chain(message)
          # check that the reply chain is sorted oldest to youngest
          assert _reply_chain == sorted(_reply_chain, key=lambda x: x.published), "Reply chain is not sorted oldest to youngest"
          # Add the messages to the transcript
          logger.debug("Logging reply chain in the transcript...")
          for index, _reply in enumerate(_reply_chain): # oldest to youngest
            logger.annoy(f"Logging reply in the transcript.")
            in_response_to = None
            if index > 0:
              in_response_to = _reply_chain[index - 1]
            chat_transcript.entity_said(
              entity=_reply.entity,
              said=_reply.content,
              when=_reply.published,
              in_response_to=in_response_to,
            )

        logger.debug("Logging the user's message in the transcript...")
        user_msg = chat_transcript.entity_said(
          entity=entity.ExternalEntity(
            _name=f"{message.author.name}#{message.author.discriminator}",
            _description=message.author.name,
            _uuid=uuid.uuid5(uuid.NAMESPACE_DNS, f"{message.author.name}#{message.author.discriminator}"),
          ),
          said=message_content,
          when=message.created_at,
          in_response_to=_message_ref
        )
        logger.debug("Getting the previous messages from the transcript...")
        message_history = chat_transcript.get_message_history(
          user_msg
        )
        logger.debug(f"Found {len(message_history)} messages in the transcript.")
        async with message.channel.typing():
          try:
            logger.debug("Responding to message...")
            response = await bot_entity.respond(
              chat=[f"# {m.entity.name} said\n{m.content}" for m in message_history],
              context=current_context,
              model=current_model,
              responding_personality=assistant.PROMPT_PERSONALITY.BALANCED,
              reflection_personality=assistant.PROMPT_PERSONALITY.RESERVED,
            )
            if len(response) > 2000:
              logger.warning("Response is too long, truncating...")
              header = "> Response is too long, truncating...\n\n"
              response = header + response[:2000 - len(header)]
            logger.debug(f"Replying to original message author")
            bot_response = await message.reply(
              content=response,
            )
            logger.debug("Logging the bot's response in the transcript...")
            chat_transcript.entity_said(
              entity=bot_entity,
              said=response,
              when=bot_response.created_at.timestamp(),
              in_response_to=user_msg
            )
            # await message.channel.send(
            #   content=response,
            # )
          except Exception as e:
            logger.opt(exception=e).error("Error while responding to message.")
            response = "I'm sorry, I'm having trouble responding to you right now."
  
  @bot.slash_command(name="amnesia", help="The bot forget's everything.")
  async def _reset_context(
    ctx: discord.ApplicationContext,
  ):
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()
    bot_entity.context = []
    await ctx.respond(
      "Who am I? Where am I? What is this place?",
      ephemeral=True,
      delete_after=5*60,
    )

  @bot.slash_command(name="change-persona", help="Change the persona of the bot.")
  @discord_option(
    name="persona",
    description="The persona to use for the bot.",
    autocomplete=discord.utils.basic_autocomplete(
      lambda ctx: list_available_personas(persona_dir)
    ),
  )
  async def _change_persona(ctx: discord.ApplicationContext, persona: str):
    # Block until all the backend is setup
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()
    logger.trace(f"Changing persona to {persona}")
    bot_entity.persona = load_persona_from_dir(persona, persona_dir)
    await ctx.respond(f"I have changed my persona to {persona} at {ctx.user.display_name}'s request.")
    await ctx.respond(
      f"The Persona is as follows:\n\n{bot_entity.persona}"[:2000],
      ephemeral=True,
      delete_after=60,
    )

  @bot.slash_command(name="prompt", help="Test a Persona with a model.")
  @discord_option(
    name="persona",
    description="The persona to use for the prompt.",
    autocomplete=discord.utils.basic_autocomplete(
      lambda ctx: list_available_personas(persona_dir)
    ),
  )
  @discord_option(
    name="model",
    description="The model to use for the prompt.",
    autocomplete=discord.utils.basic_autocomplete(
      lambda ctx: model_interface.models
    ),
    default="gpt3"
  )
  @discord_option(
    name="personality",
    description="The personality to use for the prompt.",
    autocomplete=discord.utils.basic_autocomplete(
      lambda ctx: list(p.value for p in assistant.PROMPT_PERSONALITY)
    ),
    default=assistant.PROMPT_PERSONALITY.BALANCED.value,
  )
  async def _prompt(
    ctx: discord.ApplicationContext,
    prompt: str,
    persona: str,
    model: str,
    personality: str,
  ):
    # Block until all the backend is setup
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()
    logger.trace(f"{ctx.author.name} has requested a prompt...")
    persona = load_persona_from_dir(persona, persona_dir)
    await ctx.defer(ephemeral=True, invisible=False)
    response = await prompt_model_for_response(
      prompt,
      persona,
      model,
      assistant.PROMPT_PERSONALITY(personality),
      model_interface,
    )
    await ctx.send_followup(
      content=response,
      ephemeral=True,
      delete_after=5*60,
    )

  @bot.slash_command(name="personas", help="List the available personas.")
  async def _personas(ctx: discord.ApplicationContext):
    # Block until all the backend is setup
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()

    logger.trace(f"Listing personas for {ctx.author.name}...")
    personas = list_available_personas(persona_dir)
    msg = "__Available personas:__\n{p}".format(
      p="\n".join(map(lambda p: f"\t{p}", personas))
    )
    await ctx.respond(msg)
  
  @bot.slash_command(name="print-persona", help="Print the contents of a persona.")
  @discord_option(
    name="persona",
    description="The persona to print.",
    autocomplete=discord.utils.basic_autocomplete(
      lambda ctx: list_available_personas(persona_dir)
    ),
  )
  async def _print_persona(ctx: discord.ApplicationContext, persona: str):
    # Block until all the backend is setup
    if not bot_ready.is_set():
      logger.annoying("Waiting for bot to be ready...")
      await bot_ready.wait()
    logger.trace(f"Printing persona {persona} for {ctx.author.name}...")
    persona_content = load_persona_from_dir(persona, persona_dir)
    msg = f"__Persona {persona}:__\n{persona_content}"
    await ctx.respond(msg)

  # Run the bot
  try:
    logger.info("Logging into Discord...")
    await bot.login(bot_token)
    logger.info("Starting Discord Bot...")
    await bot.connect(reconnect=True)
    logger.info("Discord Bot Started.")
  except asyncio.CancelledError:
    logger.warning("Discord Bot Cancelled. Exiting...")
  finally:
    logger.info("Stopping Discord Bot...")
    # Attempt to let users know we'll be right back
    bot.description = "I'll be right back!"
    await bot.change_presence(
      status=discord.Status.offline,
    )
    if not bot.is_closed(): 
      await bot.close()
    logger.info("Discord Bot Stopped.")
  return 0

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
    return await discord_bot(
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

