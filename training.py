# -*- coding: utf-8 -*-
"""웹 화면의 "AI 학습": 사진 촬영 -> 정리 -> 학습 -> 새 모델 적용.

터미널의 collect_data.py / train_crop_model.py 와 같은 일을 하되, 웹에서 버튼으로 한다.
(브릭을 카메라 앞에 올려놓고 화면을 보면서 누를 수 있어야 해서.)

[규칙] 이 파일의 Collector / Trainer 는 메인 루프 스레드에서만 쓴다 (카메라는 메인 스레드 독점).
       Flask 스레드는 state.Store 의 값을 읽고 명령을 큐에 넣기만 한다.

[규칙] 학습은 **별도 프로세스**로 돌린다. torch 로 임베딩을 뽑는 몇십 초 동안 메인 루프(센서, 웹
       응답, 환기창 제어)가 멈추면 안 되기 때문이다. 그 프로세스가 내는 "[progress]" 줄만 읽는다.
"""

import collections
import os
import re
import subprocess
import sys
import threading
import time

from profiles import CROP_PROFILES

DATA_DIR = "data"
COLLECT_TARGET = 20          # 한 번 누르면 찍는 장수
COLLECT_MIN, COLLECT_MAX = 5, 60
COLLECT_INTERVAL = 0.8       # 초. 이 사이에 브릭을 천천히 돌려 주길 기대한다(같은 각도만 찍으면 소용없다)
MIN_PER_CLASS = 8            # 이보다 적으면 그 클래스는 학습하지 않는 게 낫다 (증강해도 한계)
GOOD_PER_CLASS = 25          # 웹 화면에서 "충분해요"로 보여주는 기준


def valid_classes():
    """학습/촬영할 수 있는 클래스: profiles.py 의 작물 + 작물 없음(background)."""
    return list(CROP_PROFILES.keys()) + ["background"]


def count_images(data_dir=DATA_DIR):
    """{클래스: 사진 장수}. 폴더가 없으면 0."""
    out = {}
    for name in valid_classes():
        path = os.path.join(data_dir, name)
        out[name] = (
            len([f for f in os.listdir(path) if f.lower().endswith(".jpg")])
            if os.path.isdir(path) else 0
        )
    return out


def _next_index(folder):
    """겹치지 않는 다음 파일 번호. 장수가 아니라 가장 큰 번호 + 1 (중간에 지웠어도 안전)."""
    best = -1
    for f in os.listdir(folder):
        m = re.fullmatch(r"(\d+)\.jpg", f.lower())
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


# ------------------------------------------------------------------ 촬영
class Collector:
    """웹에서 [촬영]을 누르면 일정 간격으로 프레임을 찍어 data/<클래스>/ 에 저장한다."""

    def __init__(self, vision, store, audio, publish_preview, data_dir=DATA_DIR):
        self.vision = vision
        self.store = store
        self.audio = audio
        self.publish_preview = publish_preview
        self.data_dir = data_dir
        self._crop = None
        self._target = 0
        self._saved = 0
        self._next = 0.0

    @property
    def active(self):
        return self._crop is not None

    def start(self, crop, target=COLLECT_TARGET):
        if crop not in valid_classes() or self.active:
            return False
        if self.vision is None:
            self.store.add_history("collect", "카메라가 없어 사진을 찍을 수 없어요")
            return False
        self._crop = crop
        self._target = max(COLLECT_MIN, min(COLLECT_MAX, int(target)))
        self._saved = 0
        self._next = time.time() + 1.0      # 누른 직후 손을 치울 시간을 조금 준다
        self.store.add_history("collect", "%s 사진 촬영을 시작했어요" % self._label())
        self._publish()
        return True

    def stop(self):
        if self.active:
            self._finish(cancelled=True)
        return True

    def tick(self):
        if not self.active or time.time() < self._next:
            return
        self._next = time.time() + COLLECT_INTERVAL

        frame = self.vision.capture()
        if frame is None or isinstance(frame, str):     # 카메라가 프레임을 못 줬다 / 모의 비전의 문자열
            return
        self.publish_preview(frame)

        # [중요] 추론(vision.classify_crop)과 똑같은 영역을 잘라서 저장한다.
        # 학습 때 보는 영역과 실제 인식 때 보는 영역이 다르면 모델이 헛돈다.
        from vision import CROP_ROI, _crop
        import cv2
        crop_img = _crop(frame, CROP_ROI)
        folder = os.path.join(self.data_dir, self._crop)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "%04d.jpg" % _next_index(folder))
        if cv2.imwrite(path, crop_img):
            self._saved += 1
            self.audio.play("shot")     # 삑 - 이때 브릭을 조금 돌려 달라는 신호 (collect_data.py와 같은 방식)
        self._publish()
        if self._saved >= self._target:
            self._finish()

    def clear(self, crop):
        """그 클래스의 사진(.jpg)만 지운다. 알려진 클래스 이름만 받는다(경로 조작 방지)."""
        if crop not in valid_classes() or self.active:
            return 0
        folder = os.path.join(self.data_dir, crop)
        removed = 0
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.lower().endswith(".jpg"):
                    try:
                        os.remove(os.path.join(folder, f))
                        removed += 1
                    except OSError:
                        pass
        self.store.add_history("collect", "%s 사진 %d장을 지웠어요" % (self._label(crop), removed))
        self.store.update(dataset=count_images(self.data_dir))
        return removed

    def _label(self, crop=None):
        crop = crop or self._crop
        return CROP_PROFILES[crop]["name"] if crop in CROP_PROFILES else "작물 없음"

    def _publish(self):
        self.store.update(
            collect={"active": self.active, "crop": self._crop,
                     "count": self._saved, "target": self._target},
            dataset=count_images(self.data_dir),
        )

    def _finish(self, cancelled=False):
        label, saved = self._label(), self._saved
        self._crop = None
        self.store.update(collect={"active": False, "crop": None, "count": saved, "target": 0},
                          dataset=count_images(self.data_dir))
        self.store.add_history(
            "collect", "%s 사진 %d장을 %s" % (label, saved, "찍다가 멈췄어요" if cancelled else "찍었어요"))
        if not cancelled:
            self.audio.play("recognized")


