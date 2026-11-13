import React from "react";
import {
  AbsoluteFill,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { GraphicCue } from "./types";

const CueCard: React.FC<{ cue: GraphicCue }> = ({ cue }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const totalFrames = Math.max(1, Math.round(cue.duration * fps));

  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 140 } });
  const exit = spring({
    frame: Math.max(0, frame - (totalFrames - Math.round(fps * 0.35))),
    fps,
    config: { damping: 16, stiffness: 160 },
  });
  const progress = Math.max(0, enter - exit);

  if (cue.type === "lower_third") {
    return (
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "flex-start",
          padding: "0 0 180px 64px",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            transform: `translateX(${(1 - progress) * -60}px)`,
            opacity: progress,
            background: "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
            borderLeft: "6px solid #38BDF8",
            borderRadius: 12,
            padding: "16px 26px",
            boxShadow: "0 16px 40px rgba(0,0,0,0.45)",
            maxWidth: 580,
          }}
        >
          <div
            style={{
              fontFamily: "Inter, system-ui, sans-serif",
              fontSize: 30,
              fontWeight: 700,
              color: "#F8FAFC",
            }}
          >
            {cue.title}
          </div>
          {cue.subtitle ? (
            <div
              style={{
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 20,
                fontWeight: 500,
                color: "#94A3B8",
                marginTop: 4,
              }}
            >
              {cue.subtitle}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  }

  if (cue.type === "stat_card") {
    return (
      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "flex-end",
          padding: "64px 64px 0 0",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            transform: `scale(${0.88 + progress * 0.12})`,
            opacity: progress,
            backgroundColor: "rgba(15, 23, 42, 0.92)",
            border: "2px solid #FACC15",
            borderRadius: 18,
            padding: "22px 30px",
            minWidth: 260,
            textAlign: "right",
            boxShadow: "0 18px 44px rgba(0,0,0,0.5)",
          }}
        >
          {cue.value ? (
            <div
              style={{
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 52,
                fontWeight: 800,
                color: "#FACC15",
                lineHeight: 1.05,
              }}
            >
              {cue.value}
            </div>
          ) : null}
          <div
            style={{
              fontFamily: "Inter, system-ui, sans-serif",
              fontSize: 24,
              fontWeight: 700,
              color: "#F8FAFC",
              marginTop: 6,
            }}
          >
            {cue.title}
          </div>
          {cue.subtitle ? (
            <div
              style={{
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 17,
                color: "#CBD5E1",
                marginTop: 4,
              }}
            >
              {cue.subtitle}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  }

  if (cue.type === "slide_card") {
    return (
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingBottom: 150,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            transform: `translateY(${(1 - progress) * 28}px) scale(${0.96 + progress * 0.04})`,
            opacity: progress,
            backgroundColor: "rgba(16, 21, 20, 0.96)",
            border: "1px solid #597347",
            borderTop: "4px solid #c6ed98",
            borderRadius: 18,
            padding: "40px 48px",
            width: "76%",
            maxWidth: 1120,
            boxShadow: "0 24px 64px rgba(0,0,0,0.58)",
          }}
        >
          {cue.value ? (
            <div
              style={{
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 15,
                fontWeight: 700,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "#c6ed98",
                marginBottom: 12,
              }}
            >
              {cue.value}
            </div>
          ) : null}
          <div
            style={{
              fontFamily: "Inter, system-ui, sans-serif",
              fontSize: 46,
              fontWeight: 700,
              lineHeight: 1.12,
              color: "#edf0de",
            }}
          >
            {cue.title}
          </div>
          {cue.subtitle ? (
            <div
              style={{
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 25,
                lineHeight: 1.45,
                color: "#b9c8bb",
                marginTop: 18,
              }}
            >
              {cue.subtitle}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  }

  if (cue.type === "code_card") {
    const codeText = cue.value || cue.subtitle || "";
    return (
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingBottom: 150,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            transform: `translateY(${(1 - progress) * 24}px)`,
            opacity: progress,
            backgroundColor: "#09120f",
            border: "1px solid #597347",
            borderRadius: 16,
            width: "74%",
            maxWidth: 1080,
            overflow: "hidden",
            boxShadow: "0 24px 60px rgba(0,0,0,0.6)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "14px 24px",
              backgroundColor: "#181e1b",
              borderBottom: "1px solid #303a33",
              fontFamily: "Inter, system-ui, sans-serif",
            }}
          >
            <span style={{ fontSize: 20, fontWeight: 700, color: "#c6ed98" }}>
              {cue.title}
            </span>
            {cue.value && cue.subtitle ? (
              <span style={{ fontSize: 15, color: "#9da89c" }}>{cue.subtitle}</span>
            ) : null}
          </div>
          <pre
            style={{
              margin: 0,
              padding: "24px 28px",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              fontSize: 22,
              lineHeight: 1.55,
              color: "#edf0de",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            <code>{codeText}</code>
          </pre>
        </div>
      </AbsoluteFill>
    );
  }

  if (cue.type === "cursor_highlight") {
    const xPct = Math.min(1, Math.max(0, cue.x ?? 0.5)) * 100;
    const yPct = Math.min(1, Math.max(0, cue.y ?? 0.5)) * 100;
    const pulse = 1 + Math.sin((frame / fps) * Math.PI * 3) * 0.08;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div
          style={{
            position: "absolute",
            left: `${xPct}%`,
            top: `${yPct}%`,
            transform: `translate(-50%, -50%) scale(${(0.7 + progress * 0.3) * pulse})`,
            opacity: progress,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 84,
              height: 84,
              borderRadius: "50%",
              border: "4px solid #f0ae7d",
              backgroundColor: "rgba(240, 174, 125, 0.16)",
              boxShadow: "0 0 0 8px rgba(198, 237, 152, 0.22), 0 12px 32px rgba(0,0,0,0.45)",
            }}
          />
          {cue.title ? (
            <div
              style={{
                backgroundColor: "rgba(16, 21, 20, 0.94)",
                border: "1px solid #f0ae7d",
                borderRadius: 10,
                padding: "6px 14px",
                fontFamily: "Inter, system-ui, sans-serif",
                fontSize: 18,
                fontWeight: 700,
                color: "#edf0de",
                whiteSpace: "nowrap",
              }}
            >
              {cue.title}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  }

  // Default: callout or broll_card
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "flex-start",
        padding: "56px 0 0 64px",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          transform: `translateY(${(1 - progress) * -32}px)`,
          opacity: progress,
          backgroundColor: "rgba(15, 23, 42, 0.9)",
          border: "1px solid rgba(56, 189, 248, 0.55)",
          borderRadius: 14,
          padding: "16px 24px",
          maxWidth: 520,
          boxShadow: "0 14px 36px rgba(0,0,0,0.45)",
        }}
      >
        <div
          style={{
            fontFamily: "Inter, system-ui, sans-serif",
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#38BDF8",
          }}
        >
          {cue.type === "broll_card" ? "Visual Note" : "Key Point"}
        </div>
        <div
          style={{
            fontFamily: "Inter, system-ui, sans-serif",
            fontSize: 28,
            fontWeight: 700,
            color: "#FFFFFF",
            marginTop: 4,
          }}
        >
          {cue.title}
        </div>
        {cue.subtitle ? (
          <div
            style={{
              fontFamily: "Inter, system-ui, sans-serif",
              fontSize: 19,
              color: "#CBD5E1",
              marginTop: 4,
            }}
          >
            {cue.subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const GraphicsOverlay: React.FC<{ cues: GraphicCue[] }> = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {cues.map((cue) => {
        const from = Math.max(0, Math.round(cue.start * fps));
        const durationInFrames = Math.max(1, Math.round(cue.duration * fps));
        return (
          <Sequence key={cue.id} from={from} durationInFrames={durationInFrames}>
            <CueCard cue={cue} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
