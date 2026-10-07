# -*- coding: utf-8 -*-
"""판단 로직과 액추에이터 제어.

[핵심 설계] time.sleep()으로 기다리지 않는다.

모터가 2초 도는 동안 time.sleep(2)를 하면 그 2초간
센서도 못 읽고 앱 요청도 못 받는다. 대신 '언제까지 바쁜지'를
기록해두고 매 틱마다 확인하는 상태머신으로 만든다.

[모듈 역할]
  Env       온도 -> 환기 판단 / 조도 -> 생장등 판단 / 습도 -> 건조도(급수)·비 감지 판단
  LED       생장등 (조도가 낮으면 켠다)
  Display   짧은 단어 2줄
  (소리)    MODI Speaker는 안 쓴다. alert 진입/온열질환 경고/작물 인식음은 노트북에서 난다 (audio.py)
  Motor A/B 환기창 (두 모터가 함께 움직여야 열리고 닫힌다)
  Motor     스프링클러
  * ToF, Dial, IMU, Joystick, Button, Speaker 미사용 - 물리 버튼 없이 수동 조작은 앱으로만 한다
"""

import json
import os
import time

from profiles import CROP_PROFILES, get_profile
from audio import NullAudio
from state import INSTANT_COMMANDS
from training import COLLECT_TARGET, DATA_DIR, Collector, Trainer, count_images
from vision import read_class_map

def josa(word, with_batchim, without_batchim):
    """마지막 글자 받침 유무로 조사를 고른다. josa("당근", "이", "가") -> "당근이".

    작물 이름이 늘거나 바뀌어도 "당근가"/"상추을(를)" 같은 문장이 안 나가게 한다.
    """
    code = ord(word[-1]) - 0xAC00
    has_batchim = 0 <= code < 11172 and code % 28 != 0
    return word + (with_batchim if has_batchim else without_batchim)


# 환기창이 열려 있는지 닫혀 있는지를 재시작해도 기억해 두는 파일.
# [중요] 환기창은 상대회전이라 실제 위치를 읽을 방법이 없다. 프로그램을 껐다 켰는데
# 창문이 열려 있었다면, "닫혀 있다"고 가정한 채 열기를 시도해 위치가 어긋난다.
# 그래서 마지막 상태를 파일에 남겨 이어받는다. (사람이 손으로 창문을 움직였다면
# 틀릴 수 있으므로, 웹 화면의 "창문 상태 맞추기"로 바로잡을 수 있다.)
VENT_STATE_PATH = "vent_state.json"

# 장치 점검(웹 운영자 패널) 명령. 사람이 눈으로 보면서 하나씩 한다.
# AI 학습 화면이 열려 있는 동안만 미리보기를 이 간격으로 갱신한다. 웹이 몇 초마다 "열려 있다"고
# 알려 주고(studio_ping), 안 오면 알아서 멈춘다. 평소에는 인식용 6초 촬영만 쓴다 - 웹캠을 자주
# 부르면 메인 루프가 멈춘 적이 있어서(camera_preview 주석 참고) 필요한 때만 짧게 쓴다.
STUDIO_FRAME_INTERVAL = 1.2
STUDIO_HOLD = 8.0

HW_CHECK_COMMANDS = {"led_test", "display_test", "jog", "vent_test", "set_roles", "flip_sign",
                     "vent_confirm"}
LED_TEST_STEP = 0.8        # LED 점검에서 색 하나를 보여주는 시간(초)
DISPLAY_TEST_HOLD = 3.0    # Display 점검 문구를 붙잡아 두는 시간(초)
JOG_HOLD = 1.2             # 모터를 살짝 돌린 뒤 되돌리기까지 기다리는 시간(초)

VENT_DURATION = 2.5        # 환기창 여닫는 데 걸리는 시간(초)
SPRINKLER_DURATION = 4.0   # 스프링클러 회전 시간(초)
SPRINKLER_SPEED = 60

# [중요] 사람이 방금 앱으로 환기창을 조작했으면, 자동 로직이 곧바로
# 뒤집으면 안 된다. 안 그러면 "닫기를 눌러도 안 닫힌 것처럼" 보인다 -
# 실제로 겪은 문제: 실내온도(29도)가 옥수수 기준(28도)보다 높은 상태에서
# 사람이 닫자마자, 다음 틱에 "덥다 -> 열어라" 자동조치가 0.15초만에
# 다시 열어버렸다. 생장등의 LIGHT_MIN_HOLD와 같은 원리로 유예시간을 둔다.
VENT_MANUAL_HOLD = 8.0

SCAN_INTERVAL = 6.0        # 몇 초마다 작물을 촬영해서 분류할지
CAMERA_FRAME_INTERVAL = 5.0   # 미리보기 프레임 갱신 주기(초). 그 순간의 스냅샷을 5초마다 보여주는 방식 - 분류(SCAN_INTERVAL)와는 별개

GROWTH_PHOTO_DIR = "growth_photos"
GROWTH_PHOTO_INTERVAL = 7 * 24 * 3600.0   # 1주일마다 성장 사진 한 장

