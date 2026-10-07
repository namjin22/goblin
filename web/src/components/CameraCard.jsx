import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { Placeholder, useLiveFrame } from "./LiveView";
import { ProbBars } from "./ProbBars";
import { CROP_COLOR, CROP_LABEL } from "../lib/format";

const SCANNING_MS = 3500; // "다시 보기"를 누른 뒤 보는 중 표시를 유지하는 시간

export function CameraCard({ state, onScan }) {
  const frame = useLiveFrame(state.has_camera_frame);
  const recognized = state.crop_key;
  const [scanning, setScanning] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);

  const scan = async () => {
    if (scanning) return;
    setScanning(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setScanning(false), SCANNING_MS);
    const ok = await onScan();
    if (!ok) {
      clearTimeout(timer.current);
      setScanning(false);
    }
  };

  return (
    <Card
      title="작물"
      icon="camera"
      right={
        <button
          onClick={scan}
          disabled={scanning}
          className="flex h-12 items-center gap-2 rounded-full border-2 border-line bg-paper px-5 text-[16px] font-bold text-ink transition hover:border-leaf-300 hover:bg-leaf-50 active:scale-95 disabled:text-leaf-700"
        >
          <Icon name="scan" size={20} className={scanning ? "animate-pulse" : ""} />
          {scanning ? "보는 중…" : "다시 보기"}
        </button>
      }
    >
      <div className="relative aspect-[16/9] overflow-hidden rounded-3xl bg-leaf-50 ring-1 ring-line">
        {frame ? (
          <img src={frame} alt="웹캠 화면" className="h-full w-full object-cover" draggable={false} />
        ) : (
          <Placeholder />
        )}

        {/* 인식하는 영역 (vision.py의 CROP_ROI와 같은 가운데 60%) */}
        <div className="pointer-events-none absolute inset-[20%] rounded-2xl border-[3px] border-dashed border-white/90 shadow-[0_0_0_9999px_rgba(20,30,15,0.22)]">
          <span
            className="absolute inset-x-2 h-0.5 rounded-full bg-gradient-to-r from-transparent via-leaf-300 to-transparent shadow-[0_0_10px_2px_rgba(155,201,122,0.9)]"
            style={{ animation: `scan-sweep ${scanning ? 0.9 : 3.6}s linear infinite` }}
          />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={recognized || "none"}
            initial={{ opacity: 0, y: 8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="absolute left-4 top-4 flex items-center gap-3 rounded-full bg-white/95 py-2.5 pl-4 pr-6 text-[22px] font-extrabold text-ink shadow"
          >
            <span
              className="h-4 w-4 rounded-full"
              style={{ background: recognized ? CROP_COLOR[recognized] : "#b9b09c" }}
            />
            {recognized ? CROP_LABEL[recognized] : "없음"}
          </motion.div>
        </AnimatePresence>

        {/* 진짜 카메라일 땐 말이 필요 없다. 가짜 화면일 때만 알려준다. */}
        {!state.camera_real && (
          <span className="absolute bottom-3 right-4 rounded-full bg-ink/70 px-3.5 py-1.5 text-[14px] font-bold text-white">
            모의 화면
          </span>
        )}
      </div>

      <div className="mt-4">
        <ProbBars probs={state.crop_probs} activeKey={recognized || "background"} />
      </div>
    </Card>
  );
}
