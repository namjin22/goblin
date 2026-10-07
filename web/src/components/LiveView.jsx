import { useEffect, useState } from "react";
import { Icon } from "./Icons";

/**
 * 깜빡임 없이 최신 스냅샷으로 바꿔 끼운다 (미리 받아두고 다 받으면 교체).
 * 상시 연결(MJPEG)은 쓰지 않는다 - 모바일 동시연결 한도를 점유해 대시보드가 멈춘 적이 있다.
 */
export function useLiveFrame(enabled, refreshMs = 2000) {
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
        timer = setTimeout(pull, refreshMs);
      };
      img.onerror = () => {
        if (!stop) timer = setTimeout(pull, refreshMs * 2);
      };
      img.src = url;
    };
    pull();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [enabled, refreshMs]);

  return src;
}

export function Placeholder() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-leaf-50 to-leaf-100 text-leaf-600">
      <Icon name="camera" size={40} strokeWidth={1.4} />
      <p className="text-[13px] font-medium text-ink-soft">카메라 화면을 기다리는 중이에요</p>
    </div>
  );
}
