import 'dart:async';
import 'package:flutter/material.dart';
import '../../models/farm_status.dart';
import '../../services/farm_api.dart';
import '../../theme/app_colors.dart';

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

  List<GrowthPhoto> _photos = const [];

  @override
  void initState() {
    super.initState();
    _refresh();
    _refreshPhotos();
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

  Future<void> _refreshPhotos() async {
    // 사진은 일주일에 한 번만 늘어나므로 상태처럼 자주 폴링할 필요는 없다.
    final fetched = await FarmApi.fetchGrowthPhotos();
    if (!mounted || fetched == null) return;
    setState(() => _photos = fetched);
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 8),
          const _CameraPreview(),
          const SizedBox(height: 14),
          _StatusCard(state: _state),
          const SizedBox(height: 14),
          _FactsGrid(state: _state),
          const SizedBox(height: 14),
          _GrowthPhotoStrip(photos: _photos),
          const SizedBox(height: 8),
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
      height: 260,
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
                  Text('실시간', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
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
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
      decoration: BoxDecoration(color: state.level.background, borderRadius: BorderRadius.circular(24)),
      child: Column(
        children: [
          Text(state.cropName, style: const TextStyle(color: AppColors.ink, fontSize: 14, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          Text(
            state.message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.ink, fontSize: 24, fontWeight: FontWeight.w800, height: 1.4),
          ),
          if (state.harvestDate != null) ...[
            const SizedBox(height: 14),
            Container(height: 1, width: 48, color: AppColors.ink.withValues(alpha: 0.15)),
            const SizedBox(height: 14),
            Text(
              '수확 예정일 ${state.harvestDate}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.ink, fontSize: 19, fontWeight: FontWeight.w800),
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

/// 일주일 간격으로 웹캠이 찍어둔 성장 스냅샷 — server.py `/api/growth_photos`.
class _GrowthPhotoStrip extends StatelessWidget {
  const _GrowthPhotoStrip({required this.photos});

  final List<GrowthPhoto> photos;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('성장 사진', style: TextStyle(color: AppColors.ink, fontSize: 16, fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          if (photos.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24),
              decoration: BoxDecoration(color: AppColors.greenLight, borderRadius: BorderRadius.circular(16)),
              child: const Center(
                child: Text('아직 성장 사진이 없어요', style: TextStyle(color: AppColors.sub, fontSize: 14, fontWeight: FontWeight.w600)),
              ),
            )
          else
            SizedBox(
              height: 128,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: photos.length,
                separatorBuilder: (_, _) => const SizedBox(width: 10),
                itemBuilder: (context, i) => _GrowthPhotoThumb(photo: photos[i]),
              ),
            ),
        ],
      ),
    );
  }
}

class _GrowthPhotoThumb extends StatelessWidget {
  const _GrowthPhotoThumb({required this.photo});

  final GrowthPhoto photo;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: Image.network(
            FarmApi.photoUrl(photo.url),
            width: 96,
            height: 96,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stack) => Container(
              width: 96,
              height: 96,
              color: AppColors.greenLight,
              alignment: Alignment.center,
              child: const Icon(Icons.image_not_supported_outlined, color: AppColors.sub, size: 28),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text('${photo.week + 1}주차', style: const TextStyle(color: AppColors.sub, fontSize: 12, fontWeight: FontWeight.w600)),
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
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: AppColors.sub, fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(color: AppColors.ink, fontSize: 18, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}
