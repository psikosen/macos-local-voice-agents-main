import 'dart:convert';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

typedef MessageHandler = void Function(String);

class WebRTCClient {
  WebRTCClient({required this.serverUrl, required this.onMessage});

  final String serverUrl;
  final MessageHandler onMessage;

  RTCPeerConnection? _pc;
  MediaStream? _localStream;
  final RTCVideoRenderer _remoteRenderer = RTCVideoRenderer();
  RTCDataChannel? _dataChannel;

  Future<void> connect() async {
    await _remoteRenderer.initialize();
    logEvent('connect', 'initializing local media');
    final mediaConstraints = {'audio': true, 'video': false};
    _localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
    final config = {
      'iceServers': [
        {'urls': 'stun:stun.l.google.com:19302'},
      ],
    };
    _pc = await createPeerConnection(config);
    _pc!.addStream(_localStream!);
    _pc!.onTrack = (RTCTrackEvent event) {
      if (event.track.kind == 'audio') {
        _remoteRenderer.srcObject = event.streams[0];
      }
    };
    _pc!.onDataChannel = (RTCDataChannel channel) {
      _dataChannel = channel;
      _setupDataChannel(channel);
    };
    _dataChannel = await _pc!.createDataChannel(
      'oai.events',
      RTCDataChannelInit()..ordered = true,
    );
    _setupDataChannel(_dataChannel!);

    final offer = await _pc!.createOffer();
    await _pc!.setLocalDescription(offer);
    logEvent('connect', 'sending offer', method: 'POST');
    final response = await http.post(
      Uri.parse('$serverUrl/api/offer'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'sdp': offer.sdp, 'type': offer.type}),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _pc!.setRemoteDescription(
        RTCSessionDescription(data['sdp'], data['type']),
      );
      logEvent('connect', 'connection established');
    } else {
      logEvent(
        'connect',
        'failed: ${response.statusCode}',
        error: 'signaling error',
        method: 'POST',
      );
    }
  }

  void _setupDataChannel(RTCDataChannel channel) {
    channel.onMessage = (RTCDataChannelMessage message) {
      if (message.isBinary) return;
      try {
        final data = jsonDecode(message.text);
        final text = data['text'] ?? message.text;
        onMessage('${data['type'] ?? 'message'}: $text');
      } catch (_) {
        onMessage(message.text);
      }
    };
  }

  Future<void> dispose() async {
    await _dataChannel?.close();
    await _pc?.close();
    await _localStream?.dispose();
    await _remoteRenderer.dispose();
  }

  RTCVideoRenderer get remoteRenderer => _remoteRenderer;
}

void logEvent(
  String function,
  String message, {
  String method = 'NONE',
  String? error,
}) {
  final logMap = {
    'filename': 'webrtc_client.dart',
    'timestamp': DateTime.now().toIso8601String(),
    'classname': 'WebRTCClient',
    'function': function,
    'system_section': 'webrtc',
    'line_num': 0,
    'error': error,
    'db_phase': 'none',
    'method': method,
    'message': message,
  };
  debugPrint(jsonEncode(logMap));
  debugPrint('[WebRTCClient::$function] $message');
}
