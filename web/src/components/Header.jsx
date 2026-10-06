import { useEffect, useState } from "react";
import { Icon } from "./Icons";

function Logo() {
  return (
    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-leaf-600 text-white shadow-[0_6px_14px_-6px_rgba(65,116,42,0.7)]">
      <Icon name="leaf" size={24} strokeWidth={2} />
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

function PillButton({ onClick, icon, children, dot, label }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className="relative flex items-center gap-1.5 rounded-full border border-line bg-card px-3.5 py-2 text-[13px] font-semibold text-ink-soft transition hover:border-leaf-300 hover:text-leaf-700 active:scale-95"
    >
      <Icon name={icon} size={15} />
      <span className="hidden sm:inline">{children}</span>
      {dot && (
        <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-[pulse-ring_1.6s_infinite] rounded-full bg-sun-500" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-sun-500 ring-2 ring-paper" />
        </span>
      )}
    </button>
  );
}

export function Header({ online, mock, needsAttention, onShowLimits, onShowPhone, onShowOperator }) {
  const [full, toggleFull] = useFullscreen();

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 px-4 pt-4 lg:px-8 lg:pt-5">
      <div className="flex items-center gap-3.5">
        <Logo />
        <div>
          <h1 className="text-[26px] font-extrabold leading-none tracking-tight text-ink">농깨비</h1>
          <p className="mt-1 text-[13px] font-medium text-ink-soft">
            묻지 않고 알아서 돌보는 스마트팜
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {mock && (
          <span
            className="rounded-full bg-sun-100 px-3 py-1.5 text-[12px] font-bold text-sun-700"
            title="실제 장치 없이 가짜 하드웨어로 실행 중이에요"
          >
            모의 실행
          </span>
        )}
        <span
          className={`flex items-center gap-2 rounded-full px-3 py-2 text-[12.5px] font-bold ${
            online ? "bg-leaf-100 text-leaf-800" : "bg-berry-100 text-berry-700"
          }`}
        >
          <span className="relative flex h-2.5 w-2.5">
            {online && (
              <span className="absolute inline-flex h-full w-full animate-[pulse-ring_1.6s_infinite] rounded-full bg-leaf-500" />
            )}
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${online ? "bg-leaf-500" : "bg-berry-500"}`}
            />
          </span>
          {online ? "연결됨" : "연결 끊김"}
        </span>
        <PillButton icon="phone" onClick={onShowPhone} label="내 폰으로 열기">
          내 폰으로 열기
        </PillButton>
        <PillButton icon="info" onClick={onShowLimits} label="한계 보기">
          한계 보기
        </PillButton>
        <PillButton
          icon="gear"
          onClick={onShowOperator}
          dot={needsAttention}
          label={needsAttention ? "운영자 (확인이 필요해요)" : "운영자"}
        >
          운영자
        </PillButton>
        <button
          onClick={toggleFull}
          className="rounded-full border border-line bg-card p-2 text-ink-soft transition hover:border-leaf-300 hover:text-leaf-700 active:scale-95"
          aria-label={full ? "전체화면 끝내기" : "전체화면"}
          title={full ? "전체화면 끝내기" : "전체화면"}
        >
          <Icon name="expand" size={17} />
        </button>
      </div>
    </header>
  );
}
