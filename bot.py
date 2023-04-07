"""
A Bot for chat frontends like Discord, Telegram, Slack, etc.

This bot makes developement of the rest of the project faster.
"""

import asyncio
import logging
import os
import pathlib
import sys
import uuid
from dataclasses import dataclass, field
from typing import TypeVar

import discord
from discord.commands import option as discord_option
from discord.ext import commands
from loguru import logger

import assistant
import assistant.entity as entity
import assistant.openai as openai

T = TypeVar("T")

_user_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.USER)
_system_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.SYSTEM)
_assistant_msg = lambda p: assistant.PromptMessage(p, assistant.PROMPT_MESSAGE_ROLE.ASSISTANT)

### Add logging to the assistant module & PyCord
class LoguruLogger(assistant._LoggingInterface):
  """Log using Loguru"""
  async def __call__(self, msg: str, level: str):
    # Ordered by what I think is most common to least common
    if level == "trace":
      logger.trace(msg)
    elif level == "debug":
      logger.debug(msg)
    elif level == "info":
      logger.level(msg)
    elif level == "error":
      logger.error(msg)
    elif level == "warning":
      logger.warning(msg)
    elif level == "success":
      logger.success(msg)
    elif level in ["fatal", "critical"]:
      logger.critical(msg)
    else:
      RuntimeError(f"Unknown log level {level}.")
assistant.set_logger(LoguruLogger())
class InterceptHandler(logging.Handler):
  def emit(self, record):
    logger_opt = logger.opt(depth=6, exception=record.exc_info)
    logger_opt.log(record.levelno, record.getMessage())
# logging.basicConfig(handlers=[InterceptHandler()], level=0)
###

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
  bot_token = os.environ["DISCORD_BOT_TOKEN"]
  
  bot_entity = entity.Entity(
    uuid=uuid.uuid4(),
    name="Jack",
    _send=model_interface,
    persona=load_persona_from_dir("jack-of-all-trades", persona_dir),
  )
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

  # @bot.event
  # async def on_connect():
  #   logger.success("Connected to Discord.")
  
  # @bot.event
  # async def on_disconnect():
  #   logger.warning("Disconnected from Discord.")
  
  # @bot.event
  # async def on_resumed():
  #   logger.success("Resumed connection to Discord.")
  
  @bot.event
  async def on_ready():
    logger.success(f"Logged in as {bot.user.name} ({bot.user.id})")

  @bot.event
  async def on_message(message: discord.Message):
    if message.author == bot.user:
      return
    
    if message.mentions and bot.user in message.mentions:
      logger.trace(f"Message mentions bot: {message.content}")
      async with message.channel.typing():
        try:
          logger.trace("Responding to message...")
          response = await bot_entity.respond(
            chat=[message.content],
            context=current_context,
            model=current_model,
            responding_personality=assistant.PROMPT_PERSONALITY.BALANCED,
            reflection_personality=assistant.PROMPT_PERSONALITY.RESERVED,
          )
        except Exception as e:
          logger.opt(exception=e).error("Error while responding to message.")
          response = "I'm sorry, I'm having trouble responding to you right now."
      
      logger.trace(f"Sending response: {response}")
      await message.channel.send(
        content=response,
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
    logger.trace(f"Changing persona to {persona}")
    bot_entity.persona = load_persona_from_dir(persona, persona_dir)
    await ctx.respond(f"I have changed my persona to {persona} at {ctx.user.display_name}'s request.")

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
    logger.info("Waiting for instruction to quit...")
  except asyncio.CancelledError:
    logger.warning("Discord Bot Cancelled. Exiting...")
  finally:
    logger.info("Stopping Discord Bot...")
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
      _rc = asyncio.run(main(*_args, **_kwargs))
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled Exception raised during runtime...")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)

