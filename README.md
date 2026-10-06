<div align="center">

# 농깨비 🌱

### 작물의 말을 전합니다

**고령 농업인을 위한, 아무것도 묻지 않는 스마트팜**

2026 SW미래채움 AI·SW 고교 챌린지 2단계 해커톤 출품작
광주소프트웨어마이스터고 · 3인 팀 · 2박 3일

`Python` `MODI Plus` `PyTorch` `Flask` `Flutter` `OpenCV`

</div>

---

## 왜 만들었나

시중 스마트팜은 자동화는 합니다. 그런데 **판단은 사람에게 떠넘깁니다.**

앱을 켜면 이렇게 묻습니다. 재배 작물이 무엇입니까. 목표 온도는 몇 도입니까. 관수 주기는 며칠입니까.

농촌 인구의 절반이 65세 이상입니다. 평생 밭을 일궈온 분들에게 **"상추의 적정 온도를 숫자로 입력하라"**는 요구는, 기술이 아니라 장벽입니다.

농깨비는 묻지 않습니다.

> **같은 장치가 상추 앞에서는 20도에서 창문을 열고, 옥수수 앞에서는 28도까지 기다립니다.**
> **어르신은 아무것도 설정하지 않았습니다.**

---

## 어떻게 동작하나

```
        웹캠                    Python 판단 계층                MODI Plus
   ┌───────────┐          ┌─────────────────────┐        ┌──────────────┐
   │ 작물 인식  │ ──────▶ │  작물 프로파일 조회   │ ─────▶ │ 환기창 (모터×2) │
   │ (딥러닝)   │          │  센서값 + 기준 비교   │        │ 스프링클러      │
   └───────────┘          │  조치 결정            │        │ 생장등 (LED)   │
                          └──────────┬──────────┘        │ 디스플레이       │
   ┌───────────┐                     │                   │ 스피커          │
   │ Env 센서   │ ──────────────────▶ │                   └──────────────┘
   │ 온·습도·조도│                     │
   └───────────┘                     ▼
                             ┌──────────────┐         ┌──────────────┐
                             │  Flask API   │ ◀─────▶ │ Flutter 앱    │
                             └──────────────┘         └──────────────┘
```

카메라가 작물을 알아보면 `profiles.py`의 재배 기준이 자동으로 적용됩니다.
사용자가 입력하는 설정값은 **0개**입니다.

```python
CROP_PROFILES = {
    "lettuce": {"name": "상추",   "vent_temp": 20, "dry_limit": 55},
    "corn":    {"name": "옥수수", "vent_temp": 28, "dry_limit": 70},
    "carrot":  {"name": "당근",   "vent_temp": 20, "dry_limit": 45},
}
```

작물이 바뀌면 장치의 행동이 바뀝니다. 사람이 하는 일은 없습니다.

---

## 기능

| | 기능 | 설명 |
|---|---|---|
| 🔍 | **작물 자동 인식** | 전이학습 분류기가 상추·옥수수·당근을 구분하고 재배 프로파일을 자동 적용 |
| 🪟 | **환기창 자동 제어** | 작물별 기준 온도를 넘으면 개방. 습도가 급등하면(비) 자동으로 닫음 |
| 💧 | **급수 판단** | 건조 신호를 감지하면 스프링클러 작동 |
| 💡 | **생장등** | 주변이 어두우면 점등. 자기 밝기를 보정해 발진하지 않음 |
| 🗣️ | **어르신 인터페이스** | 96×96 화면에 짧은 단어 2줄 + 음성 안내. 수치 대신 상태어 |
| 🌡️ | **온열질환 경고** | 34도 이상이면 3분간 경고음. 작물이 아니라 **사람**을 위한 기준 |
| 📱 | **모바일 앱** | 조회와 수동 조작. 설정 항목은 없음 |

**설정은 묻지 않지만, 조작은 언제든 가능합니다.** 자동화는 기본값이지 강제가 아닙니다.

---

## 기술적으로 해결한 문제들

### 생장등이 스스로를 껐다 켰다 하는 문제

생장등을 켜면 조도 센서가 밝아졌다고 읽고 → 밝으니까 껐다가 → 다시 어두워지니 켜는, 무한 반복이 발생했습니다.

히스테리시스와 최소 유지 시간을 넣어도 8초 주기로 계속 깜빡였습니다. 증상만 누른 것이었습니다.

