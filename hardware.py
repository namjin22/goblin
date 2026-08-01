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
#        다르면 아래 두 숫자를 서로 바꾼다.
VENT_MOTOR_INDEX = 0
SPRINKLER_MOTOR_INDEX = 1


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

    def read_button(self):
        """버튼이 클릭되었는가. True/False"""
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

    def set_vent(self, angle, speed=50):
        """환기창 모터를 목표 각도로. 즉시 반환한다(대기하지 않음)."""
        raise NotImplementedError

    def set_sprinkler(self, speed):
        """스프링클러 모터 회전 속도. 0이면 정지."""
        raise NotImplementedError


# --------------------------------------------------------- 실물 하드웨어
class ModiHardware(BaseHardware):
    """실제 MODI Plus 연결.

    모터 배치
      motors[0] = 환기창
      motors[1] = 스프링클러 (급수 표현용, 실제로 물은 나오지 않음)
    """

    def __init__(self, conn_type=None, network_uuid=None):
        self.conn_type = conn_type
        self.network_uuid = network_uuid
        self.bundle = None
        self.env = self.tof = self.dial = self.button = None
        self.led = self.display = self.speaker = None
        self.vent_motor = None
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
        required = {
            "env": self.bundle.envs,
            "button": self.bundle.buttons,
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
        self.button = self.bundle.buttons[0]
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
        if len(motors) > VENT_MOTOR_INDEX:
            self.vent_motor = motors[VENT_MOTOR_INDEX]
        else:
            raise HardwareError("환기창 모터를 찾을 수 없다. 모터 연결을 확인할 것.")

        # 스프링클러는 두 번째 모터. 없으면 경고만 하고 계속 진행한다.
        if len(motors) > SPRINKLER_MOTOR_INDEX:
            self.sprinkler_motor = motors[SPRINKLER_MOTOR_INDEX]
        else:
            print("[HW] 경고: 모터가 %d개뿐이다. 스프링클러 동작은 생략된다."
                  % len(motors))

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

    def read_button(self):
        return bool(self.button.clicked)

    # --- 출력 ---
    def set_led(self, rgb):
        self.led.rgb = rgb

    def show_text(self, text):
        self.display.text = text

    def beep(self, freq, volume):
        self.speaker.tune = freq, volume

    def speaker_off(self):
        self.speaker.reset()

    def set_vent(self, angle, speed=50):
        self.vent_motor.angle = angle, speed

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
        self._vent_angle = 0
        self._sprinkler = 0
        self._temp = 24.0
        self._button_next = False
        self._led_on = False
        self._last = time.time()

    def connect(self):
        print("[MOCK] 가짜 하드웨어로 실행한다. MODI 키트 없이 동작한다.")

    def _step(self):
        now = time.time()
        dt = now - self._last
        self._last = now
        # 환기창이 열려 있으면 식고, 닫혀 있으면 서서히 더워진다.
        if self._vent_angle > 45:
            self._temp -= 0.8 * dt
        else:
            self._temp += 0.35 * dt
        self._temp = max(15.0, min(38.0, self._temp))

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
            "humidity": round(55 + 5 * math.sin(elapsed / 20), 1),
            "illuminance": round(max(0.0, lux), 1),
        }

    def read_distance(self):
        return None      # ToF 미사용

    def read_dial(self):
        return 0

    def read_button(self):
        if self._button_next:
            self._button_next = False
            return True
        return False

    def press_button(self):
        """테스트용. 다음 read_button()이 True를 반환하게 한다."""
        self._button_next = True

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

    def set_vent(self, angle, speed=50):
        self._vent_angle = angle

    def set_sprinkler(self, speed):
        self._sprinkler = speed


def build_hardware(mock=False, conn_type=None, network_uuid=None):
    """설정에 맞는 하드웨어 객체를 만들어 연결까지 마친 뒤 반환한다."""
    hw = MockHardware() if mock else ModiHardware(conn_type, network_uuid)
    hw.connect()
    return hw
