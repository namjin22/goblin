# 농깨비 — 통합 제어 시스템

묻지 않고 알아서 돌보는 스마트팜. MODI Plus + 웹캠 + Python.

## 설치

```bash
pip install pymodi-plus flask opencv-python
```

## 실행

```bash
python main.py --mock          # 하드웨어·웹캠 둘 다 없이 (개발용)
python main.py --mock-hw       # MODI만 없이, 웹캠은 실물 (비전 기능 개발용)
python main.py                 # 실물 MODI + 웹캠
python main.py --no-auto       # 자동 조치 끄고 수동 조작만
python main.py --ble UUID      # BLE 무선 (마지막 리허설에서만)
```

캘리브레이션은 **대회장 조명에서 반드시 다시** 잡을 것.

```bash
python main.py --calib wet     # 젖은 흙 기준
python main.py --calib dry     # 마른 흙 기준
```

### 카메라가 여러 대일 때 (`--cam`)

노트북 내장캠과 별도 USB 웹캠이 같이 꽂혀 있으면 `--cam 0`이 어느 쪽인지 장비마다 다르다.
아래로 이름과 인덱스를 먼저 확인할 것 (대회장에서도 한 번 더 확인).

```bash
pip install pygrabber
python -c "from pygrabber.dshow_graph import FilterGraph; [print(i, n) for i, n in enumerate(FilterGraph().get_input_devices())]"
```

확인한 인덱스를 `--cam`에 넘긴다. 예: `python main.py --mock-hw --cam 1`

---

## 스레드 규칙 (제일 중요)

```
메인 스레드   하드웨어 독점. 센서 읽기 → 판단 → 액추에이터
Flask 스레드  상태 읽기, 명령 큐에 넣기. 하드웨어 절대 금지
```

하드웨어를 두 스레드에서 만지면 시리얼 통신이 깨진다. 앱에서 온 명령은 큐에 쌓이고 메인 루프가 꺼내서 실행한다.

`time.sleep()`으로 모터를 기다리지 않는다. `_busy_until` 타임스탬프를 두고 매 틱마다 확인하는 상태머신이라, 모터가 도는 동안에도 센서와 API가 계속 응답한다.

---

## 모듈별 역할 (각 1개)

| 모듈 | 역할 |
|---|---|
| Network ×2 | USB 연결. 한 USB에 체인으로 연결 |
| Env | 온도 → 환기 판단 / 조도 → 생장등 판단 / 습도 → 건조도(급수)·비 감지(자동 닫기) 판단 |
| LED | **생장등**. 주변이 어두우면 켠다 (마젠타) |
| Display | 2줄 짧은 단어 |
| Speaker | alert 진입 순간 0.4초 삑 |
| Motor A | 환기창 (모터B와 함께 움직여야 열림/닫힘) |
| Motor B | 환기창 |
| Motor (스프링클러) | 스프링클러 (모형, 물 안 나옴) |

미사용: **ToF**, IMU, Joystick, Dial, **Button** (물리 버튼 없음 — 수동 조작은 앱 전용)

## 출력 규칙

**Display (96×96이라 긴 문장 금지)**

```
상추         ← 인식된 작물
물 필요      ← 상태 한 단어
```

| 상황 | 2번째 줄 |
|---|---|
| 정상 | `좋아요` |
| 조금 더움 | `조금 더움` |
| 너무 더움 | `더워요!` |
| 흙 마름 | `물 필요` |
| 동작 중 | `창문 여는중` / `창문 닫는중` / `물 주는중` |

**LED = 생장등 전용.** 상태색 표시는 하지 않는다. 상태는 Display와 앱이 보여준다.

**Speaker** — alert로 *바뀌는 순간*에만 0.4초. 계속 울리지 않는다.

## 생장등 발진 방지

생장등을 켜면 Env 조도가 올라가고 → 밝으니 끄고 → 어두워지고 → 켜고… 무한 반복한다.
세 겹으로 막았다.

