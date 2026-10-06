import { josa } from "./format";

// 개장 전 점검: BOOTH.md의 수동 체크리스트를 현재 상태로 자동 판정한다.
// level: ok(준비됨) / warn(확인 필요) / fail(문제)

const HEAT_DEFAULT = 34; // 사람 온열질환 경고의 원래 기준. controller.py의 HEAT_DANGER_TEMP 주석 참고
const STALE_AFTER_SEC = 8;

export function preflight(state, staleSec) {
  if (!state) return [];
  const items = [];

  if (state.hw_error) {
    items.push({ key: "hw", level: "fail", label: "장치 통신", detail: `문제가 있어요 (${state.hw_error})` });
  } else if (staleSec > STALE_AFTER_SEC) {
    items.push({ key: "hw", level: "fail", label: "장치 통신", detail: `${Math.round(staleSec)}초째 응답이 없어요` });
  } else {
    items.push({ key: "hw", level: "ok", label: "장치 통신", detail: "정상" });
  }

  items.push(
    state.mock
      ? { key: "mock", level: "warn", label: "실물 장치", detail: "모의 실행 중이에요 (가짜 장치)" }
      : { key: "mock", level: "ok", label: "실물 장치", detail: "연결돼 있어요" }
  );

  items.push(
    state.has_camera_frame
      ? { key: "cam", level: "ok", label: "카메라 화면", detail: "받는 중" }
      : { key: "cam", level: "warn", label: "카메라 화면", detail: "아직 못 받았어요" }
  );

  items.push(
    state.crop_key
      ? { key: "crop", level: "ok", label: "작물 인식", detail: `${josa(state.crop_name, "을", "를")} 알아봤어요` }
      : { key: "crop", level: "warn", label: "작물 인식", detail: "인식된 작물이 없어요. 브릭을 올려 보세요" }
  );

  items.push(
    state.vent_assumed
      ? { key: "vent", level: "warn", label: "환기창 상태", detail: "실제 창문과 맞는지 확인이 필요해요" }
      : { key: "vent", level: "ok", label: "환기창 상태", detail: "확인됨" }
  );

  const heat = state.thresholds.heat_danger_temp;
  items.push(
    heat < HEAT_DEFAULT
      ? {
          key: "heat",
          level: "warn",
          label: "온열질환 경고 기준",
          detail: `${heat}°C로 낮아요. 촬영용 임시값이면 ${HEAT_DEFAULT}°C로 되돌리세요`,
        }
      : { key: "heat", level: "ok", label: "온열질환 경고 기준", detail: `${heat}°C` }
  );

  items.push(
    state.auto_mode
      ? { key: "auto", level: "ok", label: "자동 조치", detail: "켜져 있어요" }
      : { key: "auto", level: "warn", label: "자동 조치", detail: "꺼져 있어요 (직접 누른 것만 움직여요)" }
  );

  return items;
}
