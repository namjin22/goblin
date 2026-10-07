import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Icon } from "./Icons";
import { CROP_COLOR, josa } from "../lib/format";

/**
 * 작물이 바뀌는 순간을 크게 보여준다 - 이 프로젝트의 핵심 장면이다.
 * "카메라가 알아봤고, 기준은 알아서 정해졌다."
 */
export function RecognitionToast({ state }) {
  const prev = useRef(undefined); // undefined = 아직 첫 상태를 못 받음 (첫 로드에는 띄우지 않는다)
  const [event, setEvent] = useState(null);

  const cropKey = state?.crop_key ?? null;
  const cropName = state?.crop_name;
  const ventTemp = state?.thresholds?.vent_temp;

  useEffect(() => {
    if (!state) return undefined;
    if (prev.current === undefined) {
      prev.current = cropKey;
      return undefined;
    }
    if (prev.current === cropKey) return undefined;
    prev.current = cropKey;
    setEvent({ id: Date.now(), cropKey, cropName, ventTemp });
    const t = setTimeout(() => setEvent(null), 4500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cropKey, !!state]);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-20 z-30 flex justify-center px-4">
      <AnimatePresence>
        {event && (
          <motion.div
            key={event.id}
            role="status"
            initial={{ opacity: 0, y: -24, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ type: "spring", stiffness: 380, damping: 26 }}
            className="flex items-center gap-4 rounded-3xl border border-line bg-card px-6 py-4 shadow-[0_18px_50px_-12px_rgba(36,48,31,0.35)]"
          >
            {event.cropKey ? (
              <>
                <span
                  className="flex h-12 w-12 items-center justify-center rounded-2xl text-white"
                  style={{ background: CROP_COLOR[event.cropKey] }}
                >
                  <Icon name="leaf" size={26} strokeWidth={2} />
                </span>
                <div>
                  <p className="text-[28px] font-extrabold text-ink">
                    {josa(event.cropName, "을", "를")} 알아봤어요
                  </p>
                  <p className="text-[18px] text-ink-soft">
                    창문은 <b className="text-ink">{event.ventTemp}°C</b>부터 열어요
                  </p>
                </div>
              </>
            ) : (
              <>
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-paper text-ink-soft">
                  <Icon name="camera" size={26} />
                </span>
                <p className="text-[24px] font-bold text-ink">작물이 안 보여요</p>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
