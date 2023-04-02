import asyncio
import enum
import contextlib
from abc import ABC, abstractmethod

class Error(Exception):
  pass

class _LoggingInterface(ABC):
  """A placeholder for the logging function"""
  async def fatal(self, msg: str):
    await self(msg=msg, level="fatal")
  async def critical(self, msg: str):
    await self(msg=msg, level="critical")
  async def error(self, msg: str):
    await self(msg=msg, level="error")
  async def success(self, msg: str):
    await self(msg=msg, level="success")
  async def warning(self, msg: str):
    await self(msg=msg, level="warning")
  async def info(self, msg: str):
    await self(msg=msg, level="info")
  async def debug(self, msg: str):
    await self(msg=msg, level="debug")
  async def trace(self, msg: str):
    await self(msg=msg, level="trace")
  @abstractmethod
  async def __call__(self, msg: str, level: str):
    ...

class _DummyLogger(_LoggingInterface):
  """A dummy logger that does nothing"""
  async def __call__(self, msg: str, level: str):
    pass

_logger = _DummyLogger()

class ENTITY(enum.Enum):
  USER = "user"
  ASSISTANT = "assistant"
