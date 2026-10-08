# 농깨비(Nongkkaebi) 포트폴리오 · 면접 정리

> 이 문서는 **저장소의 코드와 커밋 기록에서 확인되는 것만** 적었다. 모든 항목에 근거 파일 경로(가능하면 줄 번호)나 커밋 해시를 붙였다.
> 기준 시점: `HEAD = caf394d` (2026-10-08). 줄 번호는 이 시점 기준이라 이후 수정되면 어긋날 수 있다. 커밋은 `git show <해시>`로 확인한다.
> 저장소에서 확인되지 않는 것은 본문에 단정하지 않고 **[미확인]** 으로 표시했다.

---

## 0. 먼저 읽을 것 (면접 전에 바로잡아야 하는 것)

| # | 내용 | 근거 |
|---|---|---|
| 1 | **(해결됨) 예선 프로젝트 폴더가 커밋에 섞였던 사고.** `8f16fbe`("공개용 README 재작성")에 `예선 프젝/`(3,100개 파일, 89.1MB: 의류 데이터셋 이미지, `outfit_model.pth`, 별도 git 저장소 링크)가 들어갔다. 푸시 전에 발견해서 **원격에 올라가지 않은 3개 커밋만 다시 써서 그 폴더를 제거**했다 (코드는 백업과 동일함을 확인). 로컬 백업 브랜치 `backup/before-cleanup`에는 예전 커밋이 남아 있으니 **푸시 전에 삭제할 것**. 재발 방지로 `.gitignore`에 `*예선*` 추가. 문서 아래의 해시(`8f16fbe`, `fa447a3`, `caf394d`)는 정리 전 값이며 정리 후에는 각각 `dc7c60c`, `a91caa7`, `753b39a`다. | `git log origin/feature/booth-web-ui..HEAD`, `.gitignore` |
| 2 | **AI(Claude Code)와 협업한 저장소다.** 74개 커밋 중 **37개**에 `Co-Authored-By: Claude` 표기가 있고, 두 번째 커밋 제목이 "claude code로 변경"(`e87e3ec`)이다. 면접에서 "어디까지 내가 설계/판단했고 어디를 AI가 구현했나"를 구분해서 말할 수 있어야 한다. | `git log --all --grep="Co-Authored-By: Claude"` |
| 3 | **"수상(창의상)"은 저장소에서 확인되지 않는다.** README에도 수상 언급이 없다. 포트폴리오에 적을 때는 별도 증빙(상장 등)이 필요하다. | **[미확인]** |
| 4 | README의 "농촌 인구의 절반이 65세 이상"은 **출처가 저장소에 없다.** 면접에서 근거를 물으면 답할 수 있게 출처를 찾아 두거나 문구를 바꿀 것. | `README.md:24` |
| 5 | **자동 테스트 코드가 저장소에 없다.** 있는 것은 사람이 `y/n`을 눌러야 하는 실물 점검 스크립트(`hwtest.py`)와 Flutter 기본 위젯 테스트 1개(`app/test/widget_test.dart`, 2개 케이스)뿐이다. 개발 중 돌린 자동 테스트들은 저장소 밖 임시 폴더에 있었고 커밋되지 않았다. | `git ls-files \| grep -i test`, `hwtest.py:37` |
| 6 | 커밋 메시지와 내용이 다른 커밋이 있다: `8f16fbe`는 README라고 했지만 `controller.py`·`hardware.py`·`server.py`·`state.py`·`StatusBanner.jsx`(모터 움직임 확인, 시작 대기)가 같이 들어 있다. `fa447a3`("부스 운영용 개발")은 `web/dist` 재빌드뿐이다. | `git show --stat 8f16fbe fa447a3` |

---

## 1. 규모

### 1-1. 커밋

| 항목 | 값 | 근거 |
|---|---|---|
| 커밋 수 | **74개** (현재 브랜치 `feature/booth-web-ui`) · `main` 62개 · 원격 반영분 71개 | `git rev-list --count HEAD / main` |
| 작성자 | 남진 **52**, chaeeun09 **22** (Flutter 앱 `app/`) | `git shortlog -sne --all` |
| 기간 | 2026-08-01 ~ 2026-08-02(해커톤, 62개) · 2026-10-06 ~ 10-08(전시 준비, 12개) · 그 사이 공백 | `git log --format='%h %ad %s' --date=short` |
| AI 공동 작성 표기 | 37개 커밋 | 위 0-2 |

> 기간은 커밋 날짜 기준이다. 8/2 마지막 커밋(`0003a6d` "촬영 준비")과 10/6 첫 전시 준비 커밋(`e6cea24`) 사이에 2개월 공백이 있다. 수상 시점은 저장소에 없다 **[미확인]**.

### 1-2. 코드 줄 수 (HEAD 추적 파일, `wc -l`, 빌드 산출물·락파일·학습 데이터 제외)

