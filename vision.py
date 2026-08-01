# -*- coding: utf-8 -*-
"""웹캠 기반 작물 인식과 (확장용) 토양 건조도 분석.

[정직한 설계 선언]
토양 수분 센서가 없다. 카메라를 위에서 내려다보는 각도로 배치하면서
흙 자체가 프레임에 안 잡히게 됐고(레고 작물만 중앙에 보임), 이번 데모의
건조도 판단은 Env 모듈의 습도로 대체했다 (controller.humidity_to_dryness 참고).

soil_dryness()/calibrate() 등 카메라 기반 건조도 코드는 지우지 않고 남겨둔다.
레고가 아닌 실제 작물·흙으로 만들 제품에서는 흙이 카메라에 다시 보이게
배치할 수 있으므로, 그때 확장 기능으로 되살릴 것. 지금은 아무도 호출하지 않는다.

MockVision 덕분에 웹캠 없이도 전체 시스템이 돌아간다.
"""

import json
import os
import random
import sys
import time

CALIB_PATH = "calib.json"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "crop_classifier.pt")
CLASS_MAP_PATH = os.path.join(MODEL_DIR, "class_map.json")
MODEL_CONF_THRESHOLD = 0.6   # 이보다 확신이 낮으면 HSV 폴백으로 넘긴다

# [확장용, 현재 미사용] 화면에서 흙이 차지하는 영역.
# 탑다운 배치에는 흙이 아예 안 보여서 지금은 의미가 없다.
SOIL_ROI = (0.30, 0.60, 0.70, 0.95)   # (x1, y1, x2, y2)

# 작물(레고 브릭)은 위에서 내려다본 화면의 중앙에 놓인다.
# 실제 카메라 거리·배치에 맞게 조정할 것 - collect_data.py 미리보기의
# 초록 박스가 브릭을 잘 감싸는지 찍기 전에 먼저 확인할 것.
CROP_ROI = (0.20, 0.20, 0.80, 0.80)


def _crop(frame, roi):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = roi
    return frame[int(h * y1):int(h * y2), int(w * x1):int(w * x2)]


