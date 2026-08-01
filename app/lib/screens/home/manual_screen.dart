import 'package:flutter/material.dart';
import '../../services/farm_api.dart';
import '../../theme/app_colors.dart';
import '../../widgets/top_toast.dart';

/// 화면[2] 직접 하기 - 조작(Operation)은 언제든 할 수 있다.
/// server.py는 vent_open / vent_close / water 명령을 받는다.
class ManualScreen extends StatefulWidget {
  const ManualScreen({super.key});

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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('직접 하기', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.ink)),
          const SizedBox(height: 8),
          if (busy)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text(
                '$_running 중이에요...',
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.greenDark),
              ),
            ),
          const SizedBox(height: 32),
          Row(
            children: [
              Expanded(
                child: _ActionButton(
                  emoji: '🪟',
                  label: '온실 열기',
                  enabled: !busy,
                  onTap: () => _run('온실을 여는', 'vent_open', '온실을 열었어요'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _ActionButton(
                  emoji: '🚪',
                  label: '온실 닫기',
                  enabled: !busy,
                  onTap: () => _run('온실을 닫는', 'vent_close', '온실을 닫았어요'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _ActionButton(
                  emoji: '💧',
                  label: '물 주기',
                  enabled: !busy,
                  onTap: () => _run('물을 주는', 'water', '물을 주었어요'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _ActionButton(
                  emoji: '💡',
                  label: '불 켜기',
                  enabled: !busy,
                  onTap: () => _run('불을 켜는', 'light_toggle', '불을 켰어요'),
                ),
              ),
            ],
          ),
        ],
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
          padding: EdgeInsets.zero,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 38)),
            const SizedBox(height: 10),
            Text(label, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }
}