| 영역 | 파일 수 | 줄 수 | 비고 |
|---|---:|---:|---|
| Python (루트) | 14 | **4,234** | `controller.py` 976, `hardware.py` 649, `vision.py` 419, `server.py` 366, `hwtest.py` 343, `training.py` 296, `main.py` 260, `train_crop_model.py` 226, `state.py` 219, `collect_data.py` 153, `baseline.py` 97, `audio.py` 90, `profiles.py` 71, `crop_model.py` 69 |
| 웹 UI `web/src` (jsx/js/css) | 26 | **2,634** | React + Vite + Tailwind + framer-motion |
| Flutter 앱 `app/lib` (dart) | 23 | **1,681** | chaeeun09 담당 |
| 문서 (md) | 3 | 738 | `README.md` 376, `BOOTH.md` 134, `CLAUDE.md` 228 |
| 기타 | | | `testapp.html`(예전 참고 웹), `start_booth.bat`, `stop_booth.bat` |

학습 데이터(커밋됨): `data/lettuce` 75장, `data/carrot` 55장, `data/background` 55장, `data/corn` 35장. 학습된 모델 `models/crop_classifier.pt`.

### 1-3. 파일 구조

```
goblin/
├─ main.py            메인 루프 (하드웨어 독점 스레드) + CLI 옵션
├─ controller.py      판단 로직 + 논블로킹 액추에이터 제어 (가장 큼, 976줄)
├─ hardware.py        MODI 추상화(BaseHardware) + 실물(ModiHardware) + 가짜(MockHardware)
├─ state.py           두 스레드의 유일한 접점: 상태 저장소 + 명령 큐
├─ server.py          Flask API (하드웨어 접근 금지)
├─ vision.py          작물 분류(딥러닝 + HSV 폴백) + 웹캠 재연결 + Mock
├─ profiles.py        작물별 재배 기준 (프로젝트의 정체성)
├─ baseline.py        부스 "기본 환경" 기준 (건조도/조도를 장소에 맞춤)
├─ training.py        웹에서 촬영/학습(별도 프로세스)
├─ crop_model.py · train_crop_model.py · collect_data.py   분류 모델 파이프라인
├─ audio.py           노트북 스피커 출력(별도 스레드)
├─ hwtest.py          실물 점검(대화형)
├─ web/               부스용 웹 UI (src/, dist/ 커밋됨)
├─ app/               Flutter 모바일 앱 (팀원 담당)
├─ testapp.html       예전 참고 웹
├─ README.md · BOOTH.md · CLAUDE.md · start_booth.bat · stop_booth.bat
└─ data/ · models/    학습 데이터 / 모델
```

---

## 2. 웹·하드웨어 연동에서 기술적으로 까다로웠던 3가지

### 2-1. 환기창 모터가 "반대로 돈다" — 절대각 방식의 구조적 결함

- **증상**: 환기창 모터 A가 계속 반대로 돌았다. 부호를 고쳐도, 보정(calibrate) 타이밍을 고쳐도 재발했다. (`94e128e`, `bca61e2`, `edfda41` 커밋 본문)
- **원인**: `motor.angle`/`set_angle()`은 엔코더 **절대각(0~360)** 이고, 범위를 벗어난 목표각은 **에러 없이 조용히 무시**된다. 닫힘 기준각이 0/360 경계 근처일 때 `(home + sign*delta) % 360`이 최단 경로가 아니라 **반대로 훨씬 많이 도는 경로**를 만들었다. "부호 문제"로 오해해서 부호 결론이 두 번 번복됐다 (`94e128e`: "같은 부호", 이후 `bca61e2`·`edfda41`에서 재수정). 원인은 pymodi-plus 소스(`motor.py`)를 직접 읽고서야 확인했다고 `bca61e2` 본문에 적혀 있다.
- **해결**: 절대각을 버리고 **상대회전 `append_angle(delta, speed)`** 로 교체. 열기=`+부호×각도`, 닫기=정확히 반대로 되돌리기. 대신 열기/닫기가 항상 쌍으로 맞아야 해서 컨트롤러에 **상태 가드**("닫혀 있을 때만 열기 / 열려 있을 때만 닫기")를 넣었다. 그리고 위치를 읽을 수 없으니 마지막 상태를 파일에 기억하고(`vent_state.json`), 재시작 후에는 "추정"으로 표시해 사람이 확인하게 했다.
- **코드 위치**
  - `hardware.py:61`(설계 주석), `:366-372`(열기/닫기 `append_angle`), `:74`(`VENT_ROTATION_DEG = 120`)
  - `controller.py:335`(`open_vent` 상태 가드), `:351`(`close_vent`)
  - 상태 기억·확인: `controller.py`의 `_load_vent_state`/`_save_vent_state`(`e6cea24`에서 추가), `state.py`의 `vent_assumed`
- **커밋**: `eed0e09`(모터 1개→2개 구조), `94e128e`, `bca61e2`, `edfda41`(상대회전 전환), `e6cea24`(상태 기억)

### 2-2. 재조립·모듈 비동기 인식 때문에 모터 역할이 어긋난다 — "틀린 모터에 명령이 가는" 문제

- **증상**
  1. 레고를 다시 조립/배선하면 모터 순서가 바뀐다. 처음 실물 테스트에서도 순서가 예상(0/1/2)과 달랐다 (`94e128e`: 실측 `A=2, B=0, 스프링클러=1`).
  2. 모듈 인식이 비동기라, 서버 시작 직후 모터가 일부만 잡히는 일이 있었다 (`controller.py`/`hardware.py`의 `refresh` 주석: "3번째 모터가 `초기화 완료` 뒤에 잡혔다").
