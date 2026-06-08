import React from 'react';
import {Composition} from 'remotion';
import {NexusShort} from './NexusShort';
import data from './data/fcf087ea.json';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="NexusShort"
      component={NexusShort as any}
      durationInFrames={data.totalFrames}
      fps={data.fps}
      width={data.width}
      height={data.height}
      defaultProps={{}}
    />
  );
};
