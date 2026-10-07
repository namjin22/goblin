import { useEffect, useMemo, useState } from "react";
import { Icon } from "./Icons";

// 서버 hw.roles 의 키와 같다. "" 는 아직 정하지 않은/안 쓰는 모터.
const ROLE_OPTIONS = [
  { value: "", label: "정하지 않음" },
  { value: "vent_a", label: "창문 모터 A" },
  { value: "vent_b", label: "창문 모터 B" },
  { value: "sprinkler", label: "스프링클러" },
];

function draftFromHw(hw) {
  const draft = {};
  hw.motors.forEach((m) => {
    draft[m.id] = "";
  });
  Object.entries(hw.roles).forEach(([role, id]) => {
    if (id != null && id in draft) draft[id] = role;
  });
  return draft;
}

/** 저장할 수 있는 조합인지: A와 B가 각각 정확히 하나, 스프링클러는 최대 하나 */
function validate(draft) {
  const count = (role) => Object.values(draft).filter((r) => r === role).length;
  if (count("vent_a") !== 1 || count("vent_b") !== 1) return "창문 모터 A와 B를 하나씩 고르세요";
  if (count("sprinkler") > 1) return "스프링클러는 하나만 고르세요";
  return null;
}

function Step({ n, title, hint, children, done }) {
  return (
    <li className="rounded-3xl bg-paper px-5 py-5">
      <div className="flex items-start gap-4">
        <span
          className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[16px] font-extrabold ${
            done ? "bg-leaf-600 text-white" : "bg-white text-ink-soft ring-1 ring-line"
          }`}
        >
          {done ? <Icon name="check" size={18} strokeWidth={3} /> : n}
        </span>
        <div className="min-w-0 flex-1">
          <h4 className="text-[20px] font-extrabold text-ink">{title}</h4>
          {hint && <p className="mt-1 text-[16px] leading-snug text-ink-soft">{hint}</p>}
          <div className="mt-4">{children}</div>
        </div>
      </div>
    </li>
  );
}

export function Btn({ onClick, disabled, icon, children, tone = "default", full = false }) {
  const tones = {
    default: "border-line bg-card text-ink hover:border-leaf-300 hover:bg-leaf-50",
    primary: "border-leaf-600 bg-leaf-600 text-white hover:bg-leaf-700",
    warn: "border-sun-500/50 bg-sun-100 text-sun-700 hover:bg-sun-100/70",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex min-h-[56px] items-center justify-center gap-2 rounded-2xl border-2 px-6 py-3 text-[18px] font-extrabold transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-45 ${
        full ? "w-full" : ""
      } ${tones[tone]}`}
    >
      {icon && <Icon name={icon} size={22} />}
      {children}
    </button>
  );
}

/**
 * 장치 점검: 눈으로 보면서 하나씩 확인하고, 모터 역할과 열림 방향을 정한다.
 * 터미널(hwtest.py)이 없어도 된다. 모든 동작은 서버를 거쳐 메인 루프가 한다.
 */