- **원인**: pymodi-plus는 모듈이 **인식된 순서**로 `bundle.motors` 리스트를 만든다. 순서(INDEX)로 역할을 정하면 케이블 재연결·인식 시점에 따라 엉뚱한 모터를 환기창으로 착각한다. 특히 스프링클러는 **연속 회전(`speed`) 명령**이라, 환기창 모터로 가면 문이 걸릴 수 있다.
- **해결**
  - 모터를 순서가 아니라 **모듈 고유 ID**로 지정하고(`hw_config.json`), 설정이 없으면 **어떤 모터도 믿지 않는다**(`legacy = False`).
  - 역할/방향을 바꾸면 사람이 "열었다 닫기"를 눈으로 보고 `vent_confirm`을 누르기 전까지 **환기창 자동·수동 동작을 잠근다**(`VENT_VERIFIED`, `vent_ready`). 이 잠금은 테스트 중 "역할을 저장하자마자 자동 모드가 방향 미확인 상태로 창문을 여는" 문제를 직접 발견해서 넣은 것이다.
  - 모터 개수가 바뀌면 2초마다 역할을 다시 계산(`refresh`), 시작할 때 설정된 모터가 다 잡힐 때까지 최대 12초 대기(`MODULE_WAIT`).
  - 명령 후 **엔코더 각도를 읽어 실제로 움직였는지 서버가 확인**하고, 안 움직였으면 화면에 알린다(`_verify_motion` → `motor_fault`).
  - 웹의 운영자 "장치 점검"에서 모터 시험 구동·역할 선택·방향 확인을 눈으로 하게 했다.
- **코드 위치**
  - `hardware.py:23`(`pick_motor`), `:79`(`VENT_VERIFIED`), `:85`(`CONFIG_PATH`), `:92`(`MODULE_WAIT`), `:122`(`apply_config`), `:384`(`vent_ready`), `:391`(`_resolve_roles`), `:427`(`refresh`)
  - `controller.py:252`(`_vent_expected`), `:259`(`_verify_motion`), `:796`(`handle_hw_check`), `:873`(`update_hw_refresh`)
  - 서버 인자 검증: `server.py:50`(`_validate_args`: 알려진 모터 ID만, 각도 1~30°)
  - 웹: `web/src/components/HardwareCheck.jsx`, `web/src/lib/preflight.js`
- **커밋**: `338beb8`(ID·역할·방향 확인 잠금·`_validate_args`), `70d15f2`(`refresh`), `8f16fbe`(`MODULE_WAIT`, `_verify_motion`: 메시지는 README지만 내용에 들어 있다)

### 2-3. 웹캠·실시간 화면이 대시보드를 멈추게 한다 — 스레드/연결 설계

- **증상**
  1. 폰에서 대시보드가 멈춘 것처럼 보였다 (서버 로그는 매초 응답). (`a8ee861`)
  2. 실시간 카메라 스트림을 붙이자 `/api/state` 폴링이 막혔다. (`ed54007`)
  3. 카메라 미리보기와 온습도 화면이 **동시에** 멈췄다. (`67d08d2`)
- **원인**
  1. `Cache-Control` 헤더가 없어 모바일 브라우저가 GET 응답을 캐싱했다.
  2. MJPEG 상시 연결 하나가 모바일 브라우저의 동시 연결 한도(보통 6개)를 점유했고, Flask 개발 서버는 상시 연결에 약하다.
  3. 웹캠 호출(`vision.capture()`)이 0.5초마다 메인 루프에서 블로킹으로 불렸다. 드라이버가 멈추면 같은 스레드의 센서 읽기·액추에이터 제어까지 멈춘다고 **"의심"** 했다 (`67d08d2` 본문이 "의심"이라고 쓴다 — 확정 원인은 아니다).
- **해결**
  - 응답에 `no-store` 헤더(`server.py:165`).
  - MJPEG 대신 **스냅샷 한 장씩 요청하는 폴링**(`/camera/snapshot.jpg`), 웹은 "끝나면 다음 예약" 방식으로 폴링해 요청이 쌓이지 않게 함(`web/src/lib/useGoblin.js:5, 30-52`).
  - **스레드 분리 규칙**: 하드웨어는 메인 스레드만, Flask는 상태 읽기·명령 큐 넣기만 (`state.py`가 유일한 접점, `state.py:50`의 Lock).
  - 시간 기반 상태머신으로 `sleep` 없이 모터를 기다림(`controller.py`의 `_busy_until`, 첫 커밋 `e1aaaeb`부터 존재).
  - 인식용 프레임을 미리보기로 재사용해 웹캠 추가 호출을 없앴고(`controller.py:483` `_publish_preview`), 학습 화면이 열려 있는 동안만 1.2초 주기로 갱신(`studio_ping`, `70d15f2`).
  - 학습은 **별도 프로세스**로 돌려 메인 루프를 막지 않음(`training.py:211` `subprocess.Popen`).
  - 웹 쪽 방어: 서버는 응답하는데 메인 루프가 멈춘 경우를 `server_time - updated_at`으로 감지해 배너 표시(`web/src/lib/useGoblin.js:90`, `web/src/components/StatusBanner.jsx`).
- **한계(솔직히)**: 3번의 원인은 끝내 **확정하지 못했다**. 지금 구조는 "자주 부르지 않는다 + 막혀도 화면이 알린다"로 위험을 줄인 것이다.
- **커밋**: `a8ee861`, `ed54007`, `67d08d2`, `e6cea24`(`server_time`·`hw_error`), `70d15f2`

