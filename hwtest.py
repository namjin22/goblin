# -*- coding: utf-8 -*-
"""실물 MODI Plus 점검 스크립트.

main.py를 돌리기 전에 이걸 먼저 실행한다.
모듈을 하나씩 따로 확인하기 때문에, 문제가 생겨도
'어느 모듈이 문제인지' 바로 알 수 있다.

    python hwtest.py            전체 점검
    python hwtest.py --motor    모터만
    python hwtest.py --sensor   센서만
"""

import argparse
import sys
import time

try:
    import modi_plus
except ImportError:
    print("pymodi-plus가 없다.  pip install pymodi-plus")
    sys.exit(1)


def line(title):
    print()
    print("=" * 54)
    print(" " + title)
    print("=" * 54)


def ask(msg):
    """사람에게 확인받는다. y가 아니면 실패로 기록."""
    ans = input("  >> %s (y/n) " % msg).strip().lower()
    return ans.startswith("y")


def connect():
    line("1. 연결")
    print("  Network 모듈이 USB로 꽂혀 있어야 한다.")
    bundle = modi_plus.MODIPlus()
    time.sleep(1)

    print("\n  연결된 모듈:")
    for m in bundle.modules:
        print("    -", m)

    counts = {
        "env": len(bundle.envs),
        "tof": len(bundle.tofs),
        "dial": len(bundle.dials),
        "button": len(bundle.buttons),
        "led": len(bundle.leds),
        "display": len(bundle.displays),
        "speaker": len(bundle.speakers),
        "motor": len(bundle.motors),
    }
    print("\n  모듈 개수:", counts)

    missing = [k for k, v in counts.items() if v == 0]
    if missing:
        print("\n  [경고] 인식 안 된 모듈:", ", ".join(missing))
        print("         케이블을 다시 꽂고 python -m modi_plus --inspect 확인")
    if counts["motor"] < 2:
        print("\n  [경고] 모터가 2개여야 한다 (환기창 + 스프링클러)")

    return bundle, counts


def test_outputs(bundle, results):
    line("2. 출력 모듈 (LED / Display / Speaker)")

    if bundle.leds:
        led = bundle.leds[0]
        print("  LED: 빨강 -> 초록 -> 파랑 순서로 켠다")
        for name, rgb in [("빨강", (255, 0, 0)),
                          ("초록", (0, 255, 0)),
                          ("파랑", (0, 0, 255))]:
            led.rgb = rgb
            print("    ", name)
            time.sleep(1.2)
        led.turn_off()
        results["LED"] = ask("LED가 세 가지 색으로 바뀌었나?")

    if bundle.displays:
        display = bundle.displays[0]
        display.text = "농깨비 점검"
        time.sleep(2)
        results["Display"] = ask("화면에 '농깨비 점검'이 떴나?")
        display.reset()

    if bundle.speakers:
        speaker = bundle.speakers[0]
        print("  Speaker: 소리를 낸다")
        speaker.tune = 880, 50
        time.sleep(1.5)
        speaker.reset()          # 주의: turn_off()가 아니라 reset()
        results["Speaker"] = ask("소리가 났나?")


def test_sensors(bundle, results):
    line("3. 입력 모듈 (Env / ToF / Dial / Button)")

    if bundle.envs:
        env = bundle.envs[0]
        print("  Env 5초간 측정:")
        for _ in range(5):
            print("    온도 %.1fC  습도 %.0f%%  조도 %.0f"
                  % (env.temperature, env.humidity, env.illuminance))
            time.sleep(1)
        results["Env"] = ask("값이 0이 아니고 그럴듯한가?")

    if bundle.tofs:
        tof = bundle.tofs[0]
        print("  ToF: 손을 가까이 댔다 뗐다 해보세요 (5초)")
        for _ in range(10):
            print("    거리 %.0f cm" % tof.distance)
            time.sleep(0.5)
        results["ToF"] = ask("손을 움직일 때 거리가 따라 변했나?")

    if bundle.dials:
        dial = bundle.dials[0]
        print("  Dial: 손잡이를 돌려보세요 (5초)")
        for _ in range(10):
            print("    각도 %d" % dial.turn)
            time.sleep(0.5)
        results["Dial"] = ask("돌릴 때 숫자가 변했나?")

    if bundle.buttons:
        button = bundle.buttons[0]
        print("  Button: 10초 안에 버튼을 눌러보세요")
        detected = False
        for _ in range(100):
            if button.clicked:
                print("    클릭 감지!")
                detected = True
                break
            time.sleep(0.1)
        results["Button"] = detected
        if not detected:
            print("    시간 초과. 버튼이 감지되지 않았다.")


