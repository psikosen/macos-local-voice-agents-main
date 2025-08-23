import 'package:flutter_test/flutter_test.dart';
import 'package:llama_bridge/llama_bridge.dart';

void main() {
  test('infer returns stream', () {
    final stream = LlamaBridge.infer('hello');
    expect(stream, isA<Stream<String>>());
  });
}
