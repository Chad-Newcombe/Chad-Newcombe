import "./index.css";
import { Composition } from "remotion";
import { PromoVideo } from "./Composition";
import { BlackDogLoungeIntro } from "./BlackDogLoungeIntro";

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
      <Composition
        id="BlackDogLoungeIntro"
        component={BlackDogLoungeIntro}
        durationInFrames={155}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
