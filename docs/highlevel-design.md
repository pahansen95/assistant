# Assistant Architecture & Design

## High Level Goals

> Create an assistant that helps individuals or teams who solve technical problems in a digital environment by integrating into their daily workflow and maximizing their time spent on meaningful work. You want the assistant to help them with ideation and discovery of new ideas by engaging them in critical thinking tasks using natural language, retaining contextual references to recent ideas or conversations, recalling ideas, solutions, or approaches previously discussed, providing timely recommendations, and pointing out parallel ideas or approaches within different domains of expertise.

- Who is the target audience of the assistant?
  - Individuals or Teams of users who solve technical problems in a digital environment.
  - The following set of descriptors encompass the majority of individuals that will use the assistant. All descriptors need not apply to a single individual
    - creative
    - thoughtful
    - pragmatic
    - smart
    - attention to detail
    - perfectionist
    - overworked
    - limited time
    - engineer
    - logician
    - strategist
    - tactician
    - hyperfocused
    - Scatterbrained
- What is the headline for the assistant?
  - An assitant that integrates into daily workflow of the user to maximize their time spent on work meaningful to them.
- What value will the assistant provide the user?
  - Buy back the time spent during the ideation & discovery process of new ideas.
  - Expidite contextual research & identification of correlated topics & ideas.
  - Identify existing ideas, solutions & approaches.
  - Automate the boilerplate of ideation.
    - Examples of boilerplate may include:
      - formalizing ideas into written prose
      - evaluation of the application of an idea
  - Optimize "search traversal" of the "graph of ideas"
    - Ie. One idea can spawn many more, how does the user know where to spend their limited time?
- What key features does the assistant provide?
  - The assistant will thoughtfully engage the user in critical thinking tasks using Natural language.
  - The assistant will retain contextual references to recent ideas or conversations it has had with the user.
  - The assistant will be able to recall ideas, solutions or approaches previsouly discussed.
  - The assistant will provide the user with timely recommendations & even point out parallel ideas or approaches within different domains of expertise. 

## High Level Architectural Design

- Modular Design

  > One recommendation is to use a modular architecture that separates the different components of your assistant, such as the natural language understanding, the knowledge base, the reasoning engine, and the natural language generation. This way, you can easily update or replace any component without affecting the others, and you can also reuse existing modules or frameworks that suit your needs.

- External Lookups & Integrations

  > One idea is to leverage existing sources of information and knowledge that can help your assistant provide timely recommendations and insights. For example, you can use web search engines, online databases, academic papers, blogs, forums, or social media to find relevant ideas, solutions, or approaches that have been discussed or implemented by others. You can also use natural language processing techniques to extract key concepts and entities from these sources and link them to your knowledge base.

- User Input & Interfacing with the Assistant

  > To handle long or complex inputs or outputs that may not fit well in a chat window, the assistant will prioritize short-form input and outputs, keeping ideas simple and providing concise, succinct, and salient communication. For longer or complex ideas, the assistant will engage in back-and-forth communication with the user, employing active listening traits to ensure mutual understanding. This approach aims to balance the need for concise communication with the need to ensure a thorough and accurate exchange of information.
  >
  > To handle errors or misunderstandings in the user's input or the assistant's output, the assistant should employ an active listening framework. It should provide a salient summary of the user's intent or idea and seek feedback, rather than assuming it knows everything. The assistant should also seek to determine if the user understood its point of view through contextual questions, speak up if it is confused or identifies contradictory information, and avoid assuming the user knows everything. This approach prioritizes clear communication and mutual understanding, which is essential for ensuring that the assistant is most productive in helping the user achieve their goals. Actively engage the user for feedback & likewise provide the user feedback if it seems that they are not engaging efficiently with the assistant or exercising active listening.
  >
  > For handling multiple or concurrent inputs or outputs from different users or sources, the approach is not yet determined, and the focus is currently on solving conversations between one user and one assistant. Similarly, for handling interruptions or distractions in the user's attention or the assistant's processing, the approach has not been determined, and it will be addressed later in the implementation process.

  - Potential Challenges:
    - How will you handle long or complex inputs or outputs that may not fit well in a chat window?
      - Put an emphasis on short form input & outputs. Keep ideas simple & provide concise, succinct & salient communication.
      - Longer or Complex ideas should be represented by back & forth engagement that employ's active listening traits to ensure there is mutual understanding. 
    - How will you handle multiple or concurrent inputs or outputs from different users or sources?
      - I'm not sure yet, let's solve this later & focus on solving "conversations" that have 1 user & 1 assistant.
    - How will you handle errors or misunderstandings in the user’s input or the assistant’s output?
      - The assistant should employ an active listening framework. It should provide a salient summary of the user's intent or idea & seek feedback. The assistant shouldn't assume it knows everything & that it needs feedback from the user to be most productive.
      - Likewise it should seek to determine if the user understood its point of view through contextual questions. It should speak up if it is confused or identifies contradictory information. It shouldn't assume the user know's everything & that the user needs feedback to be most productive.
    - How will you handle interruptions or distractions in the user’s attention or the assistant’s processing?
      - Good question, I'm not sure yet. Let's solve this later once we know more about the implementation.

