# Channel Protocol PoC Implementation Plan

## Milestone 1: Implement Core Components

### Feature 1: Core Modules

- [x] Task 1.1: Implement a utility module for generating unique identifiers (Peers, Sessions, Topics)
- [x] Task 1.2: Implement a basic error handling module for runtime errors

### Feature 2: Peer

- [x] Task 2.1: Implement Peer with a unique 128-bit identifier using the utility module
- [ ] Task 2.2: Implement methods to manage Session lifecycle
- [ ] Task 2.3: Handle inbound and outbound network traffic

### Feature 3: Session

- [ ] Task 3.1: Implement Session with a unique 10-bit ID using the utility module
- [ ] Task 3.2: Implement Session states (OFFLINE, HANDSHAKE, SETUP, ONLINE, TEARDOWN)
- [ ] Task 3.3: Implement Session establishment and teardown logic

### Feature 4: Topic

- [ ] Task 4.1: Implement Topic with a unique 22-bit ID using the utility module
- [ ] Task 4.2: Implement Topic registration and deregistration

### Feature 5: Message

- [ ] Task 5.1: Implement Message with metadata and payload
- [ ] Task 5.2: Implement the APPLICATION message kind for basic communication
- [ ] Task 5.3: Implement Message unique 128-bit ID generation using the utility module

## Milestone 2: Implement Basic Security and Message Delivery

### Feature 6: Basic Security

- [ ] Task 6.1: Implement basic TLS for secure communication between peers

### Feature 7: Basic Message Delivery

- [ ] Task 7.1: Implement a simple message delivery mechanism without ordered delivery or retransmission

# Channel Protocol Reference Implementation

The reference implementation for `Channel` will be in Python. We will use ZeroMQ to abstract the networking implementation. We will leverage Python's asyncio for higher performant code.
