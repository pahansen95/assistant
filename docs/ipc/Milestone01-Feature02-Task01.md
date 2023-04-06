# Milestone 1, Feature 2, Task 2.1

## Task Goals
Implement the `Peer` class with a unique 128-bit identifier using the utility module.

## Plan Context
This task is part of the implementation plan for a custom L7 application protocol called `Channel`. The implementation plan is divided into two milestones. Milestone 1 focuses on implementing the core components of the protocol, while milestone 2 implements basic security and message delivery.

This task is part of Feature 2, which is focused on implementing the `Peer` class. The `Peer` class is one end of the `Channel` and has a unique 128-bit identifier.

## Specification & Relevant Information
The `Peer` class is an implementation of a `Channel` and has a unique 128-bit identifier where the first 64 bits are the `Channel` ID. The `Peer` class provides the implementation to manage `Session` lifecycle, including handling all inbound and outbound network traffic. 

The implementation should utilize the utility module to generate a unique 128-bit identifier for each `Peer`. 

## Dependencies
This task has no dependencies on the outputs of other tasks. However, it is a prerequisite for Task 2.2, which involves implementing methods to manage Session lifecycle.
