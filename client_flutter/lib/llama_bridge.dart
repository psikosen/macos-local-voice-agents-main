import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:meta/meta.dart';

void _log(
  String classname,
  String function,
  String message, {
  bool isError = false,
  String method = 'NONE',
}) {
  final log = {
    'filename': 'lib/llama_bridge.dart',
    'timestamp': DateTime.now().toIso8601String(),
    'classname': classname,
    'function': function,
    'system_section': 'plugin',
    'line_num': 0,
    'error': isError,
    'db_phase': 'none',
    'method': method,
    'message': message,
  };
  print(jsonEncode(log));
  print('[Continuous skepticism (Sherlock Protocol)] $message');
}

class LlamaBridge {
  LlamaBridge._();
  static const MethodChannel _channel = MethodChannel('llama_bridge/methods');
  static const EventChannel _events = EventChannel('llama_bridge/tokens');

  static bool _useRemote = false;
  static Uri? _remoteUrl;
  static http.Client Function() _httpClientFactory = http.Client.new;

  static Future<void> initialize({required String modelAsset, Uri? downloadUrl, Uri? remoteUrl}) async {
    _remoteUrl = remoteUrl;
    final bool? localReady = await _channel.invokeMethod('initialize', {
      'model': modelAsset,
      'downloadUrl': downloadUrl?.toString(),
    });
    _useRemote = !(localReady ?? true);
    _log('LlamaBridge', 'initialize', 'useRemote=$_useRemote remoteUrl=${_remoteUrl?.toString() ?? 'none'}');
  }

  static Stream<String> infer(String prompt) {
    if (_useRemote && _remoteUrl != null) {
      return _inferRemote(prompt);
    }
    final stream = _events.receiveBroadcastStream({'prompt': prompt}).cast<String>();
    _channel.invokeMethod('startInference', {'prompt': prompt});
    return stream;
  }

  static Stream<String> _inferRemote(String prompt) {
    final controller = StreamController<String>();
    late final http.Client client;
    try {
      client = _httpClientFactory();
    } catch (err, stack) {
      final error = LlamaBridgeRemoteException(
        'Failed to create HTTP client: $err',
        cause: err,
        stackTrace: stack,
      );
      _log('LlamaBridge', 'inferRemote', error.message, isError: true, method: 'POST');
      controller.addError(error);
      controller.close();
      return controller.stream;
    }

    var clientClosed = false;
    void closeClient() {
      if (!clientClosed) {
        client.close();
        clientClosed = true;
      }
    }

    controller.onCancel = closeClient;

    () async {
      try {
        final request = http.Request('POST', _remoteUrl!);
        request.headers['content-type'] = 'text/plain; charset=utf-8';
        request.body = prompt;
        _log('LlamaBridge', 'inferRemote', 'dispatching remote inference request', method: 'POST');
        final response = await client.send(request);
        if (response.statusCode < 200 || response.statusCode >= 300) {
          final error = LlamaBridgeRemoteException(
            'Remote inference failed with status ${response.statusCode}',
            statusCode: response.statusCode,
            reason: response.reasonPhrase,
          );
          _log('LlamaBridge', 'inferRemote', error.message, isError: true, method: 'POST');
          controller.addError(error);
          await controller.close();
          return;
        }

        await response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .forEach(controller.add);
        await controller.close();
      } catch (err, stack) {
        final error = LlamaBridgeRemoteException(
          'Remote inference request threw: $err',
          cause: err,
          stackTrace: stack,
        );
        _log('LlamaBridge', 'inferRemote', error.message, isError: true, method: 'POST');
        controller.addError(error);
        await controller.close();
      } finally {
        closeClient();
      }
    }();

    return controller.stream;
  }

  @visibleForTesting
  static void setHttpClientFactory(http.Client Function() factory) {
    _httpClientFactory = factory;
  }

  @visibleForTesting
  static void configureRemoteForTesting({required bool useRemote, Uri? remoteUrl}) {
    _useRemote = useRemote;
    _remoteUrl = remoteUrl;
  }

  @visibleForTesting
  static void resetTestingOverrides() {
    _httpClientFactory = http.Client.new;
    _useRemote = false;
    _remoteUrl = null;
  }
}

class LlamaBridgeRemoteException implements Exception {
  LlamaBridgeRemoteException(
    this.message, {
    this.cause,
    this.statusCode,
    this.reason,
    this.stackTrace,
  });

  final String message;
  final Object? cause;
  final int? statusCode;
  final String? reason;
  final StackTrace? stackTrace;

  @override
  String toString() {
    final buffer = StringBuffer('LlamaBridgeRemoteException(message: $message');
    if (statusCode != null) {
      buffer.write(', statusCode: $statusCode');
    }
    if (reason != null) {
      buffer.write(', reason: $reason');
    }
    if (cause != null) {
      buffer.write(', cause: $cause');
    }
    buffer.write(')');
    return buffer.toString();
  }
}
