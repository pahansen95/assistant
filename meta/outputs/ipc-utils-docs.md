# Implementation: IdGenerator and Error Handling

## Table of Contents
1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Interfaces](#interfaces)
   - [API Specifications](#api-specifications)
   - [Data Structures](#data-structures)
   - [File Formats](#file-formats)
4. [Examples and Use Cases](#examples-and-use-cases)
5. [Additional Notes](#additional-notes)

## Introduction
This documentation outlines the implementation of the IdGenerator and error handling components in the L7 Channel protocol. The IdGenerator provides a way to generate unique identifiers for Peers, Sessions, and Topics, while the error handling component provides a way to categorize and handle different types of errors that may occur during runtime.

## Requirements
- The IdGenerator must generate unique Peer IDs, Session IDs, and Topic IDs.
- The generated IDs must be of the appropriate size.
- The error handling component must be able to categorize and handle different types of errors that may occur during runtime.

## Interfaces

### API Specifications

#### `generate_peer_id()`:
```python
def generate_peer_id(self) -> int:
    """
    Generates a unique Peer ID.

    Returns:
    --------
    int
        A 128-bit integer representing the unique Peer ID.
    """
```

Generates a unique Peer ID.

Inputs: none

Outputs:
- int: A 128-bit integer representing the unique Peer ID.

#### `generate_session_id()`:
```python
def generate_session_id(self) -> int:
    """
    Generates a unique Session ID.

    Returns:
    --------
    int
        A 10-bit integer representing the unique Session ID.
    """
```

Generates a unique Session ID.

Inputs: none

Outputs:
- int: A 10-bit integer representing the unique Session ID.

#### `generate_topic_id()`:
```python
def generate_topic_id(self) -> int:
    """
    Generates a unique Topic ID.

    Returns:
    --------
    int
        A 22-bit integer representing the unique Topic ID.
    """
```

Generates a unique Topic ID.

Inputs: none

Outputs:
- int: A 22-bit integer representing the unique Topic ID.


#### `handle_error()`:
```python
def handle_error(error: L7Error, message: str = None):
    """
    Handle a runtime error by categorizing the error and raising an appropriate exception.
    If a message is provided, send an ERROR Message over the channel if possible.
    """
```

Handles a runtime error by categorizing the error and raising an appropriate exception.

Inputs:
- `error` (L7Error): The type of error that occurred.
- `message` (str, optional): A description of the error. Default is None.

Outputs: none


### Data Structures
```python
@dataclass
class IdGenerator:
    """
    Utility class for generating unique identifiers for Peers, Sessions, and Topics.

    Attributes:
    -----------
    channel_id : int
        The identifier of the Channel.
    used_session_ids : set[int]
        The set of Session IDs that have already been used.
    used_topic_ids : set[int]
        The set of Topic IDs that have already been used.
    """

    channel_id: int
    used_session_ids: set[int] = field(default_factory=set)
    used_topic_ids: set[int] = field(default_factory=set)
```
`IdGenerator` is a utility class for generating unique identifiers for Peers, Sessions, and Topics. The class has three attributes:
- `channel_id` (int): The identifier of the Channel.
- `used_session_ids` (set[int]): The set of Session IDs that have already been used.
- `used_topic_ids` (set[int]): The set of Topic IDs that have already been used.


#### Enum `L7Error`:
```python
class L7Error(Enum):
    """
    Define different types of errors that are relevant to the L7 Channel protocol
    """
    NETWORK_CONNECTIVITY_ERROR = "network_connectivity_error"
    MESSAGE_FORMAT_ERROR = "message_format_error"
    PROTOCOL_STATE_ERROR = "protocol_state_error"
```

Defines different types of errors that are relevant to the L7 Channel protocol. The three possible error types are:
- `NETWORK_CONNECTIVITY_ERROR`: Indicates a network connectivity issue.
- `MESSAGE_FORMAT_ERROR`: Indicates an error in the message format.
- `PROTOCOL_STATE_ERROR`: Indicates a protocol state error.

#### Exception Classes
```python
class L7Exception(Error):
    """
    Define a base exception class that inherits from Python's built-in Exception class
    """
    pass


class NetworkConnectivityError(L7Exception):
    """
    Define a custom exception class for network connectivity errors
    """
    pass


class MessageFormatError(L7Exception):
    """
    Define a custom exception class for message format errors
    """
    pass


class ProtocolStateError(L7Exception):
    """
    Define a custom exception class for protocol state errors
    """
    pass
```

These are the custom exception classes for different error types that may occur during runtime. Each custom exception class inherits from a base exception class that inherits from Python's built-in Exception class.


## Examples and Use Cases

### Example: Generating Unique Peer ID
```python
id_generator = IdGenerator(123)
peer_id = id_generator.generate_peer_id()
print(peer_id) # 8539493046037011198743226338351525
```

### Example: Handling an Error
```python
try:
    # code block that may raise an error
except Exception as e:
    handle_error(L7Error.NETWORK_CONNECTIVITY_ERROR, str(e))
```

## Additional Notes
None.