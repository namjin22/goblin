import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/farm_status.dart';

/// server.py(Flask)가 노트북에서 띄우는 로컬 API와의 통신 계약.
/// 앱과 노트북이 같은 Wi-Fi 공유기에 붙어 있다는 전제로 HTTP로 통신한다.
/// 실제 엔드포인트 정의는 goblin 레포의 server.py / README.md 참고.
class FarmApi {
  FarmApi._();

  // TODO: 데모 당일 노트북의 실제 로컬 IP로 교체 (Windows: ipconfig).
  static const baseUrl = 'http://192.168.0.10:5000';

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

  static Future<List<HistoryItem>?> fetchHistory({int limit = 100}) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/history?limit=$limit')).timeout(_timeout);
      if (res.statusCode != 200) return null;
      final items = (jsonDecode(res.body) as Map<String, dynamic>)['items'] as List;
      return items.map((e) => HistoryItem.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      return null;
    }
  }
}

class CommandResult {
  const CommandResult({required this.ok, this.error});
  final bool ok;
  final String? error;
}
