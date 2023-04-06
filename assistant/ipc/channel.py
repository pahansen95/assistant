from dataclasses import dataclass
from typing import Tuple
import asyncio
import zmq
from .utils import IdGenerator, L7Error, handle_error

@dataclass
class Peer:
    channel_id: int
    peer_id: int

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        id_generator = IdGenerator(channel_id)
        self.peer_id = id_generator.generate_peer_id()

    async def receive_message(self, socket: zmq.Socket) -> Tuple[str, bytes]:
        """Receives a message from the given ZeroMQ socket."""
        message_type = await socket.recv_string()
        message_body = await socket.recv()
        return message_type, message_body

    async def send_message(self, socket: zmq.Socket, message_type: str, message_body: bytes, destination: int):
        """Sends a message to the given ZeroMQ socket."""
        socket.send_string(str(destination), flags=zmq.SNDMORE)
        socket.send_string(message_type, flags=zmq.SNDMORE)
        socket.send(message_body)

    async def handle_inbound_traffic(self, socket: zmq.Socket):
        """Handles inbound network traffic."""
        while True:
            try:
                sender_id, message_type, message_body = await self.receive_message(socket)
                # TODO: Handle the message
            except Exception as e:
                handle_error(L7Error.NETWORK_CONNECTIVITY_ERROR, str(e))

    async def handle_outbound_traffic(self, socket: zmq.Socket):
        """Handles outbound network traffic."""
        while True:
            try:
                message_type, message_body = ..., ...# TODO: Get the message to send
                destination = None  # TODO: Determine the destination
                await self.send_message(socket, message_type, message_body, destination)
            except Exception as e:
                handle_error(L7Error.NETWORK_CONNECTIVITY_ERROR, str(e))
