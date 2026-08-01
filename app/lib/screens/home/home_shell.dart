import 'package:flutter/material.dart';
import 'history_screen.dart';
import 'manual_screen.dart';
import 'status_screen.dart';

/// 명세서 5번 화면 구성 - 3화면으로 제한: [1]지금 상태 [2]직접 하기 [3]지난 기록
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
    switch (_index) {
      case 1:
        return ManualScreen(navIndex: _index, onNavChanged: _onNavChanged);
      case 2:
        return HistoryScreen(navIndex: _index, onNavChanged: _onNavChanged);
      default:
        return StatusScreen(navIndex: _index, onNavChanged: _onNavChanged);
    }
  }
}
