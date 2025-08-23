import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'webrtc_client.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(home: HomePage());
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final List<String> _messages = [];
  WebRTCClient? _client;
  bool _connected = false;

  Future<void> _toggleConnection() async {
    if (_connected) {
      await _client?.dispose();
      setState(() {
        _connected = false;
      });
    } else {
      final client = WebRTCClient(
        serverUrl: 'http://localhost:7860',
        onMessage: (msg) {
          setState(() {
            _messages.add(msg);
          });
        },
      );
      await client.connect();
      setState(() {
        _client = client;
        _connected = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Voice Client')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) =>
                  ListTile(title: Text(_messages[index])),
            ),
          ),
          if (_client != null)
            SizedBox(
              width: 0,
              height: 0,
              child: RTCVideoView(_client!.remoteRenderer),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _toggleConnection,
        child: Icon(_connected ? Icons.stop : Icons.play_arrow),
      ),
    );
  }
}