def test_motors(bundle, results):
    line("4. 모터 - 어느 쪽이 환기창인지 확인")

    motors = bundle.motors
    if not motors:
        print("  모터가 없다.")
        return

    print("  모터를 하나씩 돌린다. 무엇이 움직이는지 잘 볼 것.\n")

    roles = {}
    for i, motor in enumerate(motors):
        print("  --- motors[%d] 를 돌린다 ---" % i)
        motor.speed = 40
        time.sleep(2.5)
        motor.speed = 0
        time.sleep(0.5)

        ans = input("  >> 무엇이 움직였나? (1=환기창, 2=스프링클러, 0=아무것도) ")
        ans = ans.strip()
        if ans == "1":
            roles["vent"] = i
        elif ans == "2":
            roles["sprinkler"] = i

    print()
    if "vent" in roles and "sprinkler" in roles:
        print("  확인 결과:")
        print("    환기창    = motors[%d]" % roles["vent"])
        print("    스프링클러 = motors[%d]" % roles["sprinkler"])
        print()
        if roles["vent"] == 0 and roles["sprinkler"] == 1:
            print("  hardware.py 기본값 그대로 쓰면 된다. 수정 불필요.")
        else:
            print("  [중요] hardware.py 위쪽을 아래처럼 고칠 것:")
            print("      VENT_MOTOR_INDEX = %d" % roles["vent"])
            print("      SPRINKLER_MOTOR_INDEX = %d" % roles["sprinkler"])
        results["Motor"] = True
    else:
        print("  모터 역할을 특정하지 못했다. 다시 실행해볼 것.")
        results["Motor"] = False

    # 환기창 각도 제어도 확인
    if "vent" in roles:
        vent = motors[roles["vent"]]
        print("\n  환기창 각도 제어 확인: 0도 -> 90도 -> 0도")
        for angle in (0, 90, 0):
            vent.angle = angle, 50
            print("    %d도" % angle)
            time.sleep(2.5)
        results["Vent angle"] = ask("환기창이 열렸다 닫혔나?")


def cleanup(bundle):
    try:
        for m in bundle.motors:
            m.speed = 0
        if bundle.speakers:
            bundle.speakers[0].reset()
        if bundle.leds:
            bundle.leds[0].turn_off()
        if bundle.displays:
            bundle.displays[0].reset()
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--motor", action="store_true", help="모터만 점검")
    p.add_argument("--sensor", action="store_true", help="센서만 점검")
    args = p.parse_args()

    results = {}
    bundle = None
    try:
        bundle, counts = connect()

        run_all = not (args.motor or args.sensor)
        if run_all:
            test_outputs(bundle, results)
        if run_all or args.sensor:
            test_sensors(bundle, results)
        if run_all or args.motor:
            test_motors(bundle, results)

        line("점검 결과")
        if not results:
            print("  확인된 항목 없음")
        for name, ok in results.items():
            print("  %-12s %s" % (name, "정상" if ok else "확인 필요"))

        bad = [k for k, v in results.items() if not v]
        print()
        if bad:
            print("  문제 항목:", ", ".join(bad))
            print("  케이블을 다시 꽂고 해당 항목만 재점검할 것.")
        else:
            print("  전부 정상. main.py를 실행해도 된다.")

    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        print("\n[오류]", e)
        print("확인: USB 케이블 / Network 모듈 펌웨어 / python -m modi_plus --inspect")
    finally:
        if bundle:
            cleanup(bundle)


if __name__ == "__main__":
    main()
