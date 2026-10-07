import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Icon } from "./Icons";

/** Esc로 닫고, 열릴 때 패널로 포커스를 옮겨서 키보드 사용자도 길을 잃지 않게 한다 */
function useOverlayBehavior(open, onClose) {
  const panelRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const previously = document.activeElement;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      previously?.focus?.();
    };
  }, [open, onClose]);
  return panelRef;
}

function CloseButton({ onClose }) {
  return (
    <button
      onClick={onClose}
      className="flex h-14 w-14 items-center justify-center rounded-full bg-paper text-ink-soft transition hover:text-ink active:scale-95"
      aria-label="닫기"
    >
      <Icon name="close" size={26} />
    </button>
  );
}

function Backdrop({ onClose }) {
  return (
    <motion.div
      className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-[2px]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    />
  );
}

/** 오른쪽에서 밀려 나오는 서랍 */
export function Drawer({ open, onClose, title, subtitle, children, width = "max-w-[460px]" }) {
  const panelRef = useOverlayBehavior(open, onClose);
  return (
    <AnimatePresence>
      {open && (
        <>
          <Backdrop onClose={onClose} />
          <motion.aside
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className={`fixed inset-y-0 right-0 z-50 flex w-full ${width} flex-col bg-card shadow-2xl outline-none`}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 36 }}
          >
            <header className="flex items-center justify-between gap-4 border-b border-line px-8 py-6">
              <div>
                <h2 className="text-[30px] font-extrabold text-ink">{title}</h2>
                {subtitle && <p className="mt-1 text-[13.5px] text-ink-soft">{subtitle}</p>}
              </div>
              <CloseButton onClose={onClose} />
            </header>
            <div className="flex-1 overflow-y-auto px-8 py-7">{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

/** 가운데에 뜨는 작은 창 */
export function Modal({ open, onClose, title, children }) {
  const panelRef = useOverlayBehavior(open, onClose);
  return (
    <AnimatePresence>
      {open && (
        <>
          <Backdrop onClose={onClose} />
          <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              ref={panelRef}
              tabIndex={-1}
              role="dialog"
              aria-modal="true"
              aria-label={title}
              className="pointer-events-auto w-full max-w-[480px] rounded-[32px] bg-card p-8 shadow-2xl outline-none"
              initial={{ opacity: 0, scale: 0.92, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            >
              <div className="mb-4 flex items-start justify-between gap-4">
                <h2 className="text-[26px] font-extrabold text-ink">{title}</h2>
                <CloseButton onClose={onClose} />
              </div>
              {children}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
