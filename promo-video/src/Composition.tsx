import {
  AbsoluteFill,
  Easing,
  interpolate,
  Series,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const PALETTE = {
  background: "#0f0f1a",
  accent: "#7c5cff",
  accentSoft: "#bfb2ff",
  text: "#f5f3ff",
  muted: "#a9a3c2",
};

const fadeIn = (frame: number, durationInFrames: number) =>
  interpolate(frame, [0, durationInFrames], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const riseIn = (frame: number, durationInFrames: number) =>
  interpolate(frame, [0, durationInFrames], [40, 0], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = fadeIn(frame, 20);
  const y = riseIn(frame, 20);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: PALETTE.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${y}px)`,
          fontFamily: "Arial, sans-serif",
          fontSize: 64,
          fontWeight: 700,
          color: PALETTE.text,
          textAlign: "center",
          maxWidth: 900,
          lineHeight: 1.3,
        }}
      >
        Stuck planning your next 90 days?
      </div>
    </AbsoluteFill>
  );
};

const Reveal: React.FC = () => {
  const frame = useCurrentFrame();
  const titleOpacity = fadeIn(frame, 18);
  const titleY = riseIn(frame, 18);
  const subtitleOpacity = fadeIn(frame - 12, 18);
  const subtitleY = riseIn(frame - 12, 18);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: PALETTE.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 920 }}>
        <div
          style={{
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
            fontFamily: "Arial, sans-serif",
            fontSize: 28,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: PALETTE.accentSoft,
            marginBottom: 24,
          }}
        >
          Introducing
        </div>
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            fontFamily: "Arial, sans-serif",
            fontSize: 76,
            fontWeight: 800,
            color: PALETTE.text,
            lineHeight: 1.15,
          }}
        >
          The 90-Day Business Planner
        </div>
      </div>
    </AbsoluteFill>
  );
};

const FEATURES = [
  "Weekly goal-setting framework",
  "Daily focus + reflection prompts",
  "Printable & digital-ready layouts",
];

const FeatureRow: React.FC<{ text: string; delay: number }> = ({ text, delay }) => {
  const frame = useCurrentFrame();
  const local = frame - delay;
  const opacity = fadeIn(local, 16);
  const x = interpolate(local, [0, 16], [-30, 0], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        display: "flex",
        alignItems: "center",
        gap: 20,
        fontFamily: "Arial, sans-serif",
        fontSize: 36,
        color: PALETTE.text,
      }}
    >
      <span
        style={{
          display: "inline-flex",
          width: 36,
          height: 36,
          borderRadius: 18,
          backgroundColor: PALETTE.accent,
          color: PALETTE.text,
          alignItems: "center",
          justifyContent: "center",
          fontSize: 20,
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        ✓
      </span>
      {text}
    </div>
  );
};

const Features: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: PALETTE.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {FEATURES.map((text, i) => (
          <FeatureRow key={text} text={text} delay={i * 12} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const CallToAction: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = interpolate(frame, [0, 20], [0.85, 1], {
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = fadeIn(frame, 14);
  const pulse = 1 + Math.sin(frame / fps) * 0.04;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: PALETTE.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity,
          transform: `scale(${scale * pulse})`,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: "Arial, sans-serif",
            fontSize: 48,
            fontWeight: 800,
            color: PALETTE.text,
            marginBottom: 28,
          }}
        >
          Plan with clarity. Start today.
        </div>
        <div
          style={{
            display: "inline-block",
            padding: "20px 48px",
            borderRadius: 999,
            backgroundColor: PALETTE.accent,
            color: PALETTE.text,
            fontFamily: "Arial, sans-serif",
            fontSize: 32,
            fontWeight: 700,
          }}
        >
          Get the planner →
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const PromoVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.background }}>
      <Series>
        <Series.Sequence durationInFrames={75}>
          <Hook />
        </Series.Sequence>
        <Series.Sequence durationInFrames={90}>
          <Reveal />
        </Series.Sequence>
        <Series.Sequence durationInFrames={105}>
          <Features />
        </Series.Sequence>
        <Series.Sequence durationInFrames={90}>
          <CallToAction />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
