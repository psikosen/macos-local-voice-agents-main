import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_client/main.dart';

void main() {
  testWidgets('renders connect button', (tester) async {
    await tester.pumpWidget(const MyApp());
    expect(find.byType(FloatingActionButton), findsOneWidget);
  });
}
