# Channel Protocol Specification

We need a custom L7 application protocol. This protocol is called `Channel`. `Channel` provides peer to peer communication via a simplified Pub/Sub architecture. `Channels` map 1 to 1 between peers & provide 2 way communication via messages. Messages are JSON objects. Each message's payload is an encrypted binary blob encoded as a base64 string. 2 peers must first establish a sesssion on the channel to communicate application data.

`Channel` is an abstract idea that is implemented through a few key objects:
- `Peer`
- `Session`
- `Topic`
- `Message`

Generaly speaking, A `Channel` has 2 `Peers` that establish `Sessions` to communicate via `Messages` scoped to a `Topic`. Each `Channel` has a unique 64bit identifier. A `Peer` can be thought of as one end of the `Channel`. It establishes `Sessions` with the `Peer` on the other end. `Sessions` serve as logical paritions in the `Channel`. A `Peer` can establish multiple `Sessions` to multiplex usage of the `Channel`. `Sessions` themselves can be further multiplexed using multiple `Topics`. `Topic` Multiplexing is simpler than `Session` Multiplexing as a `Session` allocates a socket & binds/connects a to port while a `Topic` just allocates a new inbox/outbox Queue for the `Session`.

`Peers` are one end of the `Channel`. They have a unique 128bit identifier where the first 64bits is the `Channel's` ID. `Peers` provide the implementation to manage `Session` lifecycle. This includes handling all inbound & outbound network traffic.

`Sessions` are network partitions inside a `Channel` that exchange messages as network traffic. Each `session` has a 10 bit ID unique to that peer. To establish a `Session`, one `Peer` must act as a server listening for another peer to connect.

A Session has a distinct lifecycle. The possible states of the lifecycle are:

1. `OFFLINE`: There is no active communication session.
2. `HANDSHAKE`: Peers are coordinating the security handshake of a new communication session.
2. `SETUP`: Peers are coordinating the runtime initilaization of a new communication session.
3. `ONLINE`: Peers are communicating application data accross an active communication session.
4. `TEARDOWN`: Peers are coordinating the cleanup of the communication session

Within the context of a `Session` at least one `Topic` must be registered for `Peers` to begin conversing. `Topics` have a 22bit ID unique to that session. `Topics` represent logical partitions Both `Peers` must explicitly register the same `Topic`. By default both peers will auto-register to the `main` `Topic` (ID 0). This `Topic` can be used to coordinate other `Topics` or it can be used for all communication.

`Channel` `Messages` encapsulate metadata & payload. Metadata encodes information about the `channel`, `session`, `peer` & `message` itself. Payloads encode data dependent on the `Message` kind. These are the possible kinds:
- `JOIN_SESSION`: A `Message` associated with the setup of a session.
- `LEAVE_SESSION`: A `Message` associated with the teardown of a session.
- `TOPIC_REGISTER`: A `Message` associated with the Registration of a topic.
- `TOPIC_DEREGISTER`: A `Message` associated with the Deregistration of a topic
- `APPLICATION`: A `Message` that carries application data in it's payload; these are primary kinds of `messages`.
- `ACKNOWLEDGE`: A `Message` sent in response to any other `message` (other than `ERROR`) to indicate successful reciept of that `message`.
- `ERROR`: A `Message` sent in response to any other `message` to indicated some sort of error. The specific error details are encoded in this `message's` payload.

To secure `messages` & their data a few layers will be implemented:
- Peers will utilize Mutual TLS (mTLS) to encrypt data in transit & verify authentication through `Ed25519` key pairs.
- Peers will further encrypt payloads using a symmetric-key encryption scheme called ChaCha20Poly1305 (ie. the approach WireGuard takes)

`Messages` are delivered in order. Of the unique 128bit ID for the message, the last 64 bits will be a unique identifier for that message within the session & topic that. The first 10 bits will be the unique sesion ID. The next 22 bits will be the unique Topic ID. The last 32 bits will be the messages index in the conversation.

To ensure delivery, a Peer must send an `ACKNOWLEDGE` `Message` in response to any `Message` other than `ACKNOWLEDGE` & `ERROR`. If a `Peer` does not recieve an `ACKNOWLEDGE` `Message` in response within a configurable amount of time it will resend the `Message`. Once a `Peer` recieves an `ACKNOWLEDGE` `Message` it can consider the `Message` delivered.

Errors are broken into 2 categories:
  - `Delivery` Errors: Failure to deliver or recieve a `Message` to the other `Peer` within a configurable timeout.
  - `Runtime` Errors: Any other type of error not related to delivery of messages.

Handling of errors is simple:
  - `Delivery` Errors: Retransmit the `Message` up to a configurable number of retries before raising an error.
  - `Runtime` Errors: Categorize the error accordingly & raise an error immediately. Attempt to inform the other `Peer` of the error via an `ERROR` `Message`.