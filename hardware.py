# -*- coding: utf-8 -*-
"""MODI Plus 하드웨어 추상화 계층.

[중요] 이 파일 밖에서는 modi_plus를 직접 import 하지 않는다.
       모든 하드웨어 접근은 이 인터페이스를 통한다.

[중요] 이 객체의 메서드는 메인 루프 스레드에서만 호출한다.
       Flask 스레드에서 호출하면 시리얼 통신이 깨진다.

MockHardware 덕분에 MODI 키트 없이도 전체 시스템이 돌아간다.
팀원 3명이 하드웨어 1세트를 두고 기다릴 필요가 없다.
"""

import json
import math
import time


class HardwareError(Exception):
    pass


def pick_motor(motors, motor_id, index):
    """모터 목록에서 역할에 맞는 모터를 고른다. ID가 있으면 ID로, 없으면 순서로. 못 찾으면 None."""
    if motor_id is not None:
        for m in motors:
            if m.id == motor_id:
                return m
        return None
    return motors[index] if 0 <= index < len(motors) else None


# ------------------------------------------------------------------ 모터 배치
# [주의] motors[0]이 반드시 환기창이라는 보장이 없다.
#        pymodi-plus는 모듈이 인식된 순서대로 리스트를 만들기 때문에,
#        케이블을 다시 꽂으면 순서가 바뀔 수 있다.
#        hwtest.py 로 어느 모터가 어느 것인지 확인한 뒤,
#        다르면 아래 숫자들을 실제 배치에 맞게 바꾼다.
#        (2026-08-01 hwtest.py 실측: motors[2]=A, motors[0]=B, motors[1]=스프링클러)
VENT_MOTOR_A_INDEX = 2
VENT_MOTOR_B_INDEX = 0
SPRINKLER_MOTOR_INDEX = 1

# [권장] 모터를 케이블 순서(INDEX)가 아니라 모듈 고유 ID로 지정한다.
# INDEX는 모듈이 인식된 순서라서 케이블을 다시 꽂으면 바뀌지만, 모듈 ID(예: 0x512)는
# 그 모듈에 고정돼 있어서 재조립해도 변하지 않는다. 값이 있으면 INDEX보다 우선한다.
# hwtest.py --motor 가 ID를 알려준다. None이면 위 INDEX를 쓴다.
VENT_MOTOR_A_ID = None
VENT_MOTOR_B_ID = None
SPRINKLER_MOTOR_ID = None

# [핵심 - 두 번째 설계 변경] 절대각(set_angle) 방식을 버리고 상대회전
# (append_angle)으로 바꿨다. pymodi_plus 소스(motor.py)에 두 방식이 있다:
#   - angle 프로퍼티(set_angle) - 절대각(0~360)으로 이동. 0~360을 벗어나면
#     조용히 무시됨. "닫힘 각도를 calibrate로 기억해뒀다가 그 각도로
#     되돌아간다"는 방식을 썼었는데, home 각도가 0/360 경계 근처일 때
#     (예: home=350에서 -120 이동 → (350-120)%360=230) 모터가 최단 경로가
#     아니라 반대 방향으로 훨씬 많이 도는 경우가 있었다 - "모터A가 자꾸
#     반대로 돈다"는 문제가 재발했던 진짜 원인이 이거였다(calibrate 타이밍
#     문제가 아니라 절대각 wraparound 자체가 근본 문제).
#   - append_angle(delta, speed) - "지금 위치에서 delta만큼 상대 회전".
#     delta는 음수도 그대로 먹힌다(s16). wraparound 문제 자체가 없다.
#
# 그래서 열기=+delta 회전, 닫기=-delta 회전(정확히 되돌아옴)으로 완전히
# 바꿨다. 이러면 "닫힘 기준 각도"를 기억할 필요도 없어진다 - 항상 열고
# 닫는 게 쌍으로 맞으면 원래 위치로 돌아온다. 대신 controller.py에서
# "이미 열려있는데 또 열기"를 못 하게 막아야 한다(안 그러면 계속
# 밀려나감) - Controller.open_vent()/close_vent()의 상태 가드 참고.
#
# [미확정] 아래 부호는 hwtest.py의 대화형 보정 또는 main.py 시작 시
# 자동으로 물어보는 확인 절차로 실측 후 필요하면 뒤집을 것.
VENT_A_SIGN = -1
VENT_B_SIGN = 1
VENT_ROTATION_DEG = 120

