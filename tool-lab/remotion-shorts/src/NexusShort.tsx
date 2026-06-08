import React from 'react';
import {
  AbsoluteFill, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig,
  interpolate, spring,
} from 'remotion';
import data from './data/fcf087ea.json';

const THEMES: Record<string, {top: string; bot: string; accent: string}> = {
  navy:   {top: '#10162E', bot: '#202C5C', accent: '#7AA0FF'},
  maroon: {top: '#3A101A', bot: '#701C2C', accent: '#FF7887'},
  green:  {top: '#0C2C1E', bot: '#165438', accent: '#78EBAA'},
};

// Simple animated stickman (waving arm) as inline SVG
const Stickman: React.FC<{color: string; frame: number}> = ({color, frame}) => {
  const wave = Math.sin(frame / 6) * 22; // degrees
  return (
    <svg width="220" height="320" viewBox="0 0 220 320" style={{display: 'block'}}>
      <circle cx="110" cy="50" r="34" stroke={color} strokeWidth="9" fill="none" />
      <line x1="110" y1="84" x2="110" y2="200" stroke={color} strokeWidth="9" />
      <line x1="110" y1="120" x2="60" y2="160" stroke={color} strokeWidth="9" />
      <g transform={`rotate(${wave} 110 120)`}>
        <line x1="110" y1="120" x2="170" y2="150" stroke={color} strokeWidth="9" />
      </g>
      <line x1="110" y1="200" x2="78" y2="270" stroke={color} strokeWidth="9" />
      <line x1="110" y1="200" x2="142" y2="270" stroke={color} strokeWidth="9" />
    </svg>
  );
};

const XMark: React.FC<{p: number; color: string}> = ({p, color}) => {
  const s = interpolate(p, [0, 1], [0.2, 1]);
  const rot = interpolate(p, [0, 1], [-90, 0]);
  return (
    <svg width="180" height="180" viewBox="0 0 100 100"
      style={{transform: `scale(${s}) rotate(${rot}deg)`}}>
      <line x1="22" y1="22" x2="78" y2="78" stroke={color} strokeWidth="14" strokeLinecap="round" />
      <line x1="78" y1="22" x2="22" y2="78" stroke={color} strokeWidth="14" strokeLinecap="round" />
    </svg>
  );
};

const CheckMark: React.FC<{p: number; color: string}> = ({p, color}) => {
  const dash = interpolate(p, [0, 1], [120, 0]);
  const s = interpolate(p, [0, 0.6, 1], [0.4, 1.15, 1]);
  return (
    <svg width="180" height="180" viewBox="0 0 100 100" style={{transform: `scale(${s})`}}>
      <polyline points="20,55 42,76 82,28" fill="none" stroke={color} strokeWidth="14"
        strokeLinecap="round" strokeLinejoin="round" strokeDasharray="120" strokeDashoffset={dash} />
    </svg>
  );
};

const Scene: React.FC<{scene: any}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const theme = THEMES[scene.bg] ?? THEMES.navy;
  const isMyth = (scene.label ?? '').toUpperCase().includes('MYTH');
  const isTruth = (scene.label ?? '').toUpperCase().includes('TRUTH');
  const isCTA = (scene.label ?? '').toUpperCase().includes('CTA');
  const isHook = (scene.label ?? '').toUpperCase().includes('HOOK');

  // entrance springs
  const chip = spring({frame, fps, config: {damping: 12}});
  const textIn = interpolate(frame, [2, 16], [0, 1], {extrapolateRight: 'clamp'});
  const textY = interpolate(frame, [2, 16], [40, 0], {extrapolateRight: 'clamp'});
  const iconP = interpolate(frame, [10, 28], [0, 1], {extrapolateRight: 'clamp'});
  const capIn = interpolate(frame, [14, 26], [0, 1], {extrapolateRight: 'clamp'});

  // motion of the whole scene
  let tx = 0, scale = 1;
  if (scene.motion === 'slide_left') tx = interpolate(frame, [0, 14], [180, 0], {extrapolateRight: 'clamp'});
  else if (scene.motion === 'zoom_in') scale = interpolate(frame, [0, 40], [0.94, 1.04]);
  else if (scene.motion === 'zoom_out') scale = interpolate(frame, [0, 40], [1.1, 1.0]);

  return (
    <AbsoluteFill style={{background: `linear-gradient(160deg, ${theme.top}, ${theme.bot})`}}>
      <AbsoluteFill style={{
        transform: `translateX(${tx}px) scale(${scale})`,
        padding: 90, justifyContent: 'center', alignItems: 'center',
      }}>
        {/* label chip */}
        {scene.label && (
          <div style={{
            transform: `scale(${chip})`, background: theme.accent, color: '#0C1020',
            fontWeight: 900, fontSize: 46, padding: '14px 30px', borderRadius: 24,
            fontFamily: 'Arial, sans-serif', marginBottom: 36, alignSelf: 'flex-start',
          }}>{scene.label}</div>
        )}

        {/* animated icon */}
        <div style={{height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20}}>
          {isMyth && <XMark p={iconP} color={theme.accent} />}
          {isTruth && <CheckMark p={iconP} color={theme.accent} />}
          {(isHook || isCTA) && <Stickman color={theme.accent} frame={frame} />}
        </div>

        {/* main on-screen text */}
        <div style={{
          opacity: textIn, transform: `translateY(${textY}px)`,
          color: '#F5F8FF', fontFamily: 'Arial, sans-serif', fontWeight: 900,
          fontSize: 92, lineHeight: 1.08, textAlign: 'center', maxWidth: 900,
        }}>{scene.onscreen}</div>

        {/* caption */}
        <div style={{
          position: 'absolute', bottom: 320, left: 0, right: 0, opacity: capIn,
          color: '#E1E8FA', fontFamily: 'Arial, sans-serif', fontSize: 48, fontWeight: 700,
          textAlign: 'center', padding: '0 80px',
        }}>{scene.caption}</div>

        {/* CTA disclosure */}
        {isCTA && (
          <div style={{
            position: 'absolute', bottom: 120, left: 80, right: 80, opacity: capIn,
            color: '#9FB0C8', fontFamily: 'Arial, sans-serif', fontSize: 30, textAlign: 'center',
          }}>{data.disclosure}</div>
        )}
        {!isCTA && (
          <div style={{
            position: 'absolute', bottom: 150, left: 0, right: 0,
            color: '#9FB0C8', fontFamily: 'Arial, sans-serif', fontSize: 30, textAlign: 'center',
          }}>Educational only — not financial advice</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const NexusShort: React.FC = () => {
  const frame = useCurrentFrame();
  const total = data.totalFrames;
  const progress = interpolate(frame, [0, total], [0, 1]);

  return (
    <AbsoluteFill style={{backgroundColor: '#0C1020'}}>
      <Audio src={staticFile(data.audio)} />
      {data.scenes.map((s: any) => (
        <Sequence key={s.id} from={s.from} durationInFrames={s.durationInFrames}>
          <Scene scene={s} />
        </Sequence>
      ))}
      {/* progress bar */}
      <div style={{position: 'absolute', top: 0, left: 0, height: 10, width: `${progress * 100}%`,
        background: '#7AA0FF'}} />
      {/* brand watermark */}
      <div style={{position: 'absolute', top: 36, right: 40, color: '#9FB0C8',
        fontFamily: 'Arial, sans-serif', fontSize: 30, fontWeight: 700}}>{data.brand}</div>
    </AbsoluteFill>
  );
};
