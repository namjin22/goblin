import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

const _labels = ['지금 상태', '직접 하기', '지난 기록'];

/// 목업의 .bottomnav / .status-bottomnav — 화면 배경에 맞춰 밝은/어두운 버전을 고른다.
class BottomNavBar extends StatelessWidget {
  const BottomNavBar({super.key, required this.index, required this.onChanged, this.light = false});

  final int index;
  final ValueChanged<int> onChanged;

  /// true면 밝은(흰) 배경 화면에서 쓰는 진한 글자 버전, false면 상태색 배경 위 흰 글자 버전.
  final bool light;

  @override
  Widget build(BuildContext context) {
    final borderColor = light ? AppColors.line : Colors.white.withValues(alpha: 0.3);
    final inactive = light ? AppColors.sub : Colors.white.withValues(alpha: 0.7);
    final active = light ? AppColors.greenDark : Colors.white;

    return Container(
      padding: const EdgeInsets.only(top: 10),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: borderColor))),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: List.generate(_labels.length, (i) {
          final selected = i == index;
          return GestureDetector(
            onTap: () => onChanged(i),
            behavior: HitTestBehavior.opaque,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
              child: Text(
                _labels[i],
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  color: selected ? active : inactive,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
