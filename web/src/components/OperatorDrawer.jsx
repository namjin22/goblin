import { Drawer } from "./Overlay";
import { Icon } from "./Icons";
import { preflight } from "../lib/preflight";
import { HardwareCheck, Btn } from "./HardwareCheck";

function Section({ title, children }) {
  return (
    <section className="mb-9">
      <h3 className="mb-4 text-[22px] font-extrabold text-ink">{title}</h3>
      {children}
    </section>
  );
}

function Row({ label, value, warn }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line/70 py-3.5 text-[17px] last:border-0">
      <span className="text-ink-soft">{label}</span>
      <span className={`text-right font-bold ${warn ? "text-berry-700" : "text-ink"}`}>{value}</span>
    </div>
  );
}

const LEVEL = {
  warn: { icon: "info", chip: "bg-sun-100 text-sun-700" },
  fail: { icon: "close", chip: "bg-berry-100 text-berry-700" },
};

/**
 * 개장 전 점검. 통과한 항목은 보여주지 않는다 - 문제가 있는 것만 보이면 해야 할 일이 바로 보인다.
 */
function Checklist({ items }) {
  const problems = items.filter((i) => i.level !== "ok");
  return (
    <Section title="점검">
      {problems.length === 0 ? (
        <div className="flex items-center gap-3 rounded-3xl bg-leaf-100 px-5 py-5 text-[20px] font-extrabold text-leaf-800">
          <Icon name="check" size={26} strokeWidth={3} />
          모두 준비됐어요
        </div>
      ) : (
        <ul className="space-y-3">
          {problems.map((i) => (
            <li key={i.key} className="flex items-start gap-4 rounded-3xl bg-paper px-5 py-4">
              <span
                className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${LEVEL[i.level].chip}`}
              >
                <Icon name={LEVEL[i.level].icon} size={20} strokeWidth={2.6} />
              </span>
              <span className="min-w-0 leading-snug">
                <b className="block text-[19px] text-ink">{i.label}</b>
                <span className="block text-[16px] text-ink-soft">{i.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function OperatorDrawer({ open, onClose, state, send, staleSec, profiles }) {
  const assumed = state?.vent_assumed;

  return (
    <Drawer open={open} onClose={onClose} title="운영자" width="max-w-[680px]">
      {!state ? (
        <p className="text-[18px] text-ink-soft">불러오는 중이에요</p>
      ) : (
        <>
          <Checklist items={preflight(state, staleSec, profiles)} />

          <Section title="장치 점검">
            <HardwareCheck state={state} send={send} />
          </Section>

          <Section title="기본 환경">
            <div className="rounded-3xl bg-paper px-5 py-5">
              {state.baseline ? (
                <p className="text-[19px] font-bold tabular-nums text-ink">
                  {state.baseline.temperature.toFixed(1)}°C · 습도 {Math.round(state.baseline.humidity)}% · 조도{" "}
                  {Math.round(state.baseline.illuminance)}
                </p>
              ) : (
                <p className="text-[18px] font-bold text-ink-soft">아직 저장 안 됨</p>
              )}
              <p className="mt-1 text-[16px] text-ink-soft">평상시 환경이에요. 건조도와 생장등이 여기에 맞춰져요</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Btn
                  tone="primary"
                  icon="thermo"
                  disabled={state.baseline_busy}
                  onClick={() => send("env_baseline", "5초 동안 재요. 평소 상태로 두세요")}
                >
                  {state.baseline_busy ? "재는 중…" : "지금을 기본으로"}
                </Btn>
                {state.baseline && (
                  <Btn disabled={state.baseline_busy} onClick={() => send("env_baseline_clear", "기본 환경을 지웠어요")}>
                    지우기
                  </Btn>
                )}
              </div>
            </div>
          </Section>

          <Section title="창문이 지금…">
            <div className={`rounded-3xl px-5 py-5 ${assumed ? "bg-sun-100 ring-2 ring-sun-500/40" : "bg-paper"}`}>
              <p className="text-[18px] font-bold text-ink">
                {assumed ? "확인이 필요해요. " : ""}시스템은 창문이{" "}
                <span className="text-leaf-700">{state.vent_open ? "열려" : "닫혀"} 있다</span>고 알아요
              </p>
              <p className="mt-1 text-[16px] text-ink-soft">직접 보고 맞는 쪽을 누르세요 (모터는 안 움직여요)</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Btn onClick={() => send("vent_mark_open", "열림으로 맞췄어요")}>열려 있어요</Btn>
                <Btn onClick={() => send("vent_mark_closed", "닫힘으로 맞췄어요")}>닫혀 있어요</Btn>
              </div>
            </div>
          </Section>

          <Section title="상태">
            <div className="rounded-3xl bg-paper px-5 py-1.5">
              <Row label="실행" value={state.mock ? "모의 (가짜 장치)" : "실물"} warn={state.mock} />
              <Row
                label="마지막 갱신"
                value={staleSec < 2 ? "방금" : `${Math.round(staleSec)}초 전`}
                warn={staleSec > 8}
              />
              <Row label="온열 경고" value={`${state.thresholds.heat_danger_temp}°C 이상`} />
            </div>
          </Section>
        </>
      )}
    </Drawer>
  );
}
