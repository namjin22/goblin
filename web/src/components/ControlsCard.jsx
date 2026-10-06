import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { ACTION_LABEL, ACTION_SECONDS } from "../lib/format";

/**
 * 동작 상태 줄. 높이를 고정해서(동작 중이든 아니든) 카드가 커졌다 줄어들며 화면이 출렁이지 않게 한다.
 * 모터가 도는 동안은 진행 정도를 보여준다 (서버는 busy 여부만 알려줘서 시간으로 추정).
 */
function StatusLine({ action }) {
  const total = ACTION_SECONDS[action] || 3;
  return (
    <div className="mb-3 h-[52px]">
      {/* AnimatePresence의 wait는 쓰지 않는다: 이전 것이 사라질 때까지 기다리면 누른 직후 반응이 늦어진다 */}
      <>
        {action ? (
          <motion.div
            key={action}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="h-full rounded-2xl bg-leaf-50 px-4 py-2"
          >
            <p className="mb-1.5 flex items-center gap-2 text-[14px] font-bold text-leaf-800">
              <span className="h-2 w-2 animate-[blink_0.8s_infinite] rounded-full bg-leaf-500" />
              {ACTION_LABEL[action] || "동작 중"}
            </p>
            <div className="h-2 overflow-hidden rounded-full bg-white">
              <motion.div
                className="h-full rounded-full bg-leaf-500"
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ duration: total, ease: "linear" }}
              />
            </div>
          </motion.div>
        ) : (
          <motion.p
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex h-full items-center rounded-2xl bg-paper px-4 text-[13px] text-ink-soft"
          >
            눌러 보세요. 장치가 바로 움직여요.
          </motion.p>
        )}
      </>
    </div>
  );
}

function ActionButton({ icon, label, sub, onClick, disabled, tone = "leaf" }) {
  const tones = {
    leaf: "hover:border-leaf-300 hover:bg-leaf-50",
    sky: "hover:border-sky-500/50 hover:bg-sky-100/60",
    sun: "hover:border-sun-500/50 hover:bg-sun-100/60",
    ink: "hover:border-ink/30 hover:bg-paper",
  };
  const iconTones = {
    leaf: "bg-leaf-100 text-leaf-700",
    sky: "bg-sky-100 text-sky-700",
    sun: "bg-sun-100 text-sun-700",
    ink: "bg-paper text-ink-soft",
  };
  return (
    <motion.button
      whileTap={disabled ? undefined : { scale: 0.96 }}
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-3 rounded-2xl border border-line bg-card px-3.5 py-2.5 text-left transition disabled:cursor-not-allowed disabled:opacity-45 ${tones[tone]}`}
    >
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconTones[tone]}`}>
        <Icon name={icon} size={22} />
      </span>
      <span className="min-w-0">
        <span className="block text-[16px] font-bold text-ink">{label}</span>
        <span className="block truncate text-[12px] text-ink-soft">{sub}</span>
      </span>
    </motion.button>
  );
}

function AutoSwitch({ on, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center justify-between gap-3 rounded-2xl bg-paper px-4 py-3 text-left"
      role="switch"
      aria-checked={on}
    >
      <span>
        <span className="flex items-center gap-2 text-[15px] font-bold text-ink">
          <Icon name="auto" size={18} className={on ? "text-leaf-600" : "text-ink-soft"} />
          자동 조치 {on ? "켜짐" : "꺼짐"}
        </span>
        <span className="mt-0.5 block text-[12px] leading-snug text-ink-soft">
          {on
            ? "기준을 넘으면 사람이 묻지 않아도 알아서 움직여요"
            : "꺼져 있어요. 직접 누른 것만 움직여요"}
        </span>
      </span>
      <span
        className={`relative h-8 w-14 shrink-0 rounded-full transition-colors ${
          on ? "bg-leaf-500" : "bg-line"
        }`}
      >
        <motion.span
          className="absolute top-1 h-6 w-6 rounded-full bg-white shadow"
          initial={false}
          animate={{ left: on ? 28 : 4 }}
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
        />
      </span>
    </button>
  );
}

export function ControlsCard({ state, send }) {
  // 스위치는 누르자마자 반응해야 해서, 서버 상태가 따라올 때까지 낙관적으로 보여준다
  const [optimisticAuto, setOptimisticAuto] = useState(null);
  // 모터 명령도 마찬가지: 서버 상태(busy)는 최대 1초 뒤에야 오므로, 누른 즉시 진행 표시를 켠다
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

  /** 모터를 쓰는 명령: 누르는 즉시 진행 표시, 실패하면 되돌린다 */
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
  const shownAction = state.busy ? state.busy_action : pendingAction;

  return (
    <Card title="직접 조작" icon="auto">
      <StatusLine action={busy ? shownAction : null} />

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <ActionButton
          icon="window"
          tone="leaf"
          label={state.vent_open ? "창문 닫기" : "창문 열기"}
          sub={state.vent_open ? "지금 열려 있어요" : "지금 닫혀 있어요"}
          disabled={busy}
          onClick={() =>
            state.vent_open
              ? runMotor("vent_close", "vent_close", "창문을 닫을게요")
              : runMotor("vent_open", "vent_open", "창문을 열게요")
          }
        />
        <ActionButton
          icon="drop"
          tone="sky"
          label="물 주기"
          sub="스프링클러를 돌려요"
          disabled={busy}
          onClick={() => runMotor("water", "water", "물을 줄게요")}
        />
        <ActionButton
          icon="bulb"
          tone="sun"
          label={state.light_on ? "생장등 끄기" : "생장등 켜기"}
          sub={state.light_on ? "지금 켜져 있어요" : "지금 꺼져 있어요"}
          onClick={() => send("light_toggle", state.light_on ? "생장등을 껐어요" : "생장등을 켰어요")}
        />
        <ActionButton
          icon="scan"
          tone="ink"
          label="다시 인식"
          sub="바로 다시 봐요"
          onClick={() => send("scan", "작물을 다시 확인할게요")}
        />
      </div>

      <div className="mt-2.5">
        <AutoSwitch on={auto} onToggle={toggleAuto} />
      </div>
    </Card>
  );
}
