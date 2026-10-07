import { Drawer } from "./Overlay";
import { Icon } from "./Icons";
import { preflight } from "../lib/preflight";
import { HardwareCheck } from "./HardwareCheck";

function Section({ title, children }) {
  return (
    <section className="mb-6">
      <h3 className="mb-2 text-[13px] font-bold tracking-wide text-ink-soft">{title}</h3>
      {children}
    </section>
  );
}

function Row({ label, value, warn }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line/70 py-2 text-[14px] last:border-0">
      <span className="text-ink-soft">{label}</span>
      <span className={`text-right font-semibold ${warn ? "text-berry-700" : "text-ink"}`}>{value}</span>
    </div>
  );
}

/** 부스를 운영하는 사람용 패널. 관람객은 열 일이 없다. */
const LEVEL = {
  ok: { icon: "check", chip: "bg-leaf-100 text-leaf-700" },
  warn: { icon: "info", chip: "bg-sun-100 text-sun-700" },
  fail: { icon: "close", chip: "bg-berry-100 text-berry-700" },
};

/** 개장 전 점검 - BOOTH.md의 체크리스트를 현재 상태로 자동 판정한다 */
function Checklist({ items }) {
  const ready = items.filter((i) => i.level === "ok").length;
  const allOk = ready === items.length;
  return (
    <Section title={`개장 전 점검 · ${ready}/${items.length}`}>
      <div
        className={`mb-2 rounded-2xl px-4 py-2.5 text-[14px] font-bold ${
          allOk ? "bg-leaf-100 text-leaf-800" : "bg-sun-100 text-sun-700"
        }`}
      >
        {allOk ? "모두 준비됐어요. 부스를 열어도 좋아요." : "확인할 것이 남아 있어요."}
      </div>
      <ul className="divide-y divide-line/70 rounded-2xl bg-paper px-4">
        {items.map((i) => (
          <li key={i.key} className="flex items-start gap-3 py-2.5">
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${LEVEL[i.level].chip}`}
            >
              <Icon name={LEVEL[i.level].icon} size={14} strokeWidth={2.4} />
            </span>
            <span className="min-w-0 text-[14px] leading-snug">
              <b className="text-ink">{i.label}</b>
              <span className="block text-[12.5px] text-ink-soft">{i.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function OperatorDrawer({ open, onClose, state, send, staleSec }) {
  const assumed = state?.vent_assumed;

  return (
    <Drawer open={open} onClose={onClose} title="운영자" subtitle="부스를 운영하는 분을 위한 화면이에요.">
      {!state ? (
        <p className="text-ink-soft">서버에서 상태를 받는 중이에요…</p>
      ) : (
        <>
          <Checklist items={preflight(state, staleSec)} />

          <Section title="장치 점검 (눈으로 확인하세요)">
            <HardwareCheck state={state} send={send} />
          </Section>

          <Section title="환기창 실제 상태 맞추기">
            <div
              className={`rounded-2xl px-4 py-3.5 ${
                assumed ? "bg-sun-100 ring-1 ring-sun-500/40" : "bg-paper"
              }`}
            >
              <p className="text-[14px] leading-relaxed text-ink">
                {assumed ? (
                  <>
                    <b className="text-sun-700">확인이 필요해요.</b> 시스템은 지금 창문이{" "}
                    <b>{state.vent_open ? "열려" : "닫혀"} 있다</b>고 믿고 있어요. 환기창은 위치를 읽을 수
                    없어서, 다시 조립하거나 껐다 켠 뒤에는 실제와 다를 수 있어요.
                  </>
                ) : (
                  <>
                    시스템은 창문이 <b>{state.vent_open ? "열려" : "닫혀"} 있다</b>고 알고 있어요. 손으로
                    창문을 움직였다면 아래에서 맞춰 주세요.
                  </>
                )}
              </p>
              <p className="mt-2 text-[12.5px] text-ink-soft">
                눈으로 창문을 보고 누르세요. <b>모터는 움직이지 않아요.</b>
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  onClick={() => send("vent_mark_open", "창문 상태를 '열림'으로 맞췄어요")}
                  className="rounded-xl border border-line bg-card py-2.5 text-[14px] font-bold text-ink transition hover:border-leaf-300 hover:bg-leaf-50 active:scale-95"
                >
                  지금 열려 있어요
                </button>
                <button
                  onClick={() => send("vent_mark_closed", "창문 상태를 '닫힘'으로 맞췄어요")}
                  className="rounded-xl border border-line bg-card py-2.5 text-[14px] font-bold text-ink transition hover:border-leaf-300 hover:bg-leaf-50 active:scale-95"
                >
                  지금 닫혀 있어요
                </button>
              </div>
            </div>
          </Section>

          <Section title="시스템 상태">
            <div className="rounded-2xl bg-paper px-4 py-1.5">
              <Row label="실행 모드" value={state.mock ? "모의 실행 (가짜 장치)" : "실물 장치"} warn={state.mock} />
              <Row
                label="장치 통신"
                value={state.hw_error ? `문제 있음 (${state.hw_error})` : "정상"}
                warn={!!state.hw_error}
              />
              <Row
                label="마지막 갱신"
                value={staleSec < 2 ? "방금" : `${Math.round(staleSec)}초 전`}
                warn={staleSec > 8}
              />
              <Row label="자동 조치" value={state.auto_mode ? "켜짐" : "꺼짐"} />
              <Row label="인식된 작물" value={state.crop_key ? state.crop_name : "없음"} />
              <Row label="온열질환 경고 기준" value={`${state.thresholds.heat_danger_temp}°C 이상`} />
            </div>
          </Section>

          <p className="flex items-start gap-2 rounded-2xl bg-paper px-4 py-3 text-[12.5px] leading-relaxed text-ink-soft">
            <Icon name="info" size={16} className="mt-0.5 shrink-0" />
            <span>
              환기창이 이상하게 움직이면 노트북에서 <b>python hwtest.py --motor</b>로 방향과 각도를 다시
              보정하세요.
            </span>
          </p>
        </>
      )}
    </Drawer>
  );
}
