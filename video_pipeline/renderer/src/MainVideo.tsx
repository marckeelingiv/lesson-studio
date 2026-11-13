import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { Captions } from "./Captions";
import { GraphicsOverlay } from "./Graphics";
import { TimelineManifest } from "./types";

export const MainVideo: React.FC<TimelineManifest> = ({
  videoFile,
  captionsEnabled,
  captions,
  graphicCues,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {videoFile ? (
        <OffthreadVideo
          src={staticFile(videoFile)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : null}
      <GraphicsOverlay cues={graphicCues} />
      {captionsEnabled ? <Captions words={captions} /> : null}
    </AbsoluteFill>
  );
};
