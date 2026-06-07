import "./index.css";
import { Composition } from "remotion";
import { PromoVideo } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="PromoVideo"
        component={PromoVideo}
        durationInFrames={75 + 90 + 105 + 90}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
