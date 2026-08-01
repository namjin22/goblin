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

  testWidgets('작은 폰 화면에서도 홈 탭 3개가 잘리지 않는다', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({'is_paired': true, 'user_name': '테스트'});

    // 실제 기기 중 작은 축에 속하는 화면(iPhone SE급) 기준으로 검증한다.
    // 데스크톱 테스트 창(430x1000)보다 훨씬 짧아서, 스크롤 처리가 빠지면
    // 여기서 RenderFlex 오버플로가 먼저 드러난다.
    tester.view.physicalSize = const Size(375, 667);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const NongkkaebiApp());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);

    for (final label in ['직접 하기', '성장 과정', '지금 상태']) {
      await tester.tap(find.text(label));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: '$label 탭에서 오버플로 발생');
    }
  });
}
