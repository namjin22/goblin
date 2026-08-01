import 'package:flutter/material.dart';
import '../../services/pairing_service.dart';
import '../../theme/app_colors.dart';
import '../../widgets/circle_back_button.dart';
import '../../widgets/hero_card.dart';
import '../../widgets/hero_group.dart';
import '../../widgets/mascot.dart';
import 'welcome_screen.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  // TODO: 테스트 편의용 임시 기본값 — 실제 배포 전 제거.
  final _nameController = TextEditingController(text: '박채은');
  final _moduleController = TextEditingController(text: PairingService.demoModuleId);
  String? _error;
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _moduleController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    final moduleId = _moduleController.text.trim();

    if (name.isEmpty || moduleId.isEmpty) {
      setState(() => _error = '이름과 모듈 고유 번호를 모두 입력해주세요');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    final ok = await PairingService.pair(name: name, moduleId: moduleId);

    if (!mounted) return;
    setState(() => _submitting = false);

    if (ok) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => WelcomeScreen(name: name)),
      );
    } else {
      setState(() => _error = '모듈 고유 번호를 다시 확인해주세요');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F9F5),
      body: SafeArea(
        child: Stack(
          children: [
            const Positioned(top: 6, left: 20, child: CircleBackButton()),
            SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 44),
                  HeroGroup(
                    bubbleText: '몇 가지만\n알려주시면 돼요!',
                    pose: MascotPose.wave,
                    card: HeroCard(
                      child: Column(
                        children: [
                          const CardTitle('회원가입'),
                          _FieldLabel('이름'),
                          _FieldBox(controller: _nameController),
                          _FieldLabel('모듈 고유 번호'),
                          _FieldBox(controller: _moduleController, hint: '기기 뒷면의 번호', keyboardType: TextInputType.number),
                          if (_error != null) ...[
                            const SizedBox(height: 10),
                            Text(_error!, style: const TextStyle(color: AppColors.statusRedText, fontWeight: FontWeight.w600, fontSize: 15)),
                          ],
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _submitting ? null : _submit,
                              child: _submitting
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                    )
                                  : const Text('가입하기'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 8),
      child: Align(
        alignment: Alignment.center,
        child: Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.ink)),
      ),
    );
  }
}

class _FieldBox extends StatelessWidget {
  const _FieldBox({required this.controller, this.hint, this.keyboardType});

  final TextEditingController controller;
  final String? hint;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 52,
      decoration: BoxDecoration(
        color: const Color(0xFFFAFAFA),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.line, width: 2),
      ),
      alignment: Alignment.center,
      child: TextField(
        controller: controller,
        textAlign: TextAlign.center,
        keyboardType: keyboardType,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.ink),
        decoration: InputDecoration(
          hintText: hint,
          border: InputBorder.none,
          isCollapsed: true,
        ),
      ),
    );
  }
}
