import 'package:flutter/material.dart';
import '../../widgets/bottom_nav_bar.dart';
import 'history_screen.dart';
import 'manual_screen.dart';
import 'status_screen.dart';

/// 명세서 5번 화면 구성 - 3화면으로 제한: [1]지금 상태 [2]직접 하기 [3]지난 기록
///
/// 하단 탭바를 화면마다 따로 두면 각 화면의 좌우 여백이 달라 탭 위치가
/// 화면 전환마다 미묘하게 움직여 보인다. 그래서 탭바는 여기 한 곳에서만
/// 만들고, 각 화면은 내용만 돌려준다.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  void _onNavChanged(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    final body = switch (_index) {
      1 => const ManualScreen(),
      2 => const HistoryScreen(),
      _ => const StatusScreen(),
    };

    return Scaffold(
      body: SafeArea(bottom: false, child: body),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 4, 24, 8),
          child: BottomNavBar(index: _index, onChanged: _onNavChanged, light: true),
        ),
      ),
    );
  }
}
