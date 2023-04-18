import 'package:dev_ui/src/chat/editor.dart';
import 'package:flutter/material.dart';
import 'chat/thread.dart';
import 'chat/editor.dart';
import 'chat/transcript.dart';

/// The Assistant Chat Page
/// This is a Centered Row with 2 Columns
/// The left column is the sidebar that contains the list of chat threads & the active chat thread
/// The right column is the workspace that contains the active chat thread & the chat input
///
class AssistantChatPage extends StatelessWidget {
  // const AssistantChatPage({Key? key, required this.title}) : super(key: key);
  const AssistantChatPage({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        body: Center(
      child: Row(children: const <Widget>[
        Expanded(
          flex: 2,
          child: AssistantSidebar(),
        ),
        Expanded(
          flex: 8,
          child: AssistantWorkspace(),
        ),
      ]),
    ));
  }
}

/// The Sidebar of the Assistant Chat Page
///
/// The Sidebar is a column with 2 rows.
/// The Top Column is the active chat thread
/// The Bottom Column is the remaining list of chat threads sorte by last message timestamp
///
class AssistantSidebar extends StatelessWidget {
  const AssistantSidebar({super.key, this.cardAspectRatio = 100 / 25});

  final double cardAspectRatio;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints.expand(),
      child: Column(children: <Widget>[
        Column(
          children: <Widget>[
            ChatThreadCard(
              title: "Active Thread",
              description: "Active Thread Description",
              aspectRatio: cardAspectRatio,
            ),
            NewChatThread(aspectRatio: cardAspectRatio)
          ],
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 12.0),
            child: AvailableChatThreads(cardAspectRatio: cardAspectRatio),
          ),
        ),
      ]),
    );
  }
}

/// The Workspace of the Assistant Chat Page
///
/// The Workspace is a column with 2 rows.
/// The Top Row is the message transcript of active chat thread
/// The Bottom Row is the chat input
class AssistantWorkspace extends StatelessWidget {
  const AssistantWorkspace({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints.expand(),
      child: Column(children: <Widget>[
        const Expanded(
          flex: 7,
          child: ChatTranscript(
            messages: <String>[
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
              "Hello, I'm a chat transcript\nHello, I'm a chat transcript\n\nHello, I'm a chat transcript\n\n\nHello, I'm a chat transcript\n",
            ],
          ),
        ),
        Expanded(
            flex: 3,
            child: ChatMessageEditor(
              onSend: (String message) {
                print('onSend: $message');
              },
            )),
      ]),
    );
  }
}
