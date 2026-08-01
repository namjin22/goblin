import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:nongkkaebi_app/main.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('온보딩 첫 화면이 뜬다', (WidgetTester tester) async {
    await tester.pumpWidget(const NongkkaebiApp());
    await tester.pumpAndSettle();

    expect(find.text('다음'), findsOneWidget);
  });
}
