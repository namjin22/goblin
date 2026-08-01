# -*- coding: utf-8 -*-
"""판단 로직과 액추에이터 제어.

[핵심 설계] time.sleep()으로 기다리지 않는다.

모터가 2초 도는 동안 time.sleep(2)를 하면 그 2초간
센서도 못 읽고 앱 요청도 못 받는다. 대신 '언제까지 바쁜지'를
기록해두고 매 틱마다 확인하는 상태머신으로 만든다.

[모듈 역할]
  Env       온도 -> 환기 판단 / 조도 -> 생장등 판단 / 습도 -> 건조도(급수)·비 감지 판단
  Button    창문 열기/닫기 토글 (이 일만 한다)
  LED       생장등 (조도가 낮으면 켠다)
  Display   짧은 단어 2줄
  Speaker   alert 진입 순간에만 짧게 삑 (온열질환 예방 경고 포함)
  Motor A/B 환기창 (두 모터가 반대 방향으로 함께 움직여야 열리고 닫힌다)
  Motor     스프링클러
  * ToF, Dial, IMU, Joystick 미사용
"""

import os
import time

from profiles import get_profile

VENT_DURATION = 2.5        # 환기창 여닫는 데 걸리는 시간(초)
SPRINKLER_DURATION = 4.0   # 스프링클러 회전 시간(초)
SPRINKLER_SPEED = 60

SCAN_INTERVAL = 6.0        # 몇 초마다 작물·흙을 촬영할지

GROWTH_PHOTO_DIR = "growth_photos"
GROWTH_PHOTO_INTERVAL = 7 * 24 * 3600.0   # 1주일마다 성장 사진 한 장

BEEP_DURATION = 0.4        # 경고음 길이. 이 시간 뒤 자동으로 끈다

