import aiohttp
import asyncio
import json
from loguru import logger
import time
import uuid
from typing import AsyncGenerator
import sys
import ssl
import datetime
from urllib.parse import quote as url_quote

config = {
  'matrix': {
    'server': 'https://assistant-dev.peter.vpn.assistant-dev.peterhansen.io/',
    'server_name': 'assistant-dev',
    'user': 'test',
    'password': 'test',
    'room': '#development:assistant-dev',
  }
}

client_session: aiohttp.ClientSession = None

def deserialize_content(content_type: str, content: bytes) -> str | dict:
  _type = content_type.split(';')
  _props = {
    k: v for k, v in [
      prop.split('=') for prop in _type[1:]
    ]
  }
  _type = _type[0]
  logger.trace(f'Content Type: {_type}')
  logger.trace(f'Content Properties: {_props}')

  output = None
  if _type == 'text/plain':
    output = content.decode(_props.get('charset', 'utf-8'))
  elif _type == 'application/json':
    output = json.loads(content.decode(_props.get('charset', 'utf-8')))
  else:
    raise NotImplementedError(f'Unknown Content Type: {_type}')
  assert output is not None
  logger.trace(f'Deserialized Content Type: {_type}')
  logger.trace(f'Deserialized Content: {str(output)[:512]}...')
  return output

def generate_txid() -> str:
  """Generate a transaction ID"""
  return uuid.uuid4().hex

token_expires_at_ns: int | None = None
"""The Monotonic Time that the token expires at"""
def token_expired() -> bool:
  """Has the token expired?"""
  return time.monotonic_ns() >= token_expires_at_ns

def update_token_expiration(expires_in_ms: int) -> None:
  """Update the token expiration time"""
  global token_expires_at_ns
  token_expires_at_ns = time.monotonic_ns() + int(expires_in_ms * 1e6)

async def refresh_access_token():
  logger.trace('Refreshing access token')
  
  if token_expires_at_ns is not None and not token_expired():
    logger.trace('Token is still valid')
    return

  if token_expires_at_ns is not None and token_expired():
    logger.trace('Token has expired, refreshing...')
    assert client_session.headers['access_token'] is not None
    async with client_session.post(
      '/_matrix/client/r0/refresh',
      data=json.dumps({
        'refresh_token': client_session.headers['access_token'],
      }),
    ) as response:
      data = deserialize_content(
        response.headers['Content-Type'],
        await response.read(),
      )
      client_session.headers.update({
        "Authorization": f"Bearer {data['access_token']}",
      })
  elif token_expires_at_ns is None:
    logger.trace('Token is not set, getting new token...')
    async with client_session.post(
      '/_matrix/client/r0/login',
      data=json.dumps({
        'type': 'm.login.password',
        'user': config['matrix']['user'],
        'password': config['matrix']['password'],
      }),
    ) as response:
      data = deserialize_content(
        response.headers['Content-Type'],
        await response.read(),
      )
      client_session.headers.update({
        "Authorization": f"Bearer {data['access_token']}",
      })
  else:
    raise RuntimeError('Unknown token state')
  
  update_token_expiration(data.get('expires_in_ms', 5*60*1000)) # Default to 5 minutes
  
async def get_room_id() -> str:
  async with client_session.get(
    f"/_matrix/client/v3/directory/room/{url_quote(config['matrix']['room'])}"
  ) as response:
    response.raise_for_status()
    data = deserialize_content(
      response.headers['Content-Type'],
      await response.read(),
    )
    assert config['matrix']['server_name'] in data['servers']
    return data['room_id']