### 2-4. (보충) MODI 하드웨어 때문에 겪은 문제 전체 목록

| # | 문제 | 원인 / 처리 | 근거 |
|---|---|---|---|
| 1 | 모터 인덱스가 예상과 다름 | 인식 순서 의존 → ID 지정으로 전환 | `94e128e`, `338beb8`, `hardware.py:23,391` |
| 2 | "A가 반대로 돈다" 반복 | 절대각 wraparound → 상대회전 | `edfda41`, `bca61e2` |
| 3 | `set_angle` 음수/범위 밖이 조용히 무시 | 라이브러리 동작 | `bca61e2`, `CLAUDE.md`(pymodi 함정) |
| 4 | 각도 250° 걸림 → 150° → 120° | 실측 조정 | `94e128e`, `bbc09d1`, `hardware.py:74` |
| 5 | 거울 대칭 장착으로 부호 오해 | 부호 결론이 두 번 번복 | `94e128e`, `bca61e2`, `f17dc43` |
| 6 | 점검 스크립트의 잔여 위치가 각도 테스트를 오염 | 테스트 순서 문제 | `3df6978`, `hwtest.py` |
| 7 | LED/Button "연결 안 됨" 표시 | LED는 스캔 문제였음. Button은 팀이 물리 버튼 제거를 결정 | `94e128e` |
| 8 | `Speaker.turn_off()` 없음(공식 예제 오타) | `reset()` 사용 → 이후 Speaker 자체를 제거하고 노트북 스피커로 | `CLAUDE.md`, `338beb8`, `audio.py` |
| 9 | 센서 첫 값이 0 | 연결 후 `time.sleep(1)` | `hardware.py:321`, `CLAUDE.md` |
| 10 | `connection_type`/`conn_type` 인자명 혼란, `--inspect`가 대화형 | USB는 인자 없이 `MODIPlus()` | `CLAUDE.md`(pymodi 함정) |
| 11 | 모듈 많고 모터 많으면 USB 전원 부족 가능 | **가설로만 기록됨**, 배터리 모듈 권장 | `CLAUDE.md:97` |
| 12 | 서버 시작 직후 모터 일부만 인식 / 늦게 인식 | `MODULE_WAIT`, `refresh` | `hardware.py:92,427`, `70d15f2`, `8f16fbe` |
| 13 | 환기창 실제 위치를 읽을 수 없음 | 상태 기억 + 사람 확인(`vent_assumed`, `vent_mark_*`) | `e6cea24`, `state.py` |
| 14 | 명령은 갔는데 모터가 안 움직임을 알 방법 없음 | 엔코더로 실제 회전 확인 | `controller.py:259`, `8f16fbe` |
| 15 | USB가 `WinError 6 핸들이 잘못되었습니다`로 안 열림 | **원인 미규명.** 문서에는 "프로그램을 강제로 끊은 뒤 흔하다"는 관찰만 있고 USB 재연결로 해소한다고 적혀 있다 | `BOOTH.md:110` |
| 16 | 생장등을 켜면 Env 조도가 올라가 켜짐/꺼짐이 무한 반복(발진) | 히스테리시스 + 최소 유지 시간 + **자기 밝기 자동 학습·보정** | `controller.py:110,183,398,426`, `e1aaaeb` |
| 17 | 웹캠: Windows 기본 백엔드(MSMF)는 느리고 프레임 실패 | DirectShow 사용 | `vision.py:59-60` |
| 18 | 웹캠을 못 열면 **조용히 가짜 화면(Mock)으로 대체**되어 실물 운영 중 가짜 브릭이 보임 | 열지 못해도 가짜로 바꾸지 않고, 연결 안 됨을 알리고 4초마다 자동 재연결 | `vision.py:82,97,164`, `caf394d` |
| 19 | 웹캠 호출이 메인 루프를 멈출 가능성 | 2-3 참고 (확정 못 함) | `67d08d2` |

---

## 3. 작물별 설정값을 분리한 구조

### 3-1. 한 곳에서 정의 — `profiles.py`

```python
# profiles.py:25-
CROP_PROFILES = {
    "lettuce": {"name": "상추", "vent_temp": 20, "min_lux": 3,
                "dry_limit": 55,          # 건조에 취약 -> 낮은 임계값
                "note": "고온에서 웃자람", "grow_days": 30},
    "corn":    {"name": "옥수수", "vent_temp": 28, "min_lux": 6,
                "dry_limit": 70,          # 뿌리가 깊어 가뭄엔 비교적 강함
                "note": "고온성, 광량 많이 필요", "grow_days": 90},
    "carrot":  {"name": "당근", "vent_temp": 20, "min_lux": 4,
                "dry_limit": 45,          # 뿌리 비대기에 수분 불균일하면 갈라짐 -> 일찍 급수
                "note": "서늘한 걸 선호, 균일한 수분 필요", "grow_days": 75},
}
DEFAULT_PROFILE = {"name": "확인 중", "vent_temp": 25, "min_lux": 4, "dry_limit": 65, ...}  # :54

def get_profile(crop_key):                       # :64
    return CROP_PROFILES.get(crop_key, DEFAULT_PROFILE)
```

