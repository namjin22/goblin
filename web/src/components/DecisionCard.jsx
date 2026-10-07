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

/** 작물마다 다른 "창문 여는 온도"를 한 눈금자에 놓고, 지금 온도를 동그라미로 보여준다 */
function ThermoScale({ temp, profiles, activeKey, th }) {
  const groups = groupByVentTemp(profiles);
  const nowPos = temp == null ? null : pct(temp, T_MIN, T_MAX);
  const heatPos = pct(th.heat_danger_temp, T_MIN, T_MAX);
  const ventPos = pct(th.vent_temp, T_MIN, T_MAX);
  const alertPos = pct(th.vent_alert_temp, T_MIN, T_MAX);

  return (
    <div className="select-none">
      <div className="relative h-12">
        {groups.map(({ temp: t, crops }) => {
          const isActive = crops.some((c) => c.key === activeKey);
          return (
            <motion.div
              key={t}
              className="absolute bottom-0 flex -translate-x-1/2 flex-col items-center"
              style={{ left: `${pct(t, T_MIN, T_MAX)}%` }}
              animate={{ opacity: isActive || !activeKey ? 1 : 0.45 }}
              transition={{ duration: 0.3 }}
            >
              <span
                className={`whitespace-nowrap rounded-full px-4 py-1.5 text-[17px] font-extrabold ${
                  isActive ? "bg-ink text-white" : "bg-paper text-ink-soft"
                }`}
              >
                {crops.map((c) => c.name).join("·")} {t}°
              </span>
              <span className={`h-2.5 w-0.5 ${isActive ? "bg-ink" : "bg-line"}`} />
            </motion.div>
          );
        })}
      </div>

      <div className="relative h-5 rounded-full bg-leaf-100">
        <div className="absolute inset-y-0 bg-sun-100" style={{ left: `${ventPos}%`, width: `${alertPos - ventPos}%` }} />
        <div className="absolute inset-y-0 rounded-r-full bg-berry-100" style={{ left: `${alertPos}%`, right: 0 }} />
        <div className="absolute -inset-y-2 w-[3px] bg-berry-500" style={{ left: `${heatPos}%` }} />
        {nowPos != null && (
          <motion.div
            className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
            initial={false}
            animate={{ left: `${nowPos}%` }}
            transition={{ type: "spring", stiffness: 90, damping: 18 }}
          >
            <span className="block h-9 w-9 rounded-full border-[6px] border-white bg-leaf-600 shadow-[0_2px_10px_rgba(0,0,0,0.3)]" />
          </motion.div>
        )}
      </div>

      <div className="relative mt-3 h-7 text-[15px] tabular-nums text-ink-soft">
        {[15, 20, 25, 30, 35].map((t) => (
          <span key={t} className="absolute -translate-x-1/2" style={{ left: `${pct(t, T_MIN, T_MAX)}%` }}>
            {t}°
          </span>
        ))}
      </div>
      <p className="mt-1 flex items-center gap-2 text-[15px] font-semibold text-berry-700">
        <span className="inline-block h-[3px] w-5 bg-berry-500" />
        {th.heat_danger_temp}° 넘으면 경고음
      </p>
    </div>
  );
}

/** 값 하나와 기준선을 보여주는 큰 막대. 설명 문장은 없다 - 이름과 숫자와 선만. */
function MarkerBar({ label, value, unit = "", min = 0, max = 100, marks = [], tone }) {
  const pos = value == null ? null : pct(value, min, max);
  return (
    <div className="rounded-3xl bg-paper px-5 py-3.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[17px] font-bold text-ink-soft">{label}</span>
        <span className="text-[30px] font-extrabold tabular-nums leading-none text-ink">
          {value == null ? "–" : Math.round(value * 10) / 10}
          <span className="ml-0.5 text-[16px] font-semibold text-ink-soft">{unit}</span>
        </span>
      </div>
      <div className="relative mt-3.5 h-3.5 rounded-full bg-white ring-1 ring-line">
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
            className="absolute -inset-y-1.5 w-[3px] rounded bg-ink/70"
            style={{ left: `${pct(m, min, max)}%` }}
          />
        ))}
      </div>
    </div>
  );
}

