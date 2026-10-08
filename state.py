# -*- coding: utf-8 -*-
"""시스템 상태 저장소와 명령 큐.

이 파일이 하드웨어 스레드와 Flask 스레드 사이의 유일한 접점이다.

  메인 루프 스레드  : 하드웨어를 만진다. 상태를 쓴다. 명령을 꺼내 실행한다.
  Flask 스레드      : 상태를 읽는다. 명령을 넣는다. 하드웨어는 절대 만지지 않는다.

이 규칙을 지켜야 시리얼 통신이 깨지지 않는다.
"""

import csv
import os
import threading
import time
from collections import deque

# 앱이 보낼 수 있는 명령 목록. 여기 없는 명령은 거부한다.
VALID_COMMANDS = {"vent_open", "vent_close", "vent_toggle", "water", "scan", "light_toggle",
                  "auto_on", "auto_off", "vent_mark_open", "vent_mark_closed", "sound_test",
                  # 장치 점검 (웹 운영자 패널): 사람이 눈으로 보며 하나씩 확인한다
                  "led_test", "display_test", "jog", "vent_test", "set_roles", "flip_sign",
                  "vent_confirm",
                  # AI 학습 (웹): 사진 촬영 -> 학습 -> 새 모델 적용
                  "collect_start", "collect_stop", "data_clear", "train_start", "train_stop",
                  "studio_ping"}

# 액추에이터를 안 움직이는 명령. 모터가 도는 중(busy)에도 받아서 바로 처리한다.
# (auto_on/off는 모터가 도는 동안 눌러도 버려지면 안 된다)
# vent_mark_*는 모터를 돌리지 않고 "창문이 지금 실제로 열려/닫혀 있다"고 시스템에 알려주기만 한다.
INSTANT_COMMANDS = {"scan", "light_toggle", "auto_on", "auto_off",
                    "vent_mark_open", "vent_mark_closed", "sound_test",
                    "led_test", "display_test",
                    # 학습 관련은 모터를 안 쓰므로 환기창이 도는 중에도 받는다
                    "collect_start", "collect_stop", "data_clear", "train_start", "train_stop",
                    "studio_ping"}

# LED는 생장등으로만 쓴다. 상태색 표시는 앱이 담당한다.
# light_toggle은 수동 개입("조작은 언제든 할 수 있다") — 자동 로직(update_grow_light)이
# 다음 판단 주기에 다시 조정할 수 있다는 점은 창문 자동 개방과 동일하다.

LOG_PATH = "log.csv"   # .gitignore에 이미 등록됨 (기기마다 다른 이력이라 공유 안 함)
_LOG_FIELDS = ["at", "event", "detail"]


