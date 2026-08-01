import 'package:shared_preferences/shared_preferences.dart';

/// 노트북(server.py)의 IP는 대회장마다, USB/핫스팟 상황마다 달라진다.
/// 앱 코드에 박아두면 현장에서 재빌드해야 하므로, 페어링 화면에서
/// 한 번 입력받아 기기에 저장하고 이후로는 다시 묻지 않는다.
class ServerConfig {
  ServerConfig._();

  static const _keyBaseUrl = 'server_base_url';

  // 개발 중 기본값. 실제 서버 주소는 페어링 화면에서 사용자가 입력한 값으로 덮어써진다.
  static const defaultBaseUrl = 'http://192.168.0.10:5000';

  static String _cached = defaultBaseUrl;

  /// 지금까지 로드/설정된 서버 주소. FarmApi가 요청마다 이 값을 읽는다.
  static String get baseUrl => _cached;

  /// 앱 시작 시 한 번 호출해서 저장된 주소를 메모리에 올린다.
  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _cached = prefs.getString(_keyBaseUrl) ?? defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    var normalized = url.trim();
    if (normalized.endsWith('/')) {
      normalized = normalized.substring(0, normalized.length - 1);
    }
    if (normalized.isEmpty) return;
    _cached = normalized;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyBaseUrl, normalized);
  }
}
