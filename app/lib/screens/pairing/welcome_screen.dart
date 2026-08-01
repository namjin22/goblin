import 'package:flutter/material.dart';
import '../../widgets/hero_card.dart';
import '../../widgets/hero_group.dart';
import '../../widgets/mascot.dart';
import '../../widgets/scrollable_fill.dart';
import '../home/home_shell.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key, required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F9F5),
      body: SafeArea(
        child: ScrollableFill(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              HeroGroup(
                bubbleText: '축하해요!\n이제 저랑 함께\n시작해요',
                pose: MascotPose.cheer,
                card: HeroCard(
                  child: Column(
                    children: [
                      CardTitle('환영해요,\n$name님'),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.of(context).pushAndRemoveUntil(
                              MaterialPageRoute(builder: (_) => const HomeShell()),
                              (route) => false,
                            );
                          },
                          child: const Text('대시보드로 가기'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
