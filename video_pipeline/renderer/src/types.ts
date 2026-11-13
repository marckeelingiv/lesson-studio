export interface RemappedWord {
  text: string;
  startMs: number;
  endMs: number;
}

export type GraphicType =
  | "lower_third"
  | "callout"
  | "stat_card"
  | "broll_card"
  | "slide_card"
  | "code_card"
  | "cursor_highlight";

export interface GraphicCue {
  id: string;
  type: GraphicType;
  start: number;
  duration: number;
  title: string;
  subtitle?: string;
  value?: string;
  x?: number;
  y?: number;
}

export type TimelineManifest = {
  videoFile: string;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  captionsEnabled: boolean;
  captions: RemappedWord[];
  graphicCues: GraphicCue[];
};
