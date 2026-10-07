import { useState } from "react";
import { Modal } from "./Overlay";
import { QrCode } from "./QrCode";

/** 관람객이 자기 폰으로 같은 화면을 열고 조작해 볼 수 있게 QR을 보여준다 */
export function PhoneModal({ open, onClose, info }) {
  const [copied, setCopied] = useState(false);
  const url = info?.lan_url;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* 클립보드가 막힌 환경에서는 조용히 넘어간다 (주소는 화면에 보인다) */
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="내 폰으로 열기">
      {url ? (
        <div className="flex flex-col items-center gap-4">
          <QrCode value={url} size={280} />
          <p className="text-center text-[20px] font-bold text-ink">폰 카메라로 비추세요</p>
          <button
            onClick={copy}
            className="rounded-full bg-paper px-6 py-3 text-[16px] font-semibold tabular-nums text-ink-soft transition hover:text-ink"
          >
            {copied ? "복사했어요" : url}
          </button>
          <p className="text-center text-[16px] text-ink-soft">같은 와이파이에서</p>
        </div>
      ) : (
        <p className="py-6 text-center text-[18px] leading-relaxed text-ink-soft">
          네트워크 주소를 찾지 못했어요.
          <br />
          와이파이를 확인해 주세요.
        </p>
      )}
    </Modal>
  );
}
