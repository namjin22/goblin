// 외부 아이콘 라이브러리 없이 쓰는 24px 선 아이콘 모음 (stroke 기반, 색은 currentColor)
const PATHS = {
  leaf: (
    <>
      <path d="M5 19c0-8.5 5-14 14-14 0 9-5.5 14-14 14z" />
      <path d="M5 19c3-4.5 6-7.5 10.5-10" />
    </>
  ),
  window: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="2.5" />
      <path d="M12 3.5v17M3.5 12h17" />
    </>
  ),
  drop: <path d="M12 3c3.2 4 6 7 6 10.5a6 6 0 0 1-12 0C6 10 8.8 7 12 3z" />,
  bulb: (
    <>
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8h3l1.8-2.8h6.4L17 8h3v11H4z" />
      <circle cx="12" cy="13.2" r="3.2" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16v-5a6 6 0 0 1 12 0v5l1.8 2H4.2z" />
      <path d="M10 21h4" />
    </>
  ),
  auto: (
    <>
      <path d="M12 3v3M8.5 3h7" />
      <rect x="4.5" y="7" width="15" height="11" rx="3" />
      <circle cx="9.3" cy="12.5" r="0.9" fill="currentColor" />
      <circle cx="14.7" cy="12.5" r="0.9" fill="currentColor" />
    </>
  ),
  scan: (
    <>
      <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
      <path d="M4 12h16" />
    </>
  ),
  thermo: <path d="M10 14.2V5a2 2 0 1 1 4 0v9.2a4 4 0 1 1-4 0z" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 7.8h.01" />
    </>
  ),
  expand: <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />,
  wifioff: (
    <>
      <path d="M3 3l18 18" />
      <path d="M8.5 16.4a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 3.4-2.2M19 12.9a10 10 0 0 0-4.5-2.6M2 9.4a15 15 0 0 1 4-2.7M22 9.4A15 15 0 0 0 12 5" />
      <path d="M12 20h.01" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  sprinkler: (
    <>
      <path d="M12 21v-8" />
      <path d="M8 13h8l-1.5-4h-5z" />
      <path d="M6 5.5l1.2 1.6M12 3.5v2.4M18 5.5l-1.2 1.6" />
    </>
  ),
  phone: (
    <>
      <rect x="7" y="2.5" width="10" height="19" rx="2.5" />
      <path d="M11 18.5h2" />
    </>
  ),
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6" />
    </>
  ),
  sparkle: (
    <>
      <path d="M11 3l1.9 5.4L18.5 10l-5.6 1.7L11 17l-1.9-5.3L3.5 10l5.6-1.6z" />
      <path d="M19 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
    </>
  ),
  sound: (
    <>
      <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" />
      <path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11" />
    </>
  ),
};

export function Icon({ name, size = 20, className = "", strokeWidth = 1.8 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