1. **히스테리시스** — 켜는 기준(`min_lux`)과 끄는 기준(`min_lux + 3`)을 다르게
2. **최소 유지 시간** — 한 번 바뀌면 8초는 안 건드림
3. **자기 밝기 보정** — 생장등이 만든 밝기를 자동 학습해서 빼고 판단 ← 핵심

3번이 근본 해결이다. 알고 싶은 건 "주변이 어두운가"이지 "지금 밝은가"가 아니기 때문.

> ⚠️ **배치 주의** — Env 모듈에 생장등 빛이 정면으로 닿으면 보정 오차가 커진다.
> 생장등과 Env 센서는 서로 마주 보지 않게 두거나, 사이를 레고로 가릴 것.

## 촬영 방식

ToF를 쓰지 않으므로 **6초마다 자동으로 촬영**한다 (`SCAN_INTERVAL`).
어르신은 작물을 카메라 앞에 두기만 하면 되고, 아무 조작도 필요 없다.
즉시 촬영하려면 앱에서 `scan` 명령.

## 환기창

기본은 자동으로 **열기만** 한다. 닫는 것은 사람이 앱으로 한다 (물리 버튼 없음).
단, Env 습도가 비정상적으로 높으면("비가 오는 것 같음") 자동으로 닫는 예외가 하나 있다 (`controller.RAIN_HUMIDITY_THRESHOLD`).

## 앱 담당자용 API

기본 주소 `http://<노트북IP>:5000`

### GET /api/state — 앱 [1] 지금 상태

```json
{
  "message": "상추가 잘 자라고 있어요",
  "level": "good",
  "crop_name": "상추",
  "temperature": 19.4,
  "dryness": 40.0,
  "vent_open": true,
  "sprinkler_on": false,
  "busy": false,
  "growth_stage": "한창 자라는 중이에요",
  "days_growing": 12,
  "harvest_date": "08월 20일"
}
```

`message`와 `level`만 크게 보여주면 된다. `level`은 `good`(초록) / `warn`(노랑) / `alert`(빨강)으로 배경색에 쓴다. 나머지 수치는 필요할 때만.

`growth_stage` / `days_growing` / `harvest_date`는 웹캠으로 실제 크기를 재서 계산한 값이 아니라, **이 작물을 처음 인식한 시각 + 프로파일의 평균 재배 일수(`profiles.py`의 `grow_days`)**로 추정한 값이다. 작물이 바뀌면(다른 작물을 인식하면) 카운트가 새로 시작된다. 아직 작물을 인식하지 못했으면 셋 다 `null`.

### POST /api/command — 앱 [2] 직접 하기

```json
{ "command": "water" }
```

가능한 값: `vent_open` `vent_close` `vent_toggle` `water` `scan` `light_toggle`

`light_toggle`은 생장등을 수동으로 켜고 끈다. 자동 로직(밝기 기준)이 최소
유지시간(8초) 뒤에 다시 판단할 수 있다 — 환기창 자동 개방과 같은 성격이다.

- 성공 `200` → `{"ok": true, "queued": "water"}`
- 동작 중 `409` → `{"ok": false, "error": "지금 다른 동작을 하고 있어요..."}`
- 잘못된 명령 `400`

`409`가 오면 앱은 에러가 아니라 안내 문구로 보여줄 것. 어르신이 버튼을 여러 번 눌러도 중복 실행되지 않는다.

### GET /api/history?limit=50 — 앱 [3] 지난 기록

```json
{ "items": [ { "at": 1785508793.3, "event": "water", "detail": "물을 주었습니다" } ] }
```

최신순. `detail`이 그대로 보여줄 수 있는 문장이다.

### GET /api/growth_photos — 성장 사진

```json
{ "items": [ { "week": 0, "crop_name": "상추", "taken_at": 1785508793.3,
               "url": "/growth_photos/lettuce_week0_1785508793.jpg" } ] }
```

