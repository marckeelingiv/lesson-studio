import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { RemappedWord } from "./types";

interface CaptionsProps {
  words: RemappedWord[];
}

const WORDS_PER_PAGE = 6;

export const Captions: React.FC<CaptionsProps> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;

  if (words.length === 0) return null;

  // Group words into short readable chunks
  const activeIndex = words.findIndex(
    (w) => currentMs >= w.startMs && currentMs <= w.endMs
  );
  if (activeIndex === -1) return null;

  const pageIndex = Math.floor(activeIndex / WORDS_PER_PAGE);
  const pageWords = words.slice(
    pageIndex * WORDS_PER_PAGE,
    (pageIndex + 1) * WORDS_PER_PAGE
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 72,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "8px 10px",
          maxWidth: "82%",
          backgroundColor: "rgba(10, 12, 18, 0.78)",
          padding: "14px 26px",
          borderRadius: 16,
          boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
        }}
      >
        {pageWords.map((word, idx) => {
          const isCurrent = currentMs >= word.startMs && currentMs <= word.endMs;
          const isSpoken = currentMs >= word.startMs;
          return (
            <span
              key={`${pageIndex}-${idx}`}
              style={{
                fontFamily: "Inter, system-ui, -apple-system, sans-serif",
                fontSize: 40,
                fontWeight: 800,
                lineHeight: 1.15,
                color: isCurrent ? "#FACC15" : isSpoken ? "#FFFFFF" : "#94A3B8",
                transform: isCurrent ? "scale(1.06)" : "scale(1)",
                transition: "transform 80ms ease",
              }}
            >
              {word.text.trim()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
