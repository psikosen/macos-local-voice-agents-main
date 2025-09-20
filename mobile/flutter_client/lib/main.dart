import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
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
  final TextEditingController _offerUrlController = TextEditingController();

  RTCPeerConnection? _pc;
  MediaStream? _localStream;
  MediaStream? _remoteStream;
  String? _pcId;
  bool _isConnecting = false;
  bool _connected = false;
  String _status = 'Idle';
  RTCIceConnectionState? _iceConnectionState;

  @override
  void initState() {
    super.initState();
    _remoteRenderer.initialize();
    _offerUrlController.text = _defaultOfferUrl;
  }

  @override
  void dispose() {
    _offerUrlController.dispose();
    _remoteRenderer.dispose();
    _localStream?.dispose();
    _remoteStream?.dispose();
    _pc?.close();
    super.dispose();
  }

  String get _defaultOfferUrl {
    const defaultUrl = 'http://localhost:7860/api/offer';
    if (kIsWeb) {
      return defaultUrl;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:7860/api/offer';
      case TargetPlatform.iOS:
        return 'http://127.0.0.1:7860/api/offer';
      default:
        return defaultUrl;
    }
  }

  Future<void> _start() async {
    if (_isConnecting) {
      return;
    }
    await _stop(clearPcId: true);

    setState(() {
      _isConnecting = true;
      _status = 'Requesting microphone…';
      _connected = false;
      _iceConnectionState = null;
    });
    logEvent('_start', 'initializing peer connection');

    try {
      final pc = await createPeerConnection({
        'sdpSemantics': 'unified-plan',
        'iceServers': [
          {'urls': 'stun:stun.l.google.com:19302'}
        ],
      });
      _pc = pc;

      final stream = await navigator.mediaDevices.getUserMedia({
        'audio': {
          'echoCancellation': true,
          'noiseSuppression': true,
          'autoGainControl': true,
        },
      });
      _localStream = stream;
      for (final track in stream.getTracks()) {
        await pc.addTrack(track, stream);
      }
      _updateStatus('Waiting for remote audio…');

      pc.onIceConnectionState = (state) {
        setState(() {
          _iceConnectionState = state;
        });
        logEvent('onIceConnectionState', 'state=${state?.name}');
      };

      pc.onConnectionState = (state) {
        logEvent('onConnectionState', 'state=${state?.name}');
        if (state == RTCPeerConnectionState.RTCPeerConnectionStateFailed) {
          _handleError('Peer connection failed');
        }
      };

      pc.onIceCandidate = (candidate) {
        if (candidate == null) {
          return;
        }
        logEvent('onIceCandidate', 'candidate=${candidate.toMap()}');
      };

      pc.onTrack = (event) async {
        if (event.track.kind != 'audio') {
          return;
        }
        logEvent('onTrack', 'received remote audio track');
        MediaStream? remoteStream;
        if (event.streams.isNotEmpty) {
          remoteStream = event.streams.first;
        } else {
          remoteStream = await createLocalMediaStream('remote');
          remoteStream.addTrack(event.track);
        }
        _remoteStream?.dispose();
        _remoteStream = remoteStream;
        _remoteRenderer.srcObject = remoteStream;
        _updateStatus('Remote audio ready');
        _setSpeakerphone(true);
      };

      final offer = await pc.createOffer({
        'offerToReceiveAudio': 1,
        'offerToReceiveVideo': 0,
      });
      await pc.setLocalDescription(offer);
      await _waitForIceGatheringComplete(pc);

      final localDescription = pc.localDescription;
      if (localDescription == null) {
        throw StateError('Local description missing');
      }

      final offerUrlRaw = _offerUrlController.text.trim();
      if (offerUrlRaw.isEmpty) {
        throw ArgumentError('Offer URL cannot be empty');
      }
      final offerUri = Uri.parse(offerUrlRaw);
      if (!offerUri.hasScheme || offerUri.host.isEmpty) {
        throw FormatException('Offer URL must include scheme and host');
      }

      _updateStatus('Sending offer');
      final response = await http
          .post(
            offerUri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'sdp': localDescription.sdp,
              'type': localDescription.type,
              if (_pcId != null) 'pc_id': _pcId,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception(
          'Offer failed with status ${response.statusCode}: ${response.body}',
        );
      }

      final dynamic decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Unexpected answer payload');
      }
      final answerSdp = decoded['sdp'] as String?;
      final answerType = decoded['type'] as String?;
      final answerPcId = decoded['pc_id'] as String?;
      if (answerSdp == null || answerType == null || answerPcId == null) {
        throw const FormatException('Answer missing required fields');
      }

      _pcId = answerPcId;
      await pc.setRemoteDescription(
        RTCSessionDescription(answerSdp, answerType),
      );

      setState(() {
        _connected = true;
        _status = 'Connected';
      });
      logEvent('_start', 'connection established (pcId=$_pcId)');
    } catch (error, stackTrace) {
      await _stop(clearPcId: true);
      _handleError(error, stackTrace);
    } finally {
      if (mounted) {
        setState(() {
          _isConnecting = false;
        });
      }
    }
  }

  Future<void> _stop({bool clearPcId = true}) async {
    logEvent('_stop', 'closing connection (clearPcId=$clearPcId)');
    final pc = _pc;
    _pc = null;
    try {
      await pc?.close();
    } catch (error, stackTrace) {
      _handleError(error, stackTrace);
    }
    await _localStream?.dispose();
    _localStream = null;
    await _remoteStream?.dispose();
    _remoteStream = null;
    _remoteRenderer.srcObject = null;
    if (clearPcId) {
      _pcId = null;
    }
    _setSpeakerphone(false);
    if (mounted) {
      setState(() {
        _connected = false;
        _iceConnectionState = null;
        _status = 'Idle';
      });
    }
  }

  Future<void> _waitForIceGatheringComplete(RTCPeerConnection pc) async {
    if (pc.iceGatheringState ==
        RTCIceGatheringState.RTCIceGatheringStateComplete) {
      logEvent('_waitForIceGatheringComplete', 'already complete');
      return;
    }
    final completer = Completer<void>();
    pc.onIceGatheringState = (state) {
      logEvent('onIceGatheringState', 'state=${state.name}');
      if (state == RTCIceGatheringState.RTCIceGatheringStateComplete &&
          !completer.isCompleted) {
        completer.complete();
      }
    };
    await completer.future.timeout(
      const Duration(seconds: 5),
      onTimeout: () {
        if (!completer.isCompleted) {
          logEvent('_waitForIceGatheringComplete', 'timeout waiting for ICE');
          completer.complete();
        }
        return;
      },
    );
  }

  void _updateStatus(String status) {
    if (!mounted) {
      return;
    }
    setState(() {
      _status = status;
    });
    logEvent('_updateStatus', status);
  }

  void _handleError(Object error, [StackTrace? stackTrace]) {
    logEvent('_handleError', error.toString(), error: error);
    if (!mounted) {
      return;
    }
    setState(() {
      _connected = false;
      _isConnecting = false;
      _status = 'Error';
    });
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger != null) {
      messenger.showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
    if (stackTrace != null) {
      debugPrintStack(stackTrace: stackTrace, label: 'WebRTC error');
    }
  }

  void _setSpeakerphone(bool enabled) {
    unawaited(Helper.setSpeakerphoneOn(enabled).catchError((error, stackTrace) {
      logEvent('_setSpeakerphone', 'failed to set speakerphone: $error', error: error);
      if (stackTrace is StackTrace) {
        debugPrintStack(stackTrace: stackTrace, label: 'Speakerphone failure');
      }
    }));
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('Flutter WebRTC Client')),
        body: GestureDetector(
          onTap: () => FocusScope.of(context).unfocus(),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _offerUrlController,
                  decoration: const InputDecoration(
                    labelText: 'Offer endpoint',
                    hintText: 'http://10.0.2.2:7860/api/offer',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.url,
                  enabled: !_isConnecting && !_connected,
                ),
                const SizedBox(height: 16),
                if (_isConnecting) const LinearProgressIndicator(),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isConnecting
                            ? null
                            : _connected
                                ? () => _stop(clearPcId: true)
                                : _start,
                        icon: Icon(_connected ? Icons.stop : Icons.play_arrow),
                        label:
                            Text(_connected ? 'Disconnect' : 'Connect to /api/offer'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text('Status: $_status'),
                if (_iceConnectionState != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      'ICE state: ${_iceConnectionState!.name}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                const SizedBox(height: 24),
                const Text('Remote audio'),
                SizedBox(
                  height: 1,
                  width: 1,
                  child: RTCVideoView(_remoteRenderer),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

void logEvent(String function, String message, {Object? error}) {
  final log = {
    'filename': 'lib/main.dart',
    'timestamp': DateTime.now().toIso8601String(),
    'classname': '_MyAppState',
    'function': function,
    'system_section': 'webrtc',
    'line_num': 0,
    'error': error?.toString(),
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
