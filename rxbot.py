
import asyncio
import os
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field

from loguru import logger

from assistant import PROMPT_PERSONALITY, PromptInterface, openai, PromptMessage, PROMPT_MESSAGE_ROLE
from utils.ipc import IPCInterface, TCPSocketManager
from conversation.transcript import ChatTranscript

  
async def message_producer_pipeline(
  ipc: IPCInterface,
  external_context: dict,
  internal_context: dict,
  message_context: dict,
  prompt_queue: asyncio.Queue,
  error: asyncio.Event,
):
  """
  # Produces a Message (Within the context of the pipeline)
    - Read a Platform Message
    - Deserialize the Platform Message into an Application Message
    - Update the Internal State of the Conversation
    - Publish the Application Message to the Prompt Queue
  """
  chat_transcript: ChatTranscript[str] = external_context['transcript']
  assert isinstance(chat_transcript, ChatTranscript)

  logger.debug("Message Producer Pipeline starting")

  try:
    logger.debug("Setup stdin reader")
    logger.debug("Begin Message Producer Pipeline Loop")
    while True:
      ### Read a Platform Message ###
      # For now just read a single line from stdin & simulate a platform message
      logger.debug("Reading message from platform")
      platform_message = await ipc.read()
      logger.debug("Read message from platform:")
      platform_message.update({
        'ts': time.time(),
        'id': uuid.uuid4().hex,
      })

      # This hash is the fingerprint for this message's unique context within the converstation
      message_hash = hash((
        platform_message['user'],
        platform_message['ts'],
        platform_message['id'],
      ))

      ### Deserialize the Platform Message into an Application Message ###

      # Desrialize the platform message into an application message
      application_message = {
        'speaker': platform_message['user'],
        'ts_ns': int(platform_message['ts'] * 1e9),
        'data': platform_message['content'],
      }

      message_context[message_hash] = {
        'platform': 'dev-ui',
        'platform_message': platform_message,
        'application_message': application_message,
      }

      ### Update the External State of the Conversation ###
      chat_transcript.add(
        author=application_message['speaker'],
        timestamp=application_message['ts_ns'],
        message=application_message['data'],
      )

      ### Update the Internal State of the Conversation ###

      # TODO: ...?

      ### Publish the Application Message to the Prompt Queue ###
      logger.debug("Publishing message to prompt queue")
      await prompt_queue.put(
        message_hash
      )
  except asyncio.CancelledError:
    logger.debug("Message Producer Pipeline cancelled")
    # TODO: Cleanup
  except:
    logger.opt(exception=True).error("Message Producer Pipeline failed")
    error.set()
    raise
  
  logger.debug("Message Producer Pipeline finished")

