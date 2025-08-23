import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

void _log(String classname, String function, String message) {
  final log = {
    'filename': 'lib/llama_bridge.dart',
    'timestamp': DateTime.now().toIso8601String(),
    'classname': classname,
    'function': function,
    'system_section': 'plugin',
    'line_num': 0,
    'error': 'false',
    'db_phase': 'none',
    'method': 'NONE',
    'message': message,
  };
  print(jsonEncode(log));
  print('The 17 Commandments of Quality Code');
}

class LlamaBridge {
  LlamaBridge._();
  static const MethodChannel _channel = MethodChannel('llama_bridge/methods');
  static const EventChannel _events = EventChannel('llama_bridge/tokens');

  static bool _useRemote = false;
  static Uri? _remoteUrl;

  static Future<void> initialize({required String modelAsset, Uri? downloadUrl, Uri? remoteUrl}) async {
    _remoteUrl = remoteUrl;
    final bool? localReady = await _channel.invokeMethod('initialize', {
      'model': modelAsset,
      'downloadUrl': downloadUrl?.toString(),
    });
    _useRemote = !(localReady ?? true);
    _log('LlamaBridge', 'initialize', 'useRemote=$_useRemote');
  }

  static Stream<String> infer(String prompt) {
    if (_useRemote && _remoteUrl != null) {
      final controller = StreamController<String>();
      final req = http.Request('POST', _remoteUrl!);
      req.body = prompt;
      http.Client().send(req).then((resp) {
        resp.stream.transform(utf8.decoder).transform(const LineSplitter()).listen((line) {
          controller.add(line);
        }, onError: controller.addError, onDone: controller.close);
      });
      return controller.stream;
    }
    final stream = _events.receiveBroadcastStream({'prompt': prompt}).cast<String>();
    _channel.invokeMethod('startInference', {'prompt': prompt});
    return stream;
  }
}
