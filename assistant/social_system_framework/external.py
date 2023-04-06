import asyncio
import json
from dataclasses import dataclass, field
from os import urandom

import zmq
import zmq.asyncio as aiozmq
from uri import URI

from . import (CHANNEL_ROLE, CHANNEL_STATE, BadPeerError,
               _Channel,
               OutOfOrderError, UnknownSessionError, UnsupportedRoleError,
               WrongStateError, _id, _Message, _MessageKind, _topic)


@dataclass
class ExternalEndpoint(_Channel):
  ...
