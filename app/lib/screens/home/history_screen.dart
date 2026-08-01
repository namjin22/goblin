import 'package:flutter/material.dart';
import '../../models/farm_status.dart';
import '../../services/farm_api.dart';
import '../../theme/app_colors.dart';

/// server.py(FarmApi)에 닿지 못할 때(오프라인 개발 중) 보여줄 대체 데이터.
List<HistoryItem> _buildDemoItems() {
  final now = DateTime.now();
  double hoursAgo(double h) => now.subtract(Duration(minutes: (h * 60).round())).millisecondsSinceEpoch / 1000;
  return [
    HistoryItem(at: hoursAgo(0.5), event: 'water', detail: '물을 주었습니다'),
    HistoryItem(at: hoursAgo(2), event: 'vent_open', detail: '창문을 열었습니다'),
    HistoryItem(at: hoursAgo(5), event: 'scan', detail: '상추을(를) 확인했습니다'),
    HistoryItem(at: hoursAgo(30), event: 'water', detail: '물을 주었습니다'),
    HistoryItem(at: hoursAgo(48), event: 'vent_close', detail: '창문을 닫았습니다'),
  ];
}

String _emojiFor(String event) => switch (event) {
      'water' => '💧',
      'vent_open' || 'vent_close' || 'done' => '🪟',
      'scan' => '📷',
      'light' => '💡',
      'button' => '🔘',
      _ => '📋',
    };

/// 화면[3] 지난 기록 - server.py `/api/history`를 받아 "물을 주었습니다" 수준의
/// 문장형 요약으로 보여준다. 오늘/이번 주는 서버가 나눠주지 않으므로 timestamp로 직접 나눈다.
/// 성장 사진(주간 스냅샷)도 "지난 기록"의 일부로 여기 함께 보여준다.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  static const _periods = ['오늘', '이번 주'];

  int _period = 0;
  List<HistoryItem> _allItems = [];
  List<GrowthPhoto> _photos = const [];

  @override
  void initState() {
    super.initState();
    _allItems = _buildDemoItems();
    _refresh();
    _refreshPhotos();
  }

  Future<void> _refresh() async {
    final fetched = await FarmApi.fetchHistory(limit: 200);
    if (!mounted || fetched == null) return;
    setState(() => _allItems = fetched);
  }

  Future<void> _refreshPhotos() async {
    // 사진은 일주일에 한 번만 늘어나므로 기록처럼 자주 폴링할 필요는 없다.
    final fetched = await FarmApi.fetchGrowthPhotos();
    if (!mounted || fetched == null) return;
    setState(() => _photos = fetched);
  }

  List<HistoryItem> get _visibleItems {
    final now = DateTime.now();
    final cutoff = _period == 0
        ? DateTime(now.year, now.month, now.day)
        : now.subtract(const Duration(days: 7));
    return _allItems.where((item) => item.time.isAfter(cutoff)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final items = _visibleItems;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 8),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text('지난 기록', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.ink)),
          ),
          const SizedBox(height: 16),
          _GrowthPhotoStrip(photos: _photos),
          const SizedBox(height: 20),
          _PeriodToggle(
            labels: _periods,
            selected: _period,
            onChanged: (i) => setState(() => _period = i),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: items.isEmpty
                ? const Center(
                    child: Text('아직 기록이 없어요', style: TextStyle(color: AppColors.sub, fontSize: 18, fontWeight: FontWeight.w600)),
                  )
                : ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (context, i) => _HistoryRow(item: items[i]),
                  ),
          ),
        ],
      ),
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
          const Text('성장 사진', style: TextStyle(color: AppColors.ink, fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          if (photos.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24),
              decoration: BoxDecoration(color: AppColors.greenLight, borderRadius: BorderRadius.circular(16)),
              child: const Center(
                child: Text('아직 성장 사진이 없어요', style: TextStyle(color: AppColors.sub, fontSize: 16, fontWeight: FontWeight.w600)),
              ),
            )
          else
            SizedBox(
              height: 132,
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
        Text('${photo.week + 1}주차', style: const TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _PeriodToggle extends StatelessWidget {
  const _PeriodToggle({required this.labels, required this.selected, required this.onChanged});

  final List<String> labels;
  final int selected;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: const Color(0xFFF4F9F5), borderRadius: BorderRadius.circular(16)),
      child: Row(
        children: List.generate(labels.length, (i) {
          final active = i == selected;
          return Expanded(
            child: GestureDetector(
              onTap: () => onChanged(i),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: active ? Colors.white : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: active ? [BoxShadow(color: AppColors.ink.withValues(alpha: 0.08), blurRadius: 8, offset: const Offset(0, 2))] : null,
                ),
                alignment: Alignment.center,
                child: Text(
                  labels[i],
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                    color: active ? AppColors.greenDark : AppColors.sub,
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.item});

  final HistoryItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      decoration: BoxDecoration(color: AppColors.greenLight, borderRadius: BorderRadius.circular(20)),
      child: Row(
        children: [
          Text(_emojiFor(item.event), style: const TextStyle(fontSize: 28)),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              item.detail.isEmpty ? item.event : item.detail,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.ink),
            ),
          ),
        ],
      ),
    );
  }
}
