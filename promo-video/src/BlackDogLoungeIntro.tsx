import { loadFont } from "@remotion/fonts";
import { AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame } from "remotion";

const fontFamily = "Great Vibes";

loadFont({
  family: fontFamily,
  url: staticFile("fonts/GreatVibes-Regular.ttf"),
  weight: "400",
  style: "normal",
});

const PALETTE = {
  bgTop: "#0c0a14",
  bgBottom: "#1a1024",
  glow: "rgba(201, 162, 91, 0.35)",
  text: "#f3e6cf",
  shine: "#e8c878",
};

const flowEase = Easing.bezier(0.45, 0, 0.2, 1);

const LINE_1 = { text: "Welcome to", fontSize: 56, boxWidth: 420, boxHeight: 80, start: 6, duration: 36 };
const LINE_2_START = LINE_1.start + LINE_1.duration + 14;
const LINE_2 = {
  text: "The Black Dog Lounge",
  fontSize: 108,
  boxWidth: 1020,
  boxHeight: 150,
  start: LINE_2_START,
  duration: 80,
};

const FlowingLine: React.FC<{
  frame: number;
  text: string;
  fontSize: number;
  boxWidth: number;
  boxHeight: number;
  start: number;
  duration: number;
}> = ({ frame, text, fontSize, boxWidth, boxHeight, start, duration }) => {
  const revealWidth = interpolate(frame, [start, start + duration], [0, boxWidth], {
    easing: flowEase,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const tipOpacity = interpolate(
    frame,
    [start, start + 6, start + duration - 10, start + duration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div style={{ position: "relative", width: boxWidth, height: boxHeight }}>
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", width: revealWidth }}>
        <div
          style={{
            width: boxWidth,
            fontFamily,
            fontSize,
            color: PALETTE.text,
            whiteSpace: "nowrap",
            lineHeight: 1.3,
          }}
        >
          {text}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: revealWidth - 2,
          width: 18,
          height: boxHeight,
          opacity: tipOpacity,
          background: `radial-gradient(circle, ${PALETTE.shine} 0%, rgba(232,200,120,0) 75%)`,
          filter: "blur(2px)",
        }}
      />
    </div>
  );
};

export const BlackDogLoungeIntro: React.FC = () => {
  const frame = useCurrentFrame();

  const line2EndsAt = LINE_2.start + LINE_2.duration;

  const lineWidth = interpolate(frame, [line2EndsAt + 8, line2EndsAt + 34], [0, 480], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const glowPulse = 0.5 + Math.sin(frame / 30 / 0.9) * 0.15;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${PALETTE.bgTop} 0%, ${PALETTE.bgBottom} 100%)`,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <AbsoluteFill
        style={{
          opacity: glowPulse,
          background: `radial-gradient(circle at 50% 55%, ${PALETTE.glow} 0%, rgba(201,162,91,0) 60%)`,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <FlowingLine frame={frame} {...LINE_1} />
        <FlowingLine frame={frame} {...LINE_2} />
        <div
          style={{
            marginTop: 4,
            width: lineWidth,
            height: 2,
            backgroundColor: PALETTE.shine,
            boxShadow: `0 0 10px ${PALETTE.shine}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
