import { Icon } from "./Icons";

/** 모든 패널이 공유하는 카드 틀. 같은 줄의 카드는 높이를 맞춘다(h-full). */
export function Card({ title, icon, right, children, className = "" }) {
  return (
    <section
      className={`flex h-full flex-col rounded-3xl border border-line bg-card shadow-card ${className}`}
    >
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 px-5 pt-4 pb-1">
          <h2 className="flex items-center gap-2 text-[13px] font-semibold tracking-wide text-ink-soft">
            {icon && <Icon name={icon} size={16} className="text-leaf-500" />}
            {title}
          </h2>
          {right}
        </header>
      )}
      <div className="flex-1 px-5 pb-5 pt-2">{children}</div>
    </section>
  );
}
