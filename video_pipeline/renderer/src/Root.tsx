import React from "react";
import { Composition } from "remotion";
import { MainVideo } from "./MainVideo";
import { TimelineManifest } from "./types";

const defaultProps: TimelineManifest = {
  videoFile: "rough_cut.mp4",
  fps: 30,
  width: 1920,
  height: 1080,
  durationInFrames: 150,
  captionsEnabled: true,
  captions: [],
  graphicCues: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MainVideo"
      component={MainVideo}
      durationInFrames={defaultProps.durationInFrames}
      fps={defaultProps.fps}
      width={defaultProps.width}
      height={defaultProps.height}
      defaultProps={defaultProps}
      calculateMetadata={({ props }) => {
        const manifest = props as TimelineManifest;
        return {
          durationInFrames: Math.max(1, manifest.durationInFrames),
          fps: Math.max(1, Math.round(manifest.fps)),
          width: manifest.width,
          height: manifest.height,
        };
      }}
    />
  );
};
