import 'package:flutter/material.dart';
import 'screens/home/home_shell.dart';
import 'screens/onboarding/onboarding_screen.dart';
import 'services/pairing_service.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const NongkkaebiApp());
}

class NongkkaebiApp extends StatelessWidget {
  const NongkkaebiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '농깨비',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: const _StartupGate(),
    );
  }
}

/// 페어링 여부에 따라 온보딩(최초 1회) 또는 메인 화면으로 분기.
class _StartupGate extends StatelessWidget {
  const _StartupGate();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: PairingService.isPaired(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return snapshot.data! ? const HomeShell() : const OnboardingScreen();
      },
    );
  }
}
