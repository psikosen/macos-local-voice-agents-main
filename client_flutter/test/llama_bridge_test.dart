import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:llama_bridge/llama_bridge.dart';

void main() {
  setUp(() {
    LlamaBridge.resetTestingOverrides();
  });

  test('infer returns stream', () {
    final stream = LlamaBridge.infer('hello');
    expect(stream, isA<Stream<String>>());
  });

  test('streams remote tokens when local model unavailable', () async {
    const remoteUrl = 'https://example.com/infer';
    final client = _StreamingClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.toString(), remoteUrl);
      final tokens = ['tok1', 'tok2', 'tok3'];
      final payload = Stream<List<int>>.fromIterable(
        tokens.map((token) => utf8.encode('$token\n')),
      );
      return http.StreamedResponse(payload, 200);
    });

    LlamaBridge.configureRemoteForTesting(
      useRemote: true,
      remoteUrl: Uri.parse(remoteUrl),
    );
    LlamaBridge.setHttpClientFactory(() => client);

    final results = await LlamaBridge.infer('hello world').toList();
    expect(results, ['tok1', 'tok2', 'tok3']);
  });

  test('surfaces remote HTTP failures as errors', () async {
    const remoteUrl = 'https://example.com/infer';
    final client = _StreamingClient((_) async {
      final empty = Stream<List<int>>.empty();
      return http.StreamedResponse(empty, 503, reasonPhrase: 'unavailable');
    });

    LlamaBridge.configureRemoteForTesting(
      useRemote: true,
      remoteUrl: Uri.parse(remoteUrl),
    );
    LlamaBridge.setHttpClientFactory(() => client);

    final stream = LlamaBridge.infer('prompt');
    await expectLater(
      stream,
      emitsError(
        isA<LlamaBridgeRemoteException>().having((e) => e.statusCode, 'statusCode', 503),
      ),
    );
  });
}

class _StreamingClient extends http.BaseClient {
  _StreamingClient(this._handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest request) _handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) => _handler(request);
}
