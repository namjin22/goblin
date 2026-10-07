import { useEffect, useState } from "react";
import { Icon } from "./Icons";

function Logo() {
  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-leaf-600 text-white shadow-[0_6px_14px_-6px_rgba(65,116,42,0.7)]">
      <Icon name="leaf" size={30} strokeWidth={2} />
    </div>
  );
}

function useFullscreen() {
  const [full, setFull] = useState(!!document.fullscreenElement);
  useEffect(() => {
    const on = () => setFull(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", on);
    return () => document.removeEventListener("fullscreenchange", on);
  }, []);
  const toggle = () => {
    if (document.fullscreenElement) document.exitFullscreen?.();
    else document.documentElement.requestFullscreen?.().catch(() => {});
  };
  return [full, toggle];
}

function Dot({ show }) {
  if (!show) return null;
  return (
    <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
      <span className="absolute inline-flex h-full w-full animate-[pulse-ring_1.6s_infinite] rounded-full bg-sun-500" />
      <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-sun-500 ring-2 ring-paper" />
    </span>
  );
}

/** 글자가 있는 큰 버튼 (자주 쓰는 것) */
function PillButton({ onClick, icon, children, dot, label }) {
  return (
    <button
      onClick={onClick}
      aria-label={label || undefined}
      className="relative flex h-14 items-center gap-2.5 rounded-full border-2 border-line bg-card px-6 text-[17px] font-bold text-ink transition hover:border-leaf-300 hover:bg-leaf-50 active:scale-95"
    >
      <Icon name={icon} size={22} className="text-leaf-600" />
      {children}
      <Dot show={dot} />
    </button>
  );
}

/** 아이콘만 있는 큰 동그라미 버튼 (가끔 쓰는 것) */
function RoundButton({ onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-line bg-card text-ink-soft transition hover:border-leaf-300 hover:bg-leaf-50 hover:text-leaf-700 active:scale-95"
    >
      <Icon name={icon} size={24} />
    </button>
  );
}

export function Header({
  online, mock, needsAttention, modelWarn,
  onShowLimits, onShowPhone, onShowOperator, onShowStudio,
}) {
  const [full, toggleFull] = useFullscreen();

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 px-6 pt-5 lg:px-10">
      <div className="flex items-center gap-4">
        <Logo />
        <h1 className="text-[34px] font-extrabold leading-none tracking-tight text-ink">농깨비</h1>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {mock && (
          <span className="rounded-full bg-sun-100 px-4 py-2.5 text-[15px] font-bold text-sun-700">
            모의 실행
          </span>
        )}
        <span
          className={`flex h-14 items-center gap-2.5 rounded-full px-5 text-[16px] font-bold ${
            online ? "bg-leaf-100 text-leaf-800" : "bg-berry-100 text-berry-700"
          }`}
        >
          <span className="relative flex h-3 w-3">
            {online && (
              <span className="absolute inline-flex h-full w-full animate-[pulse-ring_1.6s_infinite] rounded-full bg-leaf-500" />
            )}
            <span className={`relative inline-flex h-3 w-3 rounded-full ${online ? "bg-leaf-500" : "bg-berry-500"}`} />
          </span>
          {online ? "연결됨" : "끊김"}
        </span>

        <PillButton
          icon="sparkle"
          onClick={onShowStudio}
          dot={modelWarn}
          label={modelWarn ? "AI 학습 (학습이 필요해요)" : "AI 학습"}
        >
          AI 학습
        </PillButton>
        <PillButton
          icon="gear"
          onClick={onShowOperator}
          dot={needsAttention}
          label={needsAttention ? "운영자 (확인이 필요해요)" : "운영자"}
        >
          운영자
        </PillButton>

        <RoundButton icon="phone" onClick={onShowPhone} label="내 폰으로 열기" />
        <RoundButton icon="info" onClick={onShowLimits} label="한계 보기" />
        <RoundButton icon="expand" onClick={toggleFull} label={full ? "전체화면 끝내기" : "전체화면"} />
      </div>
    </header>
  );
}
