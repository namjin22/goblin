import { motion } from "framer-motion";
import { Card } from "./Card";

function Tile({ label, status, active, children }) {
  return (
    <div className="flex flex-col rounded-3xl bg-paper px-3 py-4">
      <div className="relative flex flex-1 items-center justify-center">{children}</div>
      <div className="mt-3 flex flex-col items-center gap-2">
        <span className="text-[18px] font-bold text-ink">{label}</span>
        <span
          className={`rounded-full px-3.5 py-1 text-[16px] font-extrabold ${
            active ? "bg-leaf-600 text-white" : "bg-white text-ink-soft ring-1 ring-line"
          }`}
        >
          {status}
        </span>
      </div>
    </div>
  );
}

/** 환기창: 가운데에서 양옆으로 열리는 두 짝 창. 실제 모터가 도는 시간(2.5초)에 맞춰 움직인다. */
function WindowGraphic({ open }) {
  const slide = { duration: 2.5, ease: "easeInOut" };
  return (
    <svg viewBox="0 0 140 100" className="h-[72px] w-full max-w-[120px]">
      <rect x="10" y="6" width="120" height="88" rx="8" fill="#e8f2dc" stroke="#8a6a49" strokeWidth="4" />
      {/* 열렸을 때 보이는 바깥 풍경 */}
      <rect x="16" y="12" width="108" height="76" rx="4" fill="#cfe7f5" />
      <circle cx="98" cy="34" r="9" fill="#fbd96b" />
      <path d="M16 88V70c14-8 24-4 38 2 14 6 26 4 38-4 12-8 22-4 32 0v20z" fill="#9bc97a" />
      {/* 두 짝의 창: 틀 안쪽으로만 보이게 잘라서, 열리면 벽 속으로 들어가는 것처럼 보인다 */}
      <clipPath id="win-clip">
        <rect x="16" y="12" width="108" height="76" />
      </clipPath>
      <g clipPath="url(#win-clip)">
        <motion.g initial={false} animate={{ x: open ? -46 : 0 }} transition={slide}>
          <rect x="16" y="12" width="54" height="76" fill="#f3f9fc" fillOpacity="0.92" stroke="#8a6a49" strokeWidth="3" />
          <path d="M24 24l14-8M24 40l30-16" stroke="#fff" strokeWidth="3" strokeLinecap="round" opacity="0.8" />
        </motion.g>
        <motion.g initial={false} animate={{ x: open ? 46 : 0 }} transition={slide}>
          <rect x="70" y="12" width="54" height="76" fill="#f3f9fc" fillOpacity="0.92" stroke="#8a6a49" strokeWidth="3" />
        </motion.g>
      </g>
    </svg>
  );
}

/** 스프링클러(레고 모형): 켜지면 머리가 흔들리고 물방울이 떨어진다 */
function SprinklerGraphic({ on }) {
  return (
    <svg viewBox="0 0 140 100" className="h-[72px] w-full max-w-[120px]">
      <rect x="62" y="48" width="16" height="40" rx="3" fill="#8a6a49" />
      <rect x="40" y="86" width="60" height="8" rx="4" fill="#5a4330" />
      {/* 머리: 아래쪽 가운데(bbox 기준)를 축으로 좌우로 흔든다 */}
      <motion.g
        style={{ originX: 0.5, originY: 1 }}
        animate={on ? { rotate: [-12, 12, -12] } : { rotate: 0 }}
        transition={on ? { duration: 1.1, repeat: Infinity, ease: "easeInOut" } : { duration: 0.3 }}
      >
        <path d="M48 46h44l-8-18H56z" fill={on ? "#3c8fc4" : "#a9b4ae"} />
        <rect x="64" y="22" width="12" height="8" rx="2" fill={on ? "#1f5f8a" : "#8c9791"} />
      </motion.g>
      {on &&
        [0, 1, 2, 3, 4, 5].map((i) => (
          <circle
            key={i}
            cx={46 + i * 10.5}
            cy="50"
            r="3"
            fill="#3c8fc4"
            style={{ animation: `drop 0.9s ${i * 0.14}s infinite ease-in` }}
          />
        ))}
    </svg>
  );
}

/** 생장등: 켜지면 따뜻하게 빛난다 */
function LightGraphic({ on }) {
  return (
    <svg viewBox="0 0 140 100" className="h-[72px] w-full max-w-[120px]">
      <defs>
        <radialGradient id="glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff3b0" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#fff3b0" stopOpacity="0" />
        </radialGradient>
      </defs>
      <motion.circle
        cx="70"
        cy="46"
        r="46"
        fill="url(#glow)"
        initial={false}
        animate={{ opacity: on ? 1 : 0, scale: on ? 1 : 0.6 }}
        transition={{ duration: 0.5 }}
        style={{ originX: 0.5, originY: 0.5 }}
      />
      <path d="M70 6v14" stroke="#5a4330" strokeWidth="3" strokeLinecap="round" />
      <motion.path
        d="M70 20c-15 0-24 10-24 22 0 8 5 13 9 17 2.5 2.5 3.5 5 3.5 8h23c0-3 1-5.5 3.5-8 4-4 9-9 9-17 0-12-9-22-24-22z"
        initial={false}
        animate={{ fill: on ? "#ffe680" : "#e7e2d6" }}
        stroke="#8a6a49"
        strokeWidth="3"
        transition={{ duration: 0.4 }}
      />
      <rect x="58" y="70" width="24" height="7" rx="3" fill="#8a6a49" />
      <rect x="62" y="79" width="16" height="6" rx="3" fill="#5a4330" />
    </svg>
  );
}

/** 실제 96×96 Display에 나가는 두 줄을 그대로 보여준다 */
function DisplayGraphic({ text }) {
  const [line1 = "", line2 = ""] = (text || "").split("\n");
  return (
    <div className="flex aspect-square w-[72px] flex-col items-center justify-center gap-1 rounded-xl bg-[#101a12] px-2 text-center shadow-[inset_0_0_0_3px_#2b3a2e,0_0_18px_rgba(116,176,79,0.25)]">
      <span className="max-w-full truncate text-[14px] font-bold leading-tight text-white">
        {line1 || "·"}
      </span>
      <span className="max-w-full truncate text-[12.5px] font-semibold leading-tight text-leaf-300">
        {line2}
      </span>
    </div>
  );
}

export function DevicesCard({ state }) {
  const ventStatus = state.busy_action === "vent_open"
    ? "여는 중"
    : state.busy_action === "vent_close"
    ? "닫는 중"
    : state.vent_open
    ? "열림"
    : "닫힘";

  return (
    <Card title="장치" icon="auto">
      <div className="flex h-full flex-col">
      <div className="grid flex-1 grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile label="환기창" status={ventStatus} active={state.vent_open}>
          <WindowGraphic open={state.vent_open} />
        </Tile>
        <Tile
          label="스프링클러"
          status={state.sprinkler_on ? "작동 중" : "대기"}
          active={state.sprinkler_on}
        >
          <SprinklerGraphic on={state.sprinkler_on} />
        </Tile>
        <Tile label="생장등" status={state.light_on ? "켜짐" : "꺼짐"} active={state.light_on}>
          <LightGraphic on={state.light_on} />
        </Tile>
        <Tile label="화면" status="켜짐" active={false}>
          <DisplayGraphic text={state.display_text} />
        </Tile>
      </div>
      </div>
    </Card>
  );
}
