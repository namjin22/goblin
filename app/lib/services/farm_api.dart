import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/farm_status.dart';
import 'server_config.dart';

/// server.py(Flask)가 노트북에서 띄우는 로컬 API와의 통신 계약.
/// 앱과 노트북이 같은 Wi-Fi 공유기에 붙어 있다는 전제로 HTTP로 통신한다.
/// 실제 엔드포인트 정의는 goblin 레포의 server.py / README.md 참고.
class FarmApi {
  FarmApi._();

  // 노트북 IP는 대회장마다 바뀌므로 하드코딩하지 않고 ServerConfig에서 읽는다
  // (페어링 화면에서 사용자가 한 번 입력, 이후 SharedPreferences에 저장됨).
  static String get baseUrl => ServerConfig.baseUrl;

  static const _timeout = Duration(seconds: 5);
  static const _headers = {'Content-Type': 'application/json'};

  static Future<bool> checkHealth() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/health')).timeout(_timeout);
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<FarmState?> fetchState() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/state')).timeout(_timeout);
      if (res.statusCode != 200) return null;
      return FarmState.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  /// 서버에 닿았으면 성공 여부와 무관하게 결과를 돌려준다(예: 동작 중이라 거부됨).
  /// 서버에 아예 닿지 못했을 때만 null.
  static Future<CommandResult?> sendCommand(String command) async {
    try {
      final res = await http
          .post(Uri.parse('$baseUrl/api/command'), headers: _headers, body: jsonEncode({'command': command}))
          .timeout(const Duration(seconds: 8));
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return CommandResult(ok: data['ok'] == true, error: data['error'] as String?);
    } catch (_) {
      return null;
    }
  }

  static Future<List<GrowthPhoto>?> fetchGrowthPhotos() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/growth_photos')).timeout(_timeout);
      if (res.statusCode != 200) return null;
      final items = (jsonDecode(res.body) as Map<String, dynamic>)['items'] as List;
      return items.map((e) => GrowthPhoto.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      return null;
    }
  }

  /// `url`(서버 기준 상대 경로)을 절대 주소로 바꾼다.
  static String photoUrl(String url) => '$baseUrl$url';
}

class CommandResult {
  const CommandResult({required this.ok, this.error});
  final bool ok;
  final String? error;
}
