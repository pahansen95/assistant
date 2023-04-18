import 'package:flutter/material.dart';

/* --- Core Chat Thread Widget & State --- */

/// The Base Chat Thread Widget
///
/// Can be used to create a new chat thread or to display an existing chat thread
class ChatThreadCard extends StatelessWidget {
  const ChatThreadCard(
      {super.key,
      required this.title,
      required this.description,
      required this.aspectRatio});

  final String title;
  final String description;
  final double aspectRatio;

  @override
  Widget build(BuildContext context) {
    return Center(
        child: AspectRatio(
      aspectRatio: aspectRatio,
      child: Card(
        child: Column(
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Text(
              description,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    ));
  }
}

class _ChatThreadState extends State<ChatThread> {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          Text(
            widget.title,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(
            widget.description,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}

/// A Chat Thread Card for Existing Chats
///
/// Existing Chat Threads have at least one message
class ChatThread extends StatefulWidget {
  const ChatThread({super.key, required this.title, required this.description});

  final String title;
  final String description;

  @override
  State<ChatThread> createState() => _ChatThreadState();
}

/// A New Chat Thread Card for Creating New Chats
///
/// Selecting this card will create a new chat thread
/// A new chat thread isn't saved until at least one message has been submitted
class NewChatThread extends ChatThreadCard {
  const NewChatThread({super.key, required super.aspectRatio})
      : super(
            title: 'New Chat Thread', description: 'Create a new chat thread');
}

/* --- Sorted List of Available Chat Threads --- */

/// The list of available chat threads
///
/// A List of threads sorted by last message timestamp
/// A thread is a Card with a title and a description
/// Selecting a thread card in the UI will make it the new active thread
class AvailableChatThreads extends StatelessWidget {
  const AvailableChatThreads({super.key, required this.cardAspectRatio});

  final double cardAspectRatio;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(itemBuilder: (context, index) {
      return ChatThreadCard(
        aspectRatio: cardAspectRatio,
        title: 'Chat Thread $index',
        description: 'This is a description of Chat Thread $index',
      );
    });
  }
}