# 역할이나 방향을 바꾼 뒤에는 사람이 "잘 열렸어요"를 눌러 확인하기 전까지 False다.
# 방향이 틀린 채 열면 레고 기구가 걸릴 수 있어서, False인 동안은 환기창이 시험 구동
# (열었다 바로 닫기) 말고는 움직이지 않는다. 설정 파일이 아예 없으면(예전 방식) True.
VENT_VERIFIED = True

# --------------------------------------------------------------- 장치 설정 파일
# 모터 역할(ID)과 열림 방향은 장비마다, 조립할 때마다 다르다. 웹 운영자 패널의
# "장치 점검"에서 눈으로 확인하며 정하면 이 파일에 저장되고, 다음 실행부터 위 상수를
# 덮어쓴다 (코드를 고치지 않아도 되게). 기기마다 다른 값이라 git에는 올리지 않는다.
CONFIG_PATH = "hw_config.json"

# 웹에서 모터를 시험 구동할 때 한 번에 돌리는 각도/속도. 레고 기구가 걸려도 부담 없는 크기.
JOG_MAX_DEG = 30
JOG_SPEED = 20


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config():
    """지금 상수 값을 파일에 남긴다."""
    cfg = {
        "vent_a_id": VENT_MOTOR_A_ID,
        "vent_b_id": VENT_MOTOR_B_ID,
        "sprinkler_id": SPRINKLER_MOTOR_ID,
        "vent_a_sign": VENT_A_SIGN,
        "vent_b_sign": VENT_B_SIGN,
        "rotation_deg": VENT_ROTATION_DEG,
        "verified": VENT_VERIFIED,
    }
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError as e:
        print("[HW] 설정 저장 실패(무시):", e)


def apply_config():
    """hw_config.json이 있으면 상수를 덮어쓴다. 없으면 코드의 기본값을 그대로 쓴다."""
    global VENT_MOTOR_A_ID, VENT_MOTOR_B_ID, SPRINKLER_MOTOR_ID
    global VENT_A_SIGN, VENT_B_SIGN, VENT_ROTATION_DEG, VENT_VERIFIED
    cfg = load_config()
    if not cfg:
        return False
    VENT_MOTOR_A_ID = cfg.get("vent_a_id", VENT_MOTOR_A_ID)
    VENT_MOTOR_B_ID = cfg.get("vent_b_id", VENT_MOTOR_B_ID)
    SPRINKLER_MOTOR_ID = cfg.get("sprinkler_id", SPRINKLER_MOTOR_ID)
    VENT_A_SIGN = cfg.get("vent_a_sign", VENT_A_SIGN)
    VENT_B_SIGN = cfg.get("vent_b_sign", VENT_B_SIGN)
    VENT_ROTATION_DEG = cfg.get("rotation_deg", VENT_ROTATION_DEG)
    # 설정 파일이 있는데 확인 기록이 없으면 미확인으로 본다
    VENT_VERIFIED = bool(cfg.get("verified", False))
    return True


# --------------------------------------------------------- 공통 인터페이스
class BaseHardware:
    """실물과 Mock이 공유하는 인터페이스. 메서드 시그니처를 반드시 맞출 것."""

    def connect(self):
        raise NotImplementedError

    def close(self):
        pass

    # --- 입력 ---
    def read_env(self):
        """{'temperature': float, 'humidity': float, 'illuminance': float}"""
        raise NotImplementedError

    def read_distance(self):
        """ToF 거리(cm). 미사용. 모듈이 없으면 None"""
        raise NotImplementedError

    def read_dial(self):
        """다이얼 각도. 0~100"""
        raise NotImplementedError

    # --- 출력 ---
    def set_led(self, rgb):
        raise NotImplementedError

    def show_text(self, text):
        raise NotImplementedError

    def open_vent(self, speed=50):
        """환기창을 연다. 즉시 반환한다(대기하지 않음)."""
        raise NotImplementedError

    def close_vent(self, speed=50):
        """환기창을 닫는다. 즉시 반환한다(대기하지 않음)."""
        raise NotImplementedError

    def set_sprinkler(self, speed):
        """스프링클러 모터 회전 속도. 0이면 정지."""
        raise NotImplementedError

    # --- 장치 점검 (웹 운영자 패널) ---
    # [중요] 환기창은 두 모터가 짝으로 움직여야 한다. 역할이 정해지지 않았으면
    # vent_ready가 False이고 컨트롤러는 환기창을 절대 움직이지 않는다.
    @property
    def vent_roles_ok(self):
        """환기창 모터 A/B 역할이 정해졌는가 (방향 확인 전이라도 시험 구동은 가능)."""
        return True

    @property
    def vent_ready(self):
        """환기창을 일반적으로 움직여도 되는가 = 역할이 정해졌고 방향까지 사람이 확인했다."""
        return True

    @property
    def sprinkler_ready(self):
        return True

    def describe(self):
        """웹 화면에 보여줄 하드웨어 구성. {motors, roles, signs, rotation_deg, vent_ready, sprinkler_ready}"""
        raise NotImplementedError

    def jog_motor(self, motor_id, delta, speed=JOG_SPEED):
        """모터 하나를 delta도(+/-) 살짝 돌린다. 어떤 모터가 어떤 건지 눈으로 확인하는 용도."""
        raise NotImplementedError

    def set_roles(self, vent_a, vent_b, sprinkler):
        """모터 ID로 역할을 정하고 저장한다. 환기창 A/B는 필수, 스프링클러는 None 가능."""
        raise NotImplementedError

    def flip_sign(self, which):
        """환기창 모터 'a' 또는 'b'의 열림 방향을 뒤집고 저장한다. 방향 확인은 다시 필요해진다."""
        raise NotImplementedError

    def confirm_vent(self):
        """사람이 시험 구동으로 방향이 맞는 걸 확인했다. 이제부터 환기창을 움직여도 된다."""
        raise NotImplementedError


