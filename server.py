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
"""

import os
import threading
import time

from flask import Flask, Response, jsonify, request, send_from_directory

from controller import GROWTH_PHOTO_DIR
from profiles import get_profile
from state import VALID_COMMANDS


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


def create_app(store):
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
        """테스트용 화면. 휴대폰 브라우저로 바로 열어볼 수 있다.

        앱이 완성되기 전까지 이걸로 전체 흐름을 확인한다.
        앱 담당자에게는 참고 구현으로 넘기면 된다.
        """
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "testapp.html")
        if not os.path.exists(path):
            return "testapp.html 이 없습니다", 404
        with open(path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")

    @app.route("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.route("/api/state")
    def get_state():
        """앱 [1] 지금 상태 화면용.

        어르신용 화면이므로 앱은 message 와 level 만 크게 보여주면 된다.
        나머지 수치는 필요할 때만 쓴다.
        """
        snap = store.snapshot()
        growth = _growth_info(snap)
        return jsonify({
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
        가능한 값: vent_open, vent_close, water, scan
        """
        if request.method == "OPTIONS":
            return ("", 204)

        data = request.get_json(silent=True) or {}
        cmd = data.get("command")

        if cmd not in VALID_COMMANDS:
            return jsonify({
                "ok": False,
                "error": "알 수 없는 명령입니다",
                "valid": sorted(VALID_COMMANDS),
            }), 400

        if store.get("busy"):
            return jsonify({
                "ok": False,
                "error": "지금 다른 동작을 하고 있어요. 잠시 뒤에 눌러주세요",
            }), 409

        store.push_command(cmd, source="app")
        return jsonify({"ok": True, "queued": cmd})

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
    app = create_app(store)

    def run():
        # reloader를 끄지 않으면 스레드에서 문제가 생긴다.
        app.run(host=host, port=port, debug=False,
                use_reloader=False, threaded=True)

    t = threading.Thread(target=run, daemon=True, name="flask")
    t.start()
    print("[API] http://%s:%d 에서 대기 중" % (host, port))
    return t
