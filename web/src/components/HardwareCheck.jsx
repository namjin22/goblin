import { useEffect, useMemo, useState } from "react";
import { Icon } from "./Icons";

// 서버 hw.roles 의 키와 같다. "" 는 아직 정하지 않은/안 쓰는 모터.
const ROLE_OPTIONS = [
  { value: "", label: "정하지 않음" },
  { value: "vent_a", label: "환기창 모터 A" },
  { value: "vent_b", label: "환기창 모터 B" },
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

/** 선택한 역할이 저장할 수 있는 조합인지: A와 B가 각각 정확히 하나, 스프링클러는 최대 하나 */
function validate(draft) {
  const count = (role) => Object.values(draft).filter((r) => r === role).length;
  if (count("vent_a") !== 1 || count("vent_b") !== 1) return "환기창 모터 A와 B를 하나씩 골라 주세요";
  if (count("sprinkler") > 1) return "스프링클러는 하나만 고를 수 있어요";
  return null;
}

function Step({ n, title, hint, children, done }) {
  return (
    <li className="rounded-2xl bg-paper px-4 py-3.5">
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[12px] font-extrabold ${
            done ? "bg-leaf-600 text-white" : "bg-white text-ink-soft ring-1 ring-line"
          }`}
        >
          {done ? <Icon name="check" size={13} strokeWidth={3} /> : n}
        </span>
        <div className="min-w-0 flex-1">
          <h4 className="text-[14.5px] font-bold text-ink">{title}</h4>
          {hint && <p className="mt-0.5 text-[12.5px] leading-snug text-ink-soft">{hint}</p>}
          <div className="mt-2.5">{children}</div>
        </div>
      </div>
    </li>
  );
}

function Btn({ onClick, disabled, icon, children, tone = "default" }) {
  const tones = {
    default: "border-line bg-card text-ink hover:border-leaf-300 hover:bg-leaf-50",
    primary: "border-leaf-600 bg-leaf-600 text-white hover:bg-leaf-700",
    warn: "border-sun-500/50 bg-sun-100 text-sun-700 hover:bg-sun-100/70",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-1.5 rounded-xl border px-3.5 py-2 text-[13.5px] font-bold transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-45 ${tones[tone]}`}
    >
      {icon && <Icon name={icon} size={15} />}
      {children}
    </button>
  );
}

