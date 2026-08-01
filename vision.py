# -*- coding: utf-8 -*-
"""웹캠 기반 작물 인식과 토양 건조도 분석.

[정직한 설계 선언]
토양 수분 센서가 없으므로 카메라로 흙 표면의 밝기·채도를 읽어
'상대 건조도 지수'를 만든다. 절대 수분 함량(%)이 아니다.
PT에서 이 한계를 먼저 밝힐 것.

MockVision 덕분에 웹캠 없이도 전체 시스템이 돌아간다.
"""

import json
import os
import random
import time

CALIB_PATH = "calib.json"

# 화면에서 흙이 차지하는 영역 (가로/세로 비율)
# 실제 배치에 맞게 조정할 것. 화면 아래쪽 가운데를 흙으로 본다.
SOIL_ROI = (0.30, 0.60, 0.70, 0.95)   # (x1, y1, x2, y2)
# 작물(잎)은 화면 위쪽 가운데
CROP_ROI = (0.25, 0.05, 0.75, 0.60)


def _crop(frame, roi):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = roi
    return frame[int(h * y1):int(h * y2), int(w * x1):int(w * x2)]


class Vision:
    """실제 웹캠 사용. opencv-python 필요."""

    def __init__(self, cam_index=0):
        import cv2  # 이 파일 안에서만 import
        self.cv2 = cv2
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            raise RuntimeError("웹캠을 열 수 없다. cam_index를 확인할 것.")
        self.calib = self.load_calib()
        time.sleep(1)   # 카메라 노출 안정화

    # ------------------------------------------------------ 캘리브레이션
    def load_calib(self):
        if os.path.exists(CALIB_PATH):
            with open(CALIB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        # 기본값. 반드시 현장에서 다시 잡을 것.
        return {"wet": {"v": 70.0, "s": 120.0}, "dry": {"v": 160.0, "s": 60.0}}

    def save_calib(self):
        with open(CALIB_PATH, "w", encoding="utf-8") as f:
            json.dump(self.calib, f, ensure_ascii=False, indent=2)

    def calibrate(self, which):
        """which: 'wet' 또는 'dry'. 지금 화면의 흙을 기준으로 삼는다.

        사용법
          1) 젖은 흙을 카메라 앞에 두고 calibrate('wet')
          2) 마른 흙을 카메라 앞에 두고 calibrate('dry')
        """
        frame = self.capture()
        if frame is None:
            return None
        v, s = self._soil_vs(frame)
        self.calib[which] = {"v": v, "s": s}
        self.save_calib()
        print("[VISION] %s 기준 저장: V=%.1f S=%.1f" % (which, v, s))
        return self.calib[which]

    # ------------------------------------------------------ 캡처
    def capture(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self):
        if self.cap:
            self.cap.release()

    # ------------------------------------------------------ 토양 분석
    def _soil_vs(self, frame):
        """흙 영역의 평균 명도(V)와 채도(S)."""
        cv2 = self.cv2
        roi = _crop(frame, SOIL_ROI)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        s = float(hsv[:, :, 1].mean())
        v = float(hsv[:, :, 2].mean())
        return v, s

    def soil_dryness(self, frame):
        """상대 건조도 지수 0(젖음) ~ 100(마름).

        마른 흙일수록 밝고(V 높음) 채도가 낮다(S 낮음).
        두 지표를 각각 정규화해 평균낸다.
        """
        v, s = self._soil_vs(frame)
        wet, dry = self.calib["wet"], self.calib["dry"]

        def norm(val, lo, hi):
            if abs(hi - lo) < 1e-6:
                return 0.5
            return (val - lo) / (hi - lo)

        v_score = norm(v, wet["v"], dry["v"])       # 밝을수록 마름
        s_score = norm(s, wet["s"], dry["s"])       # 채도 낮을수록 마름
        score = (v_score + s_score) / 2.0
        return max(0.0, min(100.0, score * 100.0))

    # ------------------------------------------------------ 작물 분류
    def classify_crop(self, frame):
        """HSV 규칙 기반 작물 분류 (1차안).

        딥러닝은 시간이 남을 때만. 이 규칙만으로 완주 가능해야 한다.
        아래 임계값은 반드시 현장 조명에서 다시 잡을 것.

        구분 기준
          - 붉은 기가 강하면        -> 토마토 또는 고추
          - 초록이 밝고 연하면      -> 상추
          - 초록이 진하고 채도 높으면 -> 배추
        """
        cv2 = self.cv2
        roi = _crop(frame, CROP_ROI)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0].astype("float")
        s = hsv[:, :, 1].astype("float")
        v = hsv[:, :, 2].astype("float")

        total = h.size
        if total == 0:
            return None

        # OpenCV의 Hue 범위는 0~179
        red_mask = ((h < 10) | (h > 170)) & (s > 90)
        green_mask = (h > 35) & (h < 85) & (s > 50)

        red_ratio = red_mask.sum() / total
        green_ratio = green_mask.sum() / total

        if red_ratio > 0.15:
            # 붉은 물체의 형태로 토마토/고추를 가른다.
            # 세로로 긴 형태면 고추, 둥글면 토마토.
            ys, xs = red_mask.nonzero()
            if len(xs) > 50:
                width = xs.max() - xs.min() + 1
                height = ys.max() - ys.min() + 1
                if height > width * 1.6:
                    return "pepper"
            return "tomato"

        if green_ratio > 0.20:
            mean_s = float(s[green_mask].mean()) if green_mask.any() else 0
            mean_v = float(v[green_mask].mean()) if green_mask.any() else 0
            if mean_v > 130 and mean_s < 140:
                return "lettuce"
            return "cabbage"

        return None   # 판단 보류. 기존 작물을 유지한다.


class MockVision:
    """웹캠 없이 개발할 때 쓰는 가짜 비전.

    건조도가 서서히 오르고, 물을 주면 떨어진다.
    """

    def __init__(self, crop="lettuce"):
        self._crop = crop
        self._dryness = 40.0
        self._last = time.time()

    def capture(self):
        return "MOCK_FRAME"

    def release(self):
        pass

    def classify_crop(self, frame):
        return self._crop

    def soil_dryness(self, frame):
        now = time.time()
        dt = now - self._last
        self._last = now
        self._dryness = min(100.0, self._dryness + 1.2 * dt)
        return self._dryness

    def on_water(self):
        """급수하면 건조도가 회복된다. 테스트용."""
        self._dryness = max(0.0, self._dryness - 45.0)

    def calibrate(self, which):
        return None


def build_vision(mock=False, cam_index=0, crop="lettuce"):
    if mock:
        return MockVision(crop=crop)
    try:
        return Vision(cam_index=cam_index)
    except Exception as e:
        print("[VISION] 웹캠 초기화 실패, Mock으로 대체한다:", e)
        return MockVision(crop=crop)
