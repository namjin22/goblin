export const CROP_ORDER = ["lettuce", "corn", "carrot"];

export const CROP_LABEL = {
  lettuce: "상추",
  corn: "옥수수",
  carrot: "당근",
  background: "작물 없음",
};

// 브릭 색에 맞춘 작물 대표색 (확률 막대 / 기준선 표시)
export const CROP_COLOR = {
  lettuce: "#74b04f",
  corn: "#e7a417",
  carrot: "#e8742c",
  background: "#b9b09c",
};

export const LEVEL_STYLE = {
  good: {
    label: "좋아요",
    bg: "bg-leaf-100",
    text: "text-leaf-800",
    dot: "bg-leaf-500",
    ring: "ring-leaf-300",
  },
  warn: {
    label: "주의",
    bg: "bg-sun-100",
    text: "text-sun-700",
    dot: "bg-sun-500",
    ring: "ring-sun-500/40",
  },
  alert: {
    label: "조치 필요",
    bg: "bg-berry-100",
    text: "text-berry-700",
    dot: "bg-berry-500",
    ring: "ring-berry-500/40",
  },
};

// 동작에 걸리는 시간(초) - controller.py의 VENT_DURATION / SPRINKLER_DURATION과 맞춘다
export const ACTION_SECONDS = { vent_open: 2.5, vent_close: 2.5, water: 4.0, vent_test: 5.3, jog: 2.7 };

export const ACTION_LABEL = {
  vent_open: "창문을 여는 중",
  vent_close: "창문을 닫는 중",
  water: "물을 주는 중",
  vent_test: "환기창을 열었다 닫는 중",
  jog: "모터를 확인하는 중",
};

export function relativeTime(epochSec, nowMs = Date.now()) {
  const diff = Math.max(0, Math.round(nowMs / 1000 - epochSec));
  if (diff < 5) return "방금";
  if (diff < 60) return `${diff}초 전`;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

export function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

/** value를 [min,max] 구간의 0~100% 위치로 바꾼다 */
export function pct(value, min, max) {
  return clamp(((value - min) / (max - min)) * 100, 0, 100);
}

/** 받침 유무로 조사를 고른다: josa("당근", "을", "를") -> "당근을" (백엔드 controller.josa와 같은 규칙) */
export function josa(word, withBatchim, without) {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  const has = code >= 0 && code < 11172 && code % 28 !== 0;
  return word + (has ? withBatchim : without);
}