async def llm_pipeline(
  model_providers: dict[str, PromptInterface],
  external_context: dict,
  internal_context: dict,
  message_context: dict,
  prompt_queue: asyncio.Queue,
  response_queue: asyncio.Queue,
  error: asyncio.Event,
):
  """
  # LLM
    - Get a Application Message from the Prompt Queue
    - Preprocess the Application Message
    - Generate a Response to the Application Message
    - Postprocess the Response
    - Publish the Response to the Response Queue
  """
  chat_transcript: ChatTranscript[str] = external_context['transcript']
  assert isinstance(chat_transcript, ChatTranscript)

  logger.debug("LLM Pipeline starting")

  logger.debug("Setting up LLM")
  _available_models = {
    _model_provider: _prompt_interface.models
    for _model_provider, _prompt_interface in model_providers.items()
  }
  logger.info(f"Available Models: {_available_models}")

  try:
    logger.debug("Begin LLM Pipeline Loop")
    while True:
      ### Get a Application Message from the Prompt Queue ###
      logger.debug("Waiting for message from prompt queue")
      message_hash = await prompt_queue.get()

      ### Preprocess the Application Message ###

      # TODO: ...?
      _pre_processed_application_message = message_context[message_hash]['application_message']

      ### Generate a Response to the Application Message ###

      async def _llm(messages: list[tuple[str, str]], model_provider: str, model_id: str, personality: PROMPT_PERSONALITY):
        logger.debug("Sending Response to LLM")
        _datum = time.monotonic_ns()
        _raw_response = await (model_providers[model_provider])(
          messages=[
            PromptMessage(
              content=msg[1],
              role=PROMPT_MESSAGE_ROLE.ASSISTANT if msg[0] == 'assistant' else PROMPT_MESSAGE_ROLE.USER,
            )
            for msg in messages
          ],
          model=model_id,
          personality=personality,
        )
        # _raw_response = "This is a test response"
        _duration = time.monotonic_ns() - _datum
        logger.debug("LLM Response Received")
        return {
          'ts_ns': time.monotonic_ns(),
          'duration': _duration,
          'data': _raw_response,
          'llm': f"{model_provider}/{model_id}", # Unique identifier for the LLM for lookup later if needed
        }
      
      message_history = chat_transcript.conversation()
      # Truncate the message history so there is at least 1024 tokens available for the response
      message_tokens = [
        model_providers['openai'].token_count('gpt3', msg[1])
        for msg in message_history
      ]
      assert hasattr(model_providers['openai'], 'model_lookup')
      if _token_count := sum(message_tokens) > model_providers['openai'].model_lookup['gpt3']['max_tokens'] - 1024:
        # find the message to truncate starting from the oldest messages (i.e. the first messages in the list)
        _truncate_index = 0
        _truncated_token_count = _token_count
        while _truncated_token_count > model_providers['openai'].model_lookup['gpt3']['max_tokens'] - 1024:
          _truncate_index += 1
          _truncated_token_count = _token_count - sum(message_tokens[:_truncate_index])
        assert _truncate_index != 0
        # TODO Truncate the overflow message to the token limit
        message_history = message_history[_truncate_index:]

      logger.debug("Running LLM")
      _response = await _llm(
        messages=message_history,
        model_provider="openai",
        model_id="gpt3",
        personality=PROMPT_PERSONALITY.BALANCED,
      )
      logger.debug("LLM finished")
      
      ### Postprocess the Response ###

      # TODO: ...?
      _post_processed_response = _response

      ### Publish the Response to the Response Queue ###
      
      assert message_hash in message_context
      assert isinstance(message_context[message_hash], dict)
      message_context[message_hash].update({
        'pre_process': _pre_processed_application_message,
        'raw_response': _response,
        'post_process': _post_processed_response,
      })

      logger.debug("Publishing message to response queue")
      await response_queue.put(
        message_hash
      )
  except asyncio.CancelledError:
    logger.debug("LLM Pipeline cancelled")
  except:
    logger.opt(exception=True).error("LLM Pipeline failed")
    error.set()
    raise
  
  logger.debug("LLM Pipeline finished")

async def message_consumer_pipeline(
  ipc: IPCInterface,
  external_context: dict,
  internal_context: dict,
  message_context: dict,
  response_queue: asyncio.Queue,
  error: asyncio.Event,
):
  """
  # Consume a Message
    - Get a Response from the Response Queue
    - Update the Internal State of the Conversation
    - Serialize the Response into a Platform Message
    - Publish the Platform Message to the Platform
  """

  chat_transcript: ChatTranscript[dict] = external_context['transcript']
  assert isinstance(chat_transcript, ChatTranscript)

  logger.debug("Message Consumer Pipeline starting")

  try:
    logger.debug("Setup stdout writer")

    logger.debug("Begin Message Consumer Pipeline Loop")
    while True:
      ### Get a Response from the Response Queue ###
      logger.debug("Waiting for message from response queue")
      message_hash = await response_queue.get()

      ### Update the Internal State of the Conversation ###

      # TODO: ...?

      ### Update the External State of the Conversation ###

      chat_transcript.add(
        author="assistant",
        timestamp=message_context[message_hash]['post_process']['ts_ns'],
        message=message_context[message_hash]['post_process']['data'],
      )

      ### Serialize the Response into a Platform Message ###

      # Serialize the response into a platform message; I'm just making this up for now
      platform_message = {
        'user': "assistant",
        'content': message_context[message_hash]['post_process']['data'],
      }

      ### Publish the Platform Message to the Platform ###
      # await asyncio.get_event_loop().run_in_executor(
      #   None,
      #   print,
      #   platform_message['content'],
      # )
      logger.debug("Writing message to platform")
      await ipc.write(platform_message)
      logger.debug("Message written to platform")
  except asyncio.CancelledError:
    logger.debug("Message Consumer Pipeline cancelled")
  except:
    logger.opt(exception=True).error("Message Consumer Pipeline failed")
    error.set()
    raise
  
  logger.debug("Message Consumer Pipeline finished")

