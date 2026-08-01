import 'dart:async';
import 'package:flutter/material.dart';
import '../../models/farm_status.dart';
import '../../services/farm_api.dart';
import '../../services/server_config.dart';
import '../../theme/app_colors.dart';
import '../../widgets/scrollable_fill.dart';

extension on FarmLevel {
  Color get background => switch (this) {
        FarmLevel.good => AppColors.statusGreenBg,
        FarmLevel.warn => AppColors.statusYellowBg,
        FarmLevel.alert => AppColors.statusRedBg,
      };
}

/// 화면[1] 지금 상태 - server.py `/api/state`를 폴링해 하드웨어 판단 결과를 반영한다.
/// 실제 시스템은 한 번에 한 작물만 인식한다(웹캠 1대 · 화분 1개 기준) — 여러 작물을
/// 동시에 보여주는 대시보드가 아니라 지금 카메라 앞에 있는 작물 하나의 상태를 보여준다.
class StatusScreen extends StatefulWidget {
  const StatusScreen({super.key});

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  FarmState _state = FarmState.loading;
  bool _hasRealData = false;
  Timer? _poller;

  @override
  void initState() {
    super.initState();
    _refresh();
    _poller = Timer.periodic(const Duration(seconds: 2), (_) => _refresh());
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final fetched = await FarmApi.fetchState();
    if (!mounted) return;
    if (fetched != null) {
      _hasRealData = true;
      setState(() => _state = fetched);
    } else if (!_hasRealData) {
      // server.py에 아직 닿지 못함 — 오프라인 개발용 대체 데이터로 보여준다.
      setState(() => _state = FarmState.demo);
    }
  }

  Future<void> _editServerAddress() async {
    final controller = TextEditingController(text: ServerConfig.baseUrl);
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('서버 주소'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(hintText: 'http://노트북IP:5000'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
          TextButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('저장'),
          ),
        ],
      ),
    );
    if (result == null || result.trim().isEmpty) return;
    await ServerConfig.setBaseUrl(result);
    _hasRealData = false;   // 새 주소로 다시 연결 시도하도록 리셋
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return ScrollableFill(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Stack(
        children: [
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const _CameraPreview(),
              const SizedBox(height: 14),
              _StatusCard(state: _state),
              const SizedBox(height: 14),
              _FactsGrid(state: _state),
            ],
          ),
          // 페어링은 한 번만 하고 다시 안 물어보므로, 서버 주소만 나중에
          // 바꿀 수 있게 여기 작은 버튼을 둔다 (재페어링 없이도 가능).
          Positioned(
            top: 4,
            right: 0,
            child: IconButton(
              icon: const Icon(Icons.settings_outlined, color: AppColors.sub, size: 22),
              onPressed: _editServerAddress,
              tooltip: '서버 주소 설정',
            ),
          ),
        ],
      ),
    );
  }
}

/// server.py `/camera/snapshot.jpg`를 주기적으로 다시 요청해서 "실시간처럼"
/// 보여준다. 연결을 계속 열어두는 스트림 방식은 메인 루프를 막을 위험이
/// 있어서 쓰지 않는다(hardware.py/controller.py 주석 참고).
///
/// [주의] 서버가 --camera-preview 옵션 없이 켜져 있으면(기본값) 프레임이
/// 아예 없어서 계속 실패 상태로 보인다 - 웹캠을 너무 자주 읽으면 메인
/// 루프가 멈출 수 있다는 의심 때문에 기본은 꺼져 있다.
class _CameraPreview extends StatefulWidget {
  const _CameraPreview();

  @override
  State<_CameraPreview> createState() => _CameraPreviewState();
}

class _CameraPreviewState extends State<_CameraPreview> {
  Timer? _timer;
  int _tick = 0;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) setState(() => _tick++);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(color: AppColors.camPreview, borderRadius: BorderRadius.circular(20)),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.network(
              '${FarmApi.baseUrl}/camera/snapshot.jpg?t=$_tick',
              fit: BoxFit.cover,
              gaplessPlayback: true,
              errorBuilder: (context, error, stack) => const Center(
                child: Text('웹캠 미리보기 없음', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.w600)),
              ),
            ),
            Positioned(
              top: 10,
              left: 12,
              child: Container(
                padding: const EdgeInsets.fromLTRB(8, 4, 10, 4),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.4), borderRadius: BorderRadius.circular(20)),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircleAvatar(radius: 3.5, backgroundColor: Color(0xFFFF5B5B)),
                    SizedBox(width: 5),
                    Text('실시간', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.state});

  final FarmState state;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 22),
      decoration: BoxDecoration(color: state.level.background, borderRadius: BorderRadius.circular(24)),
      child: Column(
        children: [
          Text(state.cropName, style: const TextStyle(color: AppColors.ink, fontSize: 14, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text(
            state.message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.ink, fontSize: 22, fontWeight: FontWeight.w800, height: 1.4),
          ),
          if (state.harvestDate != null) ...[
            const SizedBox(height: 10),
            Container(height: 1, width: 48, color: AppColors.ink.withValues(alpha: 0.15)),
            const SizedBox(height: 10),
            Text(
              '수확 예정일 ${state.harvestDate}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.ink, fontSize: 17, fontWeight: FontWeight.w800),
            ),
          ],
        ],
      ),
    );
  }
}

class _FactsGrid extends StatelessWidget {
  const _FactsGrid({required this.state});

  final FarmState state;

  @override
  Widget build(BuildContext context) {
    final temp = state.temperature;
    final humidity = state.humidity;
    final dryness = state.dryness;

    return Row(
      children: [
        Expanded(child: _Fact(label: '온도', value: temp == null ? '-' : '${temp.toStringAsFixed(1)}°')),
        const SizedBox(width: 12),
        Expanded(child: _Fact(label: '습도', value: humidity == null ? '-' : '${humidity.round()}%')),
        const SizedBox(width: 12),
        Expanded(child: _Fact(label: '흙 상태', value: dryness == null ? '-' : (dryness > 60 ? '마름' : '촉촉'))),
        const SizedBox(width: 12),
        Expanded(child: _Fact(label: '창문', value: state.ventOpen ? '열림' : '닫힘')),
      ],
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: AppColors.sub, fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(color: AppColors.ink, fontSize: 16, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}
