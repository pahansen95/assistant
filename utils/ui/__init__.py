"""# UI

Provides a minimal UI for bootstrapping development.

"""
from dataclasses import dataclass, field
import asyncio
import sys
import json
import os
import pathlib
import random

from .. import _logger as _module_logger

from aiohttp import web
from ..ipc import IPCInterface

_logger = _module_logger.getChild("ui")
_default_ui_config = {
  'data_dir': str(pathlib.Path(os.getcwd()).resolve() / 'dev-ui'),
  'ui_address': 'localhost',
  'ui_port': 8080,
  'ipc_address': 'localhost',
  'ipc_port': random.randint(49152, 65535),
}
@dataclass
class DevUIManager:
  """Manages the DevUI process."""
  config: dict = field(default_factory=_default_ui_config)
  _ui_watchdog_task: asyncio.Task = field(init=False, default=None)

  async def __aenter__(self):
    await self.start()
  
  async def __aexit__(self, exc_type, exc_value, traceback):
    await self.stop()

  async def start(self):
    for key in {'data_dir', 'ui_address', 'ui_port', 'ipc_address', 'ipc_port'}:
      assert key in self.config, f"DevUIManager config missing required key '{key}'."

    _logger.debug("DevUI starting")
    ui_args = [
      sys.executable,
      "-m", "utils.ui",
      json.dumps(self.config),
    ]
    # Hook the UI Process stderr to the main process stderr
    self._ui_process = await asyncio.create_subprocess_exec(
      *ui_args,
      stdin=asyncio.subprocess.DEVNULL,
      stdout=asyncio.subprocess.DEVNULL,
      stderr=sys.stderr.fileno(),
      close_fds=False,
    )
    _logger.info(f"DevUI serving {self.config['data_dir']} on {self.config['ui_address']}:{self.config['ui_port']} w/ PID {self._ui_process.pid}")
    
    _logger.debug("Starting DevUI watchdog")
    self._ui_watchdog_task = asyncio.create_task(self._watchdog())

  async def stop(self):
    _logger.debug("DevUI stopping")

    _logger.debug("Cancelling DevUI watchdog")
    self._ui_watchdog_task.cancel()

    _logger.debug("Stopping UI process")
    if self._ui_process.returncode is None:
      assert isinstance(self._ui_process, asyncio.subprocess.Process), f"Expected self._ui_process to be a subprocess.Process, got {self._ui_process.__class__.__name__}"
      # Schedule a Timeout
      # self._ui_process.terminate()
      self._ui_process.kill() # TODO: Use terminate() instead of kill()
      wait_task = asyncio.create_task(self._ui_process.wait())
      done, _ = await asyncio.wait(
        [wait_task],
        timeout=5,
      )
      if wait_task not in done:
        _logger.warning("UI process failed to terminate, killing...")
        wait_task.cancel()
        self._ui_process.kill()

    self._ui_process = None
    
    _logger.info("DevUI stopped")

  async def _watchdog(self):
    _logger.debug("DevUI watchdog starting")
    try:
      rc = await self._ui_process.wait()
      if rc != 0:
        _logger.error(f"UI process exited with code {rc}")
    except asyncio.CancelledError:
      _logger.debug("DevUI watchdog cancelled")
    _logger.debug("DevUI watchdog stopping")


@dataclass
class WebAppManager:
  conn: tuple[str, int]
  ipc: IPCInterface
  work_dir: str
  _context: dict = field(init=False, default_factory=dict)

  async def __aenter__(self):
    await self.setup()
  
  async def __aexit__(self, exc_type, exc_value, traceback):
    await self.teardown()

  async def _read_message(self, request: web.Request):
    _app = self._context.get('app', None)
    assert _app is not None and isinstance(_app, web.Application), "WebApp not setup."
    try:
      message = await self.ipc.read()
      if message is None:
        return web.Response(text="No message available.", status=204)
      return web.json_response(message)
    except Exception as e:
      _logger.exception("Error reading IPC message.")
      return web.Response(text=str(e), status=500)

  async def _write_message(self, request: web.Request):
    try:
      content = await request.json()
      await self.ipc.write(content)
      return web.Response(text="Message sent.", status=200)
    except Exception as e:
      _logger.exception("Error writing IPC message.")
      return web.Response(text=str(e), status=500)
  
  async def setup(self):
    ### Setup FrontEnd WebApp ###
    assert self._context.get('app', None) is None, "WebApp already setup."
    self._context['app'] = web.Application()
    # IPC Middleware routes
    self._context['app'].router.add_get('/api/ipc/read', self._read_message)
    self._context['app'].router.add_post('/api/ipc/write', self._write_message)

    # Static file handling
    self._context['app'].router.add_static('/', path=self.work_dir, name='ui-files')
    ... # TODO: Redirect '/' to '/index.html'

    self._context['runner'] = web.AppRunner(self._context['app'])
    await self._context['runner'].setup()
    self._context['site'] = web.TCPSite(self._context['runner'], *self.conn)
    await self._context['site'].start()
  
  async def teardown(self):
    ### Teardown FrontEnd WebApp ###
    _app = self._context.get('app', None)
    _runner = self._context.get('runner', None)
    _site = self._context.get('site', None)
    assert _app is not None and isinstance(_app, web.Application), "WebApp not setup."
    assert _runner is not None and isinstance(_runner, web.AppRunner), "WebApp not setup."
    assert _site is not None and isinstance(_site, web.TCPSite), "WebApp not setup."
    
    # TODO: This is broken, need to figure out how to stop the site
    await _site.stop()
    await _runner.cleanup()

    for key in {'app', 'runner', 'site'}:
      del self._context[key]
