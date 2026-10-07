# -*- coding: utf-8 -*-
"""앱과 통신하는 Flask HTTP 서버.

[규칙] 이 파일에서는 하드웨어를 절대 만지지 않는다.
       상태를 읽고, 명령을 큐에 넣을 뿐이다.

앱 담당 팀원에게 알려줄 API
  GET  /api/state          현재 상태 (앱 [1] 지금 상태 화면)
  POST /api/command        수동 조작   (앱 [2] 직접 하기 화면)
  GET  /api/history        지난 기록   (앱 [3] 지난 기록 화면)
  GET  /api/growth_photos  주간 성장 사진 목록
  GET  /api/health         서버 살아있는지 확인
  GET  /camera/snapshot.jpg  웹캠 최신 프레임 한 장 (앱이 주기적으로 다시 요청해서 "실시간처럼" 보여줄 것)
"""

import os
import socket
import threading
import time

from flask import Flask, Response, jsonify, request, send_from_directory

from controller import (GROWTH_PHOTO_DIR, HEAT_DANGER_TEMP, LIGHT_HYSTERESIS,
                        RAIN_HUMIDITY_THRESHOLD)
from profiles import CROP_PROFILES, get_profile
from state import INSTANT_COMMANDS, VALID_COMMANDS
from training import valid_classes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIST = os.path.join(BASE_DIR, "web", "dist")   # 새 웹 UI (npm run build 결과물)


