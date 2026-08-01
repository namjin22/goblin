import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// 목업의 .card-duo — 흰 둥근 카드 표면. 캐릭터와의 겹침은 [HeroGroup]이 담당한다.
class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(28, 68, 28, 32),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(color: AppColors.ink.withValues(alpha: 0.10), blurRadius: 20, offset: const Offset(0, 8)),
        ],
      ),
      child: child,
    );
  }
}

/// 목업의 .title.card-title — 1줄/2줄 제목 모두 동일한 높이를 차지.
class CardTitle extends StatelessWidget {
  const CardTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 70),
      alignment: Alignment.center,
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w700, color: AppColors.ink, height: 1.3),
      ),
    );
  }
}