class Vision:
    """실제 웹캠 사용. opencv-python 필요."""

    def __init__(self, cam_index=0):
        import cv2  # 이 파일 안에서만 import
        self.cv2 = cv2

        # [중요] Windows 기본 백엔드(MSMF)는 여는 데 20초 가까이 걸리고,
        # 촬영 중간에 "can't grab frame" 에러로 프레임을 계속 못 읽는 경우가
        # 실측됐다. DirectShow(CAP_DSHOW)가 훨씬 빠르고(7초대) 안정적이었다.
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else 0
        self.cap = cv2.VideoCapture(cam_index, backend)
        if not self.cap.isOpened():
            raise RuntimeError("웹캠을 열 수 없다. cam_index를 확인할 것.")
        self.calib = self.load_calib()
        self._model = None
        self._class_map = None
        self._preprocess = None
        self._model_tried = False
        time.sleep(1)   # 카메라 노출 안정화

    # ------------------------------------------------------ 딥러닝 모델
    def _load_model(self):
        """학습된 분류기를 지연 로드한다 (한 번만 시도).

        모델 파일이 없거나 torch가 없으면 조용히 넘어가고, 이후로는
        classify_crop이 계속 HSV 폴백만 쓴다. 대회장에 인터넷이 없어도
        되도록 pretrained=False로 빈 뼈대만 만들고 state_dict로 채운다.
        """
        self._model_tried = True
        if not (os.path.exists(MODEL_PATH) and os.path.exists(CLASS_MAP_PATH)):
            print("[VISION] 학습된 모델이 없다 (%s). HSV 폴백만 쓴다." % MODEL_PATH)
            return
        try:
            import torch
            from crop_model import build_model, preprocess

            with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
                class_map = json.load(f)
            model = build_model(len(class_map), pretrained=False)
            model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
            model.eval()
            self._model = model
            self._class_map = class_map
            self._preprocess = preprocess
            print("[VISION] 딥러닝 분류기 로드 완료:", class_map)
        except Exception as e:
            print("[VISION] 딥러닝 모델 로드 실패, HSV 폴백만 쓴다:", e)

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

    def save_snapshot(self, frame, path):
        """성장 기록용 사진 저장. 성공하면 True."""
        return bool(self.cv2.imwrite(path, frame))

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
        """작물 분류. 딥러닝 모델이 있으면 그게 주 수단, 없거나 확신이 낮으면 HSV 폴백.

        [중요] 대회 규정상 실제 작물을 반입할 수 없어 레고 브릭으로 대신한다.
        시연 작물은 상추/옥수수/당근 3종으로 확정됐다 (profiles.py 참고).
        """
        if not self._model_tried:
            self._load_model()

        roi = _crop(frame, CROP_ROI)

        if self._model is not None:
            result = self._classify_crop_model(roi)
            # [중요] "background"는 모델이 확신을 갖고 내린 "작물 없음"
            # 판단이다 - None(확신 없음, HSV로 넘김)과 구분해서 그대로
            # 돌려줘야, 호출한 쪽(controller.update_scan)이 인식 상태를
            # 초기화할 수 있다. 여기서 걸러버리면 마지막으로 인식된 작물이
            # 실제로는 치워졌는데도 화면에 계속 남는다.
            if result is not None:
                return result

        return self._classify_crop_hsv(roi)

    def _classify_crop_model(self, roi):
        """딥러닝 분류. 확신이 낮으면 None을 반환해 HSV로 넘긴다.

        "background"(작물 없음)로 확신 있게 판단되면 그 문자열 그대로
        돌려준다 - None과는 다른 의미다.
        """
        import torch

        try:
            with torch.no_grad():
                tensor = self._preprocess(roi)
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                idx = int(probs.argmax())
                conf = float(probs[idx])
        except Exception as e:
            print("[VISION] 모델 추론 실패, HSV로 넘긴다:", e)
            return None

        # [진단용] 인식이 잘 안 될 때 어느 클래스를 얼마나 확신했는지 바로
        # 보려고 매 스캔마다 전체 확률을 찍는다. 문제 해결되면 지워도 된다.
        pairs = sorted(zip(self._class_map, probs.tolist()), key=lambda p: -p[1])
        print("[VISION] 분류 확률:", ", ".join("%s=%.2f" % p for p in pairs))

        if conf < MODEL_CONF_THRESHOLD:
            print("[VISION] 확신 부족(%.2f < %.2f) - HSV로 넘긴다" % (conf, MODEL_CONF_THRESHOLD))
            return None
        return self._class_map[idx]

    def _classify_crop_hsv(self, roi):
        """HSV 규칙 기반 작물 분류 (폴백용).

        옥수수·당근은 브릭 배색이 아직 정해지지 않아 규칙을 만들 수 없다.
        브릭 색이 정해지면 여기에 판단을 추가할 것.
        지금은 상추(초록)만 규칙으로 인식하고, 나머지는 판단 보류(None).
        """
        cv2 = self.cv2
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0].astype("float")
        s = hsv[:, :, 1].astype("float")

        total = h.size
        if total == 0:
            return None

        green_mask = (h > 35) & (h < 85) & (s > 50)
        green_ratio = green_mask.sum() / total

        if green_ratio > 0.20:
            return "lettuce"

        return None   # 옥수수/당근/판단 보류. 기존 작물을 유지한다.


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

    def save_snapshot(self, frame, path):
        """웹캠이 없는 모의 모드라 실제 사진은 저장하지 않는다."""
        return False


def build_vision(mock=False, cam_index=0, crop="lettuce"):
    if mock:
        return MockVision(crop=crop)
    try:
        return Vision(cam_index=cam_index)
    except Exception as e:
        print("[VISION] 웹캠 초기화 실패, Mock으로 대체한다:", e)
        return MockVision(crop=crop)
