import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { ACTION_SECONDS, ACTION_SHORT } from "../lib/format";

const TONES = {
  leaf: { box: "hover:border-leaf-300 hover:bg-leaf-50", icon: "bg-leaf-100 text-leaf-700", bar: "bg-leaf-500" },
  sky: { box: "hover:border-sky-500/50 hover:bg-sky-100/60", icon: "bg-sky-100 text-sky-700", bar: "bg-sky-500" },
  sun: { box: "hover:border-sun-500/50 hover:bg-sun-100/60", icon: "bg-sun-100 text-sun-700", bar: "bg-sun-500" },
};

/**
 * 큰 조작 버튼. 모터가 도는 동안은 이 버튼 안에서 진행 막대와 "여는 중…"을 보여준다
 * (카드 위에 따로 상태 줄을 두면 레이아웃이 출렁이고 글자만 늘어난다).
 */
function BigButton({ icon, label, note, tone = "leaf", onClick, disabled, working, workingText, seconds }) {
  const t = TONES[tone];
  return (
    <motion.button
      whileTap={disabled ? undefined : { scale: 0.96 }}
      onClick={onClick}
      disabled={disabled}
      className={`relative flex h-full min-h-[150px] flex-col items-center justify-center gap-3.5 overflow-hidden rounded-[28px] border-2 border-line bg-card px-3 py-5 transition disabled:cursor-not-allowed ${
        working ? "border-leaf-300 bg-leaf-50" : disabled ? "opacity-45" : t.box
      }`}
    >
      <span className={`flex h-[68px] w-[68px] items-center justify-center rounded-3xl ${t.icon}`}>
        <Icon name={icon} size={38} />
      </span>
      <span className="whitespace-nowrap text-[clamp(1.15rem,1.45vw,1.5rem)] font-extrabold leading-none text-ink">{working ? workingText : label}</span>
      {note && !working && <span className="-mt-1 text-[14px] font-semibold text-ink-soft">{note}</span>}
      {working && (
        <motion.span
          key={workingText}
          className={`absolute inset-x-0 bottom-0 h-2.5 ${t.bar}`}
          initial={{ width: "0%" }}
          animate={{ width: "100%" }}
          transition={{ duration: seconds || 3, ease: "linear" }}
        />
      )}
    </motion.button>
  );
}

/** 자동 조치 스위치. 카드 제목 줄에 둔다. */
function AutoSwitch({ on, onToggle }) {
  return (
    <button
      onClick={onToggle}
      role="switch"
      aria-checked={on}
      aria-label="자동 조치"
      className="flex h-12 items-center gap-3.5 rounded-full border-2 border-line bg-paper pl-5 pr-2.5 transition hover:border-leaf-300"
    >
      <span className="text-[17px] font-bold text-ink">자동</span>
      <span className={`relative h-8 w-[3.75rem] rounded-full transition-colors ${on ? "bg-leaf-500" : "bg-line"}`}>
        <motion.span
          className="absolute top-1 h-6 w-6 rounded-full bg-white shadow"
          initial={false}
          animate={{ left: on ? 32 : 4 }}
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
        />
      </span>
    </button>
  );
}

const VENT_ACTIONS = ["vent_open", "vent_close", "vent_test"];

export function ControlsCard({ state, send }) {
  // 누르자마자 반응해야 해서, 서버 상태가 따라올 때까지(최대 1초) 낙관적으로 보여준다
  const [optimisticAuto, setOptimisticAuto] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const timer = useRef(null);
  const pendingTimer = useRef(null);
  const auto = optimisticAuto ?? state.auto_mode;

  useEffect(() => {
    if (optimisticAuto !== null && optimisticAuto === state.auto_mode) setOptimisticAuto(null);
  }, [state.auto_mode, optimisticAuto]);
  useEffect(() => {
    if (state.busy) setPendingAction(null); // 서버가 따라왔으니 진짜 상태로 넘긴다
  }, [state.busy]);
  useEffect(
    () => () => {
      clearTimeout(timer.current);
      clearTimeout(pendingTimer.current);
    },
    []
  );

  const runMotor = async (action, command, okText) => {
    setPendingAction(action);
    clearTimeout(pendingTimer.current);
    pendingTimer.current = setTimeout(() => setPendingAction(null), 3000);
    const ok = await send(command, okText);
    if (!ok) {
      clearTimeout(pendingTimer.current);
      setPendingAction(null);
    }
  };

  const toggleAuto = () => {
    const next = !auto;
    setOptimisticAuto(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOptimisticAuto(null), 4000); // 실패해도 원래 값으로 복귀
    send(next ? "auto_on" : "auto_off", next ? "자동 조치를 켰어요" : "자동 조치를 껐어요");
  };

  const busy = state.busy || !!pendingAction;
  const action = state.busy ? state.busy_action : pendingAction;
  const ventWorking = busy && VENT_ACTIONS.includes(action);
  const waterWorking = busy && action === "water";

  // 막혔을 땐 이유를 아주 짧게 (자세한 건 운영자 화면에서)
  const ventNote = !state.vent_roles_ok ? "모터 설정 필요" : !state.vent_verified ? "방향 확인 필요" : null;

  return (
    <Card title="조작" icon="auto" right={<AutoSwitch on={auto} onToggle={toggleAuto} />}>
      <div className="grid h-full grid-cols-3 gap-5">
        <BigButton
          icon="window"
          tone="leaf"
          label={state.vent_open ? "창문 닫기" : "창문 열기"}
          note={ventNote}
          disabled={busy || !!ventNote}
          working={ventWorking}
          workingText={`창문 ${ACTION_SHORT[action] || "…"}`}
          seconds={ACTION_SECONDS[action]}
          onClick={() =>
            state.vent_open
              ? runMotor("vent_close", "vent_close", "창문을 닫을게요")
              : runMotor("vent_open", "vent_open", "창문을 열게요")
          }
        />
        <BigButton
          icon="drop"
          tone="sky"
          label="물 주기"
          note={state.sprinkler_ready ? null : "모터 없음"}
          disabled={busy || !state.sprinkler_ready}
          working={waterWorking}
          workingText="물 주는 중"
          seconds={ACTION_SECONDS.water}
          onClick={() => runMotor("water", "water", "물을 줄게요")}
        />
        <BigButton
          icon="bulb"
          tone="sun"
          label={state.light_on ? "생장등 끄기" : "생장등 켜기"}
          onClick={() => send("light_toggle", state.light_on ? "생장등을 껐어요" : "생장등을 켰어요")}
        />
      </div>
    </Card>
  );
}
