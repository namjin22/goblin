import { AnimatePresence, motion } from "framer-motion";
import { Icon } from "./Icons";

const STALE_AFTER_SEC = 8;

/** 화면이 "살아 있는 척"하지 않게, 문제가 있으면 맨 위에 가장 급한 하나만 띄운다 */
export function StatusBanner({ online, state, staleSec }) {
  let banner = null;

  if (!online) {
    banner = {
      tone: "bg-berry-700",
      icon: "wifioff",
      text: "서버와 연결이 끊겼어요. 다시 연결하는 중…",
    };
  } else if (state?.hw_error) {
    banner = {
      tone: "bg-berry-700",
      icon: "info",
      text: "장치 연결이 불안정해요. USB와 전원을 확인해 주세요",
    };
  } else if (state?.motor_fault) {
    banner = {
      tone: "bg-berry-700",
      icon: "info",
      text: `${state.motor_fault}. 전원과 연결을 확인해 주세요`,
    };
  } else if (state && staleSec > STALE_AFTER_SEC) {
    banner = {
      tone: "bg-sun-700",
      icon: "info",
      text: `장치 응답이 ${Math.round(staleSec)}초째 없어요`,
    };
  }

  return (
    <AnimatePresence>
      {banner && (
        <motion.div
          key={banner.text}
          role="alert"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div
            className={`flex items-center justify-center gap-3 px-5 py-3 text-center text-[17px] font-bold text-white ${banner.tone}`}
          >
            <Icon name={banner.icon} size={22} className="shrink-0" />
            {banner.text}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
