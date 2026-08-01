import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../widgets/dots_indicator.dart';
import '../../widgets/hero_card.dart';
import '../../widgets/hero_group.dart';
import '../../widgets/mascot.dart';
import '../pairing/pairing_screen.dart';

class _OnboardingPage {
  const _OnboardingPage({
    required this.bubble,
    required this.pose,
    required this.title,
    required this.subtitle,
    required this.buttonLabel,
  });

  final String bubble;
  final MascotPose pose;
  final String title;
  final String subtitle;
  final String buttonLabel;
}

const _pages = [
  _OnboardingPage(
    bubble: '전국에 있는\n우리 할매 할배\n안녕하세요~',
    pose: MascotPose.cheer,
    title: '저는 농깨비예요!',
    subtitle: '앞으로 우리 밭을\n함께 돌봐드릴게요',
    buttonLabel: '다음',
  ),
  _OnboardingPage(
    bubble: '매일 잘 살펴보고\n있을게요',
    pose: MascotPose.point,
    title: '제가 매일 우리 밭을\n살펴보고 있어요',
    subtitle: '온도·햇빛·흙 상태를\n대신 확인해드려요',
    buttonLabel: '다음',
  ),
  _OnboardingPage(
    bubble: '설정 걱정은\n안 하셔도 돼요',
    pose: MascotPose.wink,
    title: '필요할 때만\n말씀드릴게요',
    subtitle: '어려운 설정 없이\n그냥 편하게 쓰시면 돼요',
    buttonLabel: '시작할게요',
  ),
];

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _next() {
    if (_page < _pages.length - 1) {
      _controller.nextPage(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    } else {
      Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => const PairingScreen()));
    }
  }

  void _skip() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const PairingScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _page == _pages.length - 1;
    return Scaffold(
      backgroundColor: const Color(0xFFF4F9F5),
      body: SafeArea(
        child: Stack(
          children: [
            if (!isLast)
              Positioned(
                top: 8,
                right: 20,
                child: GestureDetector(
                  onTap: _skip,
                  child: const Text(
                    '건너뛰기 →',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.sub,
                    ),
                  ),
                ),
              ),
            PageView.builder(
              controller: _controller,
              itemCount: _pages.length,
              onPageChanged: (i) => setState(() => _page = i),
              itemBuilder: (context, i) {
                final page = _pages[i];
                return LayoutBuilder(
                  builder: (context, constraints) => SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        minHeight: constraints.maxHeight,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          HeroGroup(
                            bubbleText: page.bubble,
                            pose: page.pose,
                            card: HeroCard(
                              child: Column(
                                children: [
                                  CardTitle(page.title),
                                  const SizedBox(height: 8),
                                  Text(
                                    page.subtitle,
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      fontSize: 14,
                                      color: AppColors.sub,
                                      height: 1.5,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  DotsIndicator(count: _pages.length, index: i),
                                  const SizedBox(height: 12),
                                  SizedBox(
                                    width: double.infinity,
                                    child: ElevatedButton(
                                      onPressed: _next,
                                      child: Text(page.buttonLabel),
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
              },
            ),
          ],
        ),
      ),
    );
  }
}
