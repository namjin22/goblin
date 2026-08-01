# -*- coding: utf-8 -*-
"""시스템 상태 저장소와 명령 큐.

이 파일이 하드웨어 스레드와 Flask 스레드 사이의 유일한 접점이다.

  메인 루프 스레드  : 하드웨어를 만진다. 상태를 쓴다. 명령을 꺼내 실행한다.
  Flask 스레드      : 상태를 읽는다. 명령을 넣는다. 하드웨어는 절대 만지지 않는다.

이 규칙을 지켜야 시리얼 통신이 깨지지 않는다.
"""

import threading
import time
from collections import deque

# 앱이 보낼 수 있는 명령 목록. 여기 없는 명령은 거부한다.
VALID_COMMANDS = {"vent_open", "vent_close", "vent_toggle", "water", "scan"}

# LED는 생장등으로만 쓴다. 상태색 표시는 앱이 담당한다.


class Store:
    """스레드 안전한 상태 저장소 + 명령 큐."""

    def __init__(self, history_limit=200):
        self._lock = threading.Lock()
        self._commands = deque()
        self._history = deque(maxlen=history_limit)

        self._state = {
            # 센서
            "temperature": None,
            "humidity": None,
            "illuminance": None,
            "distance": None,
            # 비전
            "crop_key": None,
            "crop_name": "확인 중",
            "dryness": None,          # 0(젖음) ~ 100(마름)
            # 판단 결과
            "level": "good",          # good / warn / alert
            "message": "시작하는 중입니다",
            "short": "준비중",
            "profile_name": "확인 중",
            # 액추에이터
            "vent_angle": 0,
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
    def push_command(self, cmd, source="app"):
        """앱에서 온 명령을 큐에 넣는다. 유효하지 않으면 False."""
        if cmd not in VALID_COMMANDS:
            return False
        with self._lock:
            # 같은 명령이 이미 대기 중이면 중복으로 쌓지 않는다.
            # (어르신이 버튼을 여러 번 누르는 상황 대비)
            if any(c["cmd"] == cmd for c in self._commands):
                return True
            self._commands.append(
                {"cmd": cmd, "source": source, "at": time.time()}
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

    # ---------------------------------------------------------- 이력
    def add_history(self, event, detail=""):
        """앱의 '지난 기록' 화면에 쓸 사건을 남긴다."""
        with self._lock:
            self._history.append(
                {"at": time.time(), "event": event, "detail": detail}
            )

    def history(self, limit=50):
        with self._lock:
            items = list(self._history)
        return items[-limit:][::-1]     # 최신순
