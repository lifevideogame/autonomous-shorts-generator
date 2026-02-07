import { AbsoluteFill, useCurrentFrame, interpolate, staticFile, useVideoConfig, useDelayRender, spring } from 'remotion';
import { Video } from '@remotion/media';
import { loadFont } from '@remotion/google-fonts/Kanit';
import { parseSrt } from '@remotion/captions';
import type { Caption } from '@remotion/captions';
import { useEffect, useState, useCallback } from 'react';

const { fontFamily } = loadFont();

// moment_final.mp4 starts at 18:30
const OFFSET_SEC = 18 * 60 + 30; 

// Detection on 1080p frame: {'x': 1544, 'y': 787, 'w': 171, 'h': 171}
const FACE_X = 1544;
const FACE_Y = 787;
const FACE_W = 171;
const FACE_H = 171;

export const GamingShort: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[]>([]);
  const { delayRender, continueRender } = useDelayRender();
  const [renderHandle] = useState(() => delayRender());

  const fetchCaptions = useCallback(async () => {
    try {
      const response = await fetch(staticFile('subtitles.srt'));
      const text = await response.text();
      const { captions: parsed } = parseSrt({ input: text });
      setCaptions(parsed);
      continueRender(renderHandle);
    } catch (e) {
      console.error(e);
    }
  }, [continueRender, renderHandle]);

  useEffect(() => {
    fetchCaptions();
  }, [fetchCaptions]);

  const currentCaption = captions.find(
    (c) => {
        const startFrameInCut = (c.startInFrames - OFFSET_SEC * fps);
        const endFrameInCut = (c.endInFrames - OFFSET_SEC * fps);
        return frame >= startFrameInCut && frame <= endFrameInCut;
    }
  );

  const captionSpring = spring({
    frame: currentCaption ? frame - (currentCaption.startInFrames - OFFSET_SEC * fps) : 0,
    fps,
    config: { stiffness: 200 },
  });

  // FACECAM CALCULATIONS
  const CONTAINER_SIZE = 650; 
  const ZOOM_SCALE = 3.2; // Zoom in enough to see the streamer clearly
  
  const faceCenterX = FACE_X + FACE_W / 2;
  const faceCenterY = FACE_Y + FACE_H / 2;
  
  const marginLeft = (CONTAINER_SIZE / 2) - (faceCenterX * ZOOM_SCALE);
  const marginTop = (CONTAINER_SIZE / 2) - (faceCenterY * ZOOM_SCALE);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', fontFamily }}>
      
      {/* 1. MAIN GAMEPLAY BACKGROUND (Zoomed on the action) */}
      <AbsoluteFill style={{ height: '100%', overflow: 'hidden' }}>
        <Video
          src={staticFile('moment_final.mp4')}
          style={{
            height: '100%',
            width: 'auto',
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%) scale(1.8)', 
          }}
        />
        {/* Cinematic Overlays */}
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(rgba(0,0,0,0.4) 0%, transparent 20%, transparent 80%, rgba(0,0,0,0.6) 100%)' }} />
      </AbsoluteFill>

      {/* 2. streamer FACECAM (HQ & Centered) */}
      <div
        style={{
          position: 'absolute',
          top: '8%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: CONTAINER_SIZE,
          height: CONTAINER_SIZE,
          borderRadius: '50%',
          border: '12px solid #00ffcc',
          overflow: 'hidden',
          boxShadow: '0 0 50px rgba(0, 255, 204, 0.8)',
          zIndex: 50,
          backgroundColor: '#111',
        }}
      >
        <Video
          src={staticFile('moment_final.mp4')}
          style={{
            transformOrigin: 'top left',
            width: 1920 * ZOOM_SCALE, 
            height: 1080 * ZOOM_SCALE, 
            marginLeft: marginLeft, 
            marginTop: marginTop,
            maxWidth: 'none',
          }}
          muted 
        />
      </div>

      {/* 3. STYLIZED NAME TAG */}
      <div
        style={{
          position: 'absolute',
          top: '40%',
          left: '50%',
          transform: 'translateX(-50%) skewX(-10deg)',
          backgroundColor: '#00ffcc',
          color: '#000',
          padding: '10px 50px',
          fontWeight: '900',
          fontSize: '48px',
          zIndex: 60,
          boxShadow: '8px 8px 0px #000',
          textTransform: 'uppercase',
        }}
      >
        DEEBEEGEEK
      </div>

      {/* 4. VIRAL POPPING CAPTIONS */}
      {currentCaption && (
        <div
          style={{
            position: 'absolute',
            bottom: '15%',
            width: '100%',
            display: 'flex',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: '#fff700',
              color: 'black',
              padding: '15px 45px',
              fontSize: '85px',
              fontWeight: '900',
              textTransform: 'uppercase',
              transform: `scale(${captionSpring}) rotate(${interpolate(captionSpring, [0, 1], [-3, 0])}deg)`,
              boxShadow: '12px 12px 0px black',
              textAlign: 'center',
              lineHeight: '1.1',
            }}
          >
            {currentCaption.text}
          </div>
        </div>
      )}

      {/* 5. HUD OVERLAY */}
      <div style={{ position: 'absolute', top: 60, right: 60, color: '#00ffcc', fontSize: 35, fontWeight: '900', opacity: 0.9 }}>
        REC ●
      </div>
      <div style={{ position: 'absolute', top: 60, left: 60, color: 'white', fontSize: 25, fontWeight: 'bold', opacity: 0.6 }}>
        4K ULTRA HD
      </div>

    </AbsoluteFill>
  );
};
