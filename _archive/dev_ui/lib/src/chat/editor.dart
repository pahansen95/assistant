import 'package:flutter/material.dart';
import 'package:flutter_quill/flutter_quill.dart' as quill;

class ChatMessageEditor extends StatefulWidget {
  const ChatMessageEditor({super.key, required this.onSend});

  final Function(String) onSend;

  @override
  State<ChatMessageEditor> createState() => _ChatMessageEditorState();
}

class _ChatMessageEditorState extends State<ChatMessageEditor> {
  final TextEditingController _textController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints.expand(),
      child: Row(
        children: <Widget>[
          Expanded(
              child: MouseRegion(
            cursor: SystemMouseCursors.text,
            child: quill.QuillEditor(
              controller: quill.QuillController.basic(),
              scrollController: ScrollController(),
              scrollable: true,
              autoFocus: true,
              focusNode: FocusNode(),
              expands: true,
              readOnly: false,
              padding: const EdgeInsets.all(12),
              showCursor: true,
              placeholder: 'Type a message',
              //onLaunchUrl: (String url) => print('launch $url'),
              //onImagePickCallback: _pickImage,
            ),
          )),
          IconButton(
            icon: const Icon(Icons.send),
            onPressed: () {
              widget.onSend(_textController.text);
              _textController.clear();
            },
          ),
        ],
      ),
    );
  }
}