문제는 **질문 자체가 틀렸다**는 것이었습니다. 알아야 할 것은 "지금 밝은가"가 아니라 **"주변이 어두운가"**였습니다.

```python
def ambient_lux(self, lux):
    """생장등이 스스로 만든 밝기를 뺀 '주변 밝기' 추정값."""
    if self._light_on:
        return max(0.0, lux - self._light_boost)   # _light_boost는 자동 학습
    return lux
```

생장등이 만드는 밝기를 켤 때마다 스스로 학습해서 빼도록 하자 발진이 사라졌습니다.

### 모터가 반대로 도는 문제

환기창 모터가 자꾸 반대 방향으로 돌았습니다. 부호를 두 번 뒤집어봤지만 계속 재발했습니다.

`pymodi_plus`의 소스를 직접 열어보고 원인을 찾았습니다. `motor.angle`은 "정면 기준 각도"가 아니라 **엔코더 절대각(0~360)**이었고, 닫힘 기준이 0/360 경계 근처일 때 `% 360` 계산이 최단 경로가 아니라 **반대로 훨씬 많이 도는 경로**를 만들고 있었습니다.

부호 문제가 아니라 좌표계 문제였습니다. 절대각을 버리고 **상대회전**(`append_angle`)으로 바꾸자 wraparound 자체가 구조적으로 사라졌습니다.

### 하드웨어가 1대인데 개발자는 3명인 문제

`hardware.py`가 `modi_plus`를 감싸고, 그 밖에서는 하드웨어를 모릅니다. `MockHardware`가 같은 인터페이스를 구현해서 **MODI 키트 없이도 전체 시스템이 돌아갑니다.**

```bash
python main.py --mock     # 하드웨어 없이 로직 전체 실행
```

덕분에 3명이 하드웨어 순서를 기다리지 않고 동시에 개발했습니다.

---

## 한계 (숨기지 않습니다)

- **건조도는 절대 수분 함량이 아닙니다.** 상대 지표이며, 현재는 흙이 아니라 **공기 중 습도**를 뒤집어 씁니다. "습도가 낮으면 흙도 마르고 있을 것"이라는 대리 가정 위에 있습니다.
- **"비가 옵니다"는 기상 정보가 아닙니다.** Env 습도가 임계값을 넘었다는 뜻이며, 그냥 습한 날에도 오인할 수 있습니다. 인터넷 없이 동작하기 위한 선택입니다.
- **스프링클러는 모형입니다.** 실제로 물은 나오지 않습니다. 실제 제품에서는 이 자리에 밸브가 연결됩니다.
- **성장 단계는 실측이 아닙니다.** 카메라로 크기를 재는 게 아니라, 처음 인식한 날로부터 경과한 일수와 평균 재배 기간으로 추정합니다.
- 대회 규정상 실제 작물을 반입할 수 없어 **레고 브릭**으로 대체했습니다.

---

## 빠른 시작

```bash
pip install pymodi-plus flask opencv-python torch torchvision

python main.py --mock       # 하드웨어·웹캠 없이 (개발용)
python main.py --mock-hw    # MODI만 없이, 웹캠은 실물
python main.py              # 실물 전체
```

실행하면 `http://<노트북IP>:5000` 에서 웹 인터페이스가 열립니다.

실물 하드웨어를 붙일 때는 **`main.py`보다 먼저** 모듈 점검을 돌리세요.

```bash
python hwtest.py            # 모듈 하나씩 확인
python hwtest.py --motor    # 환기창 방향·각도 대화형 보정
```

---

## 프로젝트 구조

```
├── profiles.py          작물별 재배 기준 ← 프로젝트의 정체성
├── vision.py            작물 분류 (딥러닝 + HSV 폴백)
├── controller.py        판단 로직 + 논블로킹 액추에이터 제어
├── hardware.py          MODI Plus 추상화 + Mock 구현
├── state.py             상태 저장소 + 명령 큐 (스레드 간 유일한 접점)
├── server.py            Flask API
├── main.py              메인 루프
├── hwtest.py            실물 모듈 점검 도구
├── web/                 부스용 웹 UI (Vite+React). npm run build → web/dist 를 서버가 서빙
├── testapp.html         예전 웹 인터페이스 (/legacy)
├── start_booth.bat      부스 시작 스크립트 (자동 재시작 + 전체화면)
├── BOOTH.md             부스 운영 가이드 (연결·점검·체크리스트·문제 해결)
├── app/                 Flutter 모바일 앱
└── crop_model.py        딥러닝 파이프라인
    train_crop_model.py
    collect_data.py
```

