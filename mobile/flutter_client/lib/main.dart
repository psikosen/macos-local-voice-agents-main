import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final RTCVideoRenderer _remoteRenderer = RTCVideoRenderer();
  RTCPeerConnection? _pc;
  MediaStream? _localStream;
  String? _pcId;

  @override
  void initState() {
    super.initState();
    _remoteRenderer.initialize();
  }

  @override
  void dispose() {
    _pc?.close();
    _remoteRenderer.dispose();
    _localStream?.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    logEvent('_start', 'creating peer connection');
    final pc = await createPeerConnection({
      'iceServers': [
        {'urls': 'stun:stun.l.google.com:19302'}
      ]
    });
    final stream = await navigator.mediaDevices.getUserMedia({'audio': true});
    for (var track in stream.getTracks()) {
      pc.addTrack(track, stream);
    }
    pc.onTrack = (event) {
      if (event.streams.isNotEmpty) {
        _remoteRenderer.srcObject = event.streams[0];
      }
    };

    _pc = pc;
    _localStream = stream;

    final offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await _waitForIceGatheringComplete(pc);

    final localDesc = await pc.getLocalDescription();
    final response = await http.post(
      Uri.parse('http://localhost:7860/api/offer'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'sdp': localDesc?.sdp,
        'type': localDesc?.type,
        if (_pcId != null) 'pc_id': _pcId,
      }),
    );

    final answer = jsonDecode(response.body) as Map<String, dynamic>;
    _pcId = answer['pc_id'] as String?;
    await pc.setRemoteDescription(
      RTCSessionDescription(
        answer['sdp'] as String,
        answer['type'] as String,
      ),
    );
    logEvent('_start', 'connection established');
  }

  Future<void> _waitForIceGatheringComplete(RTCPeerConnection pc) async {
    if (pc.iceGatheringState ==
        RTCIceGatheringState.RTCIceGatheringStateComplete) {
      return;
    }
    final completer = Completer<void>();
    pc.onIceGatheringState = (state) {
      if (state == RTCIceGatheringState.RTCIceGatheringStateComplete) {
        completer.complete();
      }
    };
    return completer.future;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('Flutter WebRTC')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('Tap to connect to /api/offer'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _start,
                child: const Text('Connect'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

void logEvent(String function, String message) {
  final log = {
    'filename': 'lib/main.dart',
    'timestamp': DateTime.now().toIso8601String(),
    'classname': '_MyAppState',
    'function': function,
    'system_section': 'webrtc',
    'line_num': 0,
    'error': null,
    'db_phase': 'none',
    'method': 'NONE',
    'message': message,
  };
  print(jsonEncode(log));
  print(_commandments);
}

const String _commandments = '''The 17 Commandments of Quality Code
1. Thou shalt write code for humans first, machines second.
2. Thou shalt choose clarity over cleverness.
3. Thou shalt document the why, not just the what.
4. Thou shalt be ruthlessly consistent.
5. Thou shalt not trust thy code; thou shalt test it relentlessly.
6. Thou shalt have thy code reviewed by another.
7. Thou shalt keep thy functions and modules small and focused.
8. Thou shalt anticipate failure and handle errors with grace.
9. Thou shalt limit the reach of thy data.
10. Thou shalt leave the code cleaner than thou found it.
11. Thou shalt name things with purpose and clarity.
12. Thou shalt favor simple control flow.
13. Thou shalt automate what can be automated.
14. Thou shalt be deliberate and sparse with thy dependencies.
15. Thou shalt not solve problems that do not exist.
16. Thou shalt treat all external data as hostile.
17. Thou shalt understand the cost of thine operations.''';