# --------------------------------------------------------- 실물 하드웨어
class ModiHardware(BaseHardware):
    """실제 MODI Plus 연결.

    모터 배치 (물리적으로 모터 모듈 3개)
      motors[VENT_MOTOR_A_INDEX] = 환기창 모터A
      motors[VENT_MOTOR_B_INDEX] = 환기창 모터B
      motors[SPRINKLER_MOTOR_INDEX] = 스프링클러 (급수 표현용, 실제로 물은 나오지 않음)

    [중요] 환기창은 절대각이 아니라 상대회전(append_angle)으로 움직인다.
    열기(+delta)/닫기(-delta)가 항상 쌍으로 맞으면 원래 위치로 돌아온다.
    """

    def __init__(self, conn_type=None, network_uuid=None):
        self.conn_type = conn_type
        self.network_uuid = network_uuid
        self.bundle = None
        self.env = self.tof = self.dial = None
        self.led = self.display = None
        self.vent_motor_a = None
        self.vent_motor_b = None
        self.sprinkler_motor = None

    def connect(self):
        import modi_plus  # 이 파일 안에서만 import

        # 개발 기본값은 USB 시리얼. BLE는 마지막 리허설에서만 시도한다.
        if self.conn_type == "ble":
            self.bundle = modi_plus.MODIPlus(
                conn_type="ble", network_uuid=self.network_uuid
            )
        else:
            self.bundle = modi_plus.MODIPlus()

        print("[HW] 연결된 모듈:", self.bundle.modules)

        # 필수 모듈 - 하나라도 없으면 진행할 수 없다
        # [주의] Button은 쓰지 않는다 - 수동 조작은 앱으로만 한다 (물리 버튼 없음).
        required = {
            "env": self.bundle.envs,
            "led": self.bundle.leds,
            "display": self.bundle.displays,
        }
        missing = [name for name, lst in required.items() if not lst]
        if missing:
            raise HardwareError(
                "필수 모듈이 빠졌다: %s\n"
                "케이블을 다시 꽂고 python hwtest.py 로 확인할 것."
                % ", ".join(missing)
            )

        self.env = self.bundle.envs[0]
        self.tof = self.bundle.tofs[0] if self.bundle.tofs else None
        self.led = self.bundle.leds[0]
        self.display = self.bundle.displays[0]
        # [참고] Speaker 모듈은 쓰지 않는다. 소리는 노트북에서 낸다 (audio.py).

        # Dial은 선택 사항. 없으면 수동 조절만 못 하고 나머지는 다 돌아간다.
        if self.bundle.dials:
            self.dial = self.bundle.dials[0]
        else:
            self.dial = None
            print("[HW] Dial 없음 - 하드웨어 수동 조절은 비활성. 앱으로는 조작 가능.")

        motors = self.bundle.motors
        print("[HW] 모터 %d개: %s" % (len(motors), ", ".join("0x%X" % m.id for m in motors)))

        if apply_config():
            print("[HW] %s 의 역할/방향 설정을 불러왔다." % CONFIG_PATH)
        self._resolve_roles()

        # 환기창은 모터 2개가 함께(반대 방향으로) 움직여야 열리고 닫힌다.
        # 둘 중 하나라도 정해지지 않았으면 문이 반만 움직이거나 걸릴 수 있어서
        # 환기창은 아예 움직이지 않는다(vent_ready=False). 예전에는 여기서 프로그램이
        # 죽었지만, 그러면 웹에서 역할을 정할 방법이 없어서 "움직이지 않는 상태"로 시작한다.
        if not self.vent_ready:
            print("[HW] 경고: 환기창 모터 역할이 정해지지 않았다 (인식된 모터 %d개). "
                  "환기창은 움직이지 않는다. 웹 운영자 > 장치 점검에서 정할 것." % len(motors))
        if self.sprinkler_motor is None:
            print("[HW] 경고: 스프링클러 모터가 없거나 역할이 정해지지 않았다. 급수 동작은 생략된다.")

        # 센서 첫 값은 0으로 나온다. 반드시 대기.
        time.sleep(1)
        print("[HW] 초기화 완료")

    def close(self):
        """종료 시 하드웨어를 안전한 상태로 되돌린다."""
        try:
            if self.sprinkler_motor:
                self.sprinkler_motor.speed = 0
            if self.led:
                self.led.turn_off()
            if self.display:
                self.display.reset()
        except Exception as e:
            print("[HW] 종료 처리 중 오류(무시):", e)

    # --- 입력 ---
    def read_env(self):
        return {
            "temperature": float(self.env.temperature),
            "humidity": float(self.env.humidity),
            "illuminance": float(self.env.illuminance),
        }

    def read_distance(self):
        # ToF는 사용하지 않는다. 꽂혀 있으면 값을 읽고, 없으면 None.
        if self.tof is None:
            return None
        return float(self.tof.distance)

    def read_dial(self):
        if self.dial is None:
            return None
        return int(self.dial.turn)

    # --- 출력 ---
    def set_led(self, rgb):
        self.led.rgb = rgb

    def show_text(self, text):
        self.display.text = text

    def open_vent(self, speed=50):
        # 상대회전: 지금 위치에서 정해진 방향으로 VENT_ROTATION_DEG만큼 돈다.
        # 절대각 방식의 wraparound 문제가 없다 - 항상 close_vent()와 쌍으로
        # 맞춰 호출된다는 전제 하에 안전하다(controller.py의 상태 가드 참고).
        self.vent_motor_a.append_angle(VENT_A_SIGN * VENT_ROTATION_DEG, speed)
        self.vent_motor_b.append_angle(VENT_B_SIGN * VENT_ROTATION_DEG, speed)

    def close_vent(self, speed=50):
        # 열 때와 정확히 반대로 회전해 원래 위치로 되돌아간다.
        self.vent_motor_a.append_angle(-VENT_A_SIGN * VENT_ROTATION_DEG, speed)
        self.vent_motor_b.append_angle(-VENT_B_SIGN * VENT_ROTATION_DEG, speed)

    def set_sprinkler(self, speed):
        if self.sprinkler_motor:
            self.sprinkler_motor.speed = speed

    # --- 장치 점검 ---
    @property
    def vent_roles_ok(self):
        return self.vent_motor_a is not None and self.vent_motor_b is not None

    @property
    def vent_ready(self):
        return self.vent_roles_ok and VENT_VERIFIED

    @property
    def sprinkler_ready(self):
        return self.sprinkler_motor is not None

    def _resolve_roles(self):
        """설정(ID)이나 옛 순서(INDEX)로 모터 역할을 정한다. 못 정하면 그 역할은 None."""
        motors = self.bundle.motors
        explicit = any(x is not None for x in
                       (VENT_MOTOR_A_ID, VENT_MOTOR_B_ID, SPRINKLER_MOTOR_ID))
        # [중요] 옛 순서(INDEX) 값은 모터가 3개일 때 잰 것이다. 모터 개수가 달라졌는데
        # 순서만 믿으면 엉뚱한 모터를 환기창으로 착각한다 - 그때는 사람이 정하게 한다.
        legacy = not explicit and len(motors) >= 3

        def find(motor_id, index):
            if motor_id is not None:
                return next((m for m in motors if m.id == motor_id), None)
            return motors[index] if legacy and 0 <= index < len(motors) else None

        a = find(VENT_MOTOR_A_ID, VENT_MOTOR_A_INDEX)
        b = find(VENT_MOTOR_B_ID, VENT_MOTOR_B_INDEX)
        s = find(SPRINKLER_MOTOR_ID, SPRINKLER_MOTOR_INDEX)
        # 같은 모터가 두 역할을 맡으면 어느 쪽도 믿을 수 없다
        if a is not None and a is b:
            a = b = None
        if s is not None and s in (a, b):
            s = None
        self.vent_motor_a, self.vent_motor_b, self.sprinkler_motor = a, b, s

    def describe(self):
        def mid(m):
            return m.id if m is not None else None
        return {
            "motors": [{"id": m.id, "label": "0x%X" % m.id} for m in self.bundle.motors],
            "roles": {"vent_a": mid(self.vent_motor_a), "vent_b": mid(self.vent_motor_b),
                      "sprinkler": mid(self.sprinkler_motor)},
            "signs": {"a": VENT_A_SIGN, "b": VENT_B_SIGN},
            "rotation_deg": VENT_ROTATION_DEG,
            "vent_roles_ok": self.vent_roles_ok,
            "vent_verified": VENT_VERIFIED,
            "vent_ready": self.vent_ready,
            "sprinkler_ready": self.sprinkler_ready,
        }

    def jog_motor(self, motor_id, delta, speed=JOG_SPEED):
        motor = next((m for m in self.bundle.motors if m.id == motor_id), None)
        if motor is None:
            raise HardwareError("그 모터를 찾을 수 없다: %r" % (motor_id,))
        delta = max(-JOG_MAX_DEG, min(JOG_MAX_DEG, int(delta)))   # 아무리 큰 값이 와도 살짝만
        motor.append_angle(delta, speed)

    def set_roles(self, vent_a, vent_b, sprinkler):
        global VENT_MOTOR_A_ID, VENT_MOTOR_B_ID, SPRINKLER_MOTOR_ID, VENT_VERIFIED
        ids = {m.id for m in self.bundle.motors}
        chosen = [x for x in (vent_a, vent_b, sprinkler) if x is not None]
        if vent_a is None or vent_b is None:
            raise HardwareError("환기창 모터 A와 B를 모두 골라야 한다.")
        if len(set(chosen)) != len(chosen):
            raise HardwareError("같은 모터를 두 역할에 쓸 수 없다.")
        if any(x not in ids for x in chosen):
            raise HardwareError("연결되지 않은 모터를 골랐다.")
        VENT_MOTOR_A_ID, VENT_MOTOR_B_ID, SPRINKLER_MOTOR_ID = vent_a, vent_b, sprinkler
        VENT_VERIFIED = False       # 역할이 바뀌면 방향도 다시 확인해야 한다
        save_config()
        self._resolve_roles()

    def flip_sign(self, which):
        global VENT_A_SIGN, VENT_B_SIGN, VENT_VERIFIED
        if which == "a":
            VENT_A_SIGN *= -1
        elif which == "b":
            VENT_B_SIGN *= -1
        else:
            raise HardwareError("a 또는 b여야 한다.")
        VENT_VERIFIED = False
        save_config()

    def confirm_vent(self):
        global VENT_VERIFIED
        if not self.vent_roles_ok:
            raise HardwareError("환기창 모터 역할이 정해지지 않았다.")
        VENT_VERIFIED = True
        save_config()


