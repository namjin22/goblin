# -*- coding: utf-8 -*-
"""농깨비 메인 루프.

실행
  python main.py --mock          하드웨어·웹캠 둘 다 없이 (개발용)
  python main.py --mock-hw       MODI만 없이, 웹캠은 실물 (비전 기능 개발용)
  python main.py                 실물 MODI + 웹캠
  python main.py --ble UUID      BLE 무선 (마지막 리허설에서만)
  python main.py --calib wet     젖은 흙 기준 잡기
  python main.py --calib dry     마른 흙 기준 잡기

[스레드 구조]
  메인 스레드  : 하드웨어를 독점한다. 센서 읽기 -> 판단 -> 액추에이터
  Flask 스레드 : 상태를 읽고 명령을 큐에 넣기만 한다

  하드웨어를 두 스레드에서 만지면 시리얼 통신이 깨진다.
"""

import argparse
import sys
import time

import hardware as hardware_module
from audio import build_audio
from controller import Controller
from hardware import build_hardware
from profiles import CROP_PROFILES
from server import start_server
from state import LOG_PATH, Store
from vision import build_vision

LOOP_INTERVAL = 0.3      # 초. 너무 짧으면 모듈 통신이 밀린다.
MOCK_LOG_PATH = "log_mock.csv"


def _verify_vent_direction(hw):
    """환기창이 실제로 열리고 닫히는지 확인하고, 틀렸으면 그 자리에서 고친다.

    hardware.open_vent()/close_vent()는 상대회전이라 여기서 열고 닫는
    것만으로 항상 원래 위치로 돌아온다(절대각 계산이 없어서 안전하다).
    VENT_A_SIGN/VENT_B_SIGN 부호가 실제 배선과 안 맞으면 여기서 그 자리에서
    바로 고칠 수 있다 - hwtest.py나 코드 편집까지 갈 필요 없다.
    """
    while True:
        print("환기창 방향을 확인한다 (여는 중)...")
        hw.open_vent()
        time.sleep(2.5)
        ans = input(
            "환기창이 잘 열렸나? "
            "(y=문제없음 / a=모터A만 반대 / b=모터B만 반대 / ab=둘다 반대 / s=건너뛰기) "
        ).strip().lower()
        print("닫는 중...")
        hw.close_vent()
        time.sleep(2.5)

        if ans in ("y", "s", ""):
            break
        if ans in ("a", "ab"):
            hardware_module.VENT_A_SIGN *= -1
        if ans in ("b", "ab"):
            hardware_module.VENT_B_SIGN *= -1
        print("수정함: VENT_A_SIGN=%d VENT_B_SIGN=%d - 다시 확인한다"
              % (hardware_module.VENT_A_SIGN, hardware_module.VENT_B_SIGN))

    print("확정: VENT_A_SIGN=%d VENT_B_SIGN=%d"
          % (hardware_module.VENT_A_SIGN, hardware_module.VENT_B_SIGN))
    print("(다음 실행에도 계속 쓰려면 hardware.py 위쪽 상수를 이 값으로 맞출 것)")


