import 'package:flutter/material.dart';
import 'hero_card.dart';
import 'mascot.dart';
import 'speech_bubble.dart';

/// 말풍선 + 캐릭터 + 카드를 하나로 묶는다.
/// 카드가 먼저 그려지고 캐릭터가 그 위(z-order 앞쪽)에 [overlap]만큼 겹쳐 그려진다.
class HeroGroup extends StatelessWidget {
  const HeroGroup({
    super.key,
    required this.bubbleText,
    required this.pose,
    required this.card,
    this.mascotSize = 200,
    this.overlap = 42,
  });

  final String bubbleText;
  final MascotPose pose;
  final Widget card;
  final double mascotSize;
  final double overlap;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SpeechBubble(text: bubbleText),
        SizedBox(height: mascotSize - overlap),
        Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.topCenter,
          children: [
            card,
            Positioned(
              top: -(mascotSize - overlap),
              child: Mascot(pose: pose, size: mascotSize),
            ),
          ],
        ),
      ],
    );
  }
}