/** 작물이 정해지면 저절로 적용되는 세 가지 기준. 짧게: 아이콘 + 이름 + 숫자. */
function AppliedProfile({ state }) {
  const th = state.thresholds;
  const known = !!state.crop_key;
  const chips = [
    { icon: "window", label: "창문", value: `${th.vent_temp}°부터` },
    { icon: "drop", label: "물", value: `건조 ${th.dry_limit}↑` },
    { icon: "bulb", label: "생장등", value: `조도 ${th.min_lux}↓` },
  ];
  return (
    <div
      key={state.crop_key || "default"}
      className={`grid grid-cols-3 gap-4 ${known ? "animate-[pop-in_0.5s_ease-out]" : "opacity-50"}`}
    >
      {chips.map((c) => (
        <div
          key={c.label}
          className={`flex items-center gap-3.5 rounded-3xl px-5 py-3 ${
            known ? "bg-leaf-50 ring-2 ring-leaf-200" : "bg-paper"
          }`}
        >
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-leaf-700">
            <Icon name={c.icon} size={26} />
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block text-[15px] font-semibold text-ink-soft">{c.label}</span>
            <span className="block truncate text-[22px] font-extrabold text-ink">{c.value}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function DecisionCard({ state, profiles }) {
  const level = LEVEL_STYLE[state.level] || LEVEL_STYLE.good;
  const th = state.thresholds;

  return (
    <Card title="지금" icon="leaf">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-[18rem] flex-1">
          <motion.div
            key={state.level}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`inline-flex items-center gap-2.5 rounded-full px-5 py-2 text-[17px] font-extrabold ${level.bg} ${level.text}`}
          >
            <span className={`h-3 w-3 rounded-full ${level.dot} ${state.level === "alert" ? "animate-[blink_1s_infinite]" : ""}`} />
            {level.label}
          </motion.div>
          <motion.h3
            key={state.message}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            aria-live="polite"
            className="mt-4 text-[clamp(2.1rem,3.1vw,3rem)] font-extrabold leading-tight text-ink"
          >
            {state.message}
          </motion.h3>
          {state.reason && <p className="mt-2.5 text-[18px] text-ink-soft">{state.reason}</p>}
        </div>

        <div className="flex items-baseline gap-1.5 rounded-3xl bg-paper px-7 py-4">
          <Icon name="thermo" size={30} className="self-center text-leaf-600" />
          <span className="text-[clamp(2.8rem,4vw,4rem)] font-extrabold tabular-nums leading-none">
            {state.temperature == null ? "–" : state.temperature.toFixed(1)}
          </span>
          <span className="text-2xl font-bold text-ink-soft">°C</span>
        </div>
      </div>

      <div className="mt-6">
        <AppliedProfile state={state} />
      </div>

      <div className="mt-6">
        <ThermoScale temp={state.temperature} profiles={profiles} activeKey={state.crop_key} th={th} />
      </div>

      <div className="mt-5 grid grid-cols-3 gap-4">
        <MarkerBar
          label="건조도"
          value={state.dryness}
          marks={[th.dry_limit]}
          tone={state.dryness != null && state.dryness > th.dry_limit ? "bg-berry-500" : "bg-sky-500"}
        />
        <MarkerBar label="조도" value={state.illuminance} min={0} max={40} marks={[th.min_lux, th.light_off_lux]} tone="bg-sun-500" />
        <MarkerBar
          label="습도"
          unit="%"
          value={state.humidity}
          marks={[th.rain_humidity]}
          tone={state.humidity != null && state.humidity > th.rain_humidity ? "bg-sky-700" : "bg-sky-500"}
        />
      </div>
    </Card>
  );
}
