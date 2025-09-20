import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_client/main.dart';

void main() {
  testWidgets('Connect flow UI renders', (tester) async {
    await tester.pumpWidget(const MyApp());
    expect(find.text('Offer endpoint'), findsOneWidget);
    expect(find.text('Connect to /api/offer'), findsOneWidget);
  });
}
