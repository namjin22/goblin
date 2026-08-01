# -*- coding: utf-8 -*-
"""MODI Plus 하드웨어 추상화 계층.

[중요] 이 파일 밖에서는 modi_plus를 직접 import 하지 않는다.
       모든 하드웨어 접근은 이 인터페이스를 통한다.

[중요] 이 객체의 메서드는 메인 루프 스레드에서만 호출한다.
       Flask 스레드에서 호출하면 시리얼 통신이 깨진다.

MockHardware 덕분에 MODI 키트 없이도 전체 시스템이 돌아간다.
팀원 3명이 하드웨어 1세트를 두고 기다릴 필요가 없다.
"""

import math
import time


class HardwareError(Exception):
    pass


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

    def beep(self, freq, volume):
        raise NotImplementedError

    def speaker_off(self):
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
        self.led = self.display = self.speaker = None
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
            "speaker": self.bundle.speakers,
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
        self.speaker = self.bundle.speakers[0]

        # Dial은 선택 사항. 없으면 수동 조절만 못 하고 나머지는 다 돌아간다.
        if self.bundle.dials:
            self.dial = self.bundle.dials[0]
        else:
            self.dial = None
            print("[HW] Dial 없음 - 하드웨어 수동 조절은 비활성. 앱으로는 조작 가능.")

        motors = self.bundle.motors
        # 환기창은 모터 2개가 함께(반대 방향으로) 움직여야 열리고 닫힌다.
        # 둘 중 하나라도 없으면 문이 반만 움직이거나 걸릴 수 있어 아예 진행하지 않는다.
        if len(motors) > max(VENT_MOTOR_A_INDEX, VENT_MOTOR_B_INDEX):
            self.vent_motor_a = motors[VENT_MOTOR_A_INDEX]
            self.vent_motor_b = motors[VENT_MOTOR_B_INDEX]
        else:
            raise HardwareError(
                "환기창 모터 2개(A, B)를 모두 찾을 수 없다. 모터 연결을 확인할 것.")

        # 스프링클러는 세 번째 모터. 없으면 경고만 하고 계속 진행한다.
        if len(motors) > SPRINKLER_MOTOR_INDEX:
            self.sprinkler_motor = motors[SPRINKLER_MOTOR_INDEX]
        else:
            print("[HW] 경고: 스프링클러 모터가 없다. 급수 동작은 생략된다.")

        # 센서 첫 값은 0으로 나온다. 반드시 대기.
        time.sleep(1)
        print("[HW] 초기화 완료")

    def close(self):
        """종료 시 하드웨어를 안전한 상태로 되돌린다."""
        try:
            if self.sprinkler_motor:
                self.sprinkler_motor.speed = 0
            if self.speaker:
                self.speaker.reset()   # 주의: Speaker에는 turn_off()가 없다
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

    def beep(self, freq, volume):
        self.speaker.tune = freq, volume

    def speaker_off(self):
        self.speaker.reset()

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

    def beep(self, freq, volume):
        pass

    def speaker_off(self):
        pass

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