# --- 생장등 ---
# 식물 생장등은 적색+청색이라 실제로 마젠타빛으로 보인다.
# 흰색으로 바꾸고 싶으면 (255, 255, 255).
GROW_LIGHT_COLOR = (255, 0, 255)
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

    def __init__(self, hw, store, vision=None):
        self.hw = hw
        self.store = store
        self.vision = vision

        self._busy_until = 0.0
        self._busy_action = None
        self._on_finish = None

        self._last_scan = 0.0
        self._last_growth_week = {}   # crop_key -> 마지막으로 사진 남긴 주차

        self._beep_until = 0.0
        self._last_level = None
        self._last_display = None

        self._light_on = False
        self._light_changed_at = 0.0
        self._light_boost = 0.0        # 생장등이 만드는 밝기 (자동 학습)
        self._lux_before_light = 0.0   # 켜기 직전의 조도

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
        if self.busy:
            return False
        self.hw.open_vent()
        self.store.update(vent_open=True)
        self.store.add_history("vent_open", "창문을 열었습니다")
        self._start_action("vent_open", VENT_DURATION)
        return True

    def close_vent(self):
        if self.busy:
            return False
        self.hw.close_vent()
        self.store.update(vent_open=False)
        self.store.add_history("vent_close", "창문을 닫았습니다")
        self._start_action("vent_close", VENT_DURATION)
        return True

    def toggle_vent(self):
        """열려 있으면 닫고, 닫혀 있으면 연다.

        사람이 Button 또는 앱으로 조작할 때 쓴다. 자동 조치는 decide()의
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
        if self.busy:
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

        crop_key = self.vision.classify_crop(frame)

        updates = {}
        crop_started_at = self.store.get("crop_started_at")
        if crop_key:
            profile = get_profile(crop_key)
            # 작물이 바뀐 경우에만 기록을 남기고, 성장 일수 기준(첫 인식 시각)을 새로 잡는다.
            if crop_key != self.store.get("crop_key"):
                self.store.add_history(
                    "scan", "%s을(를) 확인했습니다" % profile["name"])
                crop_started_at = time.time()
                updates["crop_started_at"] = crop_started_at
                self._last_growth_week.pop(crop_key, None)
            updates["crop_key"] = crop_key
            updates["crop_name"] = profile["name"]
            updates["profile_name"] = profile["name"]
        if updates:
            self.store.update(**updates)

        if crop_key and crop_started_at:
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

        반환: (level, 긴 문장, 짧은 단어, 자동조치)
              긴 문장 -> 앱 / 짧은 단어 -> Display

        우선순위: 폭염(온열질환 예방, 열기) > 비 감지(닫기) > 건조(급수) > 정상.
        폭염이 비 감지보다 우선인 이유: 사람 안전(온열질환)이 젖음 방지보다
        급하다고 봤다 - 실제로 둘이 동시에 뜨는 경우는 드물 것이다.
        """
        profile = get_profile(snap.get("crop_key"))
        temp = snap.get("temperature")
        humidity = snap.get("humidity")
        dry = snap.get("dryness")
        crop = profile["name"]

        # 조도는 생장등이 알아서 처리하므로 메시지로 띄우지 않는다.
        if temp is not None and temp > profile["vent_temp"] + 3:
            return "alert", "너무 덥습니다. 창문을 열까요?", "더워요!", "vent_open"

        if temp is not None and temp > profile["vent_temp"]:
            return "warn", "조금 덥습니다", "조금 더움", "vent_open"

        if humidity is not None and humidity > RAIN_HUMIDITY_THRESHOLD:
            return "warn", "비가 오는 것 같아요. 창문을 닫을까요?", "비 옴", "vent_close"

        if dry is not None and dry > profile["dry_limit"]:
            return "alert", "흙이 말랐어요. 물을 줄까요?", "물 필요", "water"

        return "good", "%s가 잘 자라고 있어요" % crop, "좋아요", None

    # ------------------------------------------------------ 출력
    def render_display(self, crop_name, short):
        """Display 2줄. 바뀔 때만 새로 쓴다.

        매 틱마다 새로 쓰면 화면이 깜빡이고 통신도 낭비된다.
        96x96이라 긴 문장은 읽을 수 없다. 짧은 단어만.
        """
        if self.busy and self._busy_action:
            short = {
                "vent_open": "창문 여는중",
                "vent_close": "창문 닫는중",
                "water": "물 주는중",
            }.get(self._busy_action, short)

        text = "%s\n%s" % (crop_name, short)
        if text == self._last_display:
            return
        self._last_display = text
        self.hw.show_text(text)

    def render_sound(self, level):
        """alert에 '진입하는 순간'에만 짧게 울린다.

        계속 울리면 시연장에서 재앙이다.
        """
        now = time.time()

        if self._beep_until and now >= self._beep_until:
            self._beep_until = 0.0
            self.hw.speaker_off()

        if level == "alert" and self._last_level != "alert":
            self.hw.beep(880, 40)
            self._beep_until = now + BEEP_DURATION

        self._last_level = level

    # ------------------------------------------------------ 명령 처리
    def handle_command(self, cmd):
        """앱 또는 하드웨어 버튼에서 온 명령을 실행한다."""
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
        return False

    # ------------------------------------------------------ 메인 틱
    def tick(self, auto_mode=True):
        """메인 루프에서 매번 호출한다."""
        self._finish_if_done()

        # 1) 센서 읽기
        env = self.hw.read_env()
        self.store.update(
            temperature=env["temperature"],
            humidity=env["humidity"],
            illuminance=env["illuminance"],
            dryness=humidity_to_dryness(env["humidity"]),
        )

        # 2) 주기적 촬영
        self.update_scan()

        # 3) 판단
        snap = self.store.snapshot()
        profile = get_profile(snap.get("crop_key"))
        level, message, short, auto_action = self.decide(snap)
        self.store.update(level=level, message=message, short=short)

        # 4) 출력
        self.update_grow_light(env["illuminance"], profile)
        self.render_display(snap.get("crop_name", "확인 중"), short)
        self.render_sound(level)

        # 5) 하드웨어 버튼 -> 창문 열기/닫기
        #    Button은 오직 이 일만 한다. 역할이 하나여야 헷갈리지 않는다.
        if self.hw.read_button():
            if not self.busy:
                self.toggle_vent()
                self.store.add_history("button", "버튼으로 창문을 조작했습니다")
            return

        # 6) 앱에서 온 명령
        pending = self.store.pop_command()
        if pending and not self.busy:
            self.handle_command(pending["cmd"])
            return

        # 7) 자동 조치
        #    사람이 승인하지 않아도 시스템이 알아서 하는 부분.
        #    "묻지 않는다"의 실체다.
        #    [예외] 환기창을 자동으로 닫는 건 "비 감지"(RAIN_HUMIDITY_THRESHOLD)
        #    한 가지 경우뿐이다. 그 외에는(예: 그냥 시원해짐) 여전히 사람이 닫는다.
        if auto_mode and auto_action and not self.busy:
            if auto_action == "vent_open" and not snap.get("vent_open"):
                self.open_vent()
            elif auto_action == "vent_close" and snap.get("vent_open"):
                self.close_vent()
            elif auto_action == "water":
                self.water()