지금 인식 중인 작물의 것만 준다(작물이 바뀌면 새로 시작). `url`은 이 서버 기준
상대 경로이므로 앱에서 `baseUrl + url`로 이어붙여 이미지를 불러오면 된다.
일주일에 한 장씩만 쌓인다 — 실측 크기가 아니라 시간 경과 기준 스냅샷이다.

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `profiles.py` | 작물별 재배 기준. **시연 작물 확정되면 여기만 수정** |
| `hardware.py` | MODI 추상화 + Mock. 여기 밖에서 `modi_plus` import 금지 |
| `hwtest.py` | 실물 모듈 점검. `main.py` 전에 먼저 돌릴 것 |
| `testapp.html` | 앱 참고 구현. `http://노트북IP:5000` 으로 접속 |
| `state.py` | 상태 저장소 + 명령 큐. 두 스레드의 유일한 접점 |
| `vision.py` | 작물 분류 + 토양 건조도. 웹캠 실패 시 자동 Mock |
| `controller.py` | 판단 로직 + 논블로킹 액추에이터 |
| `server.py` | Flask API. 하드웨어 접근 금지 |
| `main.py` | 메인 루프 |
| `growth_photos/` | 주간 성장 사진 저장 위치. 자동 생성, git에는 안 올라감 |

---

## 남은 작업

1. **환기창 모터 방향/각도 보정** — `motor.angle`은 절대각이라 "0=닫힘"이 보장 안 됨(모터마다 조립 기준 다름). `python hwtest.py --motor`를 돌리면 지금 닫힌 상태를 기준점으로 저장하고, 열어본 결과를 물어보면서 방향/각도를 맞을 때까지 대화형으로 조정해준다. 확정되면 나온 값을 `hardware.py`의 `VENT_A_SIGN`/`VENT_B_SIGN`/`VENT_ROTATION_DEG`에 반영할 것.
2. **`min_lux` 현장 튜닝** — 생장등 켰을 때와 껐을 때 조도를 각각 재서 그 중간으로 `profiles.py`를 고칠 것. `python hwtest.py --sensor`
3. **`RAIN_HUMIDITY_THRESHOLD` 현장 튜닝** — 실제 습도 값을 보고 "비" 오탐이 안 나도록 `controller.py`에서 조정.
4. 딥러닝 분류기(`lettuce`/`corn`/`carrot`/`background`)는 학습 완료됨. 조명·배치가 바뀌면 `collect_data.py`로 재촬영 + `train_crop_model.py` 재학습.

## 하드웨어 배치

```
motors[VENT_MOTOR_A_INDEX]    = 환기창 모터A
motors[VENT_MOTOR_B_INDEX]    = 환기창 모터B (모터A와 함께 움직여야 열림/닫힘)
motors[SPRINKLER_MOTOR_INDEX] = 스프링클러 (모형. 실제로 물은 안 나온다)
```

2026-08-01 실측 인덱스: `VENT_MOTOR_A_INDEX=2`, `VENT_MOTOR_B_INDEX=0`, `SPRINKLER_MOTOR_INDEX=1` (장비마다 다를 수 있으니 `python hwtest.py --motor`로 매번 재확인할 것).

환기창은 절대각이 아니라 **상대회전**(`append_angle`)으로 움직인다 - 열기=`+VENT_A_SIGN*VENT_ROTATION_DEG`, 닫기=그 반대. 현재 확정값: `VENT_A_SIGN=-1`, `VENT_B_SIGN=1`, `VENT_ROTATION_DEG=120`. 부호가 실물과 안 맞으면 `main.py` 실행 시 자동으로 뜨는 확인 절차에서 바로 고칠 수 있다(`hwtest.py --motor`에도 같은 보정 도구 있음). 열기/닫기가 항상 쌍으로 맞아야 하므로 `controller.py`가 "닫혀있을 때만 열기/열려있을 때만 닫기"로 막아둔다 - 두 번 연속 열면 위치가 어긋난다.

환기창 두 모터 중 하나라도 없으면 연결 자체가 실패한다(`HardwareError`). 스프링클러 모터만 없으면 경고만 뜨고 나머지는 정상 동작한다.
