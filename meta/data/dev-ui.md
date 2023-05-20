Let's try implementing a Development UI in Python3 that adheres to these guidelines:
- Spawn a asyncio.subprocess.Process that runs the Chat UI
- IPC:
  - use the `write_to_ui` and `read_from_ui` methods as the communication interface from within the parent process but outside the `DevUI` Class. I will refer to this as the external communication interface.
  - user the `_read_from_ui` and `_write_to_ui` methods as the communication interface between the `DevUI` Class & the `asyncio.subprocess.Process`. I will refer to this as the internal communication interface.
  - use the `_read_queue` & `_write_queue` to buffer messages between the external & internal communication interfaces.
  - IPC messages should be JSON de/serialized before/after being sent/received
  - Use a seperate OS Pipe to communicate between the parent & child process. The UI (child process) will use it's stdin & stdout to communicate with the user.
- Lifecycle:
  - The parent process can use the start() and stop() methods to start and stop the UI
  - The parent process can schedule the io_loop() coroutine as a task to run in the background to manage I/O
  - When the parent process is terminated, the UI should be terminated as well
  - When the UI is unexpectadely terminated, an exception should be raised in the parent process

Keep all implementation contained within the `DevUI` Class. Here is your starting point

```python
import asyncio
from dataclasses import dataclass, field
from loguru import logger

@dataclass
class DevUI:
  _read_queue: asyncio.Queue = field(init=False, default_factory=asyncio.Queue)
  _write_queue: asyncio.Queue = field(init=False, default_factory=asyncio.Queue)
  _quit: asyncio.Event = field(init=False, default_factory=asyncio.Event)
  _ui_process: asyncio.subprocess.Process = field(init=False, default=None)
  _ui_read_pipe: Any = field(init=False, default=None)
  _ui_write_pipe: Any = field(init=False, default=None)
  
  async def write_to_ui(self, content: str):
    ... # TODO

  async def _write_to_ui(self):
    ... # TODO
  
  async def read_from_ui(self) -> str:
    ... # TODO

  async def _read_from_ui(self):
    ... # TODO
    
  async def start(self):
    """Start the UI in a child process & manages I/O"""
    logger.debug("DevUI starting")
    # TODO: Create the read & write pipes
    ui_args = [
      sys.interpreter,
      "ui.py"
      # TODO: Pass the read & write pipes as arguments
    ]
    self._ui_process = await asyncio.create_subprocess_exec(
      *ui_args,
      stderr=asyncio.subprocess.PIPE, # Capture the child's stderr
    )
    logger.info("DevUI started")
  
  async def stop(self):
    """Stop the UI & cleanup"""
    logger.debug("DevUI stopping")
    if self._ui_process:
      self._quit.set()
      self._ui_process.terminate()
      await self._ui_process.wait()
      # TODO: Cleanup the read & write pipes
      self._ui_process = None
    logger.info("DevUI stopped")
  
  async def io_loop(self):
    """Event loop for the DevUI that manages I/O between the parent & child processes"""
    logger.debug("DevUI I/O loop starting")
    while not self.quit.is_set():
      ... # TODO
    logger.debug("DevUI I/O loop stopping")
```