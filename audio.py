# -*- coding: utf-8 -*-
"""노트북 스피커로 소리를 내는 계층.

MODI Speaker 모듈은 쓰지 않는다. 소리는 서버가 도는 노트북에서 난다.
(웹 화면이 아니라 서버에서 내는 이유: 키오스크 브라우저는 사용자 조작 없이는
자동 재생이 막히고, 폰으로 접속해도 소리는 부스 노트북에서 나야 하기 때문이다.)

[중요] 소리를 내는 동안 메인 루프를 막으면 안 된다. winsound.Beep()은 소리가 끝날
때까지 돌아오지 않으므로(0.6초짜리 경고음이면 0.6초간 센서도 API도 멈춘다),
별도 스레드가 큐에서 꺼내 재생한다. 메인 루프는 큐에 넣기만 하고 바로 돌아온다.
(하드웨어 접근은 메인 스레드 독점이라는 규칙과 상관없다 - 이건 MODI가 아니라 노트북 소리다.)
"""

import queue
import sys
import threading

# 소리 이름 -> [(주파수Hz, 길이ms), ...]. 짧은 멜로디를 음 단위로 이어서 낸다.
SOUNDS = {
    "alert": [(880, 400)],                              # alert 진입 순간 짧게 한 번
    "heat": [(1500, 600)],                              # 온열질환 경고 한 펄스 (컨트롤러가 간격을 둔다)
    "recognized": [(660, 110), (880, 110), (1175, 220)],  # 작물을 알아본 순간 "띠리링"
    "test": [(880, 180), (1320, 260)],                  # 운영자의 소리 확인용
}

# 큐가 이만큼 밀리면 새 소리는 버린다. 경고음이 쌓여서 한참 뒤에 몰아서 울리면
# 시연장 참사다.
MAX_BACKLOG = 3


class NullAudio:
    """소리를 내지 않는다 (--mute, 모의 실행 기본값)."""

    enabled = False

    def play(self, name):
        pass

    def close(self):
        pass


class LaptopAudio:
    """Windows의 winsound로 노트북 스피커에서 소리를 낸다."""

    enabled = True

    def __init__(self):
        import winsound  # Windows 전용. 없으면 호출한 쪽(build_audio)이 NullAudio로 대체한다
        self._winsound = winsound
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="audio")
        self._thread.start()

    def play(self, name):
        notes = SOUNDS.get(name)
        if not notes or self._queue.qsize() >= MAX_BACKLOG:
            return
        self._queue.put(notes)

    def _run(self):
        while True:
            notes = self._queue.get()
            if notes is None:
                return
            for freq, ms in notes:
                try:
                    self._winsound.Beep(int(freq), int(ms))
                except RuntimeError as e:
                    # 오디오 장치가 없거나 막힌 경우. 소리 때문에 시연이 죽으면 안 된다.
                    print("[AUDIO] 소리 재생 실패(무시):", e)
                    break

    def close(self):
        self._queue.put(None)


def build_audio(mute=False):
    """설정에 맞는 오디오 객체. 소리를 낼 수 없는 환경이면 조용히 NullAudio."""
    if mute:
        return NullAudio()
    if not sys.platform.startswith("win"):
        print("[AUDIO] Windows가 아니라 노트북 소리는 끈다.")
        return NullAudio()
    try:
        return LaptopAudio()
    except ImportError:
        print("[AUDIO] winsound를 쓸 수 없어 소리는 끈다.")
        return NullAudio()
