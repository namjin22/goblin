# -*- coding: utf-8 -*-
"""부스의 "기본 환경"(평상시 온습도/조도) 기준.

판단 기준을 코드의 고정 숫자가 아니라 **그 장소의 평상시**에 맞춘다. 같은 조명/습도라도
장소마다 절대값이 달라서(실내 형광등 3~4 / 부스 조명 20대) 고정 숫자로는 현장마다 다시
튜닝해야 했다. 운영자가 "지금 환경을 기본으로"를 누르면 그 순간의 센서값을 저장해 둔다.

[건드리지 않는 것] 온도 기준(작물별 vent_temp)은 그대로다. "상추는 20도에서 창문을 열고
옥수수는 28도까지 기다린다"는 이 프로젝트의 핵심 대비라서, 기본 온도에 맞춰 옮기면 안 된다.
부스가 24도 안팎이면 상추/당근은 열고 옥수수는 기다리는 게 의도한 모습이다.

[정직성] 이 기준은 "평상시 대비 얼마나 변했나"일 뿐 절대 수분량이나 절대 밝기가 아니다.
"""

import json
import os
import statistics
import time

PATH = "env_baseline.json"

# 건조도 지표(0~100)에서 평상시 습도가 가리키는 값. 습도가 이보다 내려가면 건조도가 올라간다.
# 작물 기준(dry_limit: 당근 45 / 상추 55 / 옥수수 70)은 이 값에서 얼마나 마르면 물을 주느냐가 된다.
DRY_BASE = 40.0

# 평상시 조도의 몇 %보다 어두워지면 생장등을 켜는가 (작물이 빛을 얼마나 요구하는가)
LIGHT_FACTORS = {"lettuce": 0.35, "carrot": 0.45, "corn": 0.60}
DEFAULT_LIGHT_FACTOR = 0.45
MIN_USEFUL_LUX = 5.0          # 평상시 조도가 이보다 어두우면(밤에 저장 등) 조도 기준은 옛 값을 쓴다
LIGHT_HYSTERESIS_ABS = 3.0    # 끄는 기준 = 켜는 기준 + max(3, 평상시의 15%)
LIGHT_HYSTERESIS_REL = 0.15

CAPTURE_SECONDS = 5.0         # 저장할 때 센서값을 모으는 시간 (순간적인 튐을 피하려고 평균)


def load(path=PATH):
    """저장된 기본 환경 {temperature, humidity, illuminance, saved_at}. 없으면 None."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if all(isinstance(data.get(k), (int, float)) for k in ("temperature", "humidity", "illuminance")):
            return data
    except (OSError, ValueError):
        pass
    return None


def save(baseline, path=PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print("[BASELINE] 저장 실패(무시):", e)


def clear(path=PATH):
    try:
        os.remove(path)
    except OSError:
        pass


def from_samples(samples):
    """센서값 여러 개 -> 기본 환경. 중앙값을 써서 순간적인 튐에 흔들리지 않는다."""
    def med(key):
        return round(statistics.median(s[key] for s in samples), 1)
    return {
        "temperature": med("temperature"),
        "humidity": med("humidity"),
        "illuminance": med("illuminance"),
        "saved_at": time.time(),
    }


def dryness(humidity, baseline=None):
    """습도 -> 건조도 지표 0(젖음)~100(마름).

    기본 환경이 있으면 그 습도를 DRY_BASE(40)로 두고 1%p 내려갈 때마다 1씩 올린다.
    없으면 예전 방식(100 - 습도).
    """
    if humidity is None:
        return None
    if baseline:
        value = DRY_BASE + (baseline["humidity"] - humidity)
    else:
        value = 100.0 - humidity
    return round(max(0.0, min(100.0, value)), 1)


def light_levels(crop_key, profile, baseline=None):
    """(켜는 기준, 끄는 기준) 조도. 주변이 켜는 기준보다 어두우면 켜고, 끄는 기준보다 밝으면 끈다."""
    if baseline and baseline["illuminance"] >= MIN_USEFUL_LUX:
        factor = LIGHT_FACTORS.get(crop_key, DEFAULT_LIGHT_FACTOR)
        on = round(baseline["illuminance"] * factor, 1)
        off = round(on + max(LIGHT_HYSTERESIS_ABS, baseline["illuminance"] * LIGHT_HYSTERESIS_REL), 1)
        return on, off
    return profile["min_lux"], profile["min_lux"] + LIGHT_HYSTERESIS_ABS