시연 작물을 바꿀 때 **이 딕셔너리만 고치면 된다**는 것이 설계 의도다 (`profiles.py` 머리 주석). 실제로 작물 구성이 바뀐 이력이 커밋에 있다: 고추/토마토/배추 → 옥수수/당근(`d81280b`), 이후 상추/옥수수/당근(현재). `CLAUDE.md`에는 2026-10-07에 대파로 바꿨다가 같은 날 되돌렸다고 적혀 있으나, 이 대파 변경은 **커밋으로 남지 않았다**(되돌린 뒤 커밋됨).

### 3-2. 판단에서 읽는 곳 — `controller.py`

```python
# controller.py:589 decide(self, snap)  — 인식된 작물의 profile만 읽는다
profile = get_profile(snap.get("crop_key"))
vent_temp = profile["vent_temp"]

if temp > vent_temp + 3:   return ("alert", "너무 덥습니다. 창문을 열까요?", "더워요!", "vent_open", ...)
if temp > vent_temp:       return ("warn",  "조금 덥습니다", "조금 더움", "vent_open", ...)
if humidity > RAIN_HUMIDITY_THRESHOLD: return ("warn", "비가 오는 것 같아요...", "비 옴", "vent_close", ...)
if dry > profile["dry_limit"]:         return ("alert", "흙이 말랐어요. 물을 줄까요?", "물 필요", "water", ...)
```

- 작물이 바뀌면(`update_scan`, `controller.py:496`) `crop_key`가 바뀌고, 다음 틱부터 **같은 코드가 다른 숫자**로 동작한다. 사용자가 입력하는 설정은 없다.
- 모델이 `profiles.py`에 없는 클래스를 내면 이전 작물을 붙들지 않고 "작물 없음"으로 처리한다 (`controller.py:534`).

### 3-3. 장소에 따라 달라지는 값은 따로 — `baseline.py`

온도 기준(`vent_temp`)은 **일부러 고정**한다("상추는 20도에서 열고 옥수수는 28도까지 기다린다"가 핵심 대비라서). 반면 조도·습도는 장소마다 절대값이 달라서 부스의 "기본 환경"을 저장해 그 값에 맞춘다.

```python
# baseline.py
LIGHT_FACTORS = {"lettuce": 0.35, "carrot": 0.45, "corn": 0.60}   # 평상시 조도의 몇 %보다 어두우면 켜는가
DRY_BASE = 40.0                                                   # 평상시 습도가 가리키는 건조도

def dryness(humidity, baseline=None):
    if baseline: value = DRY_BASE + (baseline["humidity"] - humidity)   # 1%p 내려갈 때마다 +1
    else:        value = 100.0 - humidity                               # 예전 방식
    ...
def light_levels(crop_key, profile, baseline=None):
    if baseline and baseline["illuminance"] >= MIN_USEFUL_LUX:
        on = round(baseline["illuminance"] * LIGHT_FACTORS.get(crop_key, DEFAULT_LIGHT_FACTOR), 1)
        off = round(on + max(3.0, baseline["illuminance"] * 0.15), 1)
        return on, off
    return profile["min_lux"], profile["min_lux"] + 3.0                 # 기본 환경이 없으면 profiles.py 값
```

### 3-4. 서버 → 웹으로 같은 값을 내려준다

- `server.py:96` `_thresholds(profile, crop_key, baseline)`: 판단 로직과 **같은 상수·함수**로 기준값을 만들어 `/api/state`와 `/api/profiles`(`:315`)로 내려준다. 웹의 기준선 눈금자·"창문 20°부터" 칩은 이 값을 그대로 그린다 (`web/src/components/DecisionCard.jsx:21`).
- 기준값을 코드 두 곳에 복사하지 않아서, 숫자를 고치면 판단·화면이 같이 바뀐다.

### 3-5. 작물 인식 → 설정 연결

`vision.py`의 분류기(전이학습, 얼린 MobileNetV3-small + 선형 헤드: `crop_model.py:39,42`)가 `crop_key`를 내고, 웹 "AI 학습"(`training.py`)으로 사진을 다시 찍어 재학습하면 새 모델이 즉시 적용된다(`vision.reload_model`).

---

## 4. 수상 후 전시 준비에서 바꾼 것 (커밋 기록)

구분 기준: 해커톤 마지막 커밋 `0003a6d`(08-02) 이후 `e6cea24`(10-06)부터를 전시 준비로 봤다. 수상일은 저장소에 없다 **[미확인]**.