class Store:
    """스레드 안전한 상태 저장소 + 명령 큐."""

    def __init__(self, history_limit=200, log_path=LOG_PATH):
        self._lock = threading.Lock()
        self._commands = deque()
        self._history = deque(maxlen=history_limit)
        self._log_path = log_path
        self._load_history_log()
        self._growth_photos = deque(maxlen=52)   # 1년치 주간 사진이면 충분
        self._camera_frame = None   # 실시간 미리보기용 최신 JPEG 바이트

        self._state = {
            # 센서
            "temperature": None,
            "humidity": None,
            "illuminance": None,
            "distance": None,
            # 비전
            "crop_key": None,
            "crop_name": "확인 중",
            "crop_started_at": None,  # 지금 작물을 처음 인식한 시각(성장 일수 계산용)
            "dryness": None,          # 0(젖음) ~ 100(마름)
            # 판단 결과
            "level": "good",          # good / warn / alert
            "message": "시작하는 중입니다",
            "short": "준비중",
            "profile_name": "확인 중",
            "crop_probs": None,       # 분류기의 클래스별 확률 {"lettuce": 0.93, ...}. 웹 화면용
            "reason": "",             # 지금 판단의 근거 한 줄 (웹 화면용)
            "display_text": "",       # 실제 Display 모듈에 나가는 두 줄 ("작물\n상태")
            "auto_mode": True,        # 자동 조치 on/off. 앱에서 바꿀 수 있다
            "sound_on": False,        # 노트북에서 소리가 나는지 (--mute면 False)
            # 액추에이터
            # [중요] 환기창은 상대회전이라 시스템은 실제 위치를 모르고 "열려 있다/닫혀 있다"를
            # 믿고 있을 뿐이다. vent_assumed가 True면 아직 사람이 확인하지 않은 추정값이다
            # (재조립/재시작 직후). 웹 화면이 "맞는지 확인해 주세요"를 띄운다.
            "vent_assumed": True,
            "collect": None,          # 학습 사진 촬영 진행 {active, crop, count, target}
            "train": None,            # AI 학습 진행 {running, pct, phase, accuracy, ...}
            "dataset": None,          # 클래스별 학습 사진 장수 {"carrot": 15, ...}
            "model_classes": None,    # 지금 쓰는 모델이 아는 클래스 (없으면 None)
            "camera_real": False,     # 진짜 웹캠인가 (모의 화면이 아닌가)
            "hw": None,               # 하드웨어 구성(모터 목록/역할/방향/ready). 웹의 장치 점검 화면용
            "motor_fault": None,      # 명령은 갔는데 모터가 안 움직였을 때의 안내 문구 (정상이면 None)
            "hw_error": None,         # 메인 루프 tick이 실패했을 때의 마지막 오류 (정상이면 None)
            "vent_open": False,
            "sprinkler_on": False,
            "light_on": False,        # 생장등
            "busy": False,            # 액추에이터 동작 중
            "busy_action": None,
            # 메타
            "mock": False,
            "updated_at": time.time(),
        }

    # ---------------------------------------------------------- 상태
    def snapshot(self):
        """현재 상태의 복사본. Flask가 읽을 때 쓴다."""
        with self._lock:
            return dict(self._state)

    def update(self, **kwargs):
        """상태 일부를 갱신한다. 메인 루프에서만 호출한다."""
        with self._lock:
            self._state.update(kwargs)
            self._state["updated_at"] = time.time()

    def get(self, key, default=None):
        with self._lock:
            return self._state.get(key, default)

    # ---------------------------------------------------------- 명령 큐
    def push_command(self, cmd, source="app", args=None):
        """앱에서 온 명령을 큐에 넣는다. 유효하지 않으면 False.

        args는 jog/set_roles 같은 인자가 필요한 명령용 dict. 값 검증은 server.py가 한다.
        """
        if cmd not in VALID_COMMANDS:
            return False
        with self._lock:
            # 같은 명령이 이미 대기 중이면 중복으로 쌓지 않는다.
            # (어르신이 버튼을 여러 번 누르는 상황 대비) 인자가 다르면 다른 명령이다.
            if any(c["cmd"] == cmd and c.get("args") == args for c in self._commands):
                return True
            self._commands.append(
                {"cmd": cmd, "source": source, "at": time.time(), "args": args}
            )
        return True

    def pop_command(self):
        """대기 중인 명령을 하나 꺼낸다. 메인 루프에서만 호출한다."""
        with self._lock:
            if self._commands:
                return self._commands.popleft()
        return None

    def pending_count(self):
        with self._lock:
            return len(self._commands)

    # ---------------------------------------------------------- 카메라 미리보기
    def set_camera_frame(self, jpeg_bytes):
        """메인 루프에서만 호출. 실시간 미리보기용 최신 프레임(JPEG 바이트)을 갱신한다."""
        with self._lock:
            self._camera_frame = jpeg_bytes

    def get_camera_frame(self):
        """Flask 스레드에서 호출. 최신 프레임이 없으면 None."""
        with self._lock:
            return self._camera_frame

    # ---------------------------------------------------------- 이력
    def _load_history_log(self):
        """이전 실행에서 쌓인 CSV 이력을 불러온다. 재시작해도 '지난 기록'이 안 사라지게."""
        if not os.path.exists(self._log_path):
            return
        try:
            with open(self._log_path, "r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    self._history.append({
                        "at": float(row["at"]),
                        "event": row["event"],
                        "detail": row.get("detail") or "",
                    })
        except Exception as e:
            print("[STATE] 이력 로그 로드 실패, 빈 이력으로 시작한다:", e)

    def _append_history_log(self, entry):
        """새 이력 한 줄을 CSV에 곧바로 이어 쓴다."""
        try:
            is_new = not os.path.exists(self._log_path)
            with open(self._log_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_LOG_FIELDS)
                if is_new:
                    writer.writeheader()
                writer.writerow(entry)
        except Exception as e:
            print("[STATE] 이력 로그 저장 실패:", e)

    def add_history(self, event, detail=""):
        """앱의 '지난 기록' 화면에 쓸 사건을 남긴다. CSV에도 곧바로 남겨 재시작에도 살아남게 한다."""
        entry = {"at": time.time(), "event": event, "detail": detail}
        with self._lock:
            self._history.append(entry)
        self._append_history_log(entry)

    def history(self, limit=50):
        with self._lock:
            items = list(self._history)
        return items[-limit:][::-1]     # 최신순

    # ---------------------------------------------------------- 성장 사진
    def add_growth_photo(self, crop_key, crop_name, week_index, filename):
        """일주일 간격으로 찍은 성장 기록 사진을 남긴다."""
        with self._lock:
            self._growth_photos.append({
                "crop_key": crop_key,
                "crop_name": crop_name,
                "week": week_index,
                "filename": filename,
                "taken_at": time.time(),
            })

    def growth_photos(self, crop_key=None):
        """주차 오름차순. crop_key를 주면 지금 작물 것만 돌려준다."""
        with self._lock:
            items = list(self._growth_photos)
        if crop_key is not None:
            items = [p for p in items if p["crop_key"] == crop_key]
        return sorted(items, key=lambda p: p["week"])