### 아키텍처 원칙

**하드웨어는 메인 스레드가 독점합니다.** Flask 스레드는 상태를 읽고 명령을 큐에 넣을 뿐, 하드웨어를 직접 만지지 않습니다. 두 스레드에서 동시에 접근하면 시리얼 통신이 깨집니다.

**`time.sleep()`으로 모터를 기다리지 않습니다.** 타임스탬프 기반 상태머신이라 모터가 도는 2.5초 동안에도 센서를 읽고 API가 응답합니다.

---

## 팀

| 담당 | 범위 |
|---|---|
| 남진 | HW-SW 연결 로직, MODI 제어, 비전, 서버 |
| 팀원 A | Flutter 모바일 앱 |
| 팀원 B | 레고 하드웨어 프로토타입 |

---

<div align="center">

**농깨비** · 2026 SW미래채움 AI·SW 고교 챌린지

</div>

---

<details>
<summary><b>개발자용 상세 문서</b> (클릭해서 펼치기)</summary>

## 모듈별 역할

| 모듈 | 역할 |
|---|---|
| Network ×2 | USB 연결. 한 USB에 체인으로 연결 |
| Env | 온도 → 환기 판단 / 조도 → 생장등 판단 / 습도 → 건조도·비 감지 |
| LED | 생장등 (흰색). 상태색 표시는 하지 않음 |
| Display | 2줄 짧은 단어 |
| Speaker | alert 진입 순간 0.4초 삑 + 34도 이상 온열질환 경고 |
| Motor A / B | 환기창 (둘이 함께 움직여야 열림/닫힘) |
| Motor (스프링클러) | 스프링클러 모형 |

미사용: ToF, IMU, Joystick, Dial, Button (수동 조작은 앱 전용)

## 하드웨어 배치

```
motors[VENT_MOTOR_A_INDEX]    = 환기창 모터A
motors[VENT_MOTOR_B_INDEX]    = 환기창 모터B
motors[SPRINKLER_MOTOR_INDEX] = 스프링클러
```

2026-08-01 실측: `VENT_MOTOR_A_INDEX=2`, `VENT_MOTOR_B_INDEX=0`, `SPRINKLER_MOTOR_INDEX=1`
장비마다 다르므로 `python hwtest.py --motor`로 매번 재확인할 것.

환기창은 절대각이 아니라 **상대회전**(`append_angle`)으로 움직인다. 열기=`+VENT_A_SIGN*VENT_ROTATION_DEG`, 닫기=그 반대.
현재 확정값: `VENT_A_SIGN=-1`, `VENT_B_SIGN=1`, `VENT_ROTATION_DEG=120`.
열기/닫기가 항상 쌍으로 맞아야 하므로 `controller.py`가 "닫혀있을 때만 열기 / 열려있을 때만 닫기"로 막아둔다.

환기창 두 모터 중 하나라도 없으면 연결 자체가 실패한다(`HardwareError`). 스프링클러만 없으면 경고 후 계속 진행한다.

## 카메라가 여러 대일 때

```bash
pip install pygrabber
python -c "from pygrabber.dshow_graph import FilterGraph; [print(i, n) for i, n in enumerate(FilterGraph().get_input_devices())]"
```

확인한 인덱스를 `--cam`에 넘긴다. 예: `python main.py --mock-hw --cam 1`

## 출력 규칙

Display는 96×96이라 긴 문장을 쓸 수 없다. 2줄 고정.

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

## 생장등 발진 방지 (건드릴 때 주의)

1. 히스테리시스 — 켜는 기준(`min_lux`)과 끄는 기준(`min_lux + 3`)을 다르게
2. 최소 유지 시간 8초
3. **자기 밝기 보정** — 생장등이 만든 밝기를 자동 학습해서 빼고 판단 ← 근본 해결. 지우지 말 것

> Env 모듈에 생장등 빛이 정면으로 닿으면 보정 오차가 커진다. 사이를 레고로 가릴 것.

## 촬영 방식

ToF를 쓰지 않으므로 6초마다 자동 촬영한다(`SCAN_INTERVAL`). 즉시 촬영하려면 앱에서 `scan` 명령.

## 환기창 자동 닫기

