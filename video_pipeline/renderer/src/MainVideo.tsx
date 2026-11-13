import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { Captions } from "./Captions";
import { GraphicsOverlay } from "./Graphics";
import { TimelineManifest } from "./types";

export const MainVideo: React.FC<TimelineManifest> = ({
  videoFile,
  cameraFile,
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
      {cameraFile ? (
        <div
          style={{
            position: "absolute",
            right: 48,
            bottom: 52,
            width: 280,
            height: 158,
            borderRadius: 20,
            overflow: "hidden",
            border: "2px solid rgba(198, 237, 152, 0.55)",
            boxShadow: "0 18px 42px rgba(0, 0, 0, 0.55)",
            backgroundColor: "#101514",
          }}
        >
          <OffthreadVideo
            src={staticFile(cameraFile)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      ) : null}
      <GraphicsOverlay cues={graphicCues} />
      {captionsEnabled ? <Captions words={captions} /> : null}
    </AbsoluteFill>
  );
};
