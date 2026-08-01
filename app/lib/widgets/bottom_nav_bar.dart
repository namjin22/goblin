import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

const _labels = ['지금 상태', '직접 하기', '성장 과정'];

/// 목업의 .bottomnav / .status-bottomnav — 화면 배경에 맞춰 밝은/어두운 버전을 고른다.
/// 선택 여부를 글자 굵기로 표시하면 글자 폭이 바뀌어 탭이 떨려 보이므로,
/// 굵기는 항상 고정하고 선택된 탭 뒤에만 고정 크기 배경 박스를 둔다.
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
    final activeBg = light ? AppColors.greenLight : Colors.white.withValues(alpha: 0.18);

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
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 14),
              decoration: BoxDecoration(
                color: selected ? activeBg : Colors.transparent,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                _labels[i],
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
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
