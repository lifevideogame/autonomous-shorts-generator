import { AbsoluteFill, staticFile } from 'remotion';
import { Video } from '@remotion/media';

export const MyShort: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <Video
        src={staticFile('video.mp4')}
        style={{
          height: '100%',
          width: 'auto',
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
        }}
        startFrom={0} // Start from the beginning
      />
      {/* Add some text overlay to make it look like a short */}
      <div
        style={{
          position: 'absolute',
          bottom: 100,
          width: '100%',
          textAlign: 'center',
          color: 'white',
          fontSize: 60,
          fontWeight: 'bold',
          textShadow: '2px 2px 10px rgba(0,0,0,0.8)',
          fontFamily: 'sans-serif',
        }}
      >
        Andrew Ng: State of AI 2024
      </div>
    </AbsoluteFill>
  );
};
