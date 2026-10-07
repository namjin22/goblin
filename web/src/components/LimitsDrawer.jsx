import { motion } from "framer-motion";
import { Drawer } from "./Overlay";

// README의 "한계 (숨기지 않습니다)"와 같은 내용. 질문받기 전에 먼저 밝힌다.
const LIMITS = [
  {
    title: "건조도는 흙의 수분이 아니에요",
    body: "절대 수분 함량(%)이 아니라 상대 지표예요. 지금은 흙이 아니라 공기 중 습도를 뒤집어 쓰고, '습도가 낮으면 흙도 마르고 있을 것'이라는 대리 가정 위에 있어요.",
  },
  {
    title: "'비가 온다'는 날씨 정보가 아니에요",
    body: "Env 센서의 습도가 기준을 넘었다는 뜻일 뿐이에요. 인터넷 없이도 동작하게 하려고 날씨 API를 쓰지 않았고, 그래서 그냥 습한 날도 비로 오인할 수 있어요.",
  },
  {
    title: "스프링클러는 레고 모형이에요",
    body: "실제로 물은 나오지 않아요. 실제 제품에서는 이 자리에 물 밸브가 연결돼요.",
  },
  {
    title: "작물은 레고 브릭이에요",
    body: "대회 규정상 실제 작물을 가져올 수 없어서 크기와 색을 맞춘 브릭으로 대신했어요. 색이 뚜렷이 다른 브릭이라 인식이 잘 되는 점도 있어요.",
  },
  {
    title: "작물 인식은 완벽하지 않아요",
    body: "조명이 크게 바뀌거나 브릭이 겹치면 달라질 수 있어요. 확률 막대는 모델이 얼마나 확신하는지를 그대로 보여줘요.",
  },
];

export function LimitsDrawer({ open, onClose }) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="한계"
    >
      <ul className="space-y-4">
        {LIMITS.map((l, i) => (
          <motion.li
            key={l.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 + i * 0.05 }}
            className="rounded-3xl bg-paper px-5 py-5"
          >
            <h3 className="text-[20px] font-extrabold text-ink">{l.title}</h3>
            <p className="mt-2 text-[17px] leading-relaxed text-ink-soft">{l.body}</p>
          </motion.li>
        ))}
      </ul>
    </Drawer>
  );
}