| 커밋 | 날짜 | 분류 | 무엇이 달라졌나 | 근거 |
|---|---|---|---|---|
| `e6cea24` | 10-06 | 백엔드(웹 추가 준비) | `/api/state` 확장(작물별 확률·판단 근거·Display 미러·기준값·`server_time`·`hw_error`·`vent_assumed`), `/api/profiles`, `/api/info`(폰 접속 주소), 명령 `auto_on/off`·`vent_mark_*`, 환기창 상태 파일 기억, mock 가짜 웹캠·`--mock-cycle` | `server.py`, `state.py`, `vision.py` |
| `e746e61` | 10-06 | **웹 추가** | `web/` 신규: 한 화면 대시보드(React/Vite/Tailwind/framer-motion), 작물 인식 확률 막대, 작물별 기준선 눈금자, 장치 상태 애니메이션, 조작 버튼, 기록, **운영자 서랍(창문 실제 상태 맞추기·시스템 상태)**, 폰 접속 QR, 한계 서랍, 연결 끊김/장치 오류 배너. 폰트·라이브러리 전부 번들(CDN 없음) | `web/src/App.jsx`, `components/OperatorDrawer.jsx`, `lib/useGoblin.js` |
| `627683f` | 10-06 | 문서/도구 | `BOOTH.md`(운영 가이드), `start_booth.bat`(자동 재시작) | `BOOTH.md`, `start_booth.bat` |
| `5225e19` | 10-06 | **UI/UX** | 개장 전 점검표 자동 판정(`preflight.js`), 노트북 폭(1280~1535px)에서 조작 버튼이 깨지던 레이아웃 수정 | `web/src/lib/preflight.js`, `App.jsx` |
| `338beb8` | 10-07 | **하드웨어 재구성 + 관리자 설정** | MODI **Speaker 제거 → 노트북 스피커**(`audio.py`), 모터를 **ID로 지정**(`hw_config.json`), 역할/방향 변경 뒤 **방향 확인 전 환기창 잠금**, 서버 인자 검증(`_validate_args`), 웹 **"장치 점검"**(소리·LED·화면·모터 시험 구동·역할 선택·방향 확인), `hwtest.py --probe` | `audio.py`, `hardware.py`, `controller.py`, `web/.../HardwareCheck.jsx` |
| `20ad538` | 10-07 | 문서/도구 | 점검 절차 문서, `stop_booth.bat`, `start_booth.bat` 분리 실행 지원 | `BOOTH.md`, `stop_booth.bat` |
| `70d15f2` | 10-07 | **하드웨어 재구성 + 웹 기능** | 웹 **AI 학습**(촬영→학습→즉시 적용, 학습은 별도 프로세스, 저장은 `os.replace`), 모터 구성이 바뀌면 역할 재계산(`refresh`), 모델이 모르는 클래스가 나올 때 이전 작물을 붙들던 버그 수정, 모의 실행은 `data_mock/` 분리 | `training.py`, `train_crop_model.py:212`, `controller.py:534` |
| `5d392cf` | 10-07 | **UI/UX 개선** | "큰 버튼·넓은 간격·꼭 필요한 글자만": 조작 버튼 3개를 크게(진행 상태는 버튼 안), 판단 카드의 설명 문장 제거, 점검표는 문제만 표시, 헤더는 아이콘 버튼, 서랍·모달 글자/버튼 확대. **AI 학습 화면**(`StudioDrawer`) 추가 | `web/src/components/ControlsCard.jsx`, `DecisionCard.jsx`, `Header.jsx`, `StudioDrawer.jsx` |
| `f07646e` | 10-07 | 문서 | AI 학습 절차, 모터 늦은 인식, UI 원칙 정리 | `CLAUDE.md`, `BOOTH.md` |
| `8f16fbe` | 10-08 | 하드웨어 + **저장소 사고** | (메시지: 공개용 README) 실제로는 모터 움직임 확인(`_verify_motion`)·시작 시 모터 대기(`MODULE_WAIT`) 코드가 들어 있고, **`예선 프젝` 3,100개 파일이 함께 커밋됨** (0번 참고) | `git show --stat 8f16fbe` |
| `fa447a3` | 10-08 | 빌드 | `web/dist` 재빌드뿐 | `web/dist` |
| `caf394d` | 10-08 | **하드웨어 + 관리자 설정** | **웹캠 자동 재연결**(못 열어도 가짜 화면 대신 "연결 안 됨" + 4초마다 재시도), **부스 기본 환경**(`baseline.py`: 평상시 습도/조도를 저장해 건조도·생장등 기준을 장소에 맞춤), 운영자 서랍에 "기본 환경" 섹션, 점검표에 카메라 항목, 학습 사진 160장 추가(상추 +60, 당근 +40, 배경 +40, 옥수수 +20) | `vision.py:82,97,164`, `baseline.py`, `web/.../OperatorDrawer.jsx` |

### 4-1. 질문별로 정리

- **UI/UX 개선**: `5225e19`(레이아웃), `5d392cf`(단순화·큰 버튼). 원칙은 `CLAUDE.md`의 설계 결정 표에 "웹 UI는 쉽고 간단하게"로 적혀 있다.
- **웹 추가**: `e746e61`(`web/` 전체), 그 전제인 `e6cea24`(API 확장).
- **하드웨어 재구성**: `338beb8`(스피커 제거·모터 ID·방향 확인), `70d15f2`(`refresh`), `8f16fbe`(대기·움직임 확인), `caf394d`(카메라 재연결·기본 환경).
- **관리자 설정 페이지**(웹의 "운영자" 서랍): 시작 `e746e61`(창문 상태 맞추기·시스템 상태) → `338beb8`(장치 점검 5단계) → `70d15f2`/`5d392cf`(AI 학습 화면) → `caf394d`(기본 환경 저장). 파일: `web/src/components/OperatorDrawer.jsx`, `HardwareCheck.jsx`, `StudioDrawer.jsx`.

---

## 5. 지금 남아 있는 한계와 안 된 것

