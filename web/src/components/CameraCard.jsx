import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { CROP_COLOR, CROP_LABEL, CROP_ORDER } from "../lib/format";

const FRAME_REFRESH_MS = 2000;
const SCANNING_MS = 3500; // "다시 인식"을 누른 뒤 인식 중 표시를 유지하는 시간

/** 깜빡임 없이 최신 스냅샷으로 바꿔 끼운다 (미리 받아두고 다 받으면 교체) */
function useLiveFrame(enabled) {
  const [src, setSrc] = useState(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let stop = false;
    let timer;

    const pull = () => {
      const url = `/camera/snapshot.jpg?t=${Date.now()}`;
      const img = new Image();
      img.onload = () => {
        if (stop) return;
        setSrc(url);
        timer = setTimeout(pull, FRAME_REFRESH_MS);
      };
      img.onerror = () => {
        if (!stop) timer = setTimeout(pull, FRAME_REFRESH_MS * 2);
      };
      img.src = url;
    };
    pull();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [enabled]);

  return src;
}

function Placeholder() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-leaf-50 to-leaf-100 text-leaf-600">
      <Icon name="camera" size={40} strokeWidth={1.4} />
      <p className="text-[13px] font-medium text-ink-soft">카메라 화면을 기다리는 중이에요</p>
    </div>
  );
}

function ProbBars({ probs, activeKey }) {
  if (!probs) {
    return (
      <p className="rounded-2xl bg-paper px-4 py-3 text-[13px] leading-relaxed text-ink-soft">
        지금은 확률 정보가 없어요. (분류 모델이 없거나 색깔 규칙으로 보조 판단하는 중)
      </p>
    );
  }
  const keys = [...CROP_ORDER, "background"].filter((k) => k in probs);
  return (
    <ul className="space-y-2" aria-label="작물별 인식 확률">
      {keys.map((k) => {
        const p = probs[k] ?? 0;
        const active = k === activeKey;
        return (
          <li key={k} className="grid grid-cols-[4.5rem_1fr_3rem] items-center gap-3">
            <span
              className={`text-[14px] ${active ? "font-bold text-ink" : "font-medium text-ink-soft"}`}
            >
              {CROP_LABEL[k]}
            </span>
            <div className="h-3 overflow-hidden rounded-full bg-paper">
              <motion.div
                className="h-full rounded-full"
                style={{ background: CROP_COLOR[k], opacity: active ? 1 : 0.5 }}
                initial={false}
                animate={{ width: `${Math.max(p * 100, 1.5)}%` }}
                transition={{ type: "spring", stiffness: 140, damping: 22 }}
              />
            </div>
            <span
              className={`text-right text-[13px] tabular-nums ${
                active ? "font-bold text-ink" : "text-ink-soft"
              }`}
            >
              {Math.round(p * 100)}%
            </span>
          </li>
        );
      })}
    </ul>
  );
}

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
      title="작물 인식"
      icon="camera"
      right={
        <button
          onClick={scan}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-full border border-line bg-paper px-3 py-1.5 text-[12.5px] font-semibold text-ink-soft transition hover:border-leaf-300 hover:text-leaf-700 active:scale-95 disabled:text-leaf-700"
        >
          <Icon name="scan" size={14} className={scanning ? "animate-pulse" : ""} />
          {scanning ? "인식 중…" : "다시 인식"}
        </button>
      }
    >
      <div className="relative aspect-[16/10] overflow-hidden rounded-2xl bg-leaf-50 ring-1 ring-line">
        {frame ? (
          <img src={frame} alt="웹캠 화면" className="h-full w-full object-cover" draggable={false} />
        ) : (
          <Placeholder />
        )}

        {/* 인식하는 영역 (vision.py의 CROP_ROI와 같은 가운데 60%) */}
        <div className="pointer-events-none absolute inset-[20%] rounded-xl border-2 border-dashed border-white/85 shadow-[0_0_0_9999px_rgba(20,30,15,0.22)]">
          <span
            className="absolute inset-x-2 h-0.5 rounded-full bg-gradient-to-r from-transparent via-leaf-300 to-transparent shadow-[0_0_10px_2px_rgba(155,201,122,0.9)]"
            style={{ animation: `scan-sweep ${scanning ? 0.9 : 3.6}s linear infinite` }}
          />
          {!recognized && (
            <span className="absolute inset-x-0 bottom-2 mx-auto w-fit max-w-[92%] rounded-full bg-white/90 px-3 py-1 text-center text-[12.5px] font-semibold text-ink">
              여기에 작물 브릭을 놓아 보세요
            </span>
          )}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={recognized || "none"}
            initial={{ opacity: 0, y: 8, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-white/95 py-1.5 pl-2.5 pr-4 text-[14px] font-bold text-ink shadow"
          >
            <span
              className="h-3 w-3 rounded-full"
              style={{ background: recognized ? CROP_COLOR[recognized] : "#b9b09c" }}
            />
            {recognized ? CROP_LABEL[recognized] : "찾는 중…"}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="mt-4">
        <ProbBars probs={state.crop_probs} activeKey={recognized || "background"} />
      </div>
    </Card>
  );
}