기본은 자동으로 열기만 한다. 닫는 것은 사람이 앱으로 한다.
예외적으로 Env 습도가 `RAIN_HUMIDITY_THRESHOLD`를 넘으면("비") 자동으로 닫는다.

## API

기본 주소 `http://<노트북IP>:5000`

### GET /api/state

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

`message`와 `level`만 크게 보여주면 된다. `level`은 `good`(초록) / `warn`(노랑) / `alert`(빨강).

`growth_stage` / `days_growing` / `harvest_date`는 실측이 아니라 **처음 인식한 시각 + `profiles.py`의 `grow_days`**로 추정한 값이다. 작물이 바뀌면 카운트가 새로 시작된다. 인식 전이면 셋 다 `null`.

### POST /api/command

```json
{ "command": "water" }
```

가능한 값: `vent_open` `vent_close` `vent_toggle` `water` `scan` `light_toggle` `auto_on` `auto_off` `vent_mark_open` `vent_mark_closed`

- `auto_on` / `auto_off`: 자동 조치 켜기/끄기
- `vent_mark_open` / `vent_mark_closed`: **모터를 돌리지 않고** "창문이 지금 실제로 열려/닫혀 있다"고 알려준다 (재조립·재시작 뒤 어긋난 상태를 바로잡을 때)
- `scan` `light_toggle` `auto_*` `vent_mark_*`는 모터가 도는 중에도 받는다
- 성공 `200` → `{"ok": true, "queued": "water"}`
- 동작 중 `409` → 에러가 아니라 안내 문구로 보여줄 것
- 잘못된 명령 `400`

`/api/state`에는 부스 웹 UI용 필드도 있다: `crop_key` `crop_probs`(작물별 확률) `reason`(판단 근거 한 줄) `display_text`(Display에 나가는 두 줄) `auto_mode` `vent_assumed`(창문 상태가 사람이 확인 안 된 추정값) `hw_error`(장치 통신 오류, 정상이면 null) `server_time` `thresholds`(현재 작물의 기준값).

### GET /api/profiles

모든 작물의 기준값 `{"items": [{"key", "name", "note", "thresholds": {...}}]}`.

### GET /api/info

`{"lan_url": "http://192.168.1.3:5000"}` — 폰 접속용 주소(QR에 쓴다). 못 찾으면 `null`.

### GET /api/history?limit=50

```json
{ "items": [ { "at": 1785508793.3, "event": "water", "detail": "물을 주었습니다" } ] }
```

최신순. `detail`이 그대로 보여줄 수 있는 문장이다.

### GET /api/growth_photos

```json
{ "items": [ { "week": 0, "crop_name": "상추", "taken_at": 1785508793.3,
               "url": "/growth_photos/lettuce_week0_1785508793.jpg" } ] }
```

지금 인식 중인 작물의 것만 준다. `url`은 상대 경로이므로 앱에서 `baseUrl + url`로 이어붙인다.

## 캘리브레이션

```bash
python main.py --calib wet     # 젖은 흙 기준
python main.py --calib dry     # 마른 흙 기준
```

## 남은 작업

1. **환기창 모터 방향/각도 보정** — `python hwtest.py --motor`로 대화형 조정 후 `hardware.py`에 반영
2. **`min_lux` 현장 튜닝** — 생장등 켰을 때/껐을 때 조도를 재서 중간값으로 (`python hwtest.py --sensor`)
3. **`RAIN_HUMIDITY_THRESHOLD` 현장 튜닝** — "비" 오탐 방지
4. 조명·배치가 바뀌면 `collect_data.py` 재촬영 + `train_crop_model.py` 재학습

## pymodi-plus 함정

- **Speaker에는 `.turn_off()`가 없다.** 끌 때는 `speaker.reset()` (공식 예제에 오타 있음)
- 모듈 접근은 `bundle.envs[0]`. n번째는 `[n-1]`
- 센서 첫 값은 0이다. 연결 후 `time.sleep(1)` 필수
- `motor.angle`은 엔코더 절대각이지 "정면 기준 각도"가 아니다
- `set_angle()`은 0~360 밖 값을 **에러 없이 조용히 무시한다**
- 모듈이 많고 모터가 여러 개면 USB 전원만으로 부족할 수 있다 (배터리 모듈 권장)
- `python -m modi_plus --inspect`는 대화형이다. 모듈 개수를 입력해야 한다

</details>
