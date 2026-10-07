import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Drawer } from "./Overlay";
import { Btn } from "./HardwareCheck";
import { Placeholder, useLiveFrame } from "./LiveView";
import { ProbBars } from "./ProbBars";
import { CROP_COLOR, CROP_LABEL } from "../lib/format";

// training.py 의 기준과 같다
const MIN_PER_CLASS = 8;
const GOOD_PER_CLASS = 25;
const COLLECT_TARGET = 20;

function Section({ title, hint, children }) {
  return (
    <section className="mb-9">
      <h3 className="text-[22px] font-extrabold text-ink">{title}</h3>
      {hint && <p className="mt-1 text-[16px] leading-snug text-ink-soft">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

/** 지우기는 한 번 더 눌러야 실행된다 (모아 둔 사진이 날아가는 실수를 막는다) */
function ClearButton({ count, disabled, onConfirm }) {
  const [armed, setArmed] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  if (count === 0) return null;
  return (
    <Btn
      tone={armed ? "warn" : "default"}
      disabled={disabled}
      onClick={() => {
        if (armed) {
          clearTimeout(timer.current);
          setArmed(false);
          onConfirm();
        } else {
          setArmed(true);
          timer.current = setTimeout(() => setArmed(false), 3500);
        }
      }}
    >
      {armed ? `${count}장 지울까요?` : "지우기"}
    </Btn>
  );
}

function status(count) {
  if (count < MIN_PER_CLASS) return { text: "더 필요해요", cls: "text-berry-700" };
  if (count < GOOD_PER_CLASS) return { text: "조금 더", cls: "text-sun-700" };
  return { text: "충분해요", cls: "text-leaf-700" };
}

export function StudioDrawer({ open, onClose, state, profiles, send }) {
  // 열려 있는 동안만 서버에 "미리보기를 빨리 갱신해 주세요"라고 알린다 (서버는 8초 뒤 알아서 멈춘다)
  useEffect(() => {
    if (!open) return undefined;
    const ping = () =>
      fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "studio_ping" }),
      }).catch(() => {});
    ping();
    const t = setInterval(ping, 4000);
    return () => clearInterval(t);
  }, [open]);

  const frame = useLiveFrame(open && !!state?.has_camera_frame, 900);

  if (!state) return <Drawer open={open} onClose={onClose} title="AI 학습" width="max-w-[680px]" />;

  const dataset = state.dataset || {};
  const collect = state.collect || { active: false };
  const train = state.train || { running: false, finished: false };
  const modelClasses = state.model_classes;

  // 학습할 클래스: 작물(profiles) + 빈 판(background)
  const rows = [
    ...profiles.map((p) => ({ key: p.key, name: p.name, color: CROP_COLOR[p.key] || "#999" })),
    { key: "background", name: "빈 판", color: CROP_COLOR.background },
  ];
  const usable = rows.filter((r) => (dataset[r.key] || 0) >= MIN_PER_CLASS);
  const collecting = collect.active;
  const canTrain = usable.length >= 2 && !collecting && !train.running;
  const missingInModel = profiles.filter((p) => !(modelClasses || []).includes(p.key));

  return (
    <Drawer open={open} onClose={onClose} title="AI 학습" width="max-w-[680px]">
      {/* 1. 카메라 */}
      <Section title="1. 브릭을 네모 안에">
        <div className="relative aspect-[16/10] overflow-hidden rounded-3xl bg-leaf-50 ring-1 ring-line">
          {frame ? (
            <img src={frame} alt="웹캠 화면" className="h-full w-full object-cover" draggable={false} />
          ) : (
            <Placeholder />
          )}
          <div
            className={`pointer-events-none absolute inset-[20%] rounded-2xl border-[3px] border-dashed shadow-[0_0_0_9999px_rgba(20,30,15,0.22)] ${
              collecting ? "border-leaf-300" : "border-white/90"
            }`}
          />
          {!state.camera_real && (
            <span className="absolute bottom-3 right-4 rounded-full bg-ink/70 px-3.5 py-1.5 text-[14px] font-bold text-white">
              모의 화면
            </span>
          )}
          {collecting && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute left-4 top-4 flex items-center gap-3 rounded-full bg-white/95 py-2.5 pl-4 pr-6 text-[20px] font-extrabold text-ink shadow"
            >
              <span className="h-3.5 w-3.5 animate-[blink_0.8s_infinite] rounded-full bg-berry-500" />
              {collect.crop === "background" ? "빈 판" : CROP_LABEL[collect.crop]} {collect.count}/{collect.target}
            </motion.div>
          )}
        </div>
        <p className="mt-3 text-[17px] font-bold text-ink">삑 소리마다 브릭을 조금씩 돌려 주세요</p>
      </Section>

      {/* 2. 사진 찍기 */}
      <Section title="2. 사진 찍기" hint="작물마다 25장 안팎이면 충분해요. 마지막에 빈 판도 찍으세요.">
        <ul className="space-y-4">
          {rows.map((r) => {
            const count = dataset[r.key] || 0;
            const st = status(count);
            const active = collecting && collect.crop === r.key;
            return (
              <li key={r.key} className="rounded-3xl bg-paper px-5 py-5">
                <div className="flex items-center gap-3.5">
                  <span className="h-5 w-5 shrink-0 rounded-full" style={{ background: r.color }} />
                  <span className="min-w-0 flex-1 text-[22px] font-extrabold text-ink">{r.name}</span>
                  <span className="text-[20px] font-extrabold tabular-nums text-ink">{count}장</span>
                  <span className={`w-[6.5rem] text-right text-[16px] font-bold ${st.cls}`}>{st.text}</span>
                </div>
                <div className="mt-3.5 flex flex-wrap items-center gap-3">
                  {active ? (
                    <>
                      <div className="h-3.5 min-w-[8rem] flex-1 overflow-hidden rounded-full bg-white ring-1 ring-line">
                        <motion.div
                          className="h-full rounded-full bg-berry-500"
                          initial={false}
                          animate={{ width: `${(collect.count / Math.max(1, collect.target)) * 100}%` }}
                        />
                      </div>
                      <Btn onClick={() => send("collect_stop")}>그만</Btn>
                    </>
                  ) : (
                    <>
                      <Btn
                        tone="primary"
                        icon="camera"
                        disabled={collecting || train.running}
                        onClick={() =>
                          send("collect_start", `${r.name} 촬영 시작`, { crop: r.key, target: COLLECT_TARGET })
                        }
                      >
                        {COLLECT_TARGET}장 찍기
                      </Btn>
                      <ClearButton
                        count={count}
                        disabled={collecting || train.running}
                        onConfirm={() => send("data_clear", `${r.name} 사진을 지웠어요`, { crop: r.key })}
                      />
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </Section>

      {/* 3. 학습 */}
      <Section title="3. 학습">
        {missingInModel.length > 0 && (
          <p className="mb-3 rounded-2xl bg-berry-100 px-5 py-3.5 text-[17px] font-bold text-berry-700">
            AI가 아직 몰라요: {missingInModel.map((p) => p.name).join(", ")}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Btn tone="primary" icon="sparkle" disabled={!canTrain} onClick={() => send("train_start", "학습을 시작했어요")}>
            {train.running ? "학습 중…" : "학습 시작"}
          </Btn>
          {train.running && <Btn onClick={() => send("train_stop")}>멈추기</Btn>}
          {!canTrain && !train.running && (
            <span className="text-[16px] font-semibold text-sun-700">
              {collecting ? "촬영 중이에요" : `${MIN_PER_CLASS}장 넘는 항목이 2개 필요해요`}
            </span>
          )}
        </div>

        {(train.running || train.finished) && (
          <div className="mt-4 rounded-3xl bg-paper px-5 py-5">
            <div className="flex items-baseline justify-between">
              <span className="text-[20px] font-extrabold text-ink">
                {train.running ? train.phase : train.ok ? "끝났어요" : "실패했어요"}
              </span>
              <span className="text-[18px] font-bold tabular-nums text-ink-soft">{Math.round(train.pct)}%</span>
            </div>
            <div className="mt-3 h-4 overflow-hidden rounded-full bg-white ring-1 ring-line">
              <motion.div
                className={`h-full rounded-full ${train.finished && !train.ok ? "bg-berry-500" : "bg-leaf-500"}`}
                initial={false}
                animate={{ width: `${train.pct}%` }}
                transition={{ type: "spring", stiffness: 120, damping: 22 }}
              />
            </div>
            {train.finished && train.ok && (
              <p className="mt-3 text-[18px] font-bold text-ink">
                정확도 {Math.round(train.accuracy * 100)}%
                {train.accuracy < 0.85 && <span className="text-sun-700"> · 사진을 더 찍어 보세요</span>}
              </p>
            )}
            {train.finished && !train.ok && train.log?.length > 0 && (
              <pre className="mt-3 max-h-28 overflow-auto whitespace-pre-wrap rounded-xl bg-white p-3 text-[13px] leading-snug text-ink-soft">
                {train.log.join("\n")}
              </pre>
            )}
          </div>
        )}
      </Section>

      {/* 4. 시험 */}
      <Section title="4. 시험">
        <div className="rounded-3xl bg-paper px-5 py-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <span className="text-[22px] font-extrabold text-ink">
              {state.crop_key ? CROP_LABEL[state.crop_key] ?? state.crop_name : "없음"}
            </span>
            <Btn icon="scan" onClick={() => send("scan")}>
              지금 보기
            </Btn>
          </div>
          <ProbBars probs={state.crop_probs} activeKey={state.crop_key || "background"} compact />
        </div>
      </Section>
    </Drawer>
  );
}
