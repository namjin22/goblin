import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { relativeTime } from "../lib/format";

const EVENT = {
  vent_open: { icon: "window", tone: "bg-leaf-100 text-leaf-700" },
  vent_close: { icon: "window", tone: "bg-leaf-100 text-leaf-700" },
  water: { icon: "drop", tone: "bg-sky-100 text-sky-700" },
  light: { icon: "bulb", tone: "bg-sun-100 text-sun-700" },
  scan: { icon: "camera", tone: "bg-paper text-ink-soft" },
  heat_alarm: { icon: "bell", tone: "bg-berry-100 text-berry-700" },
  auto: { icon: "auto", tone: "bg-paper text-ink-soft" },
  growth_photo: { icon: "camera", tone: "bg-paper text-ink-soft" },
  vent_sync: { icon: "window", tone: "bg-sun-100 text-sun-700" },
  hw_error: { icon: "info", tone: "bg-berry-100 text-berry-700" },
  hw_ok: { icon: "check", tone: "bg-leaf-100 text-leaf-700" },
};

/** "방금 / 3분 전" 표시가 멈춰 있지 않게 5초마다 다시 그린다 */
function useNow(ms = 5000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}

export function Timeline({ history }) {
  const now = useNow();
  // "done"은 동작이 끝났다는 내부 기록이라 사람에게는 소음이다
  const items = history.filter((h) => h.event !== "done").slice(0, 3);

  return (
    <Card title="기록" icon="bell" className="flex min-h-0 flex-1 flex-col">
      {items.length === 0 ? (
        <p className="py-6 text-center text-[17px] text-ink-soft">아직 없어요</p>
      ) : (
        <ul className="space-y-2.5">
          <AnimatePresence initial={false}>
            {items.map((h) => {
              const meta = EVENT[h.event] || { icon: "info", tone: "bg-paper text-ink-soft" };
              return (
                <motion.li
                  key={`${h.at}-${h.event}`}
                  layout
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-center gap-4 rounded-2xl px-1 py-1"
                >
                  <span
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${meta.tone}`}
                  >
                    <Icon name={meta.icon} size={22} />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[18px] font-semibold text-ink">
                    {h.detail}
                  </span>
                  <span className="shrink-0 text-[15px] tabular-nums text-ink-soft">
                    {relativeTime(h.at, now)}
                  </span>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </Card>
  );
}
