import 'package:flutter/material.dart';
import '../../services/farm_api.dart';
import '../../theme/app_colors.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../widgets/top_toast.dart';

/// 화면[2] 직접 하기 - 조작(Operation)은 언제든 할 수 있다: 버튼 2개만.
/// server.py는 vent_toggle(열림<->닫힘) / water 명령만 받는다.
class ManualScreen extends StatefulWidget {
  const ManualScreen({super.key, required this.navIndex, required this.onNavChanged});

  final int navIndex;
  final ValueChanged<int> onNavChanged;

  @override
  State<ManualScreen> createState() => _ManualScreenState();
}

class _ManualScreenState extends State<ManualScreen> {
  String? _running;

  Future<void> _run(String label, String command, String fallbackMessage) async {
    setState(() => _running = label);
    final result = await FarmApi.sendCommand(command);
    if (!mounted) return;
    setState(() => _running = null);

    if (result == null) {
      // 서버(control.py)에 닿지 못함 — 오프라인 개발 중 시뮬레이션 안내.
      showTopToast(context, fallbackMessage);
    } else if (result.ok) {
      showTopToast(context, fallbackMessage);
    } else {
      showTopToast(context, result.error ?? '지금은 할 수 없어요');
    }
  }

  @override
  Widget build(BuildContext context) {
    final busy = _running != null;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            children: [
              const SizedBox(height: 12),
              const Text('직접 하기', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.ink)),
              const SizedBox(height: 8),
              if (busy)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Text(
                    '$_running 중이에요...',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.greenDark),
                  ),
                ),
              const Spacer(),
              _ActionButton(
                emoji: '🪟',
                label: '창문 열기/닫기',
                enabled: !busy,
                onTap: () => _run('창문을 움직이는', 'vent_toggle', '창문을 움직였어요'),
              ),
              const SizedBox(height: 20),
              _ActionButton(
                emoji: '💧',
                label: '물 주기',
                enabled: !busy,
                onTap: () => _run('물을 주는', 'water', '물을 주었어요'),
              ),
              const Spacer(),
              BottomNavBar(index: widget.navIndex, onChanged: widget.onNavChanged, light: true),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({required this.emoji, required this.label, required this.enabled, required this.onTap});

  final String emoji;
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 140,
      child: ElevatedButton(
        onPressed: enabled ? onTap : null,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.greenLight,
          foregroundColor: AppColors.ink,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 40)),
            const SizedBox(height: 10),
            Text(label, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }
}