async def conversation_pipeline(
  ipc: IPCInterface,
  model_providers: dict[str, PromptInterface],
  external_context: dict,
  internal_context: dict,
  message_context: dict,
  prompt_queue: asyncio.Queue,
  response_queue: asyncio.Queue,
):
  """
  # Produce a Message
    - Read a Platform Message
    - Deserialize the Platform Message into an Application Message
    - Update the Internal State of the Conversation
    - Publish the Application Message to the Prompt Queue
  
  # LLM
    - Get a Application Message from the Prompt Queue
    - Preprocess the Application Message
    - Generate a Response to the Application Message
    - Postprocess the Response
    - Publish the Response to the Response Queue
  
  # Consume a Message
    - Get a Response from the Response Queue
    - Update the Internal State of the Conversation
    - Serialize the Response into a Platform Message
    - Publish the Platform Message to the Platform
  """
  logger.debug("Starting the conversation pipeline")
  producer_error, llm_error, consumer_error = asyncio.Event(), asyncio.Event(), asyncio.Event()
  producer_task = llm_task = consumer_task = None
  try:
    # Schedule the individual pipelines to run concurrently
    logger.debug("Schedule the Message Producer Pipeline")
    producer_task = asyncio.create_task(
      message_producer_pipeline(
        ipc,
        external_context,
        internal_context,
        message_context,
        prompt_queue,
        producer_error,
      )
    )

    logger.debug("Schedule the LLM Pipeline")
    llm_task = asyncio.create_task(
      llm_pipeline(
        model_providers,
        external_context,
        internal_context,
        message_context,
        prompt_queue,
        response_queue,
        llm_error,
      )
    )

    logger.debug("Schedule the Message Consumer Pipeline")
    consumer_task = asyncio.create_task(
      message_consumer_pipeline(
        ipc,
        external_context,
        internal_context,
        message_context,
        response_queue,
        consumer_error,
      )
    )
    
    # For now, just wait for the quit event
    logger.debug("For now, just wait for the quit event")
    await asyncio.wait(
      [
        asyncio.create_task(e.wait())
        for e in (
          producer_error,
          llm_error,
          consumer_error,
        )
      ],
      return_when=asyncio.FIRST_COMPLETED,
    )
    logger.warning("Unexpected error occurred")
    raise Exception("Unexpected error occurred")
  except asyncio.CancelledError:
    logger.debug("Conversation Pipeline cancelled")
  except:
    logger.opt(exception=True).error("Conversation Pipeline failed")
    raise
  finally:
    logger.debug("Conversation Pipeline instructed to quit, Cancelling the sub pipelines")
    # Tear down the pipeline
    scheduled_tasks = [t for t in (producer_task, llm_task, consumer_task) if t is not None]
    logger.debug("Canceling the sub pipelines")
    cancelled_results: list[Exception | None] = await asyncio.gather(
      *[
        t for t in scheduled_tasks
        if t.cancel()
      ],
      return_exceptions=True
    )
    for error in filter(lambda r: isinstance(r, Exception), cancelled_results):
      logger.opt(exception=error).error("Error occurred while cancelling a task")
    logger.debug("All Sub pipeline tasks have completed")
  
  logger.debug("Conversation Pipeline Task completed")

