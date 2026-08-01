import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// 목업의 .back-btn.
class CircleBackButton extends StatelessWidget {
  const CircleBackButton({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 32,
      height: 32,
      child: Material(
        color: AppColors.greenLight,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: () => Navigator.of(context).maybePop(),
          child: const Icon(Icons.chevron_left, color: AppColors.greenDark, size: 20),
        ),
      ),
    );
  }
}
