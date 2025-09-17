import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_client/main.dart';

void main() {
  testWidgets('Connect button appears', (tester) async {
    await tester.pumpWidget(const MyApp());
    expect(find.text('Connect'), findsOneWidget);
  });
}
