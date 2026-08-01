import 'dart:async';
import 'package:flutter/material.dart';
import '../../models/farm_status.dart';
import '../../services/farm_api.dart';
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

  @override
  Widget build(BuildContext context) {
    return ScrollableFill(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const _CameraPreview(),
          const SizedBox(height: 14),
          _StatusCard(state: _state),
          const SizedBox(height: 14),
          _FactsGrid(state: _state),
        ],
      ),
    );
  }
}

class _CameraPreview extends StatelessWidget {
  const _CameraPreview();

  @override
  Widget build(BuildContext context) {
    // TODO: vision.py 웹캠 프레임을 MJPEG 등으로 받아 실제 영상으로 교체 — 현재 server.py엔 영상 스트리밍 엔드포인트가 없다.
    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(color: AppColors.camPreview, borderRadius: BorderRadius.circular(20)),
      child: Stack(
        children: [
          const Center(
            child: Text('웹캠 미리보기', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.w600)),
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
