import openai
import openai.error
import tiktoken
from loguru import logger
import sys
import os
import jinja2
import pathlib
from typing import Generator

runtime_modes = {
  "render": {
    "description": "Render the prompt & print it to stdout.",
  },
  "response": {
    "description": "Render the prompt & use the OpenAPI to generate a response.",
  }
}

model_lookup = {
  "gpt3": {
    "name": "gpt-3.5-turbo",
    "max_tokens": 4096,
    "supported_modes": ["render", "response"],
    "personality": {
      "creative": {
        "description": "Responses are more creative; the model is more curious.",
        "tuning": {
          "temperature": 2.0,
          # "top_p": 0.76, # Wasn't creative enough
          "top_p": 0.95, # Warning! I have observed the model gets "stuck" & never generates a response
        }
      },
      "balanced": {
        "description": "Responses are more balanced; the model is more balanced.",
        "tuning": {
          "temperature": 1.0,
          "top_p": 0.815,
        }
      },
      "reserved": {
        "description": "Responses are more reserved; the model is more straightforward.",
        "tuning": {
          "temperature": 0.5,
          "top_p": 0.68,
        }
      },

    }
  },
}

prompt_suffixes = [".j2", ".md"]

def prompt_for_confirmation(prompt: str) -> bool:
  """Prompts the user for confirmation."""
  while True:
    response = input(f"{prompt} [y/n] ").lower()
    if response == "y":
      return True
    elif response == "n":
      return False
    else:
      logger.error(f"Invalid response: {response}.")

def list_prompts(lookup_dir: str) -> list:
  """Lists the prompts available in a directory."""
  return [
    prompt_path.stem
    for prompt_path in pathlib.Path(lookup_dir).iterdir()
    if prompt_path.is_file() and prompt_path.suffix in prompt_suffixes
  ]

def lookup_prompt(name: str, lookup_dir: str) -> pathlib.Path:
  """Looks up a prompt by name in a directory."""
  for suffix in prompt_suffixes:
    prompt_path = pathlib.Path(lookup_dir) / f"{name}{suffix}"
    if prompt_path.exists():
      return prompt_path
  raise FileNotFoundError(f"Prompt {name} not found in {lookup_dir}.")

def render_prompt(prompt_template: pathlib.Path, vars: dict) -> str:
  """Renders a Jinja2 template from a file using the provided vars."""
  if prompt_template.suffix == ".md":
    return prompt_template.read_text()
  elif prompt_template.suffix == ".j2":
    with open(prompt_template, "r") as template_file:
      template: jinja2.Template = jinja2.Template(template_file.read())
    return template.render(**vars)
  else:
    raise ValueError(f"Invalid prompt suffix: {prompt_template.suffix}")

def parse_prompt_vars(*args: str) -> dict[str, str]:
  """Parses the prompt vars from the command line."""
  vars = {}
  for arg in args:
    logger.trace(f"Parsing prompt var: {arg}")
    try:
      key, value = arg.split("=", maxsplit=1)
    except ValueError:
      logger.warning(f"Invalid prompt var: {arg}")
      continue
    vars[key.strip()] = value.strip()
  return vars

