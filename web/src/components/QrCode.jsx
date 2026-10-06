import { useMemo } from "react";
import qrcode from "qrcode-generator";

/** 외부 서비스 없이 브라우저에서 바로 그리는 QR 코드 (인터넷이 없어도 된다) */
export function QrCode({ value, size = 220 }) {
  const modules = useMemo(() => {
    const qr = qrcode(0, "M"); // 0 = 내용에 맞춰 크기 자동, M = 오류 정정 중간
    qr.addData(value);
    qr.make();
    const n = qr.getModuleCount();
    const cells = [];
    for (let r = 0; r < n; r += 1) {
      for (let c = 0; c < n; c += 1) {
        if (qr.isDark(r, c)) cells.push([c, r]);
      }
    }
    return { n, cells };
  }, [value]);

  const quiet = 2; // 스캔이 잘 되도록 둘레에 여백(모듈 2칸)
  const total = modules.n + quiet * 2;
  return (
    <svg
      viewBox={`0 0 ${total} ${total}`}
      width={size}
      height={size}
      role="img"
      aria-label={`접속 주소 QR 코드: ${value}`}
      shapeRendering="crispEdges"
      className="rounded-2xl bg-white"
    >
      {modules.cells.map(([c, r]) => (
        <rect key={`${c}-${r}`} x={c + quiet} y={r + quiet} width="1" height="1" fill="#24301f" />
      ))}
    </svg>
  );
}
