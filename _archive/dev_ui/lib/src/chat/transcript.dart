import 'package:flutter/material.dart';

class ChatBubble extends StatelessWidget {
  const ChatBubble({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(child: Text(message));
  }
}

class ChatTranscript extends StatefulWidget {
  const ChatTranscript({super.key, required this.messages});

  final List<String> messages;

  @override
  State<ChatTranscript> createState() => _ChatTranscriptState();
}

class _ChatTranscriptState extends State<ChatTranscript> {
  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints.expand(),
      child: ListView.builder(
        itemCount: widget.messages.length,
        itemBuilder: (BuildContext context, int index) {
          return ChatBubble(message: widget.messages[index]);
        },
      ),
    );
  }
}
