"""
# About
We can leverage the concept of emergent properties to solve a complex problem through the application of a system of simple components.

GPT provides a novel way to generate code from natural language.

Humans have a natural ability to generalize & simplify complex problems into simple components.

If we can split a complex problem into simple components & then provide natural language descriptions of each component then we can leverage the power of GPT to generate code that solves the complex problem.

We can take this a step further by describing the problem solving process as a chain of simple components.

Through this process we can automate the process of solving complex problems.

This is the what I hope to solve (or at least partially solve) with this script

# The Problem & The Solution

The primary goal is to solve a problem.

I have chosen a problem that is neither overly simple nor overly complex:

> How can we simplify concurrent, distributed systems development through a peer-to-peer messaging system that is secure, simple to use & low effort to maintain?

The solution I would like to implement can be summarized as follows:

> Develop a custom L7 application protocol using a Pub/Sub architecture to exchanges messages in a peer-to-peer network environment. Leverage already proven cryptographic solutions like TLS & Symmetric Keys to provide security. Leverage common standards like JSON & Base64 to provide flexibility & interoperability. Leverage existing open source libraries ZeroMQ to reduce maintenance effort. Use Python because it is simple, powerful & easy to learn.

# The Components

A L7 application protocol can be defined within a specification. This specification breaks the complex problem into a series of simple components described in natural language. It defines the external software contracts of the solution as well as the expected behaviours of the solution as a whole. 

# The Process

Designing any type of software can be broken down into a series of steps. Since GPT understands natural language, we can structure the process similiar to an Agile development environment. These are the steps I have identified:

1. Ideation & Pre-Planning
  1. Define the Problem
  2. Propose a Vision for the Solution
  3. Brainstorm & Exhaustively define the solution.
  4. Write a solution specification.
  5. Identify the minimal set of specification components that are required to reach MVP (Minimum Viable Product)
  6. From the MVP components, identify the minimal subset necessary to reach PoC (Proof of Concept).
2. Planning
  1. Generate a project timeline where the first 2 milestones are PoC, MVP & Feature Complete.
  2. For each milestone, identify discrete features & functionality that consitute the milestone.
  3. For each feature or functionality, identify the components that are required to implement it.
  4. Identify the dependencies between these components.
  5. Organize the components into a dependency graph, each layer of the graph represents a sprint.
  6. For each sprint, identify the implementation tasks that are required to complete the sprint.
  7. Identify success criteria for each milestone.
3. Pre-Impementation
  1. For each feature or functionality, design the expected external software interfaces & contracts.
  2. For each component of that feature or functionality, design the internal software interfaces & contracts.
  3. For each component, identify existing libraries that can be leveraged to reduce development effort.
  4. Document in depth every internal & external contracts along with every component, feature & functionality.
4. Implementation
  1. For each sprint, implement the components. Each sprint covers the following:
    - Ensure software executes.
    - Test software for expected behaviour.
    - Produce technical documentation describing the source code.
  2. At the end of the PoC Milestone, evaluate the PoC's effectiveness against success criteria.
    - If the PoC is successful, continue to the MVP Milestone.
    - If the PoC is not successful, re-evaluate the solution & re-plan the project.
  3. At the end of the MVP Milestone, evaluate the MVP's effectiveness against success criteria.
    - If the MVP is successful, continue to the Feature Complete Milestone.
    - If the MVP is not successful then ... (TODO)

Let us commence forth!
"""

from loguru import logger
import openai
import tiktoken
import os
import sys
from typing import NamedTuple, Iterable, Callable, Any
from dataclasses import dataclass
import pathlib
import enum
import functools
import json
import asyncio
import itertools
import re
import datetime

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

persona_templates = {
  "sme": """\
Take on the persona of a Subject Matter Expert (SME).

An SME is...
1. An individual with extensive knowledge in a specific domain or field.
2. An authority in their area of specialization.
3. A professional with in-depth understanding of their discipline.
4. A contributor to the development of best practices within their field.

An SME is responsible for...
1. Consulting and advising organizations, researchers, or project teams.
2. Conducting research and development to advance new theories, technologies, or methodologies.
3. Producing content such as articles, books, white papers, or other publications.
4. Ensuring work aligns with industry standards and best practices through quality assurance processes.

The particulars of your role as an SME are described below.
> {sme_description}
"""
}

