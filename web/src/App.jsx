import { useState } from "react";
import { MotionConfig, motion } from "framer-motion";
import { useGoblin } from "./lib/useGoblin";
import { Header } from "./components/Header";
import { StatusBanner } from "./components/StatusBanner";
import { CameraCard } from "./components/CameraCard";
import { DecisionCard } from "./components/DecisionCard";
import { DevicesCard } from "./components/DevicesCard";
import { ControlsCard } from "./components/ControlsCard";
import { Timeline } from "./components/Timeline";
import { LimitsDrawer } from "./components/LimitsDrawer";
import { OperatorDrawer } from "./components/OperatorDrawer";
import { PhoneModal } from "./components/PhoneModal";
import { RecognitionToast } from "./components/RecognitionToast";
import { Toast } from "./components/Toast";
import { Icon } from "./components/Icons";

function Loading({ online }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
      <motion.div
        animate={{ rotate: [0, -8, 8, 0], y: [0, -4, 0] }}
        transition={{ duration: 2.2, repeat: Infinity }}
        className="flex h-16 w-16 items-center justify-center rounded-3xl bg-leaf-600 text-white"
      >
        <Icon name="leaf" size={34} strokeWidth={2} />
      </motion.div>
      <p className="text-[17px] font-bold text-ink">
        {online ? "농깨비를 깨우는 중이에요…" : "서버에 연결할 수 없어요"}
      </p>
      {!online && (
        <p className="max-w-xs text-[13.5px] leading-relaxed text-ink-soft">
          노트북에서 <b>python main.py</b>가 실행 중인지, 같은 네트워크에 연결돼 있는지 확인해 주세요.
        </p>
      )}
    </div>
  );
}

export default function App() {
  const { state, history, profiles, online, send, toast, info, staleSec } = useGoblin();
  const [panel, setPanel] = useState(null); // "limits" | "operator" | "phone" | null
  const close = () => setPanel(null);

  return (
    // 움직임 줄이기를 켠 기기에서는 애니메이션이 자동으로 줄어든다
    <MotionConfig reducedMotion="user">
      <div className="flex min-h-full flex-col">
        <StatusBanner online={online} state={state} staleSec={staleSec} />
        <Header
          online={online}
          mock={state?.mock}
          needsAttention={!!state?.vent_assumed}
          onShowLimits={() => setPanel("limits")}
          onShowPhone={() => setPanel("phone")}
          onShowOperator={() => setPanel("operator")}
        />

        {!state ? (
          <div className="flex-1">
            <Loading online={online} />
          </div>
        ) : (
          <main className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-12 lg:gap-5 lg:px-8 lg:pb-6">
            {/* 윗줄: 보는 것(인식) → 판단 */}
            <div className="lg:col-span-4">
              <CameraCard state={state} onScan={() => send("scan", "작물을 다시 확인할게요")} />
            </div>
            <div className="lg:col-span-8">
              <DecisionCard state={state} profiles={profiles} />
            </div>

            {/* 아랫줄: 그 결과 움직이는 장치 → 직접 조작 → 기록 */}
            <div className="lg:col-span-12 xl:col-span-6">
              <DevicesCard state={state} />
            </div>
            <div className="lg:col-span-6 xl:col-span-3">
              <ControlsCard state={state} send={send} />
            </div>
            <div className="lg:col-span-6 xl:col-span-3">
              <Timeline history={history} />
            </div>
          </main>
        )}

        <LimitsDrawer open={panel === "limits"} onClose={close} />
        <OperatorDrawer open={panel === "operator"} onClose={close} state={state} send={send} staleSec={staleSec} />
        <PhoneModal open={panel === "phone"} onClose={close} info={info} />
        <RecognitionToast state={state} />
        <Toast toast={toast} />
      </div>
    </MotionConfig>
  );
}