def num_tokens_from_prompt(prompt, model):
  """Returns the number of tokens used in a prompt."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    logger.warning(f"Model {model} not found in TikToken. Using default encoding.")
    encoding = tiktoken.get_encoding("cl100k_base")
  
  return len(encoding.encode(prompt))

def submit_prompt(
  prompt: str,
  model: str,
  temperature: float,
  top_p: float,
  stream: bool,
) -> Generator[str, None, None]:
  """Submits a prompt to the OpenAI Chat API."""
  logger.trace("Submitting prompt to OpenAI...")
  try:
    response = openai.ChatCompletion.create(
      model=model,
      messages=[
        {
          "role": "system",
          "content": "Format: Markdown",
        },
        {
          "role": "user",
          "content": prompt,
        }
      ],
      stream=stream,
      temperature=temperature,
      top_p=top_p,
    )
    logger.trace("Response received.")
    if not stream:
      if response["choices"][0]["finish_reason"] != "stop":
        logger.warning(f"Expected stop reason 'stop', got {response['choices'][0]['finish_reason']}.")
      yield response["choices"][0]["message"]["content"]
    else:
      for chunk in response:
        logger.trace(f"Received chunk: {chunk}")
        if chunk["object"] != "chat.completion.chunk":
          logger.trace("chunk is not a completion chunk")
          logger.warning(f"Unhandeled OpenAI API Streaming Response: {chunk['object']}")
          continue
        if "content" in chunk["choices"][0]["delta"]:
          logger.trace("yielding content...")
          yield chunk["choices"][0]["delta"]["content"]
        elif "role" in chunk["choices"][0]["delta"]:
          logger.trace("checking role & skip to next chunk...")
          if chunk["choices"][0]["delta"]["role"] != "assistant":
            logger.warning(f"Expected role 'assistant', got {chunk['choices'][0]['delta']['role']}.")
        elif chunk["choices"][0]["delta"] == {}:
          logger.trace("delta is empty")
          logger.info(f"Response completed b/c {chunk['choices'][0]['finish_reason']}.")
          return
        else:
          raise RuntimeError(f"Unhandeled OpenAI API Streaming Response: {chunk}")
  except GeneratorExit:
    logger.info("User interrupted response. Closing stream...")
    try:
      logger.trace("Closing stream...")
      response.close()
    except Exception as e:
      logger.opt(exception=e).warning("Failed to close the stream.")
    return

def render_response(
  filtered_prompt: str,
  model_name: str,
  model_tuning: dict,
  stream: bool,
) -> str:
  logger.info("Submitting Prompt...")
  print("\n\n---\n\nStart of Response\n\n---\n\n", flush=True)
  response_generator = submit_prompt(
    prompt=filtered_prompt,
    model=model_name,
    stream=stream,
    **model_tuning,
  )
  # response = "\nThis is a test response.\n"
  response = ""
  try:
    logger.trace("Iterating over response generator...")
    for response_chunk in response_generator:
      logger.trace("Received response chunk.")
      response += response_chunk
      print(response_chunk, end="", flush=True)
    print("\n\n\n---\n\nEnd of Response\n\n---\n\n", flush=True)
  except KeyboardInterrupt:
    logger.warning("User Interrupted the Response.")
    response_generator.close()
    raise   
  logger.info(f"Response was {num_tokens_from_prompt(response, model_name)} tokens long.")
  return response


def save_output(name: str, directory: str, content: str, force: bool = False):
  logger.info("Saving Output...")
  output_dir = pathlib.Path(directory)
  if not output_dir.exists():
    logger.error(f"Output directory {output_dir} does not exist.")
    raise FileNotFoundError(directory)
  output_file = (output_dir / name).with_suffix(".md")
  if output_file.exists():
    logger.warning(f"Output file {output_file} already exists.")
    if not (force or prompt_for_confirmation(f"Overwrite {output_file}?")):
      return
  output_file.write_text(content)
  logger.info(f"Output saved to {output_file}")

def main(*args, **kwargs) -> int:
  if len(args) == 0:
    logger.error("No Prompts provided.")
    return 1
  
  prompt_vars = parse_prompt_vars(*args[1:])
  
  try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
  except KeyError:
    logger.critical("No OpenAI Token found.")
    return 1
  
  available_prompts = list_prompts(kwargs['prompts'])
  try:
    prompt_template = lookup_prompt(args[0], kwargs['prompts'])
  except FileNotFoundError:
    logger.critical(f"Prompt {args[0]} not found.")
    logger.info(f"Available Prompts: {', '.join(available_prompts)}")
    return 1

  try:
    available_models_obj = openai.Model.list()
    if available_models_obj["object"] == "list":
      available_models = set(sorted(list(model["id"] for model in available_models_obj["data"] if model["object"] == "model")))
    else:
      logger.error(f"Unhandeled OpenAI API Response: {available_models_obj['object']}")
      return 1
  except openai.error.AuthenticationError:
    logger.critical("Invalid OpenAI Token.")
    return 1
  
  model = model_lookup[kwargs['model']]
  if model['name'] not in available_models:
    logger.critical(f"Model {model['name']} not available.")
    logger.info(f"Available Models: {', '.join(available_models)}")
    return 1

  logger.info(f"Using Model: {model['name']}")
  
  try:
    rendered_prompt = render_prompt(
      prompt_template,
      prompt_vars,
    )
  except jinja2.exceptions.TemplateSyntaxError as e:
    logger.critical(f"Syntax Error in Prompt {args[0]}: {e}")
    return 1
  except jinja2.exceptions.TemplateError as e:
    logger.critical(f"Error in Prompt {args[0]}: {e}")
    return 1
  
  # strip all empty lines from the rendered prompt
  filtered_prompt = rendered_prompt.strip()
    
  token_count = num_tokens_from_prompt(filtered_prompt, model['name'])

  # Validate the mode is valid
  if kwargs["mode"] not in runtime_modes.keys():
    logger.error(f"Invalid mode: {kwargs['mode']}")
    return 1

  # Validate the mode is supported by the model
  if kwargs["mode"] not in model["supported_modes"]:
    logger.error(f"Model {model['name']} does not support {kwargs['mode']} mode.")
    return 1

  # Validate the personality is valid for the model
  if kwargs["personality"] not in model["personality"]:
    logger.error(f"Model {model['name']} does not support {kwargs['personality']} personality.")
    return 1
  logger.info(f"Using Model Personality: {kwargs['personality']}")

  if kwargs['mode'] == "render":
    if token_count >= 3400:
      logger.warning("This might not work w/ ChatGPT's Web UI!")
    else:
      logger.info(f"Prompt is ~{token_count} tokens long, you have ~{model['max_tokens'] - token_count} tokens left.")
    
    if kwargs["yes"] or prompt_for_confirmation(f"Render prompt?"):
      logger.info("Rendering Prompt...")
      print("\n".join([
          "\n\n---\n\nStart of Prompt\n\n---\n\n",
          filtered_prompt,
          "\n\n---\n\nEnd of Prompt\n\n---\n\n",
      ]))
    
    if kwargs["yes"] or prompt_for_confirmation("Would you like to save the rendered prompt?"):
      logger.trace("Saving Output...")
      save_output(kwargs.get("name", args[0]), kwargs['outputs'], filtered_prompt, kwargs["yes"])

  elif kwargs['mode'] == "response":
    if token_count > model['max_tokens']:
      logger.error(f"Prompt is ~{token_count - model['max_tokens']} tokens too long.")
      return 1
    elif token_count > model['max_tokens'] // 2:
      logger.warning(f"A Prompt of ~{token_count} is over half the total alloted tokens, the model only has ~{model['max_tokens'] - token_count} tokens to work with. The closer that is to Zero, the more often responses will be cut off.")
      if not (kwargs["yes"] or prompt_for_confirmation("Continue?")):
        return 1
    else:
      logger.info(f"Prompt is ~{token_count} tokens long, you have ~{model['max_tokens'] - token_count} tokens left.")
    
    if kwargs["yes"] or prompt_for_confirmation("Would you like to see the rendered prompt?"):
      print("\n".join([
          "\n\n---\n\nStart of Prompt\n\n---\n\n",
          filtered_prompt,
          "\n\n---\n\nEnd of Prompt\n\n---\n\n",
      ]))
    def _render_response():
      try:
        return render_response(
          filtered_prompt,
          model['name'],
          model["personality"][kwargs["personality"]]["tuning"],
          not kwargs["no-stream"],
        )
      except KeyboardInterrupt:
        logger.info("User Interrupted Response Generation.")
    if kwargs["yes"] or prompt_for_confirmation(f"Submit prompt to {model['name']} for response?"):
      response = _render_response()
      # Only regenerate response during interactive mode if the user wants to
      if not kwargs["yes"]:
        while prompt_for_confirmation("Would you like to generate another response?"):
          response = _render_response()
    
    if kwargs["yes"] or prompt_for_confirmation("Would you like to save the rendered prompt & response?"):
      logger.trace("Saving Output...")
      save_output(
        kwargs.get("name", args[0]),
        kwargs['outputs'],
        response,
        force=kwargs["yes"],
      )
      # save_output(
      #   kwargs.get("name", args[0]),
      #   kwargs['outputs'],
      #   "\n".join([
      #     "\n\n---\n\nStart of Prompt\n\n---\n\n",
      #     filtered_prompt,
      #     "\n\n---\n\nEnd of Prompt\n\n---\n\n",
      #     "\n\n---\n\nStart of Response\n\n---\n\n",
      #     response,
      #     "\n\n---\n\nEnd of Response\n\n---\n\n",
      #   ]),
      #   force=kwargs["yes"],
      # )
  else:
    raise NotImplementedError(f"Unhandeled mode: {kwargs['mode']}")

  return 0

def _parse_kwargs(*args: str, **kwargs: str) -> dict:
  _kwargs = {
    "help": False,
    "model": "gpt3",
    "prompts": f"{os.environ['CI_PROJECT_DIR']}/meta/prompts/",
    "outputs": f"{os.environ['CI_PROJECT_DIR']}/meta/outputs/",
    "verbose": False,
    "mode": "render",
    "yes": False,
    "no-stream": False,
    "personality": "balanced",
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
  possible_modes = "\n".join([
    f"      {name}: {info['description']}"
    for name, info  in runtime_modes.items()
  ])
  print(f"""
