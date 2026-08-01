import 'package:flutter/material.dart';
import '../../services/pairing_service.dart';
import '../../services/server_config.dart';
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
  final _serverController = TextEditingController(text: ServerConfig.baseUrl);
  String? _error;
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _moduleController.dispose();
    _serverController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    final moduleId = _moduleController.text.trim();
    final serverUrl = _serverController.text.trim();

    if (name.isEmpty || moduleId.isEmpty || serverUrl.isEmpty) {
      setState(() => _error = '이름, 모듈 고유 번호, 서버 주소를 모두 입력해주세요');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    final ok = await PairingService.pair(name: name, moduleId: moduleId);
    if (ok) {
      await ServerConfig.setBaseUrl(serverUrl);
    }

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
            SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 10),
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
                          _FieldLabel('서버 주소'),
                          _FieldBox(
                            controller: _serverController,
                            hint: 'http://노트북IP:5000',
                            keyboardType: TextInputType.url,
                            align: TextAlign.left,
                            fontSize: 12,
                          ),
                          if (_error != null) ...[
                            const SizedBox(height: 8),
                            Text(_error!, style: const TextStyle(color: AppColors.statusRedText, fontWeight: FontWeight.w600, fontSize: 13)),
                          ],
                          const SizedBox(height: 14),
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
            // 스크롤뷰의 제스처 인식기가 겹쳐진 자리의 탭을 먼저 가로채므로,
            // Stack에서 나중에(=위에) 그려지는 이 위치에 둬야 실제로 눌린다.
            const Positioned(top: 6, left: 20, child: CircleBackButton()),
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
      padding: const EdgeInsets.only(top: 6, bottom: 2),
      child: Align(
        alignment: Alignment.center,
        child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.sub)),
      ),
    );
  }
}

class _FieldBox extends StatelessWidget {
  const _FieldBox({
    required this.controller,
    this.hint,
    this.keyboardType,
    this.align = TextAlign.center,
    this.fontSize = 13,
  });

  final TextEditingController controller;
  final String? hint;
  final TextInputType? keyboardType;
  final TextAlign align;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 36,
      decoration: BoxDecoration(
        color: const Color(0xFFFAFAFA),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: AppColors.line, width: 1.5),
      ),
      alignment: Alignment.center,
      // 서버 주소처럼 긴 값은 가운데 정렬하면 시작 부분이 잘려 보이고
      // 읽기 어려워서, 필드별로 정렬/글자크기를 다르게 줄 수 있게 했다.
      padding: align == TextAlign.left ? const EdgeInsets.symmetric(horizontal: 10) : null,
      child: TextField(
        controller: controller,
        textAlign: align,
        keyboardType: keyboardType,
        style: TextStyle(fontSize: fontSize, fontWeight: FontWeight.w600, color: AppColors.ink),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(fontSize: fontSize, color: AppColors.sub),
          border: InputBorder.none,
          isCollapsed: true,
        ),
      ),
    );
  }
}
