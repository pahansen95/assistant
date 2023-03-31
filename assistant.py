"""
An assistant PoC for ideation & workflow automation
"""
import sys
import os
from loguru import logger

def interactive():
  """An interactive chat session"""
  # Wait for user prompt

  # log prompt to file

  # Submit prompt to LLM for response

  # Stream response back, log response & display on screen

def main(
  *args: str,
  **kwargs: str,
) -> int:
  ...

def _parse_kwargs(*args: str, **kwargs: str) -> dict:
  _kwargs = {
    "help": False,
    "verbose": False,
    "quiet": False,
    "cache": os.environ.get('ASSISTANT_CHAT_LOGS', f"{os.getcwd}/assistant_chat_logs"),
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
Usage: {sys.argv[0]} [OPTIONS] [CMD]

About:
  Entrypoint to the assistant application.

Options:
  -h, --help
    Print this help message and exit.
  --verbose
    Enable verbose logging.
  --quiet
    Suppress all output to stderr.
  --log=DIRECTORY
    Where the chat log is stored
Commands:
  chat
    Start an interactive session with the assistant
  """)

if __name__ == "__main__":
  _rc = 255
  try:
    logger.remove()
    _args = _parse_args(*sys.argv[1:])
    _kwargs = _parse_kwargs(*sys.argv[1:])
    if _kwargs["quiet"]:
      sys.stderr = open(os.devnull, "w")
    if _kwargs["verbose"]:
      logger.add(sys.stderr, level="TRACE")
    else:
      logger.add(sys.stderr, level="INFO")
    if _kwargs["help"]:
      _help()
      _rc = 0
    else:
      _rc = main(*_args, **_kwargs)
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled Exception raised during runtime...")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)