# --- 온열질환 경고 (사람 안전 - 작물 기준과는 별개) ---
# [중요] profiles.py의 vent_temp는 "작물이 덥다고 느끼는 온도"라 작물마다
# 다르다(상추 20도, 옥수수 28도...). 이 기준은 그거랑 다르다 - "사람이
# 온열질환 위험에 노출되는 온도"는 작물이 무엇이든 항상 똑같아야 하므로
# 고정값을 쓴다.
HEAT_DANGER_TEMP = 29.0     # 이 온도 이상이면 농부 온열질환 위험 (원래 34 - 시연 촬영용으로 임시로 낮춤, 실사용 시 34로 되돌릴 것)
HEAT_ALARM_DURATION = 180.0  # 경고음을 울리는 총 시간(초) = 3분
HEAT_ALARM_PULSE = 0.6      # 삑 소리 한 번의 길이(초)
HEAT_ALARM_GAP = 0.6        # 삑 소리 사이 무음 간격(초) - 계속 울리면 시연장 참사라 펄스로
HEAT_ALARM_FREQ = 1500      # 기존 alert 비프(880Hz)보다 높고 급하게 들리도록 구분

# --- 생장등 ---
# 식물 생장등은 원래 적색+청색(마젠타)인데, 흰색으로 쓰기로 함.
GROW_LIGHT_COLOR = (255, 255, 255)
LIGHT_OFF = (0, 0, 0)

# [중요] 생장등 발진 방지
#
# 생장등을 켜면 Env 조도가 올라가고 -> 밝으니 끄고 -> 조도 떨어지고 -> 켜고...
# 무한 반복하며 깜빡인다. 세 겹으로 막는다.
#
#  1) 히스테리시스 - 켜는 기준과 끄는 기준을 다르게
#  2) 최소 유지 시간 - 한 번 바뀌면 그동안은 안 건드림
#  3) 자기 밝기 보정 - 생장등이 스스로 만든 밝기를 빼고 판단  <- 핵심
#
# 3번이 근본 해결이다. 우리가 알고 싶은 건 '주변이 어두운가'이지
# '지금 밝은가'가 아니다. 생장등을 켠 뒤 조도가 얼마나 올랐는지를
# 자동으로 학습해서, 그만큼을 빼고 주변 밝기를 추정한다.
#
# 그래도 센서에 생장등 빛이 정면으로 꽂히면 오차가 커진다.
# Env 모듈은 생장등 빛이 직접 닿지 않는 위치에 배치할 것.
LIGHT_HYSTERESIS = 3.0     # 끄는 기준 = min_lux + 3 (켜는 기준보다 높게)
LIGHT_MIN_HOLD = 8.0       # 한 번 켜거나 끄면 최소 이 시간은 유지

# --- 건조도(급수 판단) ---
# [설계 변경] 카메라(HSV)로 흙 표면을 보고 건조도를 매기려 했으나,
# 카메라를 위에서 내려다보는 각도로 재배치하면서 흙이 프레임에 아예
# 안 잡히게 됐다 (레고 작물만 중앙에 보임). 그래서 이번 데모는
# Env 모듈의 습도(공기 중 습도)를 건조도의 대리 지표로 쓴다.
# vision.soil_dryness()는 지우지 않고 남겨둔다 - 레고가 아닌 실제
# 작물/흙으로 만들 실제 제품에서는 다시 카메라 기반으로 확장할 수 있다.
#
# [정직성 참고] 이것도 여전히 대리 지표다. 습도는 흙 속이 아니라
# 공기 중 수분이라 실제 토양 수분 함량과 다르다. "습도가 낮을수록
# 흙도 마르고 있을 가능성이 크다"는 가정 위에 있다.
def humidity_to_dryness(humidity):
    """습도(%)를 건조도 지표로 뒤집는다. 습도가 낮을수록 건조도가 높다."""
    if humidity is None:
        return None
    return round(max(0.0, min(100.0, 100.0 - humidity)), 1)


# --- 날씨 판단 (비 감지 -> 자동 닫기) ---
# [설계 변경] 기존 결정은 "환기창 자동 닫기 없음 - 닫는 건 사람이 한다"였다.
# 이번에 팀 결정으로 예외를 하나 추가한다: 습도가 비정상적으로 높으면
# "비가 오는 것 같다"고 보고 자동으로 닫는다. 날씨 API 없이 Env 습도만으로
# 추정하는 것이므로 오탐이 있을 수 있다 - 우천은 아니어도 그냥 습한 날일 수 있다.
# 그 외의 경우(그냥 시원해졌다 등)에는 여전히 자동으로 닫지 않는다 - 사람이 닫는다.
#
# [주의] 습도는 humidity_to_dryness()에서 건조도 계산에도 쓰인다. 급수 직후
# 습도가 급등하면(Mock의 급수 시뮬레이션 등) 이 임계값을 넘어 "비"로 오인될
# 수 있다 - 현장에서 실제 값 보고 재조정할 것.
RAIN_HUMIDITY_THRESHOLD = 85.0


