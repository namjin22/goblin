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
    <Modal open={open} onClose={onClose} title="내 폰으로 열어 보세요">
      {url ? (
        <div className="flex flex-col items-center gap-4">
          <QrCode value={url} size={236} />
          <p className="text-center text-[14px] leading-relaxed text-ink-soft">
            폰 카메라로 비추면 이 화면이 그대로 열려요.
            <br />
            <b className="text-ink">창문 열기, 물 주기도 폰에서 눌러볼 수 있어요.</b>
          </p>
          <button
            onClick={copy}
            className="rounded-full bg-paper px-4 py-2 text-[13px] font-semibold tabular-nums text-ink-soft transition hover:text-ink"
          >
            {copied ? "복사했어요" : url}
          </button>
          <p className="text-center text-[12px] text-ink-soft">
            같은 와이파이에 연결돼 있어야 해요.
          </p>
        </div>
      ) : (
        <p className="py-6 text-center text-[14px] leading-relaxed text-ink-soft">
          노트북의 네트워크 주소를 찾지 못했어요.
          <br />
          와이파이나 핫스팟에 연결됐는지 확인해 주세요.
        </p>
      )}
    </Modal>
  );
}