def lan_ip():
    """같은 네트워크의 폰이 접속할 수 있는 이 노트북의 주소. 못 찾으면 None.

    실제로 패킷을 보내지는 않는다(UDP connect는 경로만 고른다).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


def _validate_args(cmd, args, snap):
    """인자가 있는 명령의 값을 검증한다. 문제가 없으면 None, 있으면 사람이 읽을 오류 문구.

    웹 화면 말고도 같은 네트워크의 누구나 이 API를 부를 수 있으므로, 모터를 돌리는
    인자는 반드시 서버에서 다시 확인한다 (알려진 모터 ID만, 각도는 작게).
    """
    needs_args = {"jog", "set_roles", "flip_sign", "collect_start", "data_clear"}
    if cmd not in needs_args:
        return None if args is None else "이 명령은 인자를 받지 않아요"
    if not isinstance(args, dict):
        return "인자가 필요해요"

    hw = snap.get("hw") or {}
    ids = {m["id"] for m in hw.get("motors", [])}

    def is_id(v):
        return isinstance(v, int) and not isinstance(v, bool) and v in ids

    if cmd == "jog":
        delta = args.get("delta")
        if not is_id(args.get("motor_id")):
            return "연결되지 않은 모터예요"
        if not (isinstance(delta, int) and not isinstance(delta, bool) and 0 < abs(delta) <= 30):
            return "각도는 1~30도 사이여야 해요"
    elif cmd == "set_roles":
        a, b, s = args.get("vent_a"), args.get("vent_b"), args.get("sprinkler")
        if not (is_id(a) and is_id(b)):
            return "환기창 모터 A와 B를 모두 골라야 해요"
        if s is not None and not is_id(s):
            return "스프링클러 모터가 올바르지 않아요"
        chosen = [x for x in (a, b, s) if x is not None]
        if len(set(chosen)) != len(chosen):
            return "같은 모터를 두 역할에 쓸 수 없어요"
    elif cmd == "flip_sign":
        if args.get("which") not in ("a", "b"):
            return "a 또는 b여야 해요"
    elif cmd in ("collect_start", "data_clear"):
        if args.get("crop") not in valid_classes():
            return "알 수 없는 작물이에요"
        target = args.get("target")
        if cmd == "collect_start" and target is not None:
            if not (isinstance(target, int) and not isinstance(target, bool) and 5 <= target <= 60):
                return "사진 장수는 5~60장이어야 해요"
    return None


def _thresholds(profile):
    """웹 화면의 기준선 게이지에 쓰는 값. 판단 로직(controller.decide)과 같은 상수를 쓴다."""
    return {
        "vent_temp": profile["vent_temp"],
        "vent_alert_temp": profile["vent_temp"] + 3,     # decide()의 alert 경계
        "dry_limit": profile["dry_limit"],
        "min_lux": profile["min_lux"],
        "light_off_lux": profile["min_lux"] + LIGHT_HYSTERESIS,
        "rain_humidity": RAIN_HUMIDITY_THRESHOLD,
        "heat_danger_temp": HEAT_DANGER_TEMP,
    }


def _growth_info(snap):
    """성장 일수/수확 예정일을 계산한다.

    실측(웹캠으로 크기 측정)이 아니라 "이 작물을 처음 인식한 시각"부터
    프로파일의 평균 재배 일수(grow_days)를 더한 추정치다.
    """
    started_at = snap.get("crop_started_at")
    profile = get_profile(snap.get("crop_key"))
    grow_days = profile.get("grow_days")
    if started_at is None or grow_days is None:
        return {"growth_stage": None, "days_growing": None, "harvest_date": None}

    days_growing = int((time.time() - started_at) // 86400)
    percent = max(0, min(100, round(days_growing / grow_days * 100)))

    if percent >= 90:
        stage = "수확할 때가 다 됐어요"
    elif percent >= 60:
        stage = "많이 자랐어요"
    elif percent >= 25:
        stage = "한창 자라는 중이에요"
    else:
        stage = "이제 막 자라기 시작했어요"

    harvest_epoch = started_at + grow_days * 86400
    harvest_date = time.strftime("%m월 %d일", time.localtime(harvest_epoch))

    return {
        "growth_stage": stage,
        "days_growing": days_growing,
        "harvest_date": harvest_date,
    }


def create_app(store, port=5000):
    app = Flask(__name__)

    # 한글을 \uXXXX 로 escape 하지 않고 그대로 내보낸다.
    # (escape 되어도 앱의 JSON.parse 는 정상 처리하지만, 브라우저로
    #  직접 확인할 때 읽을 수 없어서 디버깅이 불편하다)
    try:
        app.json.ensure_ascii = False          # Flask 2.3 이상
    except AttributeError:
        app.config["JSON_AS_ASCII"] = False    # 구버전 Flask

    # 앱이 다른 기기에서 접속할 수 있도록 CORS 허용
    @app.after_request
    def add_cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        # [중요] 캐시 헤더가 없으면 일부 모바일 브라우저(삼성인터넷 등)가
        # /api/state 같은 GET 응답을 자체적으로 캐싱해버린다. 서버 로그로는
        # 매초 새로 응답하는데 화면은 그대로 멈춰 보이는 원인이 이거였다.
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp

    @app.route("/")
    def index():
        """부스용 새 웹 UI(web/dist). 빌드 전이면 예전 testapp.html로 대신한다."""
        if os.path.exists(os.path.join(WEB_DIST, "index.html")):
            return send_from_directory(WEB_DIST, "index.html")
        return legacy()

    @app.route("/legacy")
    def legacy():
        """예전 테스트용 화면(testapp.html). 새 웹이 문제일 때의 대비책."""
        path = os.path.join(BASE_DIR, "testapp.html")
        if not os.path.exists(path):
            return "testapp.html 이 없습니다", 404
        with open(path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")

    @app.route("/assets/<path:filename>")
    def web_assets(filename):
        """Vite 빌드가 만든 JS/CSS/폰트 (web/dist/assets)."""
        return send_from_directory(os.path.join(WEB_DIST, "assets"), filename)

    @app.route("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.route("/api/info")
    def info():
        """폰 접속용 주소(QR 코드에 쓴다). 노트북 IP는 서버만 알 수 있다."""
        ip = lan_ip()
        return jsonify({
            "lan_url": "http://%s:%d" % (ip, port) if ip else None,
            "port": port,
        })

    @app.route("/camera/snapshot.jpg")
    def camera_snapshot():
        """실시간 웹캠 미리보기용 스냅샷 한 장.

        [설계] 처음엔 MJPEG로 연결을 계속 열어두는 스트림(/camera/stream)으로
        만들었는데, Flask 개발서버는 이런 상시연결에 약해서 그 연결 하나가
        모바일 브라우저의 동시연결 한도(보통 6개)를 계속 차지해 /api/state
        폴링이 막히는 문제가 있었다("대시보드가 멈춘 것처럼 보임"의 원인).
        그래서 요청마다 바로 끝나는 스냅샷 한 장으로 바꾸고, 앱이 주기적으로
        다시 요청하는 방식으로 "실시간처럼" 보이게 한다.
        """
        frame = store.get_camera_frame()
        if frame is None:
            return "카메라 프레임 없음", 503
        return Response(frame, mimetype="image/jpeg")

    @app.route("/api/state")
    def get_state():
        """앱 [1] 지금 상태 화면용.

        어르신용 화면이므로 앱은 message 와 level 만 크게 보여주면 된다.
        나머지 수치는 필요할 때만 쓴다.
        """
        snap = store.snapshot()
        growth = _growth_info(snap)
        profile = get_profile(snap.get("crop_key"))
        return jsonify({
            # --- 부스 웹 UI용 ---
            "crop_key": snap.get("crop_key"),
            "crop_probs": snap.get("crop_probs"),        # {"lettuce": 0.93, ...} 또는 null
            "reason": snap.get("reason"),                # 판단 근거 한 줄
            "display_text": snap.get("display_text"),    # Display 모듈에 나가는 두 줄
            "auto_mode": snap.get("auto_mode"),
            "sound_on": snap.get("sound_on"),            # 노트북에서 소리가 나는지
            "hw": snap.get("hw"),                        # 모터 목록/역할/방향/ready (장치 점검 화면용)
            # --- AI 학습 화면용 ---
            "collect": snap.get("collect"),              # 사진 촬영 진행
            "train": snap.get("train"),                  # 학습 진행/결과
            "dataset": snap.get("dataset"),              # 클래스별 사진 장수
            "model_classes": snap.get("model_classes"),  # 지금 모델이 아는 클래스
            "camera_real": snap.get("camera_real"),      # 진짜 웹캠인가
            "vent_ready": (snap.get("hw") or {}).get("vent_ready", True),
            "vent_roles_ok": (snap.get("hw") or {}).get("vent_roles_ok", True),
            "vent_verified": (snap.get("hw") or {}).get("vent_verified", True),
            "sprinkler_ready": (snap.get("hw") or {}).get("sprinkler_ready", True),
            "vent_assumed": snap.get("vent_assumed"),    # True면 창문 상태가 사람이 확인 안 된 추정값
            "hw_error": snap.get("hw_error"),            # 장치 통신 오류 (정상이면 null)
            # 메인 루프가 멈췄는지(updated_at이 오래됨)를 브라우저 시계와 무관하게 판단하려고
            "server_time": time.time(),
            "thresholds": _thresholds(profile),
            "has_camera_frame": store.get_camera_frame() is not None,
            "message": snap["message"],          # 큰 글씨 한 줄
            "short": snap.get("short"),          # Display에 나가는 짧은 단어
            "level": snap["level"],              # good / warn / alert -> 배경색
            "crop_name": snap["crop_name"],
            "temperature": snap["temperature"],
            "humidity": snap["humidity"],
            "illuminance": snap["illuminance"],
            "dryness": snap["dryness"],
            "vent_open": snap["vent_open"],
            "sprinkler_on": snap["sprinkler_on"],
            "light_on": snap["light_on"],        # 생장등
            "busy": snap["busy"],
            "busy_action": snap["busy_action"],
            "mock": snap["mock"],
            "updated_at": snap["updated_at"],
            # 성장 정도 - 실측이 아니라 인식 이후 경과일 기준 추정치(_growth_info 참고)
            "growth_stage": growth["growth_stage"],
            "days_growing": growth["days_growing"],
            "harvest_date": growth["harvest_date"],
        })

    @app.route("/api/command", methods=["POST", "OPTIONS"])
    def post_command():
        """앱 [2] 직접 하기 화면용.

        요청 예: {"command": "water"}
        가능한 값: state.VALID_COMMANDS 참고
        """
        if request.method == "OPTIONS":
            return ("", 204)

        data = request.get_json(silent=True) or {}
        cmd = data.get("command")
        args = data.get("args")

        if cmd not in VALID_COMMANDS:
            return jsonify({
                "ok": False,
                "error": "알 수 없는 명령입니다",
                "valid": sorted(VALID_COMMANDS),
            }), 400

        error = _validate_args(cmd, args, store.snapshot())
        if error:
            return jsonify({"ok": False, "error": error}), 400

        # 모터를 안 쓰는 명령(자동 on/off 등)은 동작 중에도 받는다
        if store.get("busy") and cmd not in INSTANT_COMMANDS:
            return jsonify({
                "ok": False,
                "error": "지금 다른 동작을 하고 있어요. 잠시 뒤에 눌러주세요",
            }), 409

        store.push_command(cmd, source="app", args=args)
        return jsonify({"ok": True, "queued": cmd})

    @app.route("/api/profiles")
    def get_profiles():
        """모든 작물의 기준값. "같은 장치, 작물마다 다른 판단"을 나란히 보여주는 화면용."""
        return jsonify({"items": [
            {"key": key, "name": p["name"], "note": p.get("note"),
             "thresholds": _thresholds(p)}
            for key, p in CROP_PROFILES.items()
        ]})

    @app.route("/api/history")
    def get_history():
        """앱 [3] 지난 기록 화면용."""
        limit = request.args.get("limit", default=50, type=int)
        return jsonify({"items": store.history(limit=limit)})

    @app.route("/api/growth_photos")
    def get_growth_photos():
        """지금 인식 중인 작물의 주간 성장 사진 목록.

        웹캠으로 실제 크기를 잰 게 아니라 controller.py가 일주일에 한 번
        찍어 남겨둔 스냅샷이다(controller._maybe_save_growth_photo 참고).
        """
        crop_key = store.get("crop_key")
        photos = store.growth_photos(crop_key=crop_key)
        items = [{
            "week": p["week"],
            "crop_name": p["crop_name"],
            "taken_at": p["taken_at"],
            "url": "/growth_photos/%s" % p["filename"],
        } for p in photos]
        return jsonify({"items": items})

    @app.route("/growth_photos/<path:filename>")
    def get_growth_photo_file(filename):
        directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), GROWTH_PHOTO_DIR)
        return send_from_directory(directory, filename)

    return app


def start_server(store, host="0.0.0.0", port=5000):
    """Flask를 별도 스레드에서 띄운다. 메인 루프를 막지 않는다."""
    app = create_app(store, port=port)

    def run():
        # reloader를 끄지 않으면 스레드에서 문제가 생긴다.
        app.run(host=host, port=port, debug=False,
                use_reloader=False, threaded=True)

    t = threading.Thread(target=run, daemon=True, name="flask")
    t.start()
    print("[API] http://%s:%d 에서 대기 중" % (host, port))
    return t
