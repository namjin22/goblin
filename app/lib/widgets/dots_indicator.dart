import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// 목업의 .dots — 온보딩 진행 점.
class DotsIndicator extends StatelessWidget {
  const DotsIndicator({super.key, required this.count, required this.index});

  final int count;
  final int index;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(count, (i) {
        final on = i == index;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.symmetric(horizontal: 3),
          width: on ? 20 : 8,
          height: 8,
          decoration: BoxDecoration(
            color: on ? AppColors.green : const Color(0xFFDDE3DC),
            borderRadius: BorderRadius.circular(4),
          ),
        );
      }),
    );
  }
}
