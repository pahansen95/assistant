
import json
import logging
import os
import sys
import tempfile
import shutil
from aiohttp import web
import asyncio
import signal
from dataclasses import dataclass, field

from ..ipc import TCPSocketManager
from . import WebAppManager

logger = logging.getLogger()
logger.handlers = [
  logging.StreamHandler(sys.stderr),
]
logger.setLevel(logging.DEBUG)

def render_config_js(config: str) -> str:
  return f"""
    const config_string = `{config}`;
    main_config = JSON.parse(config_string);
  """

def assemble_ui_files(data_dir: str, work_dir: str, config: str):
  assert os.path.exists(work_dir) and os.path.isdir(work_dir), "Work directory doesn't exist or isn't a directory."
  assert not os.listdir(work_dir), "Work directory must be empty."

  # Copy index.html & main.js from the data directory to the temporary directory
  shutil.copy(os.path.join(data_dir, 'index.html'), os.path.join(work_dir, 'index.html'))
  shutil.copy(os.path.join(data_dir, 'main.js'), os.path.join(work_dir, 'main.js'))

  # Create a config.js file in the temporary directory with the config
  with open(os.path.join(work_dir, 'config.js'), 'w') as config_file:
    config_file.write(render_config_js(config))

async def _main(
  work_dir: str,
  ui_conn: tuple[str, int],
  ipc_conn: tuple[str, int],
) -> None:
  ### Setup Signal Handlers ###
  quit = asyncio.Event()
  def _exit_signal_handler(loop: asyncio.AbstractEventLoop):
    logger.warning("Signal received, canceling tasks.")
    quit.set()
  loop = asyncio.get_running_loop()

  # Attach the signal handler to the loop
  for signal_kind in (
    signal.SIGINT,
    signal.SIGTERM
  ):
    logger.debug(f"Attaching signal handler for {signal_kind}.")
    loop.add_signal_handler(
      signal_kind,
      _exit_signal_handler,
      loop
    )

  ### Setup backend IPC ###
  ipc_manager = TCPSocketManager(
    conn=ipc_conn,
  )

  async with ipc_manager as backend_ipc:
    ### Setup FrontEnd WebApp ###
    webapp_manager = WebAppManager(
      conn=ui_conn,
      ipc=backend_ipc,
      work_dir=work_dir,
    )
    async with webapp_manager:
      logger.info(f"Serving Web UI on http://{ui_address}:{ui_port}/index.html")
      await quit.wait()

if __name__ == "__main__":
  _rc = 255
  try:
    config = json.loads(sys.argv[1])
    for key in {'data_dir', 'ui_address', 'ui_port', 'ipc_address', 'ipc_port'}:
      assert key in config, f"Config missing required key '{key}'."
    
    data_dir = config["data_dir"]
    # The Address & Port to serve the UI on
    ui_address = config["ui_address"]
    ui_port = config["ui_port"]
    # The Address & Port to connect to the backend on
    ipc_address = config["ipc_address"]
    ipc_port = config["ipc_port"]

    # Create temporary directory
    with tempfile.TemporaryDirectory() as work_dir:
      # Load config, setup backend_ipc ...
      assemble_ui_files(
        data_dir,
        work_dir,
        json.dumps({ # The config file for the WebClient
          "address": ui_address,
          "port": ui_port,
        })
      )
      asyncio.run(
          _main(
            work_dir=work_dir,
            ui_conn=(ui_address, ui_port),
            ipc_conn=(ipc_address, ipc_port),
          )
      )
  except:
    logger.exception("An unhandled exception occurred.")
  finally:
    logger.info(f"Exiting with return code: {_rc}")
    sys.stderr.flush()
    # Don't need to close the IPC, it's stdin/stdout
    exit(_rc)
