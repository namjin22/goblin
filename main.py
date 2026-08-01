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
from controller import Controller
from hardware import build_hardware
from server import start_server
from state import Store
from vision import build_vision

LOOP_INTERVAL = 0.3      # 초. 너무 짧으면 모듈 통신이 밀린다.


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
    p.add_argument("--port", type=int, default=5000, help="API 포트")
    p.add_argument("--no-auto", action="store_true",
                   help="자동 조치를 끄고 수동 조작만 받는다")
    p.add_argument("--calib", choices=["wet", "dry"], default=None,
                   help="흙 캘리브레이션만 수행하고 종료")
    p.add_argument("--camera-preview", action="store_true",
                   help="앱에 실시간 웹캠 미리보기 제공 (실험적 - 웹캠을 "
                        "0.5초마다 읽어서 메인 루프가 멈출 위험이 있다고 "
                        "의심됨. 기본은 꺼짐)")
    p.add_argument("--skip-vent-confirm", action="store_true",
                   help="환기창 닫힘 확인 + 열림/닫힘 방향 확인 프롬프트 둘 다 "
                        "생략 (문이 항상 닫혀있고 방향도 확실할 때만. 데모 녹화 등)")
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

    store = Store()
    store.update(mock=mock_hw)

    # [중요] state.py는 시작할 때 vent_open=False(닫힘)로 가정한다.
    # 환기창은 이제 상대회전으로 움직이므로(hardware.py 참고), 이 가정이
    # 실제 상태와 다르면 열기/닫기가 상태 가드에 막히거나 겹쳐 돌아서
    # 위치가 어긋난다. 그래서 시작할 때 실제로 닫혀 있는지 확인한다.
    if not mock_hw and not args.skip_vent_confirm:
        input("환기창을 완전히 닫아둔 상태인지 확인하고 Enter를 누르세요"
              " (매번 확인 귀찮으면 --skip-vent-confirm) ")

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

    if not mock_hw and not args.skip_vent_confirm:
        _verify_vent_direction(hw)

    # 2) 비전 준비 (--mock-hw만 줬으면 웹캠은 실물을 쓴다. 실패 시 자동으로 Mock)
    vision = build_vision(mock=args.mock, cam_index=args.cam)

    # 3) API 서버 시작
    start_server(store, port=args.port)

    # 4) 제어기
    ctrl = Controller(hw, store, vision=vision, camera_preview=args.camera_preview)

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
            except Exception as e:
                # 한 틱이 실패해도 전체가 죽으면 안 된다.
                # 시연 중 모듈 하나가 튀어도 계속 돌아가야 한다.
                print("[경고] tick 실패:", e)
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
        if hasattr(vision, "release"):
            vision.release()

    return 0


if __name__ == "__main__":
    sys.exit(main())
