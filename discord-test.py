from loguru import logger
import discord
from discord.ext import commands
import asyncio
import sys
import os

logger.remove()
logger.add(sys.stderr, level="TRACE")

intents = discord.Intents.default()
### Must enable these as a pair otherwise we crash
intents.members = True
intents.presences = True
###
intents.message_content = True

bot = discord.Bot(
  intents=intents,
  debug_guilds=[
    1093645046986850346,
  ],
)

@bot.event
async def on_ready():
  logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.slash_command(name="prompt", help="Prompt the bot for a response.")
async def prompt(ctx: discord.ApplicationContext, prompt: str):
  logger.trace(f"Prompting {ctx.author.name}...")
  await ctx.respond(prompt)

async def run_bot():
  logger.trace("Get Bot Token from Environment...")
  bot_token = os.environ["DISCORD_BOT_TOKEN"]
  try:
    logger.info("Logging into Discord...")
    await bot.login(bot_token)
    logger.info("Starting Discord Bot...")
    await bot.connect(reconnect=True)
  except asyncio.CancelledError:
    logger.warning("Bot Cancelld. Exiting...")
  finally:
    logger.info("Stopping Discord Bot...")
    if not bot.is_closed(): 
      logger.info("Closing Discord Bot...")
      await bot.close()
    logger.info("Discord Bot Stopped.")

try:
  asyncio.run(
    run_bot(),
    debug=True,
  )
except KeyboardInterrupt:
  logger.warning("Keyboard Interrupt detected. Exiting...")