Usage: {sys.argv[0]} [OPTIONS] PROMPT [VAR...]

About:
  Render a prompt template for use with ChatGPT. Optionally submit the prompt to the OpenAI API for an immediate response.

Args:
  PROMPT
    The name of the prompt template to render. Templates may be jinja2 templates or markdown files. Jinja2 templates are rendered using the variables passed in VAR. Markdown files are rendered as-is.
  VAR
    A variable to pass to the prompt template. Takes the form of KEY=VALUE.

Options:
  -h, --help
    Print this help message and exit.
  --name=NAME
    A Custom name to use when saving the rendered prompt or response. Defaults to the name of the prompt template.
  --model=MODEL
    The model to use when calculating the number of tokens used by the prompt. Defaults to gpt3.
    Possible values: {', '.join(model_lookup.keys())}
  --prompts=DIRECTORY
    The path to a directory containing custom jinja2 prompt templates. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/prompts/.
  --output=DIRECTORY
    The path to a directory to save rendered prompts & responses. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/outputs/.
  --mode=MODE
    Runs the script in a specific mode. Defaults to 'render'
    Possible values: {', '.join(runtime_modes.keys())}
  --personality=PERSONALITY
    The personality to use when submitting a prompt to the OpenAI API. Defaults to 'balanced'.
    Possible values:
      creative: Better at generating ideas given open ended prompts. Response can vary widely.
      conservative: Better at generating straight forward answers to close ended prompts. Responses don't branch out much.
      balanced: A rough halfway point between creative and conservative. Probably a good place to start.
  --no-stream
    Don't stream the response from the OpenAI API; wait for the entire response to be generated before displaying.
  --yes
    Reply yes to all prompts.
  --verbose
    Enable verbose logging.
  """)

if __name__ == "__main__":
  _rc = 255
  try:
    logger.remove()
    _args = _parse_args(*sys.argv[1:])
    _kwargs = _parse_kwargs(*sys.argv[1:])
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
