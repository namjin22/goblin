import { motion } from "framer-motion";
import { CROP_COLOR, CROP_LABEL, CROP_ORDER } from "../lib/format";

/** 작물별 인식 확률 막대. activeKey 가 지금 인식된(강조할) 클래스. */
export function ProbBars({ probs, activeKey, compact = false }) {
  if (!probs) {
    return (
      <p className="rounded-2xl bg-paper px-4 py-3 text-[13px] leading-relaxed text-ink-soft">
        지금은 확률 정보가 없어요. (분류 모델이 없거나 색깔 규칙으로 보조 판단하는 중)
      </p>
    );
  }
  // 모델이 아는 클래스만, 보여줄 순서대로
  const keys = [...CROP_ORDER, "background"].filter((k) => k in probs);
  return (
    <ul className={compact ? "space-y-2.5" : "space-y-2.5"} aria-label="작물별 인식 확률">
      {keys.map((k) => {
        const p = probs[k] ?? 0;
        const active = k === activeKey;
        return (
          <li key={k} className="grid grid-cols-[6rem_1fr_3.5rem] items-center gap-3">
            <span className={`text-[18px] ${active ? "font-extrabold text-ink" : "font-medium text-ink-soft"}`}>
              {CROP_LABEL[k]}
            </span>
            <div className="h-4 overflow-hidden rounded-full bg-paper">
              <motion.div
                className="h-full rounded-full"
                style={{ background: CROP_COLOR[k], opacity: active ? 1 : 0.5 }}
                initial={false}
                animate={{ width: `${Math.max(p * 100, 1.5)}%` }}
                transition={{ type: "spring", stiffness: 140, damping: 22 }}
              />
            </div>
            <span
              className={`text-right text-[17px] tabular-nums ${active ? "font-extrabold text-ink" : "text-ink-soft"}`}
            >
              {Math.round(p * 100)}%
            </span>
          </li>
        );
      })}
    </ul>
  );
}