def parse_args():
    p = argparse.ArgumentParser(description="농깨비 - 묻지 않고 알아서 돌보는 스마트팜")
    p.add_argument("--mock", action="store_true",
                   help="MODI·웹캠 없이 가짜 하드웨어로 실행")
    p.add_argument("--mock-hw", action="store_true",
                   help="MODI만 가짜로 실행하고 웹캠은 실물을 쓴다 "
                        "(MODI 없이 비전 기능만 개발할 때)")
    p.add_argument("--ble", metavar="UUID", default=None,
                   help="BLE 무선 연결 (network uuid)")
    p.add_argument("--cam", type=int, default=0, help="웹캠 인덱스")
    p.add_argument("--mute", action="store_true",
                   help="노트북에서 나는 소리(경고음/인식음)를 끈다")
    p.add_argument("--sound", action="store_true",
                   help="모의 실행(--mock/--mock-hw)에서도 소리를 낸다 (기본은 무음)")
    p.add_argument("--mock-crop", choices=list(CROP_PROFILES.keys()), default="lettuce",
                   help="--mock일 때 가짜 비전이 인식할 작물 (웹 UI 개발용)")
    p.add_argument("--mock-cycle", type=float, default=0, metavar="SEC",
                   help="--mock일 때 이 간격(초)마다 작물이 상추→옥수수→당근→없음 순으로 "
                        "바뀐다. 하드웨어 없이 '작물이 바뀌는 순간'을 웹에서 볼 때 쓴다")
    p.add_argument("--port", type=int, default=5000, help="API 포트")
    p.add_argument("--no-auto", action="store_true",
                   help="자동 조치를 끄고 수동 조작만 받는다")
    p.add_argument("--calib", choices=["wet", "dry"], default=None,
                   help="흙 캘리브레이션만 수행하고 종료")
    p.add_argument("--camera-preview", action="store_true",
                   help="앱에 웹캠 미리보기 제공 (5초마다 그 순간의 스냅샷으로 "
                        "갱신. 기본은 꺼짐)")
    p.add_argument("--force-crop", choices=list(CROP_PROFILES.keys()), default=None,
                   help="[시연 촬영용, 임시] 카메라 인식을 무시하고 항상 이 작물로 "
                        "취급한다. 브릭 인식이 안 맞아 촬영이 힘들 때만 쓰고, "
                        "끝나면 빼고 다시 실행할 것 (묻지 않는다는 핵심과 어긋나는 우회)")
    p.add_argument("--verify-vent", action="store_true",
                   help="시작할 때 환기창 닫힘 확인 + 열림/닫힘 방향 확인 프롬프트를 "
                        "띄운다 (기본은 꺼짐 - 방향/각도가 이미 확정됐으면 "
                        "매번 확인할 필요 없다. 배선을 다시 만졌을 때만 켤 것)")
    return p.parse_args()


def run_calibration(args):
    """마른 흙 / 젖은 흙 기준을 잡는다. 대회장 조명에서 반드시 다시 할 것."""
    vision = build_vision(mock=False, cam_index=args.cam)
    if not hasattr(vision, "cap"):
        print("웹캠이 필요하다. Mock 비전으로는 캘리브레이션할 수 없다.")
        return 1

    label = "젖은" if args.calib == "wet" else "마른"
    print("%s 흙을 카메라 앞에 두고 Enter를 누르세요." % label)
    input()
    result = vision.calibrate(args.calib)
    vision.release()

    if result is None:
        print("촬영 실패. 다시 시도할 것.")
        return 1
    print("저장 완료:", result)
    return 0


