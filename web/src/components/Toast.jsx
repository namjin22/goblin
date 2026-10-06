import { AnimatePresence, motion } from "framer-motion";
import { Icon } from "./Icons";

const TONE = {
  ok: "bg-leaf-800 text-white",
  info: "bg-ink text-white",
  error: "bg-berry-700 text-white",
};

export function Toast({ toast }) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ type: "spring", stiffness: 420, damping: 30 }}
            className={`flex items-center gap-2 rounded-full px-5 py-3 text-[15px] font-medium shadow-lg ${
              TONE[toast.tone] || TONE.info
            }`}
          >
            <Icon name={toast.tone === "ok" ? "check" : "info"} size={18} />
            {toast.text}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