/**
 * 장치 점검: 사람이 눈으로 보면서 하나씩 확인하고, 모터 역할과 열림 방향을 정한다.
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

  if (!hw) {
    return <p className="text-[13px] text-ink-soft">장치 구성을 아직 받지 못했어요.</p>;
  }

  const busy = state.busy;
  const idOf = (role) => Number(Object.keys(draft).find((id) => draft[id] === role)) || null;

  const saveRoles = () =>
    send(
      "set_roles",
      "모터 역할을 저장했어요",
      { vent_a: idOf("vent_a"), vent_b: idOf("vent_b"), sprinkler: idOf("sprinkler") }
    );

  const flipBoth = async () => {
    await send("flip_sign", null, { which: "a" });
    await new Promise((r) => setTimeout(r, 900)); // 첫 명령이 처리된 뒤에 두 번째를 보낸다
    await send("flip_sign", "두 모터의 방향을 모두 뒤집었어요", { which: "b" });
  };

  const motorCount = hw.motors.length;

  return (
    <ol className="space-y-2.5">
      <Step
        n={1}
        title="노트북 소리"
        hint="삑 소리가 노트북 스피커에서 나는지 들어 보세요."
        done={false}
      >
        <Btn icon="sound" disabled={!state.sound_on} onClick={() => send("sound_test", "노트북에서 소리를 냈어요")}>
          소리 확인
        </Btn>
        {!state.sound_on && <p className="mt-1.5 text-[12px] text-sun-700">소리가 꺼져 있어요 (--mute 또는 모의 실행)</p>}
      </Step>

      <Step n={2} title="LED" hint="빨강 → 초록 → 파랑 → 흰색 순서로 바뀌는지 보세요. 색이 빠지면 선이나 모듈 문제예요.">
        <Btn icon="bulb" onClick={() => send("led_test", "LED를 켰어요")}>
          LED 켜 보기
        </Btn>
      </Step>

      <Step n={3} title="작은 화면 (Display)" hint="'농깨비 / 점검중'이 3초간 보이는지 확인하세요.">
        <Btn icon="scan" onClick={() => send("display_test", "화면에 글자를 띄웠어요")}>
          화면에 글자 띄우기
        </Btn>
      </Step>

      <Step
        n={4}
        title={`모터 역할 정하기 (인식된 모터 ${motorCount}개)`}
        hint="[살짝 움직이기]를 누르면 그 모터가 20°쯤 돌았다가 제자리로 돌아와요. 레고에서 어느 부분이 움직였는지 보고 역할을 고르세요."
        done={hw.vent_roles_ok}
      >
        {motorCount < 3 && (
          <p className="mb-2 rounded-xl bg-sun-100 px-3 py-2 text-[12.5px] leading-snug text-sun-700">
            모터가 {motorCount}개만 잡혀요. 환기창 A·B와 스프링클러, 3개여야 해요. 빠진 모터의 선과 전원(배터리)을
            확인해 보세요. 스프링클러 없이도 환기창은 쓸 수 있어요.
          </p>
        )}
        <ul className="space-y-2">
          {hw.motors.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-white px-3 py-2.5 ring-1 ring-line">
              <span className="min-w-[4.5rem] text-[13.5px] font-bold tabular-nums text-ink">모터 {m.label}</span>
              <Btn disabled={busy} onClick={() => send("jog", "모터를 살짝 움직였어요", { motor_id: m.id, delta: 20 })}>
                살짝 움직이기
              </Btn>
              <select
                value={draft[m.id] ?? ""}
                onChange={(e) => setDraft({ ...draft, [m.id]: e.target.value })}
                className="ml-auto min-w-[8.5rem] rounded-xl border border-line bg-card px-2.5 py-2 text-[13.5px] font-semibold text-ink"
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
        <div className="mt-2.5 flex flex-wrap items-center gap-2.5">
          <Btn tone="primary" disabled={busy || !dirty || !!problem || state.vent_open} onClick={saveRoles}>
            역할 저장
          </Btn>
          {dirty && problem && <span className="text-[12.5px] text-sun-700">{problem}</span>}
          {state.vent_open && <span className="text-[12.5px] text-sun-700">창문이 열려 있어서 바꿀 수 없어요. 먼저 닫아 주세요.</span>}
        </div>
      </Step>

      <Step
        n={5}
        title="환기창 방향 확인"
        hint="창문이 닫힌 상태에서 [열었다 닫기]를 누르세요. 두 모터가 함께 문을 '열리는 쪽'으로 움직였다가 돌아와야 해요. 문이 걸리거나 서로 반대로 가면 아래에서 바로잡으세요."
        done={hw.vent_ready}
      >
        {!hw.vent_roles_ok ? (
          <p className="text-[12.5px] text-sun-700">먼저 4번에서 환기창 모터 A·B를 정해 주세요.</p>
        ) : (
          <>
            <Btn icon="window" disabled={busy || state.vent_open} onClick={() => send("vent_test", "환기창을 열었다 닫을게요")}>
              열었다 닫기
            </Btn>
            <p className="mt-2 text-[12.5px] font-semibold text-ink-soft">어떻게 움직였나요?</p>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              <Btn tone="primary" disabled={busy || hw.vent_ready} onClick={() => send("vent_confirm", "방향을 확인했어요. 이제 창문을 쓸 수 있어요")}>
                잘 열렸어요
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={() => send("flip_sign", "모터 A 방향을 뒤집었어요", { which: "a" })}>
                A만 반대였어요
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={() => send("flip_sign", "모터 B 방향을 뒤집었어요", { which: "b" })}>
                B만 반대였어요
              </Btn>
              <Btn tone="warn" disabled={busy || state.vent_open} onClick={flipBoth}>
                둘 다 반대였어요
              </Btn>
            </div>
            <p className="mt-2 text-[12px] leading-snug text-ink-soft">
              {hw.vent_ready
                ? "방향이 확인됐어요. 이제 '창문 열기' 버튼과 자동 조치가 환기창을 움직여요."
                : "확인하기 전에는 '창문 열기' 버튼과 자동 조치가 환기창을 움직이지 않아요. (잘못된 방향으로 열어 레고가 걸리는 걸 막기 위해서예요)"}
            </p>
          </>
        )}
      </Step>
    </ol>
  );
}