**측정/판단의 한계 (README와 코드가 스스로 밝히는 것)** — `README.md:122` "한계 (숨기지 않습니다)", `web/src/components/LimitsDrawer.jsx`
- 건조도는 **흙의 수분이 아니라 공기 중 습도를 뒤집은 상대 지표**다 (`controller.py:123`, `baseline.py:75`). "습도가 낮으면 흙도 마르고 있을 것"이라는 대리 가정이다.
- "비가 온다"는 날씨 정보가 아니라 **습도가 85%를 넘었다**는 뜻이다 (`controller.py:140`). 습한 날도 비로 오인할 수 있다.
- 스프링클러는 **레고 모형**이라 물이 나오지 않는다. 작물은 규정상 **레고 브릭**이다.
- 작물별 기준값(20/28/20도, 55/70/45 등)은 일반적인 재배 특성에 대한 설명 주석이 달려 있지만, **출처(농업 기준)가 저장소에 없다 [미확인]**. 시연용 값이다.
- `HEAT_DANGER_TEMP = 29.0`은 **촬영용 임시값**이다 (원래 34도, `controller.py:83` 주석). 웹 점검표도 34도 미만이면 경고한다 (`preflight.js:6`).

**AI 모델의 한계**
- **검증 정확도 100%는 과대평가일 수 있다.** `train_crop_model.py`는 원본 사진을 먼저 약 10배로 증강한 뒤(`load_embeddings`) 그 전체를 무작위로 학습/검증에 나눈다(`stratified_split`). 즉 **같은 원본에서 나온 증강본이 학습과 검증에 함께 들어가** 데이터 누수가 있다. `6ff568c` 본문도 "원본 사진 기준 100%이고 실물에서 더 버티는지는 실측 필요"라고 적었다.
- 클래스당 사진이 적다 (상추 75 · 당근 55 · 배경 55 · **옥수수 35**장). 조명·브릭 배치가 바뀌면 불안정할 수 있다고 `CLAUDE.md`가 적고 있다.
- 사용자 평가(어르신이 실제로 쓸 수 있는가)나 실제 농가 검증 기록은 저장소에 **없다 [미확인]**.

**하드웨어/운영의 한계**
- 환기창은 **위치를 읽을 수 없어** 열림/닫힘을 "믿는" 구조다. 재조립·재시작 뒤에는 사람 확인이 필요하다 (`vent_assumed`).
- USB `WinError 6`은 **원인을 규명하지 못했다**. 문서는 "강제 종료 뒤 흔하다"는 관찰과 "USB 재연결"이라는 우회만 적고 있다 (`BOOTH.md:110`). `stop_booth.bat`은 지금도 프로세스를 **강제 종료**한다 (`stop_booth.bat:7` `Stop-Process -Force`). 안전 종료(graceful shutdown)는 **구현하지 않았다**.
- 웹캠이 메인 루프를 멈추는지는 **확정하지 못했다** (`67d08d2`).
- Windows 전용 요소가 있다 (`winsound`: `audio.py`, DirectShow: `vision.py:60`, `.bat`).
- **보안이 없다**: CORS `*`(`server.py:159`), 인증 없음, Flask 개발 서버(`server.py:354-361`). 같은 네트워크의 누구나 창문·물 주기를 조작할 수 있다 (`BOOTH.md`도 인정).
- 소리는 `winsound.Beep` 비프음이다. 음성(말) 안내는 없다 (`audio.py`).

**소프트웨어/저장소 품질**
- **자동 테스트가 저장소에 없다** (0번 5).
- Flutter 앱(`app/`)은 새 API(장치 점검·AI 학습·기본 환경 명령 등)를 쓰지 않는다. 새 기능은 **웹 UI에만** 있다. 앱 컴파일 검증은 Flutter SDK가 없어 못 했다고 `CLAUDE.md`(남은 작업 3)에 적혀 있다.
- 커밋 위생: `예선 프젝` 혼입, 메시지와 내용이 다른 커밋(`8f16fbe`, `caf394d` "마무리"), 학습 이미지·모델·`web/dist` 빌드 산출물이 저장소에 커밋됨.
- `CLAUDE.md`의 "남은 작업" 0번 항목은 10-07 오후 상태에서 멈춰 있어 이후 해결된 일과 맞지 않는다 (모터 3개 인식 등).

---

## 6. 면접 예상 질문 10개와 근거 위치