# --------------------------------------------------------- Mock 하드웨어
class MockHardware(BaseHardware):
    """MODI 없이 개발할 때 쓰는 가짜 하드웨어.

    온도가 서서히 오르고, 환기창을 열면 실제로 떨어진다.
    제어 로직을 검증하기에 충분한 수준으로만 흉내 낸다.
    """

    def __init__(self):
        self.t0 = time.time()
        self._vent_open = False
        self._sprinkler = 0
        self._temp = 24.0
        self._humidity = 55.0
        self._led_on = False
        self._last = time.time()
        # 웹의 장치 점검 화면을 하드웨어 없이 개발/테스트할 수 있게 가짜 모터 3개를 둔다.
        # (파일에 저장하지 않는다 - 모의 실행이 실물 설정을 건드리면 안 된다)
        self._motor_ids = [0x111, 0x222, 0x333]
        self._roles = {"vent_a": 0x111, "vent_b": 0x222, "sprinkler": 0x333}
        self._signs = {"a": -1, "b": 1}
        self._verified = True      # 모의 실행은 기본으로 확인된 상태 (set_roles/flip_sign 후엔 False)
        self.jogs = []   # 테스트가 확인할 수 있게 시험 구동 기록을 남긴다

    @property
    def vent_roles_ok(self):
        return self._roles["vent_a"] is not None and self._roles["vent_b"] is not None

    @property
    def vent_ready(self):
        return self.vent_roles_ok and self._verified

    @property
    def sprinkler_ready(self):
        return self._roles["sprinkler"] is not None

    def describe(self):
        return {
            "motors": [{"id": i, "label": "0x%X" % i} for i in self._motor_ids],
            "roles": dict(self._roles),
            "signs": dict(self._signs),
            "rotation_deg": VENT_ROTATION_DEG,
            "vent_roles_ok": self.vent_roles_ok,
            "vent_verified": self._verified,
            "vent_ready": self.vent_ready,
            "sprinkler_ready": self.sprinkler_ready,
        }

    def jog_motor(self, motor_id, delta, speed=JOG_SPEED):
        if motor_id not in self._motor_ids:
            raise HardwareError("그 모터를 찾을 수 없다: %r" % (motor_id,))
        self.jogs.append((motor_id, max(-JOG_MAX_DEG, min(JOG_MAX_DEG, int(delta)))))

    def set_roles(self, vent_a, vent_b, sprinkler):
        chosen = [x for x in (vent_a, vent_b, sprinkler) if x is not None]
        if vent_a is None or vent_b is None:
            raise HardwareError("환기창 모터 A와 B를 모두 골라야 한다.")
        if len(set(chosen)) != len(chosen) or any(x not in self._motor_ids for x in chosen):
            raise HardwareError("모터 선택이 올바르지 않다.")
        self._roles = {"vent_a": vent_a, "vent_b": vent_b, "sprinkler": sprinkler}
        self._verified = False

    def flip_sign(self, which):
        if which not in ("a", "b"):
            raise HardwareError("a 또는 b여야 한다.")
        self._signs[which] *= -1
        self._verified = False

    def confirm_vent(self):
        if not self.vent_roles_ok:
            raise HardwareError("환기창 모터 역할이 정해지지 않았다.")
        self._verified = True

    def connect(self):
        print("[MOCK] 가짜 하드웨어로 실행한다. MODI 키트 없이 동작한다.")

    def _step(self):
        now = time.time()
        dt = now - self._last
        self._last = now
        # 환기창이 열려 있으면 식고, 닫혀 있으면 서서히 더워진다.
        if self._vent_open:
            self._temp -= 0.8 * dt
        else:
            self._temp += 0.35 * dt
        self._temp = max(15.0, min(38.0, self._temp))

        # 공기가 서서히 건조해진다. 급수하면 set_sprinkler에서 곧바로 회복시킨다
        # (컨트롤러가 습도 -> 건조도로 판단하므로, 급수 루프를 mock으로 검증하려면 필요).
        self._humidity -= 0.5 * dt
        self._humidity = max(20.0, min(90.0, self._humidity))

    def read_env(self):
        self._step()
        elapsed = time.time() - self.t0
        # 실측과 비슷하게 낮은 기본 조도. 생장등을 켜면 올라간다.
        # (이 되먹임이 있어야 LED 발진 방지 로직을 검증할 수 있다)
        lux = 3 + 1.5 * math.sin(elapsed / 15)
        if self._led_on:
            lux += 8
        return {
            "temperature": round(self._temp, 1),
            "humidity": round(self._humidity, 1),
            "illuminance": round(max(0.0, lux), 1),
        }

    def read_distance(self):
        return None      # ToF 미사용

    def read_dial(self):
        return 0

    def set_led(self, rgb):
        on = any(v > 0 for v in rgb)
        if on != self._led_on:
            print("[MOCK/LED] 생장등", "켜짐" if on else "꺼짐")
        self._led_on = on

    def show_text(self, text):
        print("[MOCK/DISPLAY]", text.replace("\n", " / "))

    def open_vent(self, speed=50):
        self._vent_open = True

    def close_vent(self, speed=50):
        self._vent_open = False

    def set_sprinkler(self, speed):
        if speed > 0 and self._sprinkler == 0:
            # 급수를 막 시작한 순간(rising edge) 습도가 확 오르는 걸 흉내낸다.
            self._humidity = min(90.0, self._humidity + 30.0)
        self._sprinkler = speed


def build_hardware(mock=False, conn_type=None, network_uuid=None):
    """설정에 맞는 하드웨어 객체를 만들어 연결까지 마친 뒤 반환한다."""
    hw = MockHardware() if mock else ModiHardware(conn_type, network_uuid)
    hw.connect()
    return hw
