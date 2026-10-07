import { useCallback, useEffect, useRef, useState } from "react";

// [중요] 폴링만 쓴다. MJPEG/SSE/WebSocket처럼 연결을 계속 열어두면 모바일
// 브라우저의 동시연결 한도를 점유해서 /api/state가 막힌 적이 있다(백엔드 server.py 참고).
const STATE_MS = 1000;
const HISTORY_MS = 3000;
const OFFLINE_AFTER = 3; // 연속으로 이만큼 실패하면 "연결 끊김"으로 본다

async function getJson(url, signal) {
  const res = await fetch(url, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

/** 서버 상태를 계속 따라가고, 명령을 보내는 훅. 하드웨어는 서버가 만진다. */
export function useGoblin() {
  const [state, setState] = useState(null);
  const [history, setHistory] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [online, setOnline] = useState(true);
  const [toast, setToast] = useState(null);
  const [info, setInfo] = useState(null); // {lan_url} 폰 접속용 주소
  const failures = useRef(0);
  const toastTimer = useRef(null);

  const showToast = useCallback((text, tone = "info") => {
    setToast({ text, tone, id: Date.now() });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3200);
  }, []);

  // 상태 폴링 - setInterval이 아니라 "끝나면 다음 예약"이라 요청이 쌓이지 않는다
  useEffect(() => {
    let stop = false;
    let timer;
    const ctrl = new AbortController();

    const loop = async () => {
      try {
        const data = await getJson("/api/state", ctrl.signal);
        if (stop) return;
        failures.current = 0;
        setOnline(true);
        setState(data);
      } catch {
        if (stop) return;
        failures.current += 1;
        if (failures.current >= OFFLINE_AFTER) setOnline(false);
      }
      if (!stop) timer = setTimeout(loop, STATE_MS);
    };
    loop();
    return () => {
      stop = true;
      clearTimeout(timer);
      ctrl.abort();
    };
  }, []);

  useEffect(() => {
    let stop = false;
    let timer;
    const loop = async () => {
      try {
        const data = await getJson("/api/history?limit=30");
        if (!stop) setHistory(data.items);
      } catch {
        /* 상태 폴링이 연결 끊김을 알려주므로 여기선 조용히 */
      }
      if (!stop) timer = setTimeout(loop, HISTORY_MS);
    };
    loop();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    getJson("/api/profiles")
      .then((d) => setProfiles(d.items))
      .catch(() => {});
    getJson("/api/info")
      .then(setInfo)
      .catch(() => {});
  }, []);

  // 메인 루프가 멈췄는지: 서버가 응답은 하는데 상태가 오래 안 갱신되면(웹캠/모듈이 멈춘 경우)
  // 화면의 숫자가 "살아 있는 것처럼" 보여서 위험하다. 브라우저 시계와 무관하게 서버 시각끼리 뺀다.
  const staleSec = state ? Math.max(0, state.server_time - state.updated_at) : 0;

  /** 명령을 서버로 보낸다. 서버가 큐에 넣고, 메인 루프가 하드웨어를 움직인다. */
  const send = useCallback(
    async (command, okText, args) => {
      try {
        const res = await fetch("/api/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command, args }),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          if (okText) showToast(okText, "ok");
          return true;
        }
        // 409(동작 중)는 에러가 아니라 안내다
        showToast(data.error || "명령을 보내지 못했어요", res.status === 409 ? "info" : "error");
        return false;
      } catch {
        showToast("서버와 연결이 끊겨서 명령을 보내지 못했어요", "error");
        return false;
      }
    },
    [showToast]
  );

  return { state, history, profiles, online, send, toast, info, staleSec };
}
