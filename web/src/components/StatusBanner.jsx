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
      text: "서버와 연결이 끊겼어요. 지금 보이는 값은 마지막으로 받은 값이에요. 다시 연결하는 중…",
    };
  } else if (state?.hw_error) {
    banner = {
      tone: "bg-berry-700",
      icon: "info",
      text: `장치와 통신이 불안정해요. USB와 전원을 확인해 주세요. (${state.hw_error})`,
    };
  } else if (state && staleSec > STALE_AFTER_SEC) {
    banner = {
      tone: "bg-sun-700",
      icon: "info",
      text: `장치 응답이 ${Math.round(staleSec)}초째 없어요. 화면의 값이 최신이 아닐 수 있어요.`,
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
            className={`flex items-center justify-center gap-2 px-4 py-2 text-center text-[14px] font-semibold text-white ${banner.tone}`}
          >
            <Icon name={banner.icon} size={17} className="shrink-0" />
            {banner.text}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
