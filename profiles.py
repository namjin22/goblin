# -*- coding: utf-8 -*-
"""작물별 재배 기준 프로파일.

농깨비의 정체성이 담긴 파일이다.
사용자는 아무것도 설정하지 않는다. 카메라가 작물을 인식하면
여기 정의된 기준이 자동으로 적용된다.

※ 대회장에서 실제 시연할 작물이 확정되면 이 딕셔너리만 고치면 된다.
"""

# 건조도 지수: 0(젖음) ~ 100(마름)
# vent_temp : 이 온도를 넘으면 환기 시작
# min_lux   : 이 조도 미만이면 생장등 점등
# dry_limit : 이 건조도를 넘으면 급수
#
# [현장 튜닝 필수 - min_lux]
# Env 모듈의 조도는 0~100 범위지만 실제로는 훨씬 낮게 나온다.
# 실내 형광등 아래에서 3~4 정도로 측정되었다.
# 따라서 min_lux를 40~60으로 두면 항상 "빛이 부족합니다"가 뜬다.
# 대회장에서 python hwtest.py --sensor 로 실제 값을 보고
# (밝을 때 값 + 어두울 때 값)의 중간쯤으로 다시 잡을 것.
# grow_days : 심은(=처음 인식한) 날로부터 수확까지 걸리는 대략적인 재배 일수.
#             실측이 아니라 일반적인 재배 기간 기준값이다. 웹캠으로 실제 크기를
#             재는 게 아니라 "인식된 이후 며칠째인지"로 성장 정도를 추정한다.
CROP_PROFILES = {
    "lettuce": {
        "name": "상추",
        "vent_temp": 20,
        "min_lux": 3,
        "dry_limit": 55,          # 건조에 취약 -> 낮은 임계값
        "note": "고온에서 웃자람",
        "grow_days": 30,
    },
    "corn": {
        "name": "옥수수",
        "vent_temp": 28,
        "min_lux": 6,
        "dry_limit": 70,          # 뿌리가 깊어 가뭄엔 비교적 강함
        "note": "고온성, 광량 많이 필요",
        "grow_days": 90,
    },
    "carrot": {
        "name": "당근",
        "vent_temp": 20,
        "min_lux": 4,
        "dry_limit": 45,          # 뿌리 비대기에 수분 불균일하면 갈라짐 -> 일찍 급수
        "note": "서늘한 걸 선호, 균일한 수분 필요",
        "grow_days": 75,
    },
}

# 작물을 아직 인식하지 못했을 때 쓰는 안전한 기본값.
# 어떤 작물에도 크게 해롭지 않은 중간값으로 잡는다.
DEFAULT_PROFILE = {
    "name": "확인 중",
    "vent_temp": 25,
    "min_lux": 4,
    "dry_limit": 65,
    "note": "작물 인식 전 기본값",
    "grow_days": 60,
}


def get_profile(crop_key):
    """작물 키로 프로파일을 가져온다. 모르는 작물이면 기본값."""
    return CROP_PROFILES.get(crop_key, DEFAULT_PROFILE)


def crop_names():
    """앱·디스플레이에 보여줄 작물 이름 목록."""
    return {k: v["name"] for k, v in CROP_PROFILES.items()}
