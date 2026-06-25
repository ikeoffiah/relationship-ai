import 'package:flutter/material.dart';

class RelayInboxScreen extends StatelessWidget {
  const RelayInboxScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Relay Inbox')),
      body: const Center(child: Text('Inbox messages will be displayed here.')),
    );
  }
}