## Modular Design

> 1. Natural Language Understanding (NLU) - Interprets and extracts meaning from user inputs, understanding context, intent, and relevant entities, making it possible for the assistant to provide accurate and context-aware responses.
> 2. Knowledge Base (KB) - Serves as the central repository of information, facilitating efficient access and retrieval of domain-specific knowledge, which is crucial for offering accurate, relevant information and insights to users.
> 3. Natural Language Generation (NLG) - Produces human-like responses based on the understanding from the NLU module and information retrieved from the KB, resulting in a more natural and engaging user experience.
>
> By incorporating these modules, you create a well-rounded technical assistant capable of understanding user inputs, managing domain-specific knowledge, and generating meaningful, human-like responses.

### Knowledge Base (KB)

- At it's most basics, the interaction with the assistant will be a message. A message consists of the speaking entity (ie. user or assistant), the content as text & a timestamp of when it was submitted. Conceptually though, messages map to multiple abstract ideas such as conversations, projects or ideas. These mappings are not intrinsic to the message but instead are emergent properties of the collective system (the system being the assistant, the user & their interactions) So how can we go about: A) Efficiently representing the raw message data for persistence (such as in a database)? B) Adaptively generating or retaining the abstract ideas the emerge from this network of messages?

  > A) Efficiently representing the raw message data for persistence:
  >
  > To efficiently represent and store raw message data, you can use a relational or document-based database. Both types of databases have their own advantages and can be suitable depending on your specific requirements.
  >
  > 1. Relational Database (e.g., PostgreSQL, MySQL):
  >    - Create a table for messages with columns such as 'id', 'entity_type' (user or assistant), 'content', 'timestamp', and any other relevant metadata.
  >    - Use primary keys and indexing to optimize query performance.
  >    - Foreign keys can be used to link messages to other entities like conversations, projects, or ideas.
  > 2. Document-based Database (e.g., MongoDB, CouchDB):
  >    - Store messages as documents with fields like 'entity_type', 'content', 'timestamp', and any other relevant metadata.
  >    - Index fields to improve query performance.
  >    - Create references to other collections (e.g., conversations, projects, or ideas) as needed.
  >
  > B) Adaptively generating or retaining the abstract ideas that emerge from the network of messages:
  >
  > To generate and retain abstract ideas emerging from the network of messages, consider using a graph database, which can efficiently model complex relationships and connections between messages, conversations, projects, and ideas.
  >
  > 1. Graph Database (e.g., Neo4j, Amazon Neptune):
  >    - Create nodes for messages, conversations, projects, and ideas.
  >    - Define relationships between nodes (e.g., a message belongs to a conversation, or a conversation is part of a project).
  >    - Utilize graph queries to traverse and explore relationships between nodes, allowing you to identify and extract abstract ideas from the interconnected network of messages.
  >
  > By combining an appropriate database for message persistence and a graph database for representing emergent abstract ideas, you can create a flexible and efficient system capable of handling complex relationships and connections in your assistant application.

- Persisting Message Data

> The chosen approach for storing messaging data in CouchDB involves separate documents for messages and chat sessions, offering simplicity and flexibility:
>
> 1. Message Document: Store each message as an individual document with fields such as 'id', 'entity_type', 'content', 'timestamp', and other relevant metadata. This allows for efficient querying and management of individual messages.
> 2. Chat Session Document: Store each chat session as a separate document with fields like 'id', 'start_timestamp', 'end_timestamp', and other relevant metadata. Maintain an array field called 'message_ids' that contains the 'id's of message documents generated during the session, sorted by submission timestamp.
>
> This approach enables efficient querying of both chat sessions and individual messages while reducing data duplication and allowing for easy association of messages with multiple chat sessions or other entities. Views can be incorporated later if needed to composite data and further optimize the system.

## Entity to Entity Interactions

-  The concept of an assistant is an entity that is prompted with messages & replies accordingly. In implementation the "assistant" is really a collection of systems that work together to interact with the user entity through natural language. This collection of systems will be called the `social framework system`.
-  The minimal set of responsibilities the `social framework system` has are...
   -  Provide a centralized communication hub between the external entity (aka a User) & the internal entity (aka the assistant).
      -  Ex. The user submits a message & the assistant responds.
   -  Manage the persistence of data for all interactions between the external & internal entity.
      -  Ex. Persisting the raw chat log to a database
-  The extended set of responsibilities the `social framework system` has are...
   -  TBD...

###  Social Framework System

- External Interfaces...
  - `prompt` the assistant
  -  `listen` to the assistant
- Internal Interfaces...
  - `think` about the messages
  - `stage` a message into short term memory (ie. data persistence for the KB)
  - `reply` to the user
