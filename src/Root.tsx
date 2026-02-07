import { Composition } from 'remotion';
import { MyShort } from './MyShort';
import { GamingShort } from './GamingShort';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Short"
        component={MyShort}
        durationInFrames={1800} // 30 seconds at 60fps
        fps={60}
        width={720}
        height={1280}
      />
      <Composition
        id="GamingShort"
        component={GamingShort}
        durationInFrames={900} // 15 seconds
        fps={60}
        width={1080}
        height={1920}
      />
    </>
  );
};
