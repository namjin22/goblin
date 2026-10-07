import { Icon } from "./Icons";

/** 모든 패널이 공유하는 카드 틀. 같은 줄의 카드는 높이를 맞춘다(h-full). */
export function Card({ title, icon, right, children, className = "" }) {
  return (
    <section
      className={`flex h-full flex-col rounded-[28px] border border-line bg-card shadow-card ${className}`}
    >
      {(title || right) && (
        <header className="flex min-h-[3.5rem] items-center justify-between gap-4 px-6 pt-5">
          <h2 className="flex items-center gap-2.5 text-[17px] font-bold text-ink-soft">
            {icon && <Icon name={icon} size={20} className="text-leaf-500" />}
            {title}
          </h2>
          {right}
        </header>
      )}
      <div className="flex-1 px-6 pb-6 pt-3">{children}</div>
    </section>
  );
}
