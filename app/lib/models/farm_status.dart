/// server.py `/api/state`가 돌려주는 값과 1:1로 대응한다.
/// level: good(정상) / warn(주의) / alert(조치 필요).
enum FarmLevel { good, warn, alert }

FarmLevel farmLevelFromJson(String value) => switch (value) {
      'warn' => FarmLevel.warn,
      'alert' => FarmLevel.alert,
      _ => FarmLevel.good,
    };

class FarmState {
  const FarmState({
    required this.message,
    required this.level,
    required this.cropName,
    required this.temperature,
    required this.humidity,
    required this.dryness,
    required this.ventOpen,
    required this.busy,
    required this.growthStage,
    required this.daysGrowing,
    required this.harvestDate,
  });

  final String message;
  final FarmLevel level;
  final String cropName;
  final double? temperature;
  final double? humidity;

  /// 0(젖음) ~ 100(마름).
  final double? dryness;
  final bool ventOpen;
  final bool busy;

  /// 웹캠으로 실제 크기를 잰 값이 아니라, 처음 인식한 시각 + 프로파일의
  /// 평균 재배 일수로 추정한 값이다(server.py `_growth_info` 참고).
  final String? growthStage;
  final int? daysGrowing;
  final String? harvestDate;

  static const loading = FarmState(
    message: '불러오는 중이에요',
    level: FarmLevel.good,
    cropName: '확인 중',
    temperature: null,
    humidity: null,
    dryness: null,
    ventOpen: false,
    busy: false,
    growthStage: null,
    daysGrowing: null,
    harvestDate: null,
  );

  /// server.py(FarmApi)에 닿지 못할 때(오프라인 개발 중) 보여줄 대체 데이터.
  static const demo = FarmState(
    message: '상추가 잘 자라고 있어요',
    level: FarmLevel.good,
    cropName: '상추',
    temperature: 24,
    humidity: 55,
    dryness: 35,
    ventOpen: false,
    busy: false,
    growthStage: '한창 자라는 중이에요',
    daysGrowing: 12,
    harvestDate: '8월 20일',
  );

  factory FarmState.fromJson(Map<String, dynamic> json) => FarmState(
        message: json['message'] as String,
        level: farmLevelFromJson(json['level'] as String),
        cropName: json['crop_name'] as String? ?? '확인 중',
        temperature: (json['temperature'] as num?)?.toDouble(),
        humidity: (json['humidity'] as num?)?.toDouble(),
        dryness: (json['dryness'] as num?)?.toDouble(),
        ventOpen: json['vent_open'] as bool? ?? false,
        busy: json['busy'] as bool? ?? false,
        growthStage: json['growth_stage'] as String?,
        daysGrowing: json['days_growing'] as int?,
        harvestDate: json['harvest_date'] as String?,
      );
}

/// server.py `/api/growth_photos`의 항목 하나 — 일주일에 한 번 남긴 성장 스냅샷.
class GrowthPhoto {
  const GrowthPhoto({required this.week, required this.cropName, required this.url});

  final int week;
  final String cropName;

  /// 서버 기준 상대 경로(예: `/growth_photos/xxx.jpg`) — FarmApi.baseUrl과 이어붙여야 한다.
  final String url;

  factory GrowthPhoto.fromJson(Map<String, dynamic> json) => GrowthPhoto(
        week: json['week'] as int,
        cropName: json['crop_name'] as String? ?? '',
        url: json['url'] as String,
      );
}
