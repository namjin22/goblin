import 'package:shared_preferences/shared_preferences.dart';

/// 최초 1회 모듈 고유 번호 페어링 상태를 저장한다.
/// 명세서 원칙: 로그인 없음 — 페어링 후에는 앱을 열 때마다 다시 묻지 않는다.
///
/// goblin 레포의 실제 server.py에는 페어링 개념 자체가 없다(기기 인증 엔드포인트 없음).
/// 이 번호는 서버와 검증하는 값이 아니라 온보딩 단계에서 어르신이 딱 한 번 입력하는
/// 절차용 값이라 로컬 상수와만 비교한다.
class PairingService {
  PairingService._();

  static const _keyPaired = 'is_paired';
  static const _keyName = 'user_name';
  static const _keyModuleId = 'module_id';

  static const demoModuleId = '123456';

  static Future<bool> isPaired() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyPaired) ?? false;
  }

  static Future<String?> getName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyName);
  }

  static Future<bool> pair({required String name, required String moduleId}) async {
    if (moduleId != demoModuleId) return false;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyPaired, true);
    await prefs.setString(_keyName, name);
    await prefs.setString(_keyModuleId, moduleId);
    return true;
  }

  static Future<void> unpair() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyPaired);
    await prefs.remove(_keyName);
    await prefs.remove(_keyModuleId);
  }
}
