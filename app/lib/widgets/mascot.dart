import 'package:flutter/material.dart';

enum MascotPose { wave, cheer, wink, point }

/// 농깨비_앱_플로우.html의 .character-hero 이미지와 동일한 일러스트.
class Mascot extends StatelessWidget {
  const Mascot({super.key, this.pose = MascotPose.wave, this.size = 240});

  final MascotPose pose;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/images/mascot_${pose.name}.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
    );
  }
}
