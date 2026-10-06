import { motion } from "framer-motion";
import { Card } from "./Card";
import { Icon } from "./Icons";
import { LEVEL_STYLE, pct } from "../lib/format";

const T_MIN = 14;
const T_MAX = 38;

/** 같은 온도의 작물끼리 묶는다: [{temp: 20, crops:[상추,당근]}, {temp: 28, ...}] */
function groupByVentTemp(profiles) {
  const map = new Map();
  profiles.forEach((p) => {
    const t = p.thresholds.vent_temp;
    if (!map.has(t)) map.set(t, []);
    map.get(t).push(p);
  });
  return [...map.entries()].map(([temp, crops]) => ({ temp, crops })).sort((a, b) => a.temp - b.temp);
}

/** 작물마다 다른 "창문 여는 온도"를 한 눈금자에 놓고, 지금 온도를 바늘로 보여준다 */
function ThermoScale({ temp, profiles, activeKey, th }) {
  const groups = groupByVentTemp(profiles);
  const nowPos = temp == null ? null : pct(temp, T_MIN, T_MAX);
  const heatPos = pct(th.heat_danger_temp, T_MIN, T_MAX);
  const ventPos = pct(th.vent_temp, T_MIN, T_MAX);
  const alertPos = pct(th.vent_alert_temp, T_MIN, T_MAX);

  return (
    <div className="select-none">
      {/* 작물별 기준선 이름표 */}
      <div className="relative h-11">
        {groups.map(({ temp: t, crops }) => {
          const isActive = crops.some((c) => c.key === activeKey);
          const left = pct(t, T_MIN, T_MAX);
          return (
            <motion.div
              key={t}
              className="absolute bottom-0 flex -translate-x-1/2 flex-col items-center"
              style={{ left: `${left}%` }}
              animate={{ opacity: isActive || !activeKey ? 1 : 0.4, scale: isActive ? 1.04 : 1 }}
              transition={{ duration: 0.3 }}
            >
              <span
                className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[12.5px] font-bold ${
                  isActive ? "bg-ink text-white" : "bg-paper text-ink-soft"
                }`}
              >
                {crops.map((c) => c.name).join("·")} {t}°
              </span>
              <span className={`h-2 w-0.5 ${isActive ? "bg-ink" : "bg-line"}`} />
            </motion.div>
          );
        })}
      </div>

      {/* 눈금자 */}
      <div className="relative h-4 rounded-full bg-leaf-100">
        {/* 지금 작물의 환기 구간: 기준~기준+3 = 주의, 그 이상 = 조치 */}
        <div
          className="absolute inset-y-0 bg-sun-100"
          style={{ left: `${ventPos}%`, width: `${alertPos - ventPos}%` }}
        />
        <div
          className="absolute inset-y-0 rounded-r-full bg-berry-100"
          style={{ left: `${alertPos}%`, right: 0 }}
        />
        {/* 온열질환 경고선 */}
        <div
          className="absolute -inset-y-1.5 w-0.5 bg-berry-500"
          style={{ left: `${heatPos}%` }}
        />
        {/* 지금 온도 바늘 */}
        {nowPos != null && (
          <motion.div
            className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
            initial={false}
            animate={{ left: `${nowPos}%` }}
            transition={{ type: "spring", stiffness: 90, damping: 18 }}
          >
            <span className="block h-7 w-7 rounded-full border-[5px] border-white bg-leaf-600 shadow-[0_2px_8px_rgba(0,0,0,0.3)]" />
          </motion.div>
        )}
      </div>

      {/* 눈금 + 경고선 이름 */}
      <div className="relative mt-2 h-5 text-[11.5px] tabular-nums text-ink-soft">
        {[15, 20, 25, 30, 35].map((t) => (
          <span
            key={t}
            className="absolute -translate-x-1/2"
            style={{ left: `${pct(t, T_MIN, T_MAX)}%` }}
          >
            {t}°
          </span>
        ))}
      </div>
      <p className="mt-0.5 flex items-center gap-1.5 text-[12px] font-medium text-berry-700">
        <span className="inline-block h-0.5 w-4 bg-berry-500" />
        {th.heat_danger_temp}°C부터 사람 온열질환 경고음 (작물과 상관없는 고정 기준)
      </p>
    </div>
  );
}

/** 값 하나와 기준선을 보여주는 작은 막대 */
function MarkerBar({ label, hint, value, unit = "", min = 0, max = 100, marks = [], tone }) {
  const pos = value == null ? null : pct(value, min, max);
  return (
    <div className="rounded-2xl bg-paper px-4 py-3">
      <div className="flex items-baseline justify-between">
        <span className="text-[13px] font-semibold text-ink-soft">{label}</span>
        <span className="text-[19px] font-bold tabular-nums text-ink">
          {value == null ? "–" : Math.round(value * 10) / 10}
          <span className="ml-0.5 text-[12px] font-medium text-ink-soft">{unit}</span>
        </span>
      </div>
      <div className="relative mt-2.5 h-2 rounded-full bg-white ring-1 ring-line">
        {pos != null && (
          <motion.div
            className={`absolute inset-y-0 left-0 rounded-full ${tone}`}
            initial={false}
            animate={{ width: `${pos}%` }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
          />
        )}
        {marks.map((m) => (
          <span
            key={m}
            className="absolute -inset-y-1 w-0.5 rounded bg-ink/70"
            style={{ left: `${pct(m, min, max)}%` }}
          />
        ))}
      </div>
      <p className="mt-2 text-[11.5px] leading-snug text-ink-soft">{hint}</p>
    </div>
  );
}

/** 작물이 정해지는 순간 저절로 적용되는 세 가지 기준. "아무도 설정하지 않았다"를 눈으로 보여준다. */
function AppliedProfile({ state }) {
  const th = state.thresholds;
  const known = !!state.crop_key;
  const chips = [
    { icon: "window", label: "창문", value: `${th.vent_temp}°C부터 열어요` },
    { icon: "drop", label: "물", value: `건조도 ${th.dry_limit} 넘으면 줘요` },
    { icon: "bulb", label: "생장등", value: `조도 ${th.min_lux} 아래면 켜요` },
  ];
  return (
    <div className="mt-4">
      <p className="mb-2 flex items-center gap-2 text-[12.5px] font-semibold text-ink-soft">
        {known ? (
          <>
            <span className="rounded-md bg-leaf-600 px-1.5 py-0.5 text-[11px] font-bold text-white">자동</span>
            {state.crop_name}에 맞춰 저절로 정해진 기준 · 설정한 사람 0명
          </>
        ) : (
          "작물을 알아보면 이 기준이 저절로 정해져요 (지금은 기본값)"
        )}
      </p>
      <div
        key={state.crop_key || "default"}
        className={`grid grid-cols-1 gap-2 sm:grid-cols-3 ${known ? "animate-[pop-in_0.5s_ease-out]" : "opacity-60"}`}
      >
        {chips.map((c) => (
          <div
            key={c.label}
            className={`flex items-center gap-2.5 rounded-2xl px-3 py-2 ${
              known ? "bg-leaf-50 ring-1 ring-leaf-200" : "bg-paper"
            }`}
          >
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                known ? "bg-white text-leaf-700" : "bg-white text-ink-soft"
              }`}
            >
              <Icon name={c.icon} size={17} />
            </span>
            <span className="min-w-0 leading-tight">
              <span className="block text-[11.5px] font-semibold text-ink-soft">{c.label}</span>
              <span className="block truncate text-[13.5px] font-bold text-ink">{c.value}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function contrastSentence(profiles) {
  const groups = groupByVentTemp(profiles);
  if (groups.length < 2) return null;
  const parts = groups.map(
    (g) => `${g.crops.map((c) => c.name).join("·")}은 ${g.temp}°C`
  );
  return `${parts.join(", ")}부터 창문을 엽니다. 어르신은 아무것도 설정하지 않았습니다.`;
}

export function DecisionCard({ state, profiles }) {
  const level = LEVEL_STYLE[state.level] || LEVEL_STYLE.good;
  const th = state.thresholds;
  const sentence = contrastSentence(profiles);

  return (
    <Card title="지금 판단" icon="leaf">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-[15rem] flex-1">
          <motion.div
            key={state.level}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[13px] font-bold ${level.bg} ${level.text}`}
          >
            <span className={`h-2 w-2 rounded-full ${level.dot} ${state.level === "alert" ? "animate-[blink_1s_infinite]" : ""}`} />
            {level.label}
          </motion.div>
          <motion.h3
            key={state.message}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            aria-live="polite"
            className="mt-2.5 text-[clamp(1.6rem,2.6vw,2.4rem)] font-extrabold leading-tight text-ink"
          >
            {state.message}
          </motion.h3>
          {state.reason && (
            <p className="mt-2 flex items-start gap-2 text-[14.5px] text-ink-soft">
              <span className="mt-0.5 shrink-0 rounded-md bg-leaf-100 px-1.5 py-0.5 text-[11px] font-bold text-leaf-700">
                왜?
              </span>
              {state.reason}
            </p>
          )}
        </div>

        <div className="flex items-baseline gap-1 rounded-2xl bg-paper px-5 py-3">
          <Icon name="thermo" size={22} className="self-center text-leaf-600" />
          <span className="text-[clamp(2rem,3.2vw,3rem)] font-extrabold tabular-nums leading-none">
            {state.temperature == null ? "–" : state.temperature.toFixed(1)}
          </span>
          <span className="text-lg font-semibold text-ink-soft">°C</span>
        </div>
      </div>

      <AppliedProfile state={state} />

      <div className="mt-5">
        <ThermoScale
          temp={state.temperature}
          profiles={profiles}
          activeKey={state.crop_key}
          th={th}
        />
        {sentence && (
          <p className="mt-2 rounded-2xl bg-leaf-50 px-4 py-2 text-[13.5px] font-medium leading-relaxed text-leaf-800">
            {sentence}
          </p>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MarkerBar
          label="건조도"
          unit=""
          value={state.dryness}
          marks={[th.dry_limit]}
          tone={state.dryness != null && state.dryness > th.dry_limit ? "bg-berry-500" : "bg-sky-500"}
          hint={`${th.dry_limit} 넘으면 물을 줘요 · 공기 습도로 추정한 값`}
        />
        <MarkerBar
          label="조도"
          value={state.illuminance}
          min={0}
          max={20}
          marks={[th.min_lux, th.light_off_lux]}
          tone="bg-sun-500"
          hint={`${th.min_lux} 아래면 생장등 켬 · ${th.light_off_lux} 위면 끔`}
        />
        <MarkerBar
          label="습도"
          unit="%"
          value={state.humidity}
          marks={[th.rain_humidity]}
          tone={state.humidity != null && state.humidity > th.rain_humidity ? "bg-sky-700" : "bg-sky-500"}
          hint={`${th.rain_humidity}% 넘으면 비로 보고 창문을 닫아요`}
        />
      </div>
    </Card>
  );
}
