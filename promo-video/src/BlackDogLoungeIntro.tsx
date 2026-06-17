import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const PALETTE = {
  background: "#0a0707",
  backgroundEdge: "#1a0f0d",
  gold: "#c9a25b",
  goldBright: "#e8c878",
  text: "#f3e6cf",
};

const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

const fadeIn = (frame: number, start: number, duration: number) =>
  interpolate(frame, [start, start + duration], [0, 1], {
    easing: easeOut,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const DogMark: React.FC<{ frame: number }> = ({ frame }) => {
  const scale = interpolate(frame, [0, 22], [0.7, 1], {
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = fadeIn(frame, 0, 18);

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        position: "relative",
        width: 220,
        height: 150,
      }}
    >
      {/* tail */}
      <div
        style={{
          position: "absolute",
          left: 18,
          top: 38,
          width: 14,
          height: 46,
          backgroundColor: PALETTE.gold,
          borderRadius: "10px 10px 0px 10px",
          transform: "rotate(18deg)",
          transformOrigin: "bottom center",
        }}
      />
      {/* body */}
      <div
        style={{
          position: "absolute",
          left: 30,
          top: 70,
          width: 150,
          height: 64,
          backgroundColor: PALETTE.gold,
          borderRadius: 32,
        }}
      />
      {/* head */}
      <div
        style={{
          position: "absolute",
          left: 140,
          top: 22,
          width: 72,
          height: 72,
          backgroundColor: PALETTE.gold,
          borderRadius: "50%",
        }}
      />
      {/* snout */}
      <div
        style={{
          position: "absolute",
          left: 196,
          top: 56,
          width: 30,
          height: 26,
          backgroundColor: PALETTE.gold,
          borderRadius: "0px 14px 14px 14px",
        }}
      />
      {/* floppy ear */}
      <div
        style={{
          position: "absolute",
          left: 150,
          top: 30,
          width: 26,
          height: 50,
          backgroundColor: PALETTE.background,
          borderRadius: "0% 60% 60% 60%",
          transform: "rotate(15deg)",
          transformOrigin: "top center",
        }}
      />
      {/* legs (lounging, tucked) */}
      <div
        style={{
          position: "absolute",
          left: 46,
          top: 124,
          width: 26,
          height: 18,
          backgroundColor: PALETTE.gold,
          borderRadius: "0 0 12px 12px",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 130,
          top: 124,
          width: 26,
          height: 18,
          backgroundColor: PALETTE.gold,
          borderRadius: "0 0 12px 12px",
        }}
      />
    </div>
  );
};

export const BlackDogLoungeIntro: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = fadeIn(frame, 26, 20);
  const titleLetterSpacing = interpolate(frame, [26, 50], [14, 4], {
    easing: easeOut,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [26, 50], [16, 0], {
    easing: easeOut,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [54, 80], [0, 260], {
    easing: easeOut,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const glowOpacity = interpolate(frame, [0, 24], [0, 0.55], {
    easing: easeOut,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% 42%, ${PALETTE.backgroundEdge} 0%, ${PALETTE.background} 70%)`,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <AbsoluteFill
        style={{
          opacity: glowOpacity,
          background:
            "radial-gradient(circle at 50% 40%, rgba(232,200,120,0.5) 0%, rgba(232,200,120,0) 55%)",
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <DogMark frame={frame} />
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            marginTop: 22,
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: 54,
            fontWeight: 700,
            color: PALETTE.text,
            letterSpacing: titleLetterSpacing,
            textTransform: "uppercase",
            textAlign: "center",
          }}
        >
          The Black Dog Lounge
        </div>
        <div
          style={{
            marginTop: 18,
            width: lineWidth,
            height: 2,
            backgroundColor: PALETTE.goldBright,
            boxShadow: `0 0 8px ${PALETTE.goldBright}`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