class Controller:
    """센서값을 판단하고 액추에이터를 움직인다. 메인 루프에서만 쓴다."""

    def __init__(self, hw, store, vision=None, camera_preview=False, force_crop=None,
                 audio=None, data_dir=DATA_DIR, model_dir="models", train_args=None, train_root=None):
        self.hw = hw
        # 소리는 MODI Speaker가 아니라 노트북에서 낸다 (audio.py 참고). 없으면 무음.
        self.audio = audio if audio is not None else NullAudio()
        store.update(sound_on=self.audio.enabled)
        self.store = store
        self.vision = vision
        # [시연 촬영용, 임시] 켜두면 실제 카메라 인식 결과를 무시하고 항상
        # 이 작물로 취급한다 - 브릭 인식이 매번 잘 안 맞아서 촬영이 힘들 때
        # 쓴다. 촬영 끝나면 반드시 끌 것 (묻지 않는다는 핵심 정체성과
        # 어긋나는 임시 우회다).
        self.force_crop = force_crop
        # [기본 꺼짐] 실시간 미리보기가 vision.capture()를 훨씬 자주(0.5초마다)
        # 부르는데, 실물 테스트에서 이게 메인 루프를 통째로 멈추게 하는
        # 것으로 의심됨(웹캠 드라이버가 잦은 호출에 멈추는 듯) - 분류용
        # 6초 주기 촬영은 안정적이었다. 확실해지기 전까진 기본 꺼둔다.
        self.camera_preview = camera_preview

        self._busy_until = 0.0
        self._busy_action = None
        self._on_finish = None

        self._last_scan = 0.0
        self._last_growth_week = {}   # crop_key -> 마지막으로 사진 남긴 주차
        self._last_camera_frame = 0.0

        self._last_level = None
        self._last_display = None

        self._heat_alarm_active = False    # 지금 고온 구간 안에서 이미 경고를 시작했는지
        self._heat_alarm_until = 0.0       # 경고 종료 예정 시각 (0이면 비활성)
        self._heat_alarm_next_pulse = 0.0  # 다음 삑/무음 전환 시각

        self._light_on = False
        self._light_changed_at = 0.0
        self._light_boost = 0.0        # 생장등이 만드는 밝기 (자동 학습)
        self._lux_before_light = 0.0   # 켜기 직전의 조도

        self._vent_manual_at = 0.0     # 사람이 마지막으로 앱에서 환기창을 조작한 시각

        # 모의 실행은 가짜 상태를 파일에 남기면 실물 실행 때 오해하므로 이어받지 않는다.
        if not self.store.get("mock"):
            saved = self._load_vent_state()
            if saved is not None:
                self.store.update(vent_open=saved)

        # 장치 점검(웹 운영자 패널)용 진행 상태. 전부 "언제까지/언제 할지"만 기억하는
        # 타임스탬프 방식이다 - sleep으로 기다리면 센서도 API도 멈춘다.
        self._led_test = None            # {"steps": [(rgb, 초), ...], "i": 0, "next": 시각}
        self._display_hold_until = 0.0   # 이 시각까지 Display에 점검 문구를 붙잡아 둔다
        self._vent_test_close_at = 0.0   # 시험 구동으로 연 창문을 닫을 시각 (0이면 없음)
        self._jog_back = None            # (motor_id, delta, 시각): 살짝 돌린 모터를 되돌릴 계획
        self._last_hw_refresh = 0.0

        self._publish_hw()

        # --- AI 학습 (웹) ---
        self._studio_until = 0.0
        self._last_studio_frame = 0.0
        self.collector = Collector(vision, store, self.audio, self._publish_preview, data_dir=data_dir)
        self.trainer = Trainer(store, vision, self.audio, root=train_root, data_dir=data_dir,
                               model_dir=model_dir, extra_args=train_args)
        # 모의 비전은 학습된 모델이 없지만 모든 작물을 "아는 척"한다 (웹 화면 개발용).
        # 모의 모드에서 직접 학습시키면(model_dir 아래에 저장) 그 모델의 클래스로 바뀐다.
        classes = read_class_map(os.path.join(model_dir, "class_map.json"))
        if classes is None and vision is not None and not hasattr(vision, "cap"):
            classes = list(CROP_PROFILES) + ["background"]
        store.update(dataset=count_images(data_dir), model_classes=classes,
                     camera_real=hasattr(vision, "cap"))

    def shutdown(self):
        """프로그램을 끌 때: 돌고 있는 학습 프로세스가 고아로 남지 않게 정리한다."""
        proc = getattr(self.trainer, "_proc", None)
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def update_studio_preview(self):
        """AI 학습 화면이 열려 있는 동안만 웹 미리보기를 빠르게 갱신한다."""
        now = time.time()
        if (self.vision is None or now >= self._studio_until or self.collector.active
                or now - self._last_studio_frame < STUDIO_FRAME_INTERVAL):
            return
        self._last_studio_frame = now
        frame = self.vision.capture()
        if frame is not None:
            self._publish_preview(frame)

    def _publish_hw(self):
        """하드웨어 구성(모터 목록/역할/방향/ready)을 웹에 알린다. 바뀔 때만 부르면 된다."""
        try:
            self.store.update(hw=self.hw.describe())
        except Exception as e:
            print("[CTRL] 하드웨어 구성 읽기 실패(무시):", e)

    @property
    def vent_ready(self):
        """환기창 모터 A/B 역할이 정해졌는가. 아니면 환기창은 절대 움직이지 않는다."""
        return getattr(self.hw, "vent_ready", True)

    @property
    def sprinkler_ready(self):
        return getattr(self.hw, "sprinkler_ready", True)

    # ------------------------------------------------------ 환기창 상태 기억
    def _load_vent_state(self):
        try:
            with open(VENT_STATE_PATH, "r", encoding="utf-8") as f:
                return bool(json.load(f)["vent_open"])
        except (OSError, ValueError, KeyError):
            return None

    def _save_vent_state(self):
        if self.store.get("mock"):
            return
        try:
            with open(VENT_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"vent_open": bool(self.store.get("vent_open"))}, f)
        except OSError as e:
            print("[CTRL] 환기창 상태 저장 실패(무시):", e)

    # ------------------------------------------------------ 바쁨 상태
    @property
    def busy(self):
        return time.time() < self._busy_until

    def _start_action(self, name, duration, on_finish=None):
        self._busy_action = name
        self._busy_until = time.time() + duration
        self._on_finish = on_finish
        self.store.update(busy=True, busy_action=name)

    def _finish_if_done(self):
        if self._busy_action and not self.busy:
            cb = self._on_finish
            name = self._busy_action
            self._busy_action = None
            self._on_finish = None
            if cb:
                cb()
            self.store.update(busy=False, busy_action=None)
            self.store.add_history("done", name)

    # ------------------------------------------------------ 액추에이터
    def open_vent(self):
        # [중요] hardware.open_vent()는 이제 절대각이 아니라 상대회전이다.
        # 이미 열려 있는데 또 열면 그만큼 더 돌아가버린다(원래 자리로
        # 돌아올 수 없게 됨) - 그래서 "닫혀 있을 때만" 열도록 막는다.
        if self.busy or self.store.get("vent_open") or not self.vent_ready:
            return False
        self.hw.open_vent()
        self.store.update(vent_open=True)
        self._save_vent_state()
        self.store.add_history("vent_open", "창문을 열었습니다")
        self._start_action("vent_open", VENT_DURATION)
        return True

    def close_vent(self):
        # 같은 이유로 "열려 있을 때만" 닫는다.
        if self.busy or not self.store.get("vent_open") or not self.vent_ready:
            return False
        self.hw.close_vent()
        self.store.update(vent_open=False)
        self._save_vent_state()
        self.store.add_history("vent_close", "창문을 닫았습니다")
        self._start_action("vent_close", VENT_DURATION)
        return True

    def toggle_vent(self):
        """열려 있으면 닫고, 닫혀 있으면 연다.

        사람이 앱으로 조작할 때 쓴다(물리 버튼 없음). 자동 조치는 decide()의
        auto_action("vent_open"/"vent_close")을 통해서만 닫거나 연다 - 온도로
        열기, 비 감지(습도)로 닫기 두 경우만 자동이고 그 외엔 사람이 한다.
        """
        if self.store.get("vent_open"):
            return self.close_vent()
        return self.open_vent()

    def water(self):
        """스프링클러를 돌린다.

        실제로 물이 나오지는 않는다. 레고 스프링클러 모형이 회전하여
        급수 동작을 표현한다. 시연 중에는 이 타이밍에 맞춰
        분무기로 흙 표면에 소량 분무한다.
        """
        # 모터가 없는데 "물을 주었습니다"라고 하면 화면이 거짓말이 된다
        if self.busy or not self.sprinkler_ready:
            return False
        self.hw.set_sprinkler(SPRINKLER_SPEED)
        self.store.update(sprinkler_on=True)
        self.store.add_history("water", "물을 주었습니다")

        def stop():
            self.hw.set_sprinkler(0)
            self.store.update(sprinkler_on=False)

        self._start_action("water", SPRINKLER_DURATION, on_finish=stop)
        return True

    # ------------------------------------------------------ 생장등
    def ambient_lux(self, lux):
        """생장등이 스스로 만든 밝기를 뺀 '주변 밝기' 추정값.

        우리가 알고 싶은 건 '주변이 어두운가'이지 '지금 밝은가'가 아니다.
        """
        if lux is None:
            return None
        if self._light_on:
            return max(0.0, lux - self._light_boost)
        return lux

    def update_grow_light(self, lux, profile):
        """주변이 어두우면 생장등을 켠다."""
        if lux is None:
            return

        now = time.time()
        elapsed = now - self._light_changed_at

        # 생장등을 켠 직후 조도가 얼마나 올랐는지 학습한다.
        # 이 값을 빼야 주변 밝기를 알 수 있다.
        if self._light_on and 1.0 < elapsed < LIGHT_MIN_HOLD:
            measured = max(0.0, lux - self._lux_before_light)
            # 완만하게 갱신해서 순간적인 튐에 흔들리지 않게 한다
            self._light_boost = self._light_boost * 0.7 + measured * 0.3

        if elapsed < LIGHT_MIN_HOLD:
            return      # 아직 유지 시간 - 건드리지 않는다

        ambient = self.ambient_lux(lux)
        on_below = profile["min_lux"]                      # 이보다 어두우면 켠다
        off_above = profile["min_lux"] + LIGHT_HYSTERESIS  # 이보다 밝으면 끈다

        if not self._light_on and ambient < on_below:
            self._lux_before_light = lux
            self._set_light(True)
        elif self._light_on and ambient > off_above:
            self._set_light(False)

    def _set_light(self, on):
        self._light_on = on
        self._light_changed_at = time.time()
        self.hw.set_led(GROW_LIGHT_COLOR if on else LIGHT_OFF)
        self.store.update(light_on=on)
        self.store.add_history(
            "light", "생장등을 켰습니다" if on else "생장등을 껐습니다")

    # ------------------------------------------------------ 카메라 미리보기
    def update_camera_frame(self):
        """앱의 실시간 미리보기용 프레임을 갱신한다.

        작물 분류(update_scan, 6초 주기)와는 별개로 더 자주(0.5초) 갱신해서
        "라이브"처럼 보이게 한다. Mock 비전은 진짜 프레임이 없어서 건너뛴다.
        """
        if self.vision is None or not hasattr(self.vision, "cv2"):
            return
        now = time.time()
        if now - self._last_camera_frame < CAMERA_FRAME_INTERVAL:
            return
        self._last_camera_frame = now

        frame = self.vision.capture()
        if frame is None:
            return
        ok, buf = self.vision.cv2.imencode(".jpg", frame)
        if ok:
            self.store.set_camera_frame(buf.tobytes())

    def _publish_preview(self, frame):
        """이미 찍은 프레임을 JPEG로 만들어 웹 미리보기에 올린다. 추가 캡처 없음."""
        cv2 = getattr(self.vision, "cv2", None)
        if cv2 is None:      # MockVision은 진짜 프레임이 없다
            return
        try:
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                self.store.set_camera_frame(buf.tobytes())
        except Exception as e:
            print("[CTRL] 미리보기 인코딩 실패(무시):", e)

    # ------------------------------------------------------ 비전 스캔
    def update_scan(self):
        """일정 주기마다 작물을 촬영해서 인식한다.

        ToF 거리 게이트를 쓰지 않으므로, 어르신은 작물을 카메라 앞에
        두기만 하면 된다. 아무 조작도 필요 없다.

        건조도는 더 이상 여기서 카메라로 재지 않는다 (humidity_to_dryness 참고).
        """
        if self.vision is None:
            return
        if time.time() - self._last_scan < SCAN_INTERVAL:
            return

        self._last_scan = time.time()
        frame = self.vision.capture()
        if frame is None:
            return

        # 분류하려고 이미 찍은 프레임을 웹 미리보기로도 쓴다. 미리보기 전용으로
        # 웹캠을 따로 부르면 메인 루프가 멈춘 적이 있어서(camera_preview 참고),
        # 추가 캡처 없이 6초 주기로 갱신하는 가장 안전한 방법이다.
        self._publish_preview(frame)

        crop_key = self.force_crop if self.force_crop else self.vision.classify_crop(frame)

        # 모델이 프로파일에 없는 클래스를 내놓으면(작물 구성을 바꾼 직후 등) 그 작물의 기준을 알 수
        # 없다. None으로 두면 "인식 못 하면 이전 작물 유지" 규칙 때문에 확률 막대는 새 클래스를
        # 가리키는데 화면 이름만 옛 작물로 남는 모순이 생긴다(실제로 상추 95%인데 '당근'이 떴다).
        # 그래서 "작물이 안 보인다"로 정리한다.
        if crop_key and crop_key != "background" and crop_key not in CROP_PROFILES:
            crop_key = "background"

        updates = {
            # force_crop이면 화면의 작물은 강제값이라 모델 확률을 보여주면 거짓이 된다
            "crop_probs": None if self.force_crop else getattr(self.vision, "last_probs", None),
        }
        crop_started_at = self.store.get("crop_started_at")
        if crop_key == "background":
            # 모델이 확신을 갖고 "작물 없음"이라고 판단했다. 마지막으로
            # 인식했던 작물을 계속 붙들고 있으면 안 된다 - 실제로 치웠는데
            # 화면엔 계속 "옥수수"라고 뜨는 문제가 이거였다.
            if self.store.get("crop_key") is not None:
                self.store.add_history("scan", "작물이 안 보여요")
                updates["crop_key"] = None
                updates["crop_name"] = "확인 중"
                updates["profile_name"] = "확인 중"
                updates["crop_started_at"] = None
        elif crop_key:
            profile = get_profile(crop_key)
            # 작물이 바뀐 경우에만 기록을 남기고, 성장 일수 기준(첫 인식 시각)을 새로 잡는다.
            if crop_key != self.store.get("crop_key"):
                self.store.add_history(
                    "scan", "%s 확인했습니다" % josa(profile["name"], "을", "를"))
                crop_started_at = time.time()
                updates["crop_started_at"] = crop_started_at
                self.audio.play("recognized")   # 핵심 장면: 웹의 인식 알림과 같은 순간에 "띠리링"
                self._last_growth_week.pop(crop_key, None)
            updates["crop_key"] = crop_key
            updates["crop_name"] = profile["name"]
            updates["profile_name"] = profile["name"]
        if updates:
            self.store.update(**updates)

        if crop_key and crop_key != "background" and crop_started_at:
            profile = get_profile(crop_key)
            self._maybe_save_growth_photo(crop_key, profile["name"], frame, crop_started_at)

    def _maybe_save_growth_photo(self, crop_key, crop_name, frame, crop_started_at):
        """일주일에 한 번, 지금 작물의 성장 기록 사진을 남긴다."""
        week_index = int((time.time() - crop_started_at) // GROWTH_PHOTO_INTERVAL)
        if self._last_growth_week.get(crop_key) == week_index:
            return

        os.makedirs(GROWTH_PHOTO_DIR, exist_ok=True)
        filename = "%s_week%d_%d.jpg" % (crop_key, week_index, int(time.time()))
        path = os.path.join(GROWTH_PHOTO_DIR, filename)

        if self.vision.save_snapshot(frame, path):
            self.store.add_growth_photo(crop_key, crop_name, week_index, filename)
            self.store.add_history(
                "growth_photo", "%s주차 성장 사진을 남겼습니다" % (week_index + 1))
        self._last_growth_week[crop_key] = week_index

    # ------------------------------------------------------ 판단
    def decide(self, snap):
        """센서값과 프로파일로 상태를 정한다.

        반환: (level, 긴 문장, 짧은 단어, 자동조치, 판단 근거)
              긴 문장 -> 앱 / 짧은 단어 -> Display / 판단 근거 -> 웹 화면의 "왜?" 한 줄

        우선순위: 폭염(온열질환 예방, 열기) > 비 감지(닫기) > 건조(급수) > 정상.
        폭염이 비 감지보다 우선인 이유: 사람 안전(온열질환)이 젖음 방지보다
        급하다고 봤다 - 실제로 둘이 동시에 뜨는 경우는 드물 것이다.
        """
        profile = get_profile(snap.get("crop_key"))
        temp = snap.get("temperature")
        humidity = snap.get("humidity")
        dry = snap.get("dryness")
        crop = profile["name"]
        vent_temp = profile["vent_temp"]

        # 조도는 생장등이 알아서 처리하므로 메시지로 띄우지 않는다.
        if temp is not None and temp > vent_temp + 3:
            return ("alert", "너무 덥습니다. 창문을 열까요?", "더워요!", "vent_open",
                    "지금 %.1f°C — %s 기준(%d°C)을 3°C 넘게 초과" % (temp, crop, vent_temp))

        if temp is not None and temp > vent_temp:
            return ("warn", "조금 덥습니다", "조금 더움", "vent_open",
                    "지금 %.1f°C — %s 기준(%d°C)보다 높음" % (temp, crop, vent_temp))

        if humidity is not None and humidity > RAIN_HUMIDITY_THRESHOLD:
            return ("warn", "비가 오는 것 같아요. 창문을 닫을까요?", "비 옴", "vent_close",
                    "습도 %.0f%% — 비 기준(%d%%) 초과" % (humidity, RAIN_HUMIDITY_THRESHOLD))

        if dry is not None and dry > profile["dry_limit"]:
            return ("alert", "흙이 말랐어요. 물을 줄까요?", "물 필요", "water",
                    "건조도 %.0f — %s 기준(%d) 초과" % (dry, crop, profile["dry_limit"]))

        # 작물이 아직 인식 안 됐으면(DEFAULT_PROFILE, name="확인 중") "확인
        # 중가 잘 자라고 있어요" 같은 말이 안 되는 문장이 나간다 - 정직하게
        # "아직 안 보인다"고 말할 것.
        if snap.get("crop_key") is None:
            return "good", "아직 작물이 안 보여요", "대기 중", None, "작물을 인식하는 중이라 기본 기준을 쓰는 중"

        if temp is not None:
            reason = "지금 %.1f°C — %s 기준(%d°C) 이내" % (temp, crop, vent_temp)
        else:
            reason = "센서값을 읽는 중"
        return "good", "%s 잘 자라고 있어요" % josa(crop, "이", "가"), "좋아요", None, reason

    # ------------------------------------------------------ 출력
    def render_display(self, crop_name, short):
        """Display 2줄. 바뀔 때만 새로 쓴다.

        매 틱마다 새로 쓰면 화면이 깜빡이고 통신도 낭비된다.
        96x96이라 긴 문장은 읽을 수 없다. 짧은 단어만.
        """
        # 운영자가 "화면에 글자 띄우기"를 눌렀으면 그 문구를 잠깐 붙잡아 둔다
        if time.time() < self._display_hold_until:
            return

        if self.busy and self._busy_action:
            short = {
                "vent_open": "창문 여는중",
                "vent_close": "창문 닫는중",
                "water": "물 주는중",
                "vent_test": "창문 점검중",
                "jog": "모터 점검중",
            }.get(self._busy_action, short)

        text = "%s\n%s" % (crop_name, short)
        if text == self._last_display:
            return
        self._last_display = text
        self.hw.show_text(text)
        self.store.update(display_text=text)   # 웹 화면이 같은 두 줄을 그대로 보여준다

    def update_heat_alarm(self, temp):
        """온도가 HEAT_DANGER_TEMP 이상이면 3분간 경고음을 울린다.

        작물별 vent_temp(냉방 판단)와는 별개의, 사람(농부) 안전을 위한
        고정 기준이다. 계속 울리면 시연장 참사라 삑-무음을 반복하는
        펄스로 만들었다. HEAT_DANGER_TEMP 아래로 내려갔다가 다시 올라가면
        새로 경고가 시작된다(같은 고온 구간에서는 한 번만 3분 채운다).
        """
        now = time.time()

        if temp is not None and temp >= HEAT_DANGER_TEMP:
            if not self._heat_alarm_active:
                self._heat_alarm_active = True
                self._heat_alarm_until = now + HEAT_ALARM_DURATION
                self._heat_alarm_next_pulse = now
                self.store.add_history(
                    "heat_alarm",
                    "온도 %.1f도 - 온열질환 위험. 경고음을 울립니다" % temp)
        else:
            # 위험 온도 아래로 내려오면 다음에 다시 넘을 때 재발동하도록 리셋한다.
            self._heat_alarm_active = False

        if now >= self._heat_alarm_until:
            return

        # 소리 길이는 audio가 알아서 끝낸다(끄는 단계가 필요 없다). 펄스 + 무음 간격마다 한 번씩.
        if now >= self._heat_alarm_next_pulse:
            self.audio.play("heat")
            self._heat_alarm_next_pulse = now + HEAT_ALARM_PULSE + HEAT_ALARM_GAP

    def render_sound(self, level):
        """alert에 '진입하는 순간'에만 짧게 울린다.

        계속 울리면 시연장에서 재앙이다. 온열질환 경고음(update_heat_alarm)이
        울리는 동안에는 이 짧은 삑을 겹쳐 울리지 않는다 - 우선순위가
        더 높은 경고라서 방해하면 안 된다.
        """
        now = time.time()

        if now < self._heat_alarm_until:
            self._last_level = level
            return

        if level == "alert" and self._last_level != "alert":
            self.audio.play("alert")

        self._last_level = level

    # ------------------------------------------------------ 명령 처리
    def handle_command(self, cmd, args=None):
        """앱(웹)에서 온 명령을 실행한다. args는 jog/set_roles/flip_sign 같은 인자 있는 명령용."""
        if cmd in ("vent_open", "vent_close", "vent_toggle"):
            # 사람이 방금 조작했다는 기록. VENT_MANUAL_HOLD 동안은 자동
            # 조치가 이걸 뒤집지 않는다 (아래 tick()의 자동 조치 단계 참고).
            self._vent_manual_at = time.time()
            if not self.vent_ready:
                if getattr(self.hw, "vent_roles_ok", True):
                    why = "환기창 방향을 아직 확인하지 않아 움직이지 않았어요"
                else:
                    why = "환기창 모터 역할이 정해지지 않아 움직이지 않았어요"
                self.store.add_history("vent_blocked", why)
                return False
        if cmd == "water" and not self.sprinkler_ready:
            self.store.add_history("water_blocked", "스프링클러 모터가 없어 물을 주지 못했어요")
            return False
        if cmd in HW_CHECK_COMMANDS:
            return self.handle_hw_check(cmd, args or {})
        if cmd == "vent_open":
            return self.open_vent()
        if cmd == "vent_close":
            return self.close_vent()
        if cmd == "vent_toggle":
            return self.toggle_vent()
        if cmd == "water":
            return self.water()
        if cmd == "scan":
            self._last_scan = 0.0     # 다음 틱에 바로 촬영
            return True
        if cmd == "light_toggle":
            self._set_light(not self._light_on)
            return True
        if cmd == "sound_test":
            self.audio.play("test")
            return True
        if cmd == "studio_ping":
            self._studio_until = time.time() + STUDIO_HOLD
            return True
        if cmd == "collect_start":
            a = args or {}
            return self.collector.start(a.get("crop"), a.get("target", COLLECT_TARGET))
        if cmd == "collect_stop":
            return self.collector.stop()
        if cmd == "data_clear":
            self.collector.clear((args or {}).get("crop"))
            return True
        if cmd == "train_start":
            if self.collector.active:
                self.store.add_history("train", "사진을 찍는 중에는 학습을 시작할 수 없어요")
                return False
            return self.trainer.start()
        if cmd == "train_stop":
            return self.trainer.stop()
        if cmd in ("vent_mark_open", "vent_mark_closed"):
            # 모터는 돌리지 않는다. 실제 창문 위치를 사람이 보고 시스템의 믿음을 바로잡는다.
            is_open = cmd == "vent_mark_open"
            self.store.update(vent_open=is_open, vent_assumed=False)
            self._save_vent_state()
            self.store.add_history(
                "vent_sync", "창문 상태를 '%s'로 맞췄습니다" % ("열림" if is_open else "닫힘"))
            return True
        if cmd in ("auto_on", "auto_off"):
            on = cmd == "auto_on"
            if self.store.get("auto_mode") != on:
                self.store.update(auto_mode=on)
                self.store.add_history(
                    "auto", "자동 조치를 켰습니다" if on else "자동 조치를 껐습니다")
            return True
        return False

    # ------------------------------------------------------ 장치 점검 (웹 운영자 패널)
    def handle_hw_check(self, cmd, args):
        """사람이 눈으로 확인하는 점검 명령. 하나씩, 아주 작게만 움직인다."""
        now = time.time()

        if cmd == "led_test":
            # 빨강 -> 초록 -> 파랑 -> 흰색. 색 하나가 안 나오면 선/모듈 문제다.
            steps = [((255, 0, 0), LED_TEST_STEP), ((0, 255, 0), LED_TEST_STEP),
                     ((0, 0, 255), LED_TEST_STEP), ((255, 255, 255), LED_TEST_STEP)]
            self._led_test = {"steps": steps, "i": 0, "next": now + steps[0][1]}
            self.hw.set_led(steps[0][0])
            self.store.add_history("hw_check", "LED 점검: 빨강 → 초록 → 파랑 → 흰색")
            return True

        if cmd == "display_test":
            self._display_hold_until = now + DISPLAY_TEST_HOLD
            self.hw.show_text("농깨비\n점검중")
            self.store.add_history("hw_check", "Display 점검: '농깨비 / 점검중'을 띄웠습니다")
            return True

        if cmd == "jog":
            motor_id, delta = args.get("motor_id"), int(args.get("delta", 20))
            try:
                self.hw.jog_motor(motor_id, delta)
            except Exception as e:
                self.store.add_history("hw_check", "모터 점검 실패: %s" % e)
                return False
            # 살짝 돌렸다가 같은 만큼 되돌려서 제자리로 돌아오게 한다
            self._jog_back = (motor_id, -delta, now + JOG_HOLD)
            self.store.add_history("hw_check", "모터 0x%X를 %+d° 살짝 돌렸다가 되돌립니다" % (motor_id, delta))
            self._start_action("jog", JOG_HOLD * 2 + 0.3)
            return True

        if cmd == "vent_test":
            # 환기창을 열었다가 같은 부호로 바로 닫는다 (방향이 맞는지 눈으로 보는 용도).
            # 이미 열려 있으면 안 한다 - 열린 채로 또 열면 위치가 어긋난다.
            # 방향 확인 전이라도 시험 구동은 가능해야 한다(그게 확인하는 방법이다)
            if not getattr(self.hw, "vent_roles_ok", True) or self.store.get("vent_open"):
                self.store.add_history("hw_check", "환기창 점검은 모터 역할이 정해지고 창문이 닫혀 있을 때만 할 수 있어요")
                return False
            self.hw.open_vent()
            self._vent_test_close_at = now + VENT_DURATION
            self.store.add_history("hw_check", "환기창 점검: 열었다가 바로 닫습니다")
            self._start_action("vent_test", VENT_DURATION * 2 + 0.3)
            return True

        if cmd == "vent_confirm":
            try:
                self.hw.confirm_vent()
            except Exception as e:
                self.store.add_history("hw_check", "방향 확인 실패: %s" % e)
                return False
            self.store.add_history("hw_check", "환기창 방향을 확인했습니다. 이제 창문을 움직일 수 있어요")
            self._publish_hw()
            return True

        if cmd in ("set_roles", "flip_sign"):
            # 환기창이 열린 채로 역할/방향을 바꾸면 "열린 위치"의 의미가 달라져 위치가 어긋난다
            if self.store.get("vent_open"):
                self.store.add_history("hw_check", "창문이 열려 있어서 모터 설정을 바꾸지 않았어요. 먼저 닫아 주세요")
                return False
            try:
                if cmd == "set_roles":
                    self.hw.set_roles(args.get("vent_a"), args.get("vent_b"), args.get("sprinkler"))
                    self.store.add_history("hw_check", "모터 역할을 저장했습니다")
                else:
                    self.hw.flip_sign(args.get("which"))
                    self.store.add_history(
                        "hw_check", "환기창 모터 %s의 방향을 뒤집었습니다. 다시 확인해 주세요" % str(args.get("which")).upper())
            except Exception as e:
                self.store.add_history("hw_check", "모터 설정 실패: %s" % e)
                return False
            self._publish_hw()
            return True

        return False

    def update_hw_refresh(self):
        """2초마다 모터 구성이 바뀌었는지 본다(늦게 인식된 모터 반영). 바뀌면 웹에 다시 알린다."""
        now = time.time()
        if now - self._last_hw_refresh < 2.0:
            return
        self._last_hw_refresh = now
        if self.hw.refresh():
            self._publish_hw()
            self.store.add_history("hw_change", "모터 연결이 바뀌었어요")

    def update_hw_checks(self):
        """진행 중인 점검(LED 색 순서, 시험 구동 복귀, Display 문구)을 한 틱씩 이어간다."""
        now = time.time()

        t = self._led_test
        if t and now >= t["next"]:
            t["i"] += 1
            if t["i"] < len(t["steps"]):
                rgb, secs = t["steps"][t["i"]]
                self.hw.set_led(rgb)
                t["next"] = now + secs
            else:
                self._led_test = None
                self.hw.set_led(GROW_LIGHT_COLOR if self._light_on else LIGHT_OFF)  # 원래 생장등 상태로

        if self._jog_back and now >= self._jog_back[2]:
            motor_id, delta, _ = self._jog_back
            self._jog_back = None
            try:
                self.hw.jog_motor(motor_id, delta)
            except Exception as e:
                print("[CTRL] 모터 되돌리기 실패:", e)

        if self._vent_test_close_at and now >= self._vent_test_close_at:
            self._vent_test_close_at = 0.0
            self.hw.close_vent()

        if self._display_hold_until and now >= self._display_hold_until:
            self._display_hold_until = 0.0
            self._last_display = None   # 평소 문구를 다시 쓰게 한다

    # ------------------------------------------------------ 메인 틱
    def tick(self, auto_mode=True):
        """메인 루프에서 매번 호출한다."""
        self._finish_if_done()
        self.update_hw_checks()
        self.update_hw_refresh()
        self.collector.tick()
        self.trainer.tick()
        self.update_studio_preview()

        # 1) 센서 읽기
        env = self.hw.read_env()
        self.store.update(
            temperature=env["temperature"],
            humidity=env["humidity"],
            illuminance=env["illuminance"],
            dryness=humidity_to_dryness(env["humidity"]),
        )

        # 2) 주기적 촬영 (분류) + (기본 꺼짐) 실시간 미리보기 프레임
        self.update_scan()
        if self.camera_preview:
            self.update_camera_frame()

        # 3) 판단
        snap = self.store.snapshot()
        profile = get_profile(snap.get("crop_key"))
        level, message, short, auto_action, reason = self.decide(snap)
        self.store.update(level=level, message=message, short=short, reason=reason)

        # 4) 출력
        self.update_grow_light(env["illuminance"], profile)
        self.render_display(snap.get("crop_name", "확인 중"), short)
        self.update_heat_alarm(env["temperature"])
        self.render_sound(level)

        # 5) 앱에서 온 명령 (물리 버튼 없음 - 수동 조작은 앱으로만 한다)
        pending = self.store.pop_command()
        if pending and (not self.busy or pending["cmd"] in INSTANT_COMMANDS):
            self.handle_command(pending["cmd"], pending.get("args"))
            return

        # 6) 자동 조치
        #    사람이 승인하지 않아도 시스템이 알아서 하는 부분.
        #    "묻지 않는다"의 실체다.
        #    [예외] 환기창을 자동으로 닫는 건 "비 감지"(RAIN_HUMIDITY_THRESHOLD)
        #    한 가지 경우뿐이다. 그 외에는(예: 그냥 시원해짐) 여전히 사람이 닫는다.
        #    [중요] 사람이 방금(VENT_MANUAL_HOLD 이내) 앱으로 조작했으면
        #    자동 조치가 그걸 곧바로 뒤집지 않는다 - 안 그러면 "닫아도
        #    바로 다시 열리는" 것처럼 보인다 (실제로 겪은 문제).
        vent_manual_hold = time.time() - self._vent_manual_at < VENT_MANUAL_HOLD
        # 자동 조치 on/off는 앱에서 바꿀 수 있어서 Store가 진실이다.
        # (main.py의 --no-auto는 시작할 때 Store에 초기값으로 넣는다)
        auto_mode = self.store.get("auto_mode", auto_mode)
        if auto_mode and auto_action and not self.busy:
            if auto_action == "vent_open" and not snap.get("vent_open") and not vent_manual_hold:
                self.open_vent()
            elif auto_action == "vent_close" and snap.get("vent_open") and not vent_manual_hold:
                self.close_vent()
            elif auto_action == "water":
                self.water()