async def _main(*args, **kwargs) -> int:
  rc = 0
  loop = asyncio.get_running_loop()
  _task = asyncio.current_task()
  assert isinstance(_task, asyncio.Task)

  external_context = {
    "transcript": ChatTranscript(),
  }
  internal_context = {}
  message_context = {}
  prompt_queue = asyncio.Queue()#maxsize=1)
  response_queue = asyncio.Queue()#maxsize=1)
  quit = asyncio.Event()
  quit.clear()

  model_providers: dict[str, PromptInterface] = {
    'openai': openai.OpenAIChatCompletion(
      token=kwargs['openai_token'],
    )
  }

  ipc_manager = None
  dev_ui = None
  if kwargs.get('dev', False):
    from utils.ui import DevUIManager, _default_ui_config
    ui_config = {k: v for k, v in _default_ui_config.items()}
    dev_ui = DevUIManager(
      config=ui_config,
    )
    ipc_manager = TCPSocketManager(
      conn=(
        ui_config['ipc_address'],
        ui_config['ipc_port'],
      )
    )
  
  async def _pipeline_task():
    logger.trace("Starting pipeline task.")
    assert ipc_manager is not None, "IPC Manager wasn't set."
    async with ipc_manager as pipeline_ipc:
      assert isinstance(pipeline_ipc, IPCInterface), "IPC Manager didn't return an IPC Interface."
      logger.trace("IPC Manager returned an IPC Interface.")
      logger.info("Starting pipeline.")
      await conversation_pipeline(
        pipeline_ipc,
        model_providers,
        external_context,
        internal_context,
        message_context,
        prompt_queue,
        response_queue,
      )
      logger.info("Pipeline Finished")
      # async def _test_ipc():
      #   """Read Messages from the IPC & Write Messages to the IPC in response.
      #   """
      #   logger.trace("Starting IPC test.")
      #   try:
      #     while True:
      #       logger.trace("Waiting for message...")
      #       msg = await pipeline_ipc.read()
      #       logger.trace(f"Received message: {msg}")
      #       logger.trace("Sending response...")
      #       await pipeline_ipc.write({
      #         "user": "assistant",
      #         "content": f"Test response to...\n{msg['content']} from {msg['user']}",
      #       })
      #       logger.trace("Response sent.")
      #   except asyncio.CancelledError:
      #     logger.trace("IPC test cancelled.")
      
      # logger.info("Starting IPC test.")
      # await _test_ipc()
      # logger.info("IPC test finished.")
  
  logger.debug("Scheduling pipeline task.")
  pipeline_task = asyncio.create_task(
    _pipeline_task()
  )
  logger.debug("Pipeline task scheduled.")

  ### Setup Signal Handlers ###

  def _exit_signal_handler(loop: asyncio.AbstractEventLoop):
    logger.warning("Signal received, canceling tasks.")
    if quit.is_set():
      logger.warning("Signal received again; Cancelling Tasks.")
      _task.cancel()
    quit.set()

  # Attach the signal handler to the loop
  for signal_kind in (
    signal.SIGINT,
    signal.SIGTERM
  ):
    logger.debug(f"Attaching signal handler for {signal_kind.name}.")
    loop.add_signal_handler(
      signal_kind,
      _exit_signal_handler,
      loop
    )

  try:
    if dev_ui is not None:
      logger.debug("Starting Dev UI.")
      await dev_ui.start()
    logger.debug("Waiting for Signal to quit.")
    await quit.wait()
    logger.debug("Signal received, canceling tasks.")
    assert quit.is_set(), "Quit event should be set."
    pipeline_task.cancel()
  except asyncio.CancelledError:
    logger.debug("Pipeline task canceled, shutting down gracefully.")
  finally:
    if dev_ui is not None:
      logger.debug("Stopping Dev UI.")
      await dev_ui.stop()
    logger.debug("Shutting down.")
    for signal_kind in (
      signal.SIGINT,
      signal.SIGTERM
    ):
      logger.debug(f"Removing signal handler for {signal_kind.name}.")
      loop.remove_signal_handler(signal_kind)

  return rc

if __name__ == '__main__':
  logger.remove()
  logger.add(
    sys.stderr,
    level="TRACE",
    # format="::".join([
    #   "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>",
    #   "<level>{level}</level>",
    #   ":".join([
    #     "<cyan>rxbot</cyan>",
    #     "<cyan>{name}</cyan>",
    #     "<cyan>{function}</cyan>",
    #     "<cyan>{line}</cyan>",
    #   ]),
    #   "<level>{message}</level>",
    # ])
  )
  _rc = 255
  try:
    _rc = asyncio.run(
      _main(
        *sys.argv[1:],
        **{
          "openai_token": os.environ['OPENAI_API_KEY'],
          "dev": True,
        },
      )
    )
  except:
    logger.opt(exception=True).error('An unhandled exception occurred.')
  finally:
    # assert stdin, stdout & stderr are open
    assert not sys.stdin.closed, "stdin is closed"
    assert not sys.stdout.closed, "stdout is closed"
    assert not sys.stderr.closed, "stderr is closed"
    sys.stdout.flush()
    sys.stderr.flush()
    exit(_rc)