async def listen_for_messages(
  room_id: str,
) -> AsyncGenerator[dict, None]:
  """Listen for messages in a room"""
  _filter_def = {
    'room': {
      'rooms': [room_id],
      'timeline': {
        'limit': 10,
        'types': ['m.room.message'],
      },
    },
  }
  # TODO: Create Server Side Filter
  
  sync_batches: list[str] = []
  while True:
    async with client_session.get(
      f"/_matrix/client/r0/sync",
      headers={
        'Content-Type': 'application/json',
      },
      params={
        k: v for k, v in {
          'since': sync_batches[-1] if len(sync_batches) > 0 else None,
          'timeout': int(5 * 1000),
          'filter': json.dumps(_filter_def), # TODO: Replace with Server Side Filter ID
        }.items() if v is not None
      },
    ) as response:
      if not (response.status >= 200 and response.status < 300):
        try:
          response.raise_for_status()
        except Exception as e:
          logger.opt(exception=e).error('Sync Error')
        await asyncio.sleep(1)
        continue
      room_data = deserialize_content(
        response.headers['Content-Type'],
        await response.read(),
      )['rooms']['join'][room_id]
      room_timeline = room_data['timeline']
      if room_timeline['limited']:
        logger.debug(f'limited payload...\n{json.dumps(room_data, indent=2)}')
        logger.info(f"FYI; This isn't the full message history, just the last {_filter_def['room']['timeline']['limit']} messages")
      if 'prev_batch' in room_timeline:
        if room_timeline['prev_batch'] not in sync_batches:
          assert len(sync_batches) == 0
          sync_batches.append(room_timeline['prev_batch'])
      
      for event in room_timeline['events']:
        if event['type'] == 'm.room.message':
          assert {'body', 'msgtype'} <= event['content'].keys(), 'Malformed Message'
          yield event

      sync_batches.append(sync_batches['next_batch'])
  
async def send_new_message(
  content: str,
  room_id: str,
) -> str:
  txid = generate_txid()
  async with client_session.put(
    f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txid}",
    data=json.dumps({
      'msgtype': 'm.text',
      'body': content,
    }),
  ) as response:
    response.raise_for_status()
    data = deserialize_content(
      response.headers['Content-Type'],
      await response.read(),
    )
    assert "event_id" in data
    return data['event_id']

async def main() -> int:
  result = 1
  # Disable SSL Verification
  ssl_context = ssl.create_default_context()
  # ssl_context.check_hostname = False
  # ssl_context.verify_mode = ssl.CERT_NONE

  global client_session
  async with aiohttp.ClientSession(
    base_url=config['matrix']['server'],
    headers={
      'Content-Type': 'application/json',
    },
    connector=aiohttp.TCPConnector(ssl=ssl_context),
  ) as _client_session:
    client_session = _client_session

    await refresh_access_token()

    # Verify that the token is valid
    async with client_session.get('/_matrix/client/v3/account/whoami') as response:
      response.raise_for_status()
      data = deserialize_content(
        response.headers['Content-Type'],
        await response.read(),
      )
      logger.info(data)
    
    # Get the Room ID
    room_id = await get_room_id()
    logger.info(f"Room ID for {config['matrix']['room']} is {room_id}")

    # Send a message
    logger.info('Sending message...')
    msg_content = f'Hello World! @ {datetime.datetime.now().ctime()}'
    event_id = await send_new_message(msg_content, room_id)
    logger.success('Message sent')

    # Listen for messages
    logger.info('Listening for messages...')
    found_message = False
    async for event in listen_for_messages(room_id):
      logger.trace(event)
      # Datatype: ClientEventWithoutRoomID
      assert {'content', 'event_id', 'origin_server_ts', 'sender', 'type'} <= event.keys(), 'Not a ClientEventWithoutRoomID Object'
      assert event['type'] == 'm.room.message', 'Not a message!'
      if event['event_id'] == event_id:
        assert event['content']['msgtype'] == 'm.text', 'Not a text message!'
        assert event['content']['body'] == msg_content, 'Message body does not match!'
        found_message = True
        break

    assert found_message, 'Did not find message'
    logger.success('Found message')
    result = 0

  return result


if __name__ == '__main__':
  logger.remove()
  logger.add(sys.stderr, level='TRACE')
  _rc = 255
  try:
    _rc = asyncio.run(main())
  except KeyboardInterrupt:
    _rc = 0
  except Exception as e:
      logger.opt(exception=e).error('Unhandled exception')
  if _rc == 0:
    logger.success('Wow it works!')
  else:
    logger.critical('Task Failed Successfully')
  exit(_rc)