def main():
    args = parse_args()

    if args.calib:
        return run_calibration(args)

    mock_hw = args.mock or args.mock_hw

    # [중요] 모의 실행의 가짜 기록이 실물 실행의 "최근 기록"에 섞이지 않게 파일을 따로 쓴다.
    store = Store(log_path=MOCK_LOG_PATH if mock_hw else LOG_PATH)
    store.update(mock=mock_hw, auto_mode=not args.no_auto)

    # [중요] state.py는 시작할 때 vent_open=False(닫힘)로 가정한다.
    # 환기창은 상대회전으로 움직이므로(hardware.py 참고), 이 가정이 실제
    # 상태와 다르면 열기/닫기가 상태 가드에 막히거나 겹쳐 돌아서 위치가
    # 어긋난다. 방향(VENT_A_SIGN/VENT_B_SIGN)도 이미 실물로 확정됐으니
    # (2026-08-01) 기본은 그냥 믿고 넘어간다 - 배선을 다시 만졌을 때만
    # --verify-vent로 다시 확인할 것.
    if not mock_hw and args.verify_vent:
        input("환기창을 완전히 닫아둔 상태인지 확인하고 Enter를 누르세요 ")

    # 1) 하드웨어 연결
    try:
        hw = build_hardware(
            mock=mock_hw,
            conn_type="ble" if args.ble else None,
            network_uuid=args.ble,
        )
    except Exception as e:
        print("[오류] 하드웨어 연결 실패:", e)
        print("       --mock 또는 --mock-hw 로 실행하면 MODI 없이 개발할 수 있다.")
        return 1

    if not mock_hw and args.verify_vent:
        _verify_vent_direction(hw)

    # 2) 비전 준비 (--mock-hw만 줬으면 웹캠은 실물을 쓴다. 실패 시 자동으로 Mock)
    vision = build_vision(mock=args.mock, cam_index=args.cam, crop=args.mock_crop,
                          cycle=args.mock_cycle)

    # 3) API 서버 시작
    start_server(store, port=args.port)

    # 4) 제어기
    # 소리는 MODI Speaker가 아니라 노트북에서 낸다. 모의 실행은 개발 중 시끄러우니 기본 무음.
    audio = build_audio(mute=args.mute or (mock_hw and not args.sound))
    # [중요] 모의 비전(--mock)이 만드는 건 가짜(합성) 사진이다. 웹에서 촬영/학습을 해 보더라도
    # 진짜 data/ models/ 에 섞이거나 진짜 모델을 덮어쓰면 안 되므로 폴더를 따로 쓴다.
    # (--mock-hw 는 진짜 웹캠이라 진짜 폴더를 쓴다)
    data_dir, model_dir = ("data_mock", "models_mock") if args.mock else ("data", "models")
    ctrl = Controller(hw, store, vision=vision, camera_preview=args.camera_preview,
                      force_crop=args.force_crop, audio=audio,
                      data_dir=data_dir, model_dir=model_dir)
    if args.force_crop:
        print("[주의] --force-crop %s : 카메라 인식 무시하고 항상 이 작물로 표시함 (촬영용)" % args.force_crop)

    # Mock 환경에서는 급수 시 건조도가 실제로 회복되도록 연결해둔다.
    if hasattr(vision, "on_water"):
        original_water = ctrl.water

        def water_with_effect():
            ok = original_water()
            if ok:
                vision.on_water()
            return ok

        ctrl.water = water_with_effect

    print("=" * 56)
    print(" 농깨비 - 묻지 않고 알아서 돌보는 스마트팜")
    print(" 모드: %s | 자동조치: %s" % (
        "MOCK" if args.mock else ("MOCK-HW(웹캠 실물)" if mock_hw else "실물"),
        "끔" if args.no_auto else "켬",
    ))
    print(" 종료하려면 Ctrl+C")
    print("=" * 56)

    # 5) 메인 루프
    last_print = 0.0
    try:
        while True:
            started = time.time()

            try:
                ctrl.tick(auto_mode=not args.no_auto)
                if store.get("hw_error"):
                    store.update(hw_error=None)
                    store.add_history("hw_ok", "장치 통신이 다시 정상이 되었습니다")
            except Exception as e:
                # 한 틱이 실패해도 전체가 죽으면 안 된다.
                # 시연 중 모듈 하나가 튀어도 계속 돌아가야 한다.
                print("[경고] tick 실패:", e)
                # 웹 화면이 "장치 통신 문제"를 바로 보여줄 수 있게 남긴다
                if not store.get("hw_error"):
                    store.add_history("hw_error", "장치 통신에 문제가 생겼습니다")
                store.update(hw_error=str(e)[:160] or e.__class__.__name__)
                time.sleep(1)

            # 1초에 한 번만 콘솔에 출력
            if started - last_print >= 1.0:
                last_print = started
                s = store.snapshot()
                print("[%s] %.1fC 조도%.0f 건조도%s %s | %s" % (
                    time.strftime("%H:%M:%S"),
                    s["temperature"] or 0,
                    s["illuminance"] or 0,
                    round(s["dryness"]) if s["dryness"] is not None else "-",
                    "(동작중:%s)" % s["busy_action"] if s["busy"] else "",
                    s["message"],
                ))

            elapsed = time.time() - started
            time.sleep(max(0.0, LOOP_INTERVAL - elapsed))

    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        try:
            hw.set_sprinkler(0)
            hw.close()
        except Exception:
            pass
        audio.close()
        ctrl.shutdown()
        if hasattr(vision, "release"):
            vision.release()

    return 0


if __name__ == "__main__":
    sys.exit(main())