| # | 질문 | 이렇게 답할 수 있다 | 근거 |
|---|---|---|---|
| 1 | 하드웨어 제어를 왜 메인 스레드 하나로 몰았나? Flask가 직접 모터를 만지면 안 되나? | 시리얼 통신이 두 스레드에서 동시에 접근하면 깨진다. Flask는 상태를 읽고 명령을 큐에 넣기만 하고, 메인 루프가 꺼내 실행한다. `state.Store`(Lock)가 유일한 접점이다. 같은 명령 중복 큐잉도 막는다. | `state.py:46-50, 106, 122, 139`, `controller.py` 아키텍처 규칙(`CLAUDE.md`) |
| 2 | 모터를 기다리는 동안 `sleep`하면 왜 안 되나? 어떻게 했나? | sleep하면 그 시간 동안 센서도 못 읽고 API도 응답 못 한다. 끝나는 시각을 기록하고 매 틱 확인하는 시간 기반 상태머신이다. | `controller.py`의 `_busy_until`·`_start_action`, 첫 커밋 `e1aaaeb` |
| 3 | "모터가 반대로 돈다"의 진짜 원인은? 어떻게 찾았나? | 절대각 `% 360`이 0/360 경계에서 먼 길로 돌았다. 부호를 의심하며 두 번 틀렸고, pymodi 소스를 읽고서야 알았다. 상대회전(`append_angle`)으로 바꾸고 열기/닫기 쌍을 상태 가드로 보장했다. | `hardware.py:61, 366-372`, `controller.py:335, 351`, `edfda41`, `bca61e2` 본문 |
| 4 | 위치를 못 읽는 모터를 어떻게 안전하게 다루나? | 마지막 상태를 파일에 기억하되 "추정"으로 표시하고 사람이 눈으로 맞추게 한다. 역할/방향을 바꾸면 사람이 시험 구동을 보고 확인하기 전까지 환기창을 잠근다. 명령 뒤 엔코더로 실제 회전을 확인한다. | `vent_state.json`(`e6cea24`), `hardware.py:79,384`, `controller.py:259`, `web/.../HardwareCheck.jsx` |
| 5 | 모터 순서가 바뀌는 문제를 어떻게 해결했나? | 순서가 아니라 모듈 고유 ID로 지정하고, 설정이 없으면 아무 모터도 믿지 않는다. 늦게 인식되는 모터는 2초마다 다시 계산하고, 시작 때 최대 12초 기다린다. 장치 점검은 웹에서 눈으로 하게 했다. | `hardware.py:23, 92, 391, 427`, `338beb8`, `70d15f2` |
| 6 | 작물별 설정을 어떻게 분리했고, 새 작물은 어떻게 추가하나? | `profiles.py`의 딕셔너리 한 곳. 판단 코드는 `get_profile(crop_key)`만 읽는다. 새 작물은 항목 추가 + 사진 촬영 + 재학습(웹에서 가능). 서버가 같은 값을 웹에 내려줘서 숫자가 한 곳에만 있다. | `profiles.py:25-66`, `controller.py:589`, `server.py:96, 315`, `training.py` |
| 7 | 작물 분류 모델은 어떻게 만들었고 정확도는 믿을 만한가? | 얼린 MobileNetV3-small 위에 선형 헤드만 학습(임베딩 캐싱 → 데이터가 적어도 빠르고 과적합 완화). 검증 100%는 **증강본이 학습/검증에 섞여 과대평가**됐을 가능성이 있다고 스스로 인정할 수 있다. 개선: 원본 단위로 분할. | `crop_model.py:39-42`, `train_crop_model.py:70, 177`(분할 순서), `6ff568c` |
| 8 | 학습 중에도 장치가 계속 돌아가게 한 방법은? | 학습을 별도 프로세스로 실행하고 `[progress]` 출력 줄만 읽는다. 모델 저장은 임시 파일 후 `os.replace`로 바꿔치기해 도중에 꺼져도 기존 모델이 안 깨진다. | `training.py:167, 211`, `train_crop_model.py:212` |
| 9 | 실시간 영상을 왜 MJPEG/WebSocket이 아니라 폴링으로 했나? | MJPEG 상시 연결이 모바일 브라우저의 동시 연결 한도를 점유해 상태 폴링이 막혔다. 스냅샷 한 장 요청 방식으로 바꿨고, 웹 폴링은 "끝나면 다음 예약"으로 요청이 쌓이지 않게 했다. 대신 지연(수 초)과 낭비가 있다. | `ed54007`, `web/src/lib/useGoblin.js:5, 30-52`, `server.py` `/camera/snapshot.jpg` |
| 10 | 이 시스템의 가장 큰 한계/위험은? 다음에 뭘 고치겠나? | 건조도·비 감지가 습도 대리 지표다, 환기창 위치를 못 읽는다, USB `WinError 6` 원인 미규명·강제 종료, 인증 없음, 자동 테스트 부재. 다음: 안전 종료, 원본 단위 검증 분할, 테스트 코드 저장소 편입, 인증. | 본 문서 5번 |

### 보너스 질문

- **"AI가 얼마나 썼나?"** → 0번 2. 설계 결정(스레드 분리, 작물 구성, 정직성 원칙, 한계 공개)과 AI가 구현한 부분을 구분해서 답할 것.
- **"생장등이 켜졌다 꺼졌다 하는 문제는?"** → 켜면 Env 조도가 올라가는 되먹임. 히스테리시스 + 최소 유지 8초 + **자기 밝기 자동 학습·보정**으로 "지금 밝은가"가 아니라 "주변이 어두운가"를 판단. `controller.py:110, 398-439`, `CLAUDE.md`의 "생장등 발진 방지".
- **"테스트는 어떻게 했나?"** → 0번 5와 5번을 솔직히. `MockHardware`/`MockVision`으로 하드웨어 없이 전체 로직을 돌릴 수 있게 설계한 것은 사실이다 (`hardware.py:497`, `vision.py` `MockVision`, `main.py --mock`).

---

## 부록: 확인 명령

```bash
git rev-list --count HEAD                          # 커밋 수
git shortlog -sne --all                            # 작성자별
git log --all --grep="Co-Authored-By: Claude" --format=%h | wc -l
git log --reverse --format='%h %ad %s' --date=short
git log origin/feature/booth-web-ui..HEAD          # 아직 원격에 없는 커밋
git -c core.quotepath=false ls-files | grep -c 예선   # 혼입된 예선 폴더 파일 수
wc -l *.py                                         # 파이썬 줄 수
```