# ------------------------------------------------------------------ 학습
_PROGRESS = re.compile(r"\[progress\]\s+(\w+)\s+(\d+)/(\d+)")
_RESULT = re.compile(r"\[result\]\s+acc=([\d.]+)\s+classes=(\S+)")


class Trainer:
    """train_crop_model.py 를 별도 프로세스로 돌리고, 출력에서 진행 상황만 읽는다."""

    def __init__(self, store, vision, audio, root=None, data_dir=DATA_DIR, model_dir="models",
                 extra_args=None):
        self.store = store
        self.vision = vision
        self.audio = audio
        self.root = root or os.path.dirname(os.path.abspath(__file__))
        self.data_dir = data_dir
        self.model_dir = model_dir
        # 사진/모델 폴더를 스크립트에 그대로 넘긴다 - 모의 실행이 진짜 data/ models/ 를 건드리지 않게
        self.extra_args = extra_args if extra_args is not None else [
            "--data-dir", data_dir, "--model-dir", model_dir]
        self._proc = None
        self._lines = collections.deque(maxlen=60)
        self._phase = ("", 0, 1)
        self._result = None
        self._started = 0.0
        self._finalized = True
        self._stop_requested = False
        self._lock = threading.Lock()
        self.store.update(train=self._snapshot())

    @property
    def running(self):
        return self._proc is not None and not self._finalized

    def start(self):
        if self.running:
            return False
        counts = count_images(self.data_dir)
        usable = [c for c, n in counts.items() if n >= MIN_PER_CLASS]
        if len(usable) < 2:
            self.store.add_history(
                "train", "학습하려면 사진이 %d장 이상인 클래스가 2개 이상 필요해요" % MIN_PER_CLASS)
            return False

        self._lines.clear()
        self._phase, self._result = ("준비", 0, 1), None
        self._started, self._finalized, self._stop_requested = time.time(), False, False
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows에서 검은 콘솔 창이 뜨지 않게
        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-u", "train_crop_model.py"] + self.extra_args,
                cwd=self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", creationflags=flags,
            )
        except OSError as e:
            self._finalized = True
            self.store.add_history("train", "학습을 시작하지 못했어요: %s" % e)
            return False
        threading.Thread(target=self._read, args=(self._proc,), daemon=True, name="train-reader").start()
        self.store.add_history("train", "AI 학습을 시작했어요 (%s)" % ", ".join(usable))
        self._publish()
        return True

    def stop(self):
        if self.running and self._proc.poll() is None:
            self._stop_requested = True
            self._proc.terminate()
            self.store.add_history("train", "AI 학습을 멈췄어요")
            self._result = None
        return True

    def _read(self, proc):
        """학습 프로세스의 출력을 한 줄씩 읽어 둔다. 이 스레드는 Store나 장치를 건드리지 않는다."""
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            with self._lock:
                self._lines.append(line)
                m = _PROGRESS.search(line)
                if m:
                    self._phase = (m.group(1), int(m.group(2)), max(1, int(m.group(3))))
                r = _RESULT.search(line)
                if r:
                    self._result = (float(r.group(1)), r.group(2).split(","))

    def tick(self):
        if self._proc is None or self._finalized:
            return
        if self._proc.poll() is None:
            self._publish()
            return
        # 끝났다. 출력을 다 읽을 시간을 아주 조금 준 뒤 마무리한다.
        time.sleep(0.05)
        self._finalized = True
        ok = self._proc.returncode == 0 and self._result is not None
        if ok:
            from vision import read_class_map
            if self.vision is not None:
                self.vision.reload_model()      # 다음 인식부터 새 모델
            acc, classes = self._result
            self.store.update(model_classes=read_class_map(os.path.join(self.model_dir, "class_map.json")))
            self.store.add_history("train", "AI 학습을 마쳤어요 (검증 정확도 %.0f%%)" % (acc * 100))
            self.audio.play("recognized")
        elif not self._stop_requested:
            self.store.add_history("train", "AI 학습에 실패했어요")
        self._publish()

    def _snapshot(self):
        with self._lock:
            phase, done, total = self._phase
            lines = list(self._lines)[-6:]
            result = self._result
        if phase == "embed":
            pct = done / total * 40
        elif phase == "train":
            pct = 40 + done / total * 60
        else:
            pct = 0
        finished = self._proc is not None and self._finalized
        ok = bool(finished and result is not None and self._proc.returncode == 0)
        return {
            "running": self.running,
            "finished": finished,
            "ok": ok,
            "pct": round(100.0 if ok else pct, 1),
            "phase": {"embed": "사진 특징 뽑는 중", "train": "분류기 학습 중"}.get(phase, "준비 중"),
            "accuracy": result[0] if result else None,
            "classes": result[1] if result else None,
            "elapsed": round(time.time() - self._started, 1) if self._started else 0,
            "log": lines,
        }

    def _publish(self):
        self.store.update(train=self._snapshot())