string_alnum_lower = lambda s: re.sub(r"[^a-zA-Z0-9]", "", s).lower()

class CHAT_ROLE(enum.Enum):
  SYSTEM: str = "system"
  USER: str = "user"
  ASSISTANT: str = "assistant"

class ChatMessage(NamedTuple):
  """Represents a chat message."""
  role: CHAT_ROLE
  content: str

  def to_dict(self):
    return {
      "role": self.role.value,
      "content": self.content,
    }

def count_tokens(model: str, *messages: ChatMessage):
  """Returns the number of tokens used in a prompt."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    logger.warning(f"Model {model} not found in TikToken. Using default encoding.")
    encoding = tiktoken.get_encoding("cl100k_base")
  
  return len(encoding.encode(
    "\n".join(map(lambda m: m.content, messages))
  ))


async def chat(
  persona: ChatMessage,
  messages: Iterable[ChatMessage],
  model: str,
  personality: dict,
) -> ChatMessage:
  """Submits a chat for completion to the OpenAI Chat API."""
  logger.trace("Submitting chat to OpenAI...")
  try:
    response = await openai.ChatCompletion.acreate(
      model=model,
      messages=[
        persona.to_dict(),
        *map(lambda m: m.to_dict(), messages),
      ],
      stream=False,
      temperature=personality["tuning"]["temperature"],
      top_p=personality["tuning"]["top_p"],
    )
    logger.trace("Response received.")
    if response["choices"][0]["finish_reason"] != "stop":
      logger.warning(f"Expected stop reason 'stop', got {response['choices'][0]['finish_reason']}.")
    return ChatMessage(
      role=CHAT_ROLE.ASSISTANT,
      content=response["choices"][0]["message"]["content"],
    )
  except openai.error.APIError as e:
    logger.error(f"OpenAI API Error: {e}")
    raise e

def load_persona(name: str, dir: str) -> ChatMessage:
  """Loads a persona from a file."""
  logger.trace(f"Loading persona {name} from {dir}")
  try:
    persona_path = pathlib.Path(dir) / f"{name}.md"
    persona = persona_path.read_text()
    return ChatMessage(
      role=CHAT_ROLE.USER,
      content=f"This is your persona:\n{persona}",
    )
  except FileNotFoundError:
    logger.error(f"Persona {name} not found in {dir}.")
    raise FileNotFoundError(f"Persona {name} not found in {dir}.")

def load_api_token():
  """Loads the OpenAI API Token from the environment."""
  try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
  except KeyError:
    logger.critical("No OpenAI Token found.")
    raise RuntimeError("No OpenAI Token found.")

class ParseError(Exception):
  """Raised when a response cannot be parsed."""
  def __init__(self, msg: str, error: str, *args) -> None:
    self.msg: str = msg
    self.error: str = error
    super().__init__(*args)

async def _parse_and_retry_chat(
  messages: list[ChatMessage],
  persona: ChatMessage,
  model: str,
  personality: str,
  parse_response: Callable[..., Any],
  max_retry_count: int = 0,
) -> Any:
  """Convience function that wraps a chat session with GPT such that it responds in JSON."""
  retry_count = 0
  _messages = list(messages)
  while True:
    response = await chat(
      persona=persona,
      messages=_messages,
      model=model_lookup[model]["name"],
      personality=model_lookup[model]["personality"][personality]
    )
    try:
      response = parse_response(response.content)
      if response is None:
        raise RuntimeError(f"Function {parse_response.__name__} returned {None.__class__.__name__}")
      return response
    except ParseError as pe:
      logger.warning(f"Failed to parse response: {pe.error}")
      logger.trace(f"Bad Response: {response.content}")
      if retry_count > max_retry_count:
        logger.error(f"Failed to parse response after {max_retry_count} retries.")
        raise RuntimeError("Failed to parse response.")
      retry_count += 1
      error_message = ChatMessage(
        role=CHAT_ROLE.USER,
        content=f"Please fix your response, {pe.msg}: {pe.error}",
      )
      if not messages[-1].content.startswith("Please fix your response"):
        messages.append(error_message)
      else:
        messages[-1] = error_message

def _parse_json_list(
  response: str,
  item_types: tuple[type] | type,
) -> list:
  if not isinstance(item_types, tuple):
    item_types = (item_types,)
  try:
    result = json.loads(response)
    if not isinstance(result, list):
      raise TypeError(f"Expected a list but got {type(result).__name__}.")
    all_wrong_types = [
      f"bad type {type(r).__name__} at index {i}"
      for i, r in enumerate(result)
      if not isinstance(result[i], item_types)
    ]
    if len(all_wrong_types) > 0:
      raise TypeError(f"Expected a list of {', '.join([t.__name__ for t in item_types])} but found the following errors: {', '.join(all_wrong_types)}.")
    return result
  except TypeError as te:
    raise ParseError("invalid JSON detected", te) from te
  except json.JSONDecodeError as jde:
    raise ParseError("invalid JSON detected", jde.msg) from jde
  
async def generate_sme_descriptions(
  problem_statement_message: ChatMessage,
  vision_statement_message: ChatMessage,
  get_persona: Callable[..., ChatMessage],
) -> dict[tuple[str, ...], str]:
  """Generate a list of descriptions for potential SMEs that can contribute to the solutioning process."""
  # Based on the problem and vision provided, generate a list of domain areas that are relevant to the problem.
  domain_excpetation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array of strings in plain text. Do not use markdown or any other formatting.",
  )
  tightly_relevant_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Generate a list of 30 technical fields, research domains & areas of expertise that are tightly correlated to the problem statement.",
  )
  loosely_relevant_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Generate a list of 30 technical fields, research domains & areas of expertise that are loosely correlated to the problem statement.",
  )
  domain_fields_parse_response = functools.partial(
    _parse_json_list,
    item_types=str,
  )
  domain_fields = list(itertools.chain.from_iterable(await asyncio.gather(
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="creative",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="balanced",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="balanced",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, tightly_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=domain_fields_parse_response,
    ),
    _parse_and_retry_chat(
      messages=[problem_statement_message, loosely_relevant_message, domain_excpetation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=domain_fields_parse_response,
    ),
  )))


  domain_fields = list(set(map(string_alnum_lower, domain_fields)))
    
  logger.info(f"Domain fields: {domain_fields}")

  # Group these domain areas into clusters of related fields.
  cluster_request_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Please group the following fields into clusters based on how closely they are related to each other. Fields may be used more than once if neccesary. These are the following fields:\n{', '.join(domain_fields)}",
  )
  cluster_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array where each item is itself a JSON array of strings. Do not use markdown or any other formatting.",
  )
  cluster_parse_response = functools.partial(
    _parse_json_list,
    item_types=list,
  )
  clusters = await _parse_and_retry_chat(
    messages=[cluster_request_message, cluster_expectation_message],
    persona=get_persona("jack-of-all-trades"),
    model="gpt3",
    personality="balanced",
    parse_response=cluster_parse_response,
  )
  logger.info(f"Clusters: {clusters}")

  # For each cluster generate a natural language description of such an SME.
  sme_description_messages: list[ChatMessage] = [
    ChatMessage(
      role=CHAT_ROLE.USER,
      content=f"I will provide a clustering of related domain fields. Please write a natural language description of a Subjet Matter Expert. When writing a description for a subject matter expert (SME), include three key components. First, briefly describe the SME's field or domain of specialization to establish their area of expertise. Next, highlight their key technical skills, tools, methodologies, and knowledge areas to emphasize their proficiency within the field. Finally, emphasize the expert's unique strengths and qualities, focusing on what sets them apart in their discipline. By incorporating these three elements, you'll create a concise and informative description that showcases the SME's expertise, technical capabilities, and personal strengths. This description should not include any information related to their personal life or their personality. The description should be salient & succinct. Here are the related domain fields you should consider: \n{', '.join(cluster)}",
    )
    for cluster in clusters
  ]
  sme_description_example = f"""
  The expert is a Marine Biologist specializing in coral reef ecosystems and conservation. They are proficient in underwater survey techniques, statistical analysis of ecological data, and remote sensing technologies for marine habitats. With a strong understanding of the taxonomy and ecology of coral reef species, including fish, invertebrates, and coral, they possess strong observational and research skills. Their adaptability to different fieldwork environments and ability to synthesize complex ecological data make them invaluable for practical conservation applications.
  """
  sme_description_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"My expectation is you will respond in plain text with only the requested description. Use plain text, do not use markdown or any other formatting. Here is an example of a description of an SME:\n{sme_description_example}",
  )
  sme_descriptions = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[sme_description_message, sme_description_expectation_message],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=lambda s: s,
    )
    for sme_description_message in sme_description_messages
  ])
  for sme_description in sme_descriptions:
    logger.info(f"Generated SME Description...\n{sme_description}")
  
  # Scope down the SMEs to only those most relevant to the problem.
  sme_descriptions_as_markdown_list = "\n".join(f"{i+1}. {sme_description}" for i, sme_description in enumerate(sme_descriptions))
  relevant_sme_request_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Please select the 10 most relevant SMEs for our problem statement:\n{sme_descriptions_as_markdown_list}",
  )
  relevant_sme_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you will respond with a JSON array of integers. Each integer should be the list number corresponding of the SME you selected. Do not use markdown or any other formatting.",
  )
  relevant_sme_parse_response = functools.partial(
    _parse_json_list,
    item_types=int,
  )
  relevant_sme: list[int] = await _parse_and_retry_chat(
    messages=[
      problem_statement_message,
      relevant_sme_request_message,
      relevant_sme_expectation_message,
    ],
    persona=get_persona("jack-of-all-trades"),
    model="gpt3",
    personality="balanced",
    parse_response=relevant_sme_parse_response,
  )
  selected_smes = [sme_descriptions[i-1] for i in relevant_sme]
  for selected_sme in selected_smes:
    logger.info(f"Selected sme...\n{selected_sme}")
  
  # Generate a unique identifier for each SME that describes their area of expertise.
  sme_id_expectation_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="My expectation is you MUST respond with only the JSON array of strings. The array SHOULD have a length of between five and ten inclusive. Each item in the list MUST be less or equal to three words. You MUST NOT use markdown or any syntax other than JSON.",
  )
  sme_id_responses = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[
        ChatMessage(
          role=CHAT_ROLE.USER,
          content=f"Given the provided description of the SME please provide a salient set of descriptors that describes their core domain of competency:\n{selected_sme}",
        ),
        sme_id_expectation_message,
      ],
      persona=get_persona("jack-of-all-trades"),
      model="gpt3",
      personality="reserved",
      parse_response=functools.partial(
        _parse_json_list,
        item_types=str,
      ),
    )
    for selected_sme in selected_smes
  ])
  assert isinstance(sme_id_responses, list)
  assert all(isinstance(sme_id_response, list) for sme_id_response in sme_id_responses)
  assert all(isinstance(sme_id, str) for sme_id_response in sme_id_responses for sme_id in sme_id_response)
  for sme_id_response in sme_id_responses:
    logger.info(f"Generated SME ID...\n{sme_id_response}")
  
  assert len(sme_id_responses) == len(selected_smes)
  return {
    tuple(set(
      string_alnum_lower(sme_id)
      for sme_id in sme_ids
    )): sme_description
    for sme_ids, sme_description in zip(sme_id_responses, selected_smes)
  }

async def think_tank(
  sme_descriptions: dict[tuple[str, ...], str],
  problem_statement_message: ChatMessage,
  vision_statement_message: ChatMessage,
  get_persona: Callable[..., ChatMessage],
) -> ...:
  """A Think tank is a group of Subject Matter Experts (SMEs) who sit down together and discuss the problem, the vision, and the solution through a series of sessions.
  
  The first session is focused on exploring the problem space. The goal of this part of the discussion is to understand the problem. The SMEs should ask questions to clarify the problem. They should also ask questions to understand the problem from different perspectives.

  The second session is to brainstorm ideas for solutions that meet the vision. Ideas can be new or existing. They can be simple or complex. They can be good or bad. The goal is to generate as many ideas as possible. The more ideas, the better.

  It is also important to note that the brainstorming session is not a discussion of what solution specifically to use or how to implement it. The goal is to generate ideas, not to evaluate them. The evaluation of ideas is done later.

  The brainstorming session is facilitated by a moderator who ensures that the discussion stays on track. The moderator should be a neutral party who is not an SME. 

  Additional members should be present to offer points of view outside from outside the problem space. These members are called "Observers". Observers do not contribute the same amount as SMEs but offer valuable insights.

  The third session is to evaluate the ideas generated in the brainstorming session. The goal of this session is to determine which ideas are worth pursuing. The evaluation process is called "Prioritization". The SMEs should evaluate each idea based on criteria such as:

  - Does the idea meet the vision?
  - Is the idea realistic?
  - Is the idea pragmatic?
  - How much effort is required to implement the idea?
  - How much effort is required to maintain & support the idea?

  Finally the fourth session is to select the best idea. The goal of this session is to select the best idea to implement. The SMEs should select the idea that best meets the vision, is the most realistic, is the most pragmatic, requires the least effort to implement, and requires the least effort to maintain & support. This is the output of the Think Tank.
  """
    
  # Template the Persona's from the SMEs
  sme_persona_messages = [
    ChatMessage(
      role=CHAT_ROLE.USER,
      content=persona_templates['sme'].format(
        sme_description=sme_desc,
      ),
    )
    for sme_desc in sme_descriptions.values()
  ]

  # TEST: Generate a response from the SMEs based on the problem statement & vision statement.

  contextual_header_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="You are participating in a think tank as an SME. I will provide you some contextual information first & then I will share with you the conversational transcript.",
  )
  moderator_asks_preliminary_questions_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content="Here starts the conversation...\nThank you for joining us on today's session. I will be today's moderator. To start I would like to cover some preliminary items. First, I would like to ask each of you to briefly introduce your areas of expertise & your strengths. Second, please restate the problem statement as you understand it. Third, please restate the vision statement as you understand it. Lastly please tell us your initial thoughts on the customer's problem & vision statement.",
  )
  
  responses = await asyncio.gather(*[
    _parse_and_retry_chat(
      messages=[
        contextual_header_message,
        problem_statement_message, vision_statement_message,
        moderator_asks_preliminary_questions_message,
      ],
      persona=sme_persona_message,
      model="gpt3",
      personality="balanced",
      parse_response=lambda s: s,
    )
    for sme_persona_message in sme_persona_messages
  ])
  for response in responses:
    logger.info(f"Generated response...\n{response}")

async def main(*args, **kwargs) -> int:
  """Main entry point for the program."""
  cache_dir = pathlib.Path(kwargs["cache"])
  personas_dir = pathlib.Path(kwargs["personas"])
  if not cache_dir.exists():
    logger.info(f"Creating cache directory {cache_dir}")
    cache_dir.mkdir(parents=True)
  if not personas_dir.exists():
    logger.info(f"Creating personas directory {personas_dir}")
    personas_dir.mkdir(parents=True)
  
  # Find available personas
  personas = list(map(lambda p: p.stem, personas_dir.glob("*.md")))
  logger.info(f"Found {len(personas)} personas: {', '.join(personas)}")
  _load_persona = functools.partial(load_persona, dir=personas_dir)
  
  load_api_token()

  # Load the Problem & Vision Statement
  problem_statement = pathlib.Path(os.environ["CI_PROJECT_DIR"]) / "docs" / "ipc" / "problem-statement.md"
  vision_statement = pathlib.Path(os.environ["CI_PROJECT_DIR"]) / "docs" / "ipc" / "vision-statement.md"

  # Create Messages from the Problem & Vision Statement
  problem_statement_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Here is our problem statement describing what we want to solve:\n{problem_statement}",
  )
  vision_statement_message = ChatMessage(
    role=CHAT_ROLE.USER,
    content=f"Here is our vision statement describing what we believe the solution to our problem statement should be:\n{vision_statement}",
  )
  
  if kwargs['phase-gen-smes']:
    # Generate a set of SMEs that will contribute to the problem solving process.
    logger.trace("Generating SME Descriptions...")
    sme_descriptions = await generate_sme_descriptions(
      problem_statement_message,
      vision_statement_message,
      get_persona=_load_persona,
    )
    # Cache the SME Descriptions
    logger.trace("Caching SME Descriptions...")
    sme_descriptions_path = cache_dir / "sme-descriptions.json"
    # Backup the old SMEs if they exist
    if sme_descriptions_path.exists():
      backup_path = sme_descriptions_path.parent / f"{sme_descriptions_path.stem}-{datetime.datetime.now().isoformat()}{sme_descriptions_path.suffix}"
      logger.trace(f"Backing up old SME Descriptions to {backup_path}")
      sme_descriptions_path.rename(backup_path)
    # lambda that strips all non-alphanumeric characters from a string
    sme_descriptions_path.write_text(json.dumps(
      {
        "|".join(sme_ids): sme_desc
        for sme_ids, sme_desc in sme_descriptions.items()
      }
    ))
    logger.info(f"Saved SME Descriptions to {sme_descriptions_path}")
  else:
    # Load the SME Descriptions
    logger.trace("Loading SME Descriptions...")
    sme_descriptions_path = cache_dir / "sme-descriptions.json"
    if not sme_descriptions_path.exists():
      logger.error(f"No SME Descriptions found at {sme_descriptions_path}; please run with --phase-gen-smes")
      return 1
    sme_descriptions = {
      tuple(sme_ids.split("|")): sme_desc
      for sme_ids, sme_desc in json.loads(sme_descriptions_path.read_text()).items()
    }
    logger.info(f"Loaded SME Descriptions from {sme_descriptions_path}")
    for sme_ids, sme_desc in sme_descriptions.items():
      logger.info(f"{sme_ids}: {sme_desc}")

  # Sanity check the SME Descriptions
  assert isinstance(sme_descriptions, dict)
  assert all(
    isinstance(sme_ids, tuple) and isinstance(sme_desc, str)
    for sme_ids, sme_desc in sme_descriptions.items()
  )
  assert all(
    isinstance(sme_id, str)
    for sme_ids in sme_descriptions.keys()
    for sme_id in sme_ids
  )

  # Move on to the Think Tank phase

  if kwargs['phase-think-tank']:
    _ = await think_tank(
      sme_descriptions,
      problem_statement_message,
      vision_statement_message,
      get_persona=_load_persona,
    )

  return 0

def _parse_kwargs(*args: str, **kwargs: str) -> dict:
  _kwargs = {
    "help": False,
    "verbose": False,
    "cache": f"{os.environ['CI_PROJECT_DIR']}/meta/chain/",
    "personas": f"{os.environ['CI_PROJECT_DIR']}/meta/personas/",
    "phase-gen-smes": False,
    "phase-think-tank": False,
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
Usage: {sys.argv[0]} [OPTIONS]

About:
  ...

Args:
  ...

Options:
  -h, --help
    Print this help message and exit.
  --cache=DIRECTORY
    The path to a directory to save chat log. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/chain/
  --personas=DIRECTORY
    The path to a directory containing persona files. Defaults to {os.environ['CI_PROJECT_DIR']}/meta/personas/
  --verbose
    Enable verbose logging.
  --phase-gen-smes
    Generate SME Descriptions and save them to the cache directory.
  --phase-think-tank
    Run the Think Tank phase of the process.
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
      _rc = asyncio.run(main(*_args, **_kwargs))
  except Exception as e:
    logger.opt(exception=e).critical("Unhandled Exception raised during runtime...")
  finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(_rc)
