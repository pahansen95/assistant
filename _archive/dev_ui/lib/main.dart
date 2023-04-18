import 'package:flutter/material.dart';
import 'src/assistant.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assistant Dev UI',
      theme: ThemeData.light(),
      darkTheme: ThemeData.dark(),
      home: const AssistantChatPage(title: 'Assistant Chat'),
    );
  }
}

