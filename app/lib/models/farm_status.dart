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

  static const initial = FarmState(
    message: '불러오는 중이에요',
    level: FarmLevel.good,
    cropName: '확인 중',
    temperature: null,
    humidity: null,
    dryness: null,
    ventOpen: false,
    busy: false,
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
      );
}

/// server.py `/api/history`의 항목 하나. `at`은 UNIX epoch(초).
class HistoryItem {
  const HistoryItem({required this.at, required this.event, required this.detail});

  final double at;
  final String event;
  final String detail;

  DateTime get time => DateTime.fromMillisecondsSinceEpoch((at * 1000).round());

  factory HistoryItem.fromJson(Map<String, dynamic> json) => HistoryItem(
        at: (json['at'] as num).toDouble(),
        event: json['event'] as String,
        detail: json['detail'] as String? ?? '',
      );
}
