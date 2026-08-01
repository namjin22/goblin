# -*- coding: utf-8 -*-
"""작물 분류 학습용 사진 자동 촬영.

vision.py와 똑같은 CROP_ROI로 잘라서 저장한다.
학습 데이터와 실제 추론이 보는 영역이 다르면 모델이 산다.

실제 작물은 반입 금지라 크기·색을 맞춘 레고 브릭으로 촬영한다.

사용법 (클래스는 profiles.py의 lettuce/corn/carrot + background)
  python collect_data.py --crop lettuce --cam 1
  python collect_data.py --crop corn --cam 1
  python collect_data.py --crop carrot --cam 1
  python collect_data.py --crop background --cam 1 --seconds 15

카메라 앞에서 작물을 천천히 돌리거나 각도를 바꿔가며 촬영할 것.
같은 각도로 가만히 있으면 사진만 많고 다양성은 없다.

ESC 또는 Ctrl+C로 중간에 멈출 수 있다. 그때까지 찍은 사진은 남는다.
"""

import argparse
import os
import sys
import time

import cv2

from vision import CROP_ROI, _crop

DATA_DIR = "data"


def parse_args():
    p = argparse.ArgumentParser(description="작물 분류 학습 데이터 촬영")
    p.add_argument("--crop", required=True,
                   help="클래스 이름 (예: lettuce, corn, carrot, background)")
    p.add_argument("--cam", type=int, default=0, help="웹캠 인덱스")
    p.add_argument("--seconds", type=float, default=20.0, help="촬영 지속 시간(초)")
    p.add_argument("--interval", type=float, default=1.5,
                   help="촬영 간격(초). 브릭을 옮길 시간을 확보하려고 기본값을 넉넉히 잡았다")
    return p.parse_args()


def _beep():
    """촬영 순간 삑 소리. Windows 전용, 없으면 조용히 넘어간다."""
    if sys.platform.startswith("win"):
        try:
            import winsound
            winsound.Beep(1200, 80)
        except Exception:
            pass


def main():
    args = parse_args()

    out_dir = os.path.join(DATA_DIR, args.crop)
    os.makedirs(out_dir, exist_ok=True)
    existing = len([f for f in os.listdir(out_dir) if f.endswith(".jpg")])

    # vision.py와 같은 이유로 DirectShow 백엔드를 쓴다 (MSMF는 느리고 불안정했다).
    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else 0
    cap = cv2.VideoCapture(args.cam, backend)
    if not cap.isOpened():
        print("웹캠을 열 수 없다. --cam 값을 확인할 것.")
        return 1
    time.sleep(1)   # 노출 안정화

    print("=" * 50)
    print(" 클래스: %s" % args.crop)
    print(" %.0f초 동안 %.1f초마다 자동 촬영한다." % (args.seconds, args.interval))
    print(" 미리보기 창의 카운트다운을 보고, 삑 소리가 나면 그 직후에")
    print(" 브릭 위치/각도를 바꿀 것 (촬영 자체는 그 순간 이미 끝났다).")
    print(" ESC로 중단, 초록 박스가 저장되는 영역이다.")
    print("=" * 50)

    saved = 0
    start = time.time()
    last_capture = -999.0
    flash_until = 0.0
    consecutive_fails = 0

    try:
        while time.time() - start < args.seconds:
            ok, frame = cap.read()
            if not ok:
                # 프레임 그랩이 계속 실패하면(카메라 끊김 등) 무한정 돌지 않고 멈춘다.
                consecutive_fails += 1
                if consecutive_fails > 30:
                    print("카메라에서 프레임을 계속 못 읽는다. 연결을 확인할 것.")
                    break
                time.sleep(0.1)
                continue
            consecutive_fails = 0

            now = time.time()
            until_next = args.interval - (now - last_capture)
            capturing_now = until_next <= 0

            h, w = frame.shape[:2]
            x1, y1, x2, y2 = CROP_ROI
            preview = frame.copy()
            box_color = (0, 0, 255) if now < flash_until else (0, 255, 0)  # 촬영 순간 빨강 플래시
            cv2.rectangle(
                preview, (int(w * x1), int(h * y1)), (int(w * x2), int(h * y2)),
                box_color, 3)
            remaining = args.seconds - (now - start)
            cv2.putText(
                preview, "%s  %d장  전체 %.0fs 남음" % (args.crop, saved, remaining),
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            countdown_text = "촬영!" if now < flash_until else "다음 촬영까지 %.1fs" % max(0.0, until_next)
            cv2.putText(
                preview, countdown_text, (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, box_color, 2)
            cv2.imshow("collect_data - ESC to stop", preview)

            if capturing_now:
                last_capture = now
                flash_until = now + 0.4
                crop_img = _crop(frame, CROP_ROI)
                idx = existing + saved
                path = os.path.join(out_dir, "%04d.jpg" % idx)
                cv2.imwrite(path, crop_img)
                saved += 1
                _beep()

            if cv2.waitKey(1) & 0xFF == 27:   # ESC
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("완료: %d장 저장 (%s)" % (saved, out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
