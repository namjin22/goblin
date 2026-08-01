import 'package:flutter/material.dart';
import '../../models/farm_status.dart';
import '../../services/farm_api.dart';
import '../../theme/app_colors.dart';

/// 화면[3] 성장 과정 - 웹캠이 일주일에 한 번 찍어둔 성장 사진 타임라인.
/// server.py `/api/growth_photos` (지금 인식 중인 작물 것만 준다).
class GrowthScreen extends StatefulWidget {
  const GrowthScreen({super.key});

  @override
  State<GrowthScreen> createState() => _GrowthScreenState();
}

class _GrowthScreenState extends State<GrowthScreen> {
  List<GrowthPhoto> _photos = const [];

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    // 사진은 일주일에 한 번만 늘어나므로 지금 상태처럼 자주 폴링할 필요는 없다.
    final fetched = await FarmApi.fetchGrowthPhotos();
    if (!mounted || fetched == null) return;
    setState(() => _photos = fetched);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          const Text('성장 과정', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.ink)),
          const SizedBox(height: 4),
          const Text(
            '일주일마다 한 장씩 사진으로 남겨요',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.sub),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: _photos.isEmpty
                ? const Center(
                    child: Text(
                      '아직 성장 사진이 없어요',
                      style: TextStyle(color: AppColors.sub, fontSize: 18, fontWeight: FontWeight.w600),
                    ),
                  )
                : ListView.separated(
                    itemCount: _photos.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 14),
                    itemBuilder: (context, i) => _GrowthPhotoCard(photo: _photos[i]),
                  ),
          ),
        ],
      ),
    );
  }
}

class _GrowthPhotoCard extends StatelessWidget {
  const _GrowthPhotoCard({required this.photo});

  final GrowthPhoto photo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.greenLight, borderRadius: BorderRadius.circular(20)),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Image.network(
              FarmApi.photoUrl(photo.url),
              width: 88,
              height: 88,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stack) => Container(
                width: 88,
                height: 88,
                color: Colors.white,
                alignment: Alignment.center,
                child: const Icon(Icons.image_not_supported_outlined, color: AppColors.sub, size: 28),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${photo.week + 1}주차', style: const TextStyle(color: AppColors.ink, fontSize: 20, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(photo.cropName, style: const TextStyle(color: AppColors.sub, fontSize: 15, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