export function HardwareCheck({ state, send }) {
  const hw = state.hw;
  const roleKey = hw ? JSON.stringify([hw.motors.map((m) => m.id), hw.roles]) : "";
  const [draft, setDraft] = useState(() => (hw ? draftFromHw(hw) : {}));

  // 서버의 역할이 바뀌면(저장 직후 등) 선택 상태를 서버 기준으로 다시 맞춘다
  useEffect(() => {
    if (hw) setDraft(draftFromHw(hw));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleKey]);

  const problem = useMemo(() => validate(draft), [draft]);
  const dirty = hw ? JSON.stringify(draft) !== JSON.stringify(draftFromHw(hw)) : false;

  if (!hw) return <p className="text-[17px] text-ink-soft">장치 정보를 받는 중이에요</p>;

  const busy = state.busy;
  const idOf = (role) => Number(Object.keys(draft).find((id) => draft[id] === role)) || null;

  const saveRoles = () =>
    send("set_roles", "모터 역할을 저장했어요", {
      vent_a: idOf("vent_a"),
      vent_b: idOf("vent_b"),
      sprinkler: idOf("sprinkler"),
    });

  const flipBoth = async () => {
    await send("flip_sign", null, { which: "a" });
    await new Promise((r) => setTimeout(r, 900)); // 첫 명령이 처리된 뒤에 두 번째를 보낸다
    await send("flip_sign", "두 모터 방향을 바꿨어요", { which: "b" });
  };

  const motorCount = hw.motors.length;

  return (
    <ol className="space-y-5">
      <Step n={1} title="소리" hint="노트북에서 삑 소리가 나나요?">
        <Btn icon="sound" disabled={!state.sound_on} onClick={() => send("sound_test", "소리를 냈어요")}>
          소리 내기
        </Btn>
        {!state.sound_on && <p className="mt-2 text-[15px] font-semibold text-sun-700">소리가 꺼져 있어요</p>}
      </Step>

      <Step n={2} title="LED" hint="빨강 · 초록 · 파랑 · 흰색으로 바뀌나요?">
        <Btn icon="bulb" onClick={() => send("led_test", "LED를 켰어요")}>
          LED 켜기
        </Btn>
      </Step>

      <Step n={3} title="작은 화면" hint="'농깨비 / 점검중'이 보이나요?">
        <Btn icon="scan" onClick={() => send("display_test", "화면에 띄웠어요")}>
          글자 띄우기
        </Btn>
      </Step>

      <Step
        n={4}
        title={`모터 역할 (${motorCount}개)`}
        hint="[움직이기]를 눌러 어느 부분이 움직이는지 보고 고르세요"
        done={hw.vent_roles_ok}
      >
        {motorCount < 3 && (
          <p className="mb-3 rounded-2xl bg-sun-100 px-4 py-3 text-[16px] font-semibold text-sun-700">
            모터가 {motorCount}개예요. 3개여야 해요
          </p>
        )}
        <ul className="space-y-3">
          {hw.motors.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center gap-3 rounded-2xl bg-white px-4 py-3.5 ring-1 ring-line">
              <span className="min-w-[5.5rem] text-[18px] font-extrabold tabular-nums text-ink">{m.label}</span>
              <Btn disabled={busy} onClick={() => send("jog", "모터를 움직였어요", { motor_id: m.id, delta: 20 })}>
                움직이기
              </Btn>
              <select
                value={draft[m.id] ?? ""}
                onChange={(e) => setDraft({ ...draft, [m.id]: e.target.value })}
                className="ml-auto min-h-[56px] min-w-[10rem] rounded-2xl border-2 border-line bg-card px-4 text-[18px] font-bold text-ink"
                aria-label={`모터 ${m.label}의 역할`}
              >
                {ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Btn tone="primary" disabled={busy || !dirty || !!problem || state.vent_open} onClick={saveRoles}>
            저장
          </Btn>
          {dirty && problem && <span className="text-[16px] font-semibold text-sun-700">{problem}</span>}
          {state.vent_open && <span className="text-[16px] font-semibold text-sun-700">창문을 먼저 닫아 주세요</span>}
        </div>
      </Step>

      <Step
        n={5}
        title="창문 방향"
        hint="두 모터가 함께 창문을 여는 쪽으로 움직였다 돌아오나요?"
        done={hw.vent_ready}
      >
        {!hw.vent_roles_ok ? (
          <p className="text-[16px] font-semibold text-sun-700">4번에서 창문 모터를 먼저 정하세요</p>
        ) : (
          <>
            <Btn icon="window" disabled={busy || state.vent_open} onClick={() => send("vent_test", "열었다 닫을게요")}>
              열었다 닫기
            </Btn>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Btn tone="primary" disabled={busy || hw.vent_ready} onClick={() => send("vent_confirm", "확인했어요")}>
                잘 열렸어요
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={() => send("flip_sign", "A 방향을 바꿨어요", { which: "a" })}>
                A만 반대
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={() => send("flip_sign", "B 방향을 바꿨어요", { which: "b" })}>
                B만 반대
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={flipBoth}>
                둘 다 반대
              </Btn>
            </div>
            <p className={`mt-3 text-[16px] font-semibold ${hw.vent_ready ? "text-leaf-700" : "text-ink-soft"}`}>
              {hw.vent_ready ? "확인됐어요" : "확인 전에는 창문이 움직이지 않아요"}
            </p>
          </>
        )}
      </Step>
    </ol>
  );
}
