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

const FULL_TEXT = "The Black Dog Lounge";
const TEXT_BOX_WIDTH = 900;
const REVEAL_START = 6;
const REVEAL_DURATION = 70;

const flowEase = Easing.bezier(0.45, 0, 0.2, 1);

export const BlackDogLoungeIntro: React.FC = () => {
  const frame = useCurrentFrame();

  const revealWidth = interpolate(
    frame,
    [REVEAL_START, REVEAL_START + REVEAL_DURATION],
    [0, TEXT_BOX_WIDTH],
    { easing: flowEase, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const tipOpacity = interpolate(
    frame,
    [REVEAL_START, REVEAL_START + 6, REVEAL_START + REVEAL_DURATION - 10, REVEAL_START + REVEAL_DURATION],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const revealEndsAt = REVEAL_START + REVEAL_DURATION;

  const lineWidth = interpolate(frame, [revealEndsAt + 8, revealEndsAt + 34], [0, 360], {
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
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            position: "relative",
            width: TEXT_BOX_WIDTH,
            height: 130,
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              overflow: "hidden",
              width: revealWidth,
            }}
          >
            <div
              style={{
                width: TEXT_BOX_WIDTH,
                fontFamily,
                fontSize: 96,
                color: PALETTE.text,
                whiteSpace: "nowrap",
                lineHeight: 1.3,
              }}
            >
              {FULL_TEXT}
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: revealWidth - 2,
              width: 18,
              height: 130,
              opacity: tipOpacity,
              background: `radial-gradient(circle, ${PALETTE.shine} 0%, rgba(232,200,120,0) 75%)`,
              filter: "blur(2px)",
            }}
          />
        </div>
        <div
          style={{
            marginTop: 6,
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
