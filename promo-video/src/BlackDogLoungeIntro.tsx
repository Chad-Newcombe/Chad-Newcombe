import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

const PALETTE = {
  bgTop: "#0c0a14",
  bgBottom: "#1a1024",
  glow: "rgba(201, 162, 91, 0.35)",
  text: "#f3e6cf",
  cursor: "#e8c878",
};

const FULL_TEXT = "The Black Dog Lounge";
const CHAR_FRAMES = 3;
const CURSOR_BLINK_FRAMES = 16;

const getTypedText = (frame: number, fullText: string, charFrames: number): string => {
  const typedChars = Math.min(fullText.length, Math.floor(frame / charFrames));
  return fullText.slice(0, typedChars);
};

const Cursor: React.FC<{ frame: number; blinkFrames: number }> = ({ frame, blinkFrames }) => {
  const opacity = interpolate(frame % blinkFrames, [0, blinkFrames / 2, blinkFrames], [1, 0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return <span style={{ opacity, color: PALETTE.cursor }}>|</span>;
};

export const BlackDogLoungeIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const typedText = getTypedText(frame, FULL_TEXT, CHAR_FRAMES);
  const typingDoneAt = FULL_TEXT.length * CHAR_FRAMES;

  const glowPulse = 0.5 + Math.sin(frame / fps / 0.9) * 0.15;

  const lineWidth = interpolate(
    frame,
    [typingDoneAt + 10, typingDoneAt + 36],
    [0, 360],
    {
      easing: Easing.bezier(0.16, 1, 0.3, 1),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

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
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontStyle: "italic",
            fontSize: 64,
            fontWeight: 600,
            color: PALETTE.text,
            letterSpacing: 2,
            whiteSpace: "pre",
          }}
        >
          {typedText}
          <Cursor frame={frame} blinkFrames={CURSOR_BLINK_FRAMES} />
        </div>
        <div
          style={{
            marginTop: 22,
            width: lineWidth,
            height: 2,
            backgroundColor: PALETTE.cursor,
            boxShadow: `0 0 10px ${PALETTE.cursor}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
