#!/usr/bin/env node
/**
 * HyperFrames Project Compiler (Starter Asset Pack v0.1)
 *
 * Compiles storyboard.json + timeline_manifest.json + tokens.css into a self-contained
 * HyperFrames project with sub-compositions, fixed lower-center captions, local GSAP,
 * and dom_layout_manifest.json for automated QC gates.
 */

import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const HYPERFRAMES_DIR = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(HYPERFRAMES_DIR, "..", "..");
const ASSETS_DIR = path.join(REPO_ROOT, "editing_system", "assets");
const DEFAULT_TOKENS_CSS = path.join(
  ASSETS_DIR,
  "tokens",
  "engineering-editorial",
  "tokens.css",
);
const LOCAL_GSAP_MIN = path.join(
  HYPERFRAMES_DIR,
  "node_modules",
  "gsap",
  "dist",
  "gsap.min.js",
);

const VIDEO_EXTS = new Set([".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"]);
const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"]);

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeId(raw, fallbackPrefix) {
  const cleaned = String(raw || fallbackPrefix)
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (!cleaned) return fallbackPrefix;
  return /^[a-zA-Z]/.test(cleaned) ? cleaned : `${fallbackPrefix}-${cleaned}`;
}

function normalizeLayout(raw) {
  const key = String(raw || "full-graphic")
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-");
  if (key === "center") return "centre";
  if (
    key === "full-screen" ||
    key === "panel" ||
    key === "centre" ||
    key === "full-graphic" ||
    key === "circle"
  ) {
    return key;
  }
  return "full-graphic";
}

function normalizeTransition(raw) {
  const key = String(raw || "subtle")
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-");
  if (key === "swipe" || key === "zoom" || key === "subtle" || key === "none") {
    return key;
  }
  if (key === "hard-cut") return "none";
  return "subtle";
}

function detectTemplateKind(beat) {
  const vd = beat.visual_data && typeof beat.visual_data === "object" ? beat.visual_data : {};
  const explicit = String(vd.framework || vd.hero || vd.template || "").toLowerCase();
  const assetIds = Array.isArray(beat.asset_ids)
    ? beat.asset_ids.map((id) => String(id).toLowerCase())
    : [];
  const allHints = [explicit, ...assetIds].join(" ");

  if (allHints.includes("engineering-section-deck") || allHints.includes("section-deck")) {
    return "hero-engineering-section-deck";
  }
  if (allHints.includes("linear-steps")) return "framework-linear-steps";
  if (allHints.includes("non-linear-pillars")) return "framework-non-linear-pillars";
  if (allHints.includes("cyclical-loop")) return "framework-cyclical-loop";
  if (allHints.includes("hierarchical-tree")) return "framework-hierarchical-tree";
  if (allHints.includes("matrix-2x2")) return "framework-matrix-2x2";
  return null;
}

function parsePairs(items, fallback) {
  const source = Array.isArray(items) && items.length > 0 ? items : fallback;
  return source.map((entry) => {
    if (entry && typeof entry === "object") {
      return {
        num: entry.num ? String(entry.num) : "",
        label: String(entry.label || entry.title || entry.name || ""),
        detail: String(entry.detail || entry.summary || entry.body || ""),
      };
    }
    const text = String(entry ?? "");
    const pipeIdx = text.indexOf("|");
    if (pipeIdx !== -1) {
      return {
        num: "",
        label: text.slice(0, pipeIdx).trim(),
        detail: text.slice(pipeIdx + 1).trim(),
      };
    }
    const colonIdx = text.indexOf(":");
    if (colonIdx > 0 && colonIdx < 32) {
      return {
        num: "",
        label: text.slice(0, colonIdx).trim(),
        detail: text.slice(colonIdx + 1).trim(),
      };
    }
    return { num: "", label: text, detail: "" };
  });
}

function resolveExistingMedia(ref, searchDirs) {
  if (!ref || typeof ref !== "string") return null;
  const trimmed = ref.trim();
  if (!trimmed || /^(https?:|data:|blob:)/i.test(trimmed)) return null;
  if (path.isAbsolute(trimmed) && existsSync(trimmed)) {
    return trimmed;
  }
  for (const dir of searchDirs) {
    if (!dir) continue;
    const candidate = path.resolve(dir, trimmed);
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function probeMediaHasAudio(filePath) {
  if (!filePath || !existsSync(filePath)) return false;
  try {
    const out = execFileSync(
      "ffprobe",
      [
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        filePath,
      ],
      { encoding: "utf-8", stdio: ["ignore", "pipe", "ignore"] },
    );
    return out.trim().length > 0;
  } catch {
    return false;
  }
}

function groupCaptionWords(words) {
  if (!Array.isArray(words) || words.length === 0) return [];
  const groups = [];
  let bucket = [];

  const flush = () => {
    if (bucket.length === 0) return;
    const first = bucket[0];
    const last = bucket[bucket.length - 1];
    const start = Math.max(0, Number(first.startMs || 0) / 1000);
    const rawEnd = Number(last.endMs || 0) / 1000;
    const end = Math.max(start + 0.4, rawEnd);
    groups.push({
      id: `cg-${groups.length}`,
      start: Number(start.toFixed(3)),
      end: Number(end.toFixed(3)),
      words: bucket.map((w, idx) => {
        const wStart = Math.max(start, Number(w.startMs || 0) / 1000);
        const wEnd = Math.max(wStart + 0.05, Number(w.endMs || 0) / 1000);
        return {
          id: `cg-${groups.length}-w-${idx}`,
          text: String(w.text ?? "").trim(),
          start: Number(wStart.toFixed(3)),
          end: Number(wEnd.toFixed(3)),
        };
      }),
    });
    bucket = [];
  };

  for (const w of words) {
    const text = String(w.text ?? "").trim();
    if (!text) continue;
    if (bucket.length > 0) {
      const prev = bucket[bucket.length - 1];
      const gapMs = Number(w.startMs || 0) - Number(prev.endMs || 0);
      const charCount = bucket.reduce((acc, item) => acc + String(item.text || "").length + 1, 0);
      const prevText = String(prev.text || "").trim();
      if (
        bucket.length >= 7 ||
        charCount + text.length > 44 ||
        gapMs > 420 ||
        /[.!?]$/.test(prevText)
      ) {
        flush();
      }
    }
    bucket.push(w);
  }
  flush();

  for (let i = 0; i < groups.length - 1; i += 1) {
    if (groups[i].end > groups[i + 1].start) {
      groups[i].end = groups[i + 1].start;
    }
  }
  return groups;
}

function renderInnerFrameworkOrHero(templateKind, beat, safeId) {
  const vd = beat.visual_data && typeof beat.visual_data === "object" ? beat.visual_data : {};
  const kicker = escapeHtml(vd.kicker || beat.subtitle || "SYSTEM MODEL");
  const title = escapeHtml(beat.title || "Engineering Concept");

  if (templateKind === "hero-engineering-section-deck") {
    const chapters = Array.isArray(vd.chapters) && vd.chapters.length > 0
      ? vd.chapters
      : parsePairs(beat.items, [
          "Signal Ingest:Probe VFR & build word timestamps",
          "Scientific Sift:Cut dead space with tail protection",
          "Storyboard:Map beats to 5 Scene Layouts",
          "Verify QC:Pass all 8 blocking checks",
        ]).map((p, idx) => ({
          num: p.num || `0${idx + 1}`,
          title: p.label,
          summary: p.detail,
        }));
    const activeIndex = Number.isFinite(Number(vd.activeIndex))
      ? Math.max(0, Math.min(chapters.length - 1, Number(vd.activeIndex)))
      : 0;
    const cardsHtml = chapters
      .map((ch, idx) => {
        const isActive = idx === activeIndex;
        const num = escapeHtml(ch.num || `0${idx + 1}`);
        const cTitle = escapeHtml(ch.title || ch.label || `Chapter ${idx + 1}`);
        const summary = escapeHtml(ch.summary || ch.detail || "");
        return `
          <div class="hf-hero-chapter-card${isActive ? " is-active" : ""}">
            <div class="hf-hero-card-top">
              <span class="hf-hero-card-num">${num}</span>
              ${isActive ? '<span class="hf-hero-card-badge">ACTIVE</span>' : ""}
            </div>
            <div>
              <h2 class="hf-hero-card-title">${cTitle}</h2>
              ${summary ? `<p class="hf-hero-card-summary">${summary}</p>` : ""}
            </div>
            <div class="hf-hero-card-bar"><div class="hf-hero-card-bar-fill"></div></div>
          </div>`;
      })
      .join("\n");

    return {
      html: `
        <div id="${safeId}-deck" class="hf-hero-deck-shell">
          <div class="hf-hero-deck-header">
            <div>
              <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
              <h1 id="${safeId}-title" class="hf-title">${title}</h1>
            </div>
            <div class="hf-hero-deck-meta">0${activeIndex + 1} / 0${chapters.length}</div>
          </div>
          <div id="${safeId}-rail" class="hf-hero-deck-rail">${cardsHtml}</div>
        </div>`,
      animScript: `
        window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
        window.LessonMotion.cards(tl, "#${safeId}-rail .hf-hero-chapter-card", { at: 0.06, stagger: 0.08 });`,
    };
  }

  if (templateKind === "framework-linear-steps") {
    const pairs = parsePairs(beat.items, ["Step 01:First stage", "Step 02:Second stage", "Step 03:Third stage"]);
    const activeStep = Number.isFinite(Number(vd.activeStep)) ? Number(vd.activeStep) : -1;
    const stepsHtml = pairs
      .map((pair, idx) => {
        const arrow =
          idx < pairs.length - 1
            ? `<svg class="hf-fw-arrow" viewBox="0 0 40 40" fill="none"><path class="hf-fw-arrow-path" d="M6 20 H32 M23 11 L32 20 L23 29" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
            : "";
        return `
          <div class="hf-fw-step-wrap">
            <div class="hf-fw-step-card${idx === activeStep ? " is-active" : ""}">
              <div class="hf-fw-step-num">0${idx + 1}</div>
              <div class="hf-fw-step-title">${escapeHtml(pair.label)}</div>
              ${pair.detail ? `<div class="hf-fw-step-detail">${escapeHtml(pair.detail)}</div>` : ""}
            </div>
            ${arrow}
          </div>`;
      })
      .join("\n");

    return {
      html: `
        <div class="hf-fw-shell">
          <div class="hf-fw-header">
            <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
            <h1 id="${safeId}-title" class="hf-title">${title}</h1>
          </div>
          <div class="hf-fw-stage"><div id="${safeId}-track" class="hf-fw-linear-track">${stepsHtml}</div></div>
        </div>`,
      animScript: `
        window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
        window.LessonMotion.cards(tl, "#${safeId}-track .hf-fw-step-card", { at: 0.06, stagger: 0.09 });
        window.LessonMotion.circlesAndMarks(tl, "#${safeId}-track .hf-fw-arrow-path", { at: 0.16, stagger: 0.09 });`,
    };
  }

  if (templateKind === "framework-non-linear-pillars") {
    const pairs = parsePairs(beat.items, ["Rules:Invariants", "Brief:Direction", "Assets:Templates"]);
    const hubTitle = escapeHtml(vd.hubTitle || beat.body || "Unified System Core");
    const pillarsHtml = pairs
      .map(
        (pair, idx) => `
          <div class="hf-fw-pillar-card">
            <div class="hf-fw-step-num">P${idx + 1}</div>
            <div class="hf-fw-step-title">${escapeHtml(pair.label)}</div>
            ${pair.detail ? `<div class="hf-fw-step-detail">${escapeHtml(pair.detail)}</div>` : ""}
          </div>`,
      )
      .join("\n");

    return {
      html: `
        <div class="hf-fw-shell">
          <div class="hf-fw-header">
            <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
            <h1 id="${safeId}-title" class="hf-title">${title}</h1>
          </div>
          <div class="hf-fw-stage">
            <div class="hf-fw-pillars-layout">
              <div id="${safeId}-hub" class="hf-fw-hub-banner">
                <span class="hf-fw-hub-label">CORE</span>
                <span class="hf-fw-hub-title">${hubTitle}</span>
              </div>
              <div id="${safeId}-grid" class="hf-fw-pillars-grid">${pillarsHtml}</div>
            </div>
          </div>
        </div>`,
      animScript: `
        window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
        window.LessonMotion.slides(tl, "#${safeId}-hub", { at: 0.05, y: -10, x: 0 });
        window.LessonMotion.cards(tl, "#${safeId}-grid .hf-fw-pillar-card", { at: 0.12, stagger: 0.08 });`,
    };
  }

  if (templateKind === "framework-cyclical-loop") {
    const pairs = parsePairs(beat.items, ["Plan:Storyboard", "Render:Stills", "Verify:QC", "Refine:Taste Log"]).slice(0, 4);
    const pos = ["top", "right", "bottom", "left"];
    const nodesHtml = pairs
      .map(
        (pair, idx) => `
          <div class="hf-fw-cycle-node hf-fw-cycle-node--${pos[idx]}">
            <div class="hf-fw-step-num">0${idx + 1} · ${escapeHtml(pair.label)}</div>
            ${pair.detail ? `<div class="hf-fw-step-detail">${escapeHtml(pair.detail)}</div>` : ""}
          </div>`,
      )
      .join("\n");

    return {
      html: `
        <div class="hf-fw-shell">
          <div class="hf-fw-header">
            <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
            <h1 id="${safeId}-title" class="hf-title">${title}</h1>
          </div>
          <div class="hf-fw-stage">
            <div id="${safeId}-cycle" class="hf-fw-cycle-grid">
              <svg class="hf-fw-cycle-ring" viewBox="0 0 220 220" fill="none">
                <circle class="hf-fw-cycle-arc" cx="110" cy="110" r="82" stroke="var(--border-strong)" stroke-width="6"/>
                <path class="hf-fw-cycle-arc" d="M110 28 A82 82 0 0 1 192 110" stroke="var(--accent-primary)" stroke-width="8" stroke-linecap="round"/>
                <path class="hf-fw-cycle-arc" d="M110 192 A82 82 0 0 1 28 110" stroke="var(--accent-secondary)" stroke-width="8" stroke-linecap="round"/>
              </svg>
              ${nodesHtml}
            </div>
          </div>
        </div>`,
      animScript: `
        window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
        window.LessonMotion.circlesAndMarks(tl, "#${safeId}-cycle .hf-fw-cycle-arc", { at: 0.08, stagger: 0.08 });
        window.LessonMotion.cards(tl, "#${safeId}-cycle .hf-fw-cycle-node", { at: 0.14, stagger: 0.08 });`,
    };
  }

  if (templateKind === "framework-hierarchical-tree") {
    const pairs = parsePairs(beat.items, ["Video:A-Roll", "Overlay:Motion Plates", "Audio:Speech + Bed"]).slice(0, 3);
    const rootLabel = escapeHtml(vd.rootLabel || beat.body || "Canonical Timeline (.otio)");
    const branchesHtml = pairs
      .map(
        (pair, idx) => `
          <div class="hf-fw-tree-branch">
            <div class="hf-fw-step-num">TIER 0${idx + 1}</div>
            <div class="hf-fw-step-title">${escapeHtml(pair.label)}</div>
            ${pair.detail ? `<div class="hf-fw-tree-leaf">${escapeHtml(pair.detail)}</div>` : ""}
          </div>`,
      )
      .join("\n");

    return {
      html: `
        <div class="hf-fw-shell">
          <div class="hf-fw-header">
            <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
            <h1 id="${safeId}-title" class="hf-title">${title}</h1>
          </div>
          <div class="hf-fw-stage">
            <div class="hf-fw-tree-layout">
              <div id="${safeId}-root-node" class="hf-fw-tree-root">
                <div class="hf-fw-step-num">ROOT</div>
                <div class="hf-fw-step-title">${rootLabel}</div>
              </div>
              <svg class="hf-fw-tree-connectors" viewBox="0 0 1200 76" fill="none">
                <path class="hf-fw-tree-edge" d="M600 0 V38" stroke="var(--accent-primary)" stroke-width="4"/>
                <path class="hf-fw-tree-edge" d="M200 38 H1000" stroke="var(--border-strong)" stroke-width="4"/>
                <path class="hf-fw-tree-edge" d="M200 38 V76" stroke="var(--accent-secondary)" stroke-width="4"/>
                <path class="hf-fw-tree-edge" d="M600 38 V76" stroke="var(--accent-primary)" stroke-width="4"/>
                <path class="hf-fw-tree-edge" d="M1000 38 V76" stroke="var(--accent-secondary)" stroke-width="4"/>
              </svg>
              <div id="${safeId}-branches" class="hf-fw-tree-branches">${branchesHtml}</div>
            </div>
          </div>
        </div>`,
      animScript: `
        window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
        window.LessonMotion.cards(tl, "#${safeId}-root-node", { at: 0.04 });
        window.LessonMotion.circlesAndMarks(tl, "#${safeId}-branches, .hf-fw-tree-edge", { at: 0.12 });`,
    };
  }

  // framework-matrix-2x2
  const pairs = parsePairs(beat.items, ["Q1:High Clarity", "Q2:Reusable Core", "Q3:Raw Cut", "Q4:Slop"]).slice(0, 4);
  const highlightIdx = Number.isFinite(Number(vd.highlightIndex)) ? Number(vd.highlightIndex) : 1;
  const cellsHtml = pairs
    .map(
      (pair, idx) => `
        <div class="hf-fw-matrix-cell${idx === highlightIdx ? " is-highlighted" : ""}">
          <div class="hf-fw-step-num">Q${idx + 1}</div>
          <div class="hf-fw-step-title">${escapeHtml(pair.label)}</div>
          ${pair.detail ? `<div class="hf-fw-step-detail">${escapeHtml(pair.detail)}</div>` : ""}
        </div>`,
    )
    .join("\n");

  return {
    html: `
      <div class="hf-fw-shell">
        <div class="hf-fw-header">
          <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
          <h1 id="${safeId}-title" class="hf-title">${title}</h1>
        </div>
        <div class="hf-fw-stage">
          <div class="hf-fw-matrix-wrap">
            <div class="hf-fw-matrix-yaxis">${escapeHtml(vd.yAxis || "Clarity")}</div>
            <div id="${safeId}-matrix" class="hf-fw-matrix-grid">${cellsHtml}</div>
            <div class="hf-fw-matrix-xaxis">${escapeHtml(vd.xAxis || "Reuse")}</div>
          </div>
        </div>
      </div>`,
    animScript: `
      window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.cards(tl, "#${safeId}-matrix .hf-fw-matrix-cell", { at: 0.08, stagger: 0.08 });`,
  };
}

function buildBeatSubComposition(beat, safeId, opts) {
  const layout = normalizeLayout(beat.scene_layout);
  const transition = normalizeTransition(beat.transition);
  const templateKind = detectTemplateKind(beat);
  const vd = beat.visual_data && typeof beat.visual_data === "object" ? beat.visual_data : {};
  const kicker = escapeHtml(vd.kicker || layout.replace("-", " ").toUpperCase());
  const title = escapeHtml(beat.title || "Engineering Lesson Beat");
  const subtitle = escapeHtml(beat.subtitle || beat.body || "");
  const holdAttr = Number(beat.duration || 0) > 2.8 ? ' data-hold="true"' : "";
  const hasVideo = Boolean(opts.videoSrc);
  const imageRel = opts.imageSrc ? `../${opts.imageSrc}` : "";

  let innerHtml = "";
  let animScript = "";

  if (layout === "full-screen") {
    const backdropClass = hasVideo
      ? "hf-fullscreen-backdrop"
      : "hf-fullscreen-backdrop hf-fullscreen-backdrop--empty";
    const backdropBody = hasVideo
      ? ""
      : imageRel
        ? `<img class="hf-fullscreen-media" src="${escapeHtml(imageRel)}" alt="${title}" />`
        : `<div class="hf-fullscreen-placeholder"><span>${escapeHtml(vd.speakerLabel || "A-Roll Speaker Frame")}</span></div>`;

    innerHtml = `
      <div class="hf-stage${hasVideo ? " hf-stage--transparent" : ""}"${holdAttr}>
        <div id="${safeId}-layer" class="hf-transition-layer hf-layout-full-screen${hasVideo ? " hf-layout-full-screen--transparent" : ""}">
          <div class="${backdropClass}">${backdropBody}</div>
          <div id="${safeId}-thesis" class="hf-fullscreen-thesis">
            <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
            <h1 id="${safeId}-title" class="hf-title">${title}</h1>
            ${subtitle ? `<p id="${safeId}-subtitle" class="hf-subtitle">${subtitle}</p>` : ""}
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      window.LessonMotion.textEntrances(tl, ["#${safeId}-title"${subtitle ? `, "#${safeId}-subtitle"` : ""}], { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.cards(tl, "#${safeId}-thesis", { at: 0.04 });`;
  } else if (layout === "panel") {
    const speakerRight = vd.speakerSide === "right";
    const pairs = parsePairs(beat.items, beat.body ? [beat.body] : ["Verified pipeline telemetry"]);
    const listItems = pairs
      .map((p, idx) => {
        const line = p.detail ? `${p.label}: ${p.detail}` : p.label;
        return `<li class="hf-panel-item"><span class="hf-panel-bullet">0${idx + 1}</span><span>${escapeHtml(line)}</span></li>`;
      })
      .join("\n");

    const speakerSlot = hasVideo
      ? `<div class="hf-panel-speaker hf-panel-speaker--transparent"></div>`
      : `<div class="hf-panel-speaker">${imageRel ? `<img class="hf-panel-speaker-media" src="${escapeHtml(imageRel)}" alt="Speaker" />` : ""}<div class="hf-panel-speaker-tag">${escapeHtml(vd.speakerLabel || "Speaker Feed")}</div></div>`;

    innerHtml = `
      <div class="hf-stage${hasVideo ? " hf-stage--transparent" : ""}"${holdAttr}>
        <div class="hf-safe-frame">
          <div id="${safeId}-layer" class="hf-transition-layer hf-layout-panel${speakerRight ? " hf-layout-panel--speaker-right" : ""}">
            ${speakerSlot}
            <div class="hf-panel-content">
              <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
              <h1 id="${safeId}-title" class="hf-title">${title}</h1>
              ${subtitle ? `<p id="${safeId}-subtitle" class="hf-subtitle">${subtitle}</p>` : ""}
              <ul id="${safeId}-list" class="hf-panel-list">${listItems}</ul>
            </div>
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      window.LessonMotion.textEntrances(tl, ["#${safeId}-title"${subtitle ? `, "#${safeId}-subtitle"` : ""}], { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.cards(tl, "#${safeId}-list .hf-panel-item", { at: 0.1, stagger: 0.08 });`;
  } else if (layout === "centre") {
    const leftPoints = Array.isArray(vd.leftPoints)
      ? vd.leftPoints
      : Array.isArray(beat.items) && beat.items.length >= 2
        ? [beat.items[0]]
        : ["Manual single-pass edits"];
    const rightPoints = Array.isArray(vd.rightPoints)
      ? vd.rightPoints
      : Array.isArray(beat.items) && beat.items.length >= 2
        ? [beat.items[1]]
        : ["Deterministic gated pipeline"];
    const renderPts = (pts) =>
      pts.map((pt) => `<li class="hf-centre-point">${escapeHtml(typeof pt === "string" ? pt : JSON.stringify(pt))}</li>`).join("\n");

    innerHtml = `
      <div class="hf-stage${hasVideo ? " hf-stage--transparent" : ""}"${holdAttr}>
        <div class="hf-safe-frame">
          <div id="${safeId}-layer" class="hf-transition-layer hf-layout-centre">
            <div class="hf-centre-header">
              <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
              <h1 id="${safeId}-title" class="hf-title">${title}</h1>
            </div>
            <div class="hf-centre-columns">
              <div id="${safeId}-left" class="hf-centre-card hf-centre-card--left">
                <div class="hf-centre-card-label">${escapeHtml(vd.leftLabel || "BEFORE")}</div>
                <ul class="hf-centre-points">${renderPts(leftPoints)}</ul>
              </div>
              <div class="hf-centre-speaker${hasVideo ? " hf-centre-speaker--transparent" : ""}">
                ${hasVideo ? "" : `<div class="hf-panel-speaker-tag">${escapeHtml(vd.speakerLabel || "Speaker Centre")}</div>`}
              </div>
              <div id="${safeId}-right" class="hf-centre-card hf-centre-card--right">
                <div class="hf-centre-card-label">${escapeHtml(vd.rightLabel || "AFTER")}</div>
                <ul class="hf-centre-points">${renderPts(rightPoints)}</ul>
              </div>
            </div>
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      window.LessonMotion.textEntrances(tl, "#${safeId}-title", { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.slides(tl, "#${safeId}-left", { at: 0.08, x: -24 });
      window.LessonMotion.slides(tl, "#${safeId}-right", { at: 0.12, x: 24 });`;
  } else if (layout === "circle") {
    const pipCorner = vd.pipCorner || "bottom-right";
    const mediaBox = imageRel
      ? `<img src="${escapeHtml(imageRel)}" alt="${title}" />`
      : `<div class="hf-fullscreen-placeholder"><span>${escapeHtml(beat.body || "UI & Architecture Walkthrough")}</span></div>`;

    innerHtml = `
      <div class="hf-stage${hasVideo ? " hf-stage--transparent" : ""}"${holdAttr}>
        <div class="hf-safe-frame">
          <div id="${safeId}-layer" class="hf-transition-layer hf-layout-circle">
            <div class="hf-circle-canvas">
              <div>
                <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
                <h1 id="${safeId}-title" class="hf-title">${title}</h1>
                ${subtitle ? `<p id="${safeId}-subtitle" class="hf-subtitle">${subtitle}</p>` : ""}
              </div>
              <div class="hf-circle-media-box">${mediaBox}</div>
            </div>
            <div id="${safeId}-pip" class="hf-circle-pip hf-circle-pip--${escapeHtml(pipCorner)}${hasVideo ? " hf-circle-pip--transparent" : ""}"${hasVideo ? ' style="z-index: 25; pointer-events: none;"' : ""}>
              ${hasVideo ? "" : `<span class="hf-circle-pip-label">${escapeHtml(vd.speakerLabel || "PiP")}</span>`}
            </div>
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      window.LessonMotion.textEntrances(tl, ["#${safeId}-title"${subtitle ? `, "#${safeId}-subtitle"` : ""}], { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.circlesAndMarks(tl, "#${safeId}-pip", { at: 0.1 });`;
  } else if (templateKind) {
    // full-graphic with embedded framework or hero deck
    const nested = renderInnerFrameworkOrHero(templateKind, beat, safeId);
    innerHtml = `
      <div class="hf-stage"${holdAttr}>
        <div class="hf-safe-frame">
          <div id="${safeId}-layer" class="hf-transition-layer">
            ${nested.html}
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      ${nested.animScript}`;
  } else {
    // default full-graphic
    const pairs = parsePairs(beat.items, beat.body ? [beat.body] : ["Stage 01:Structured evidence"]);
    const metricVal = vd.metricValue;
    const metricHtml =
      metricVal !== undefined && metricVal !== null && metricVal !== ""
        ? `<div class="hf-graphic-metric-box">
             <span id="${safeId}-metric" class="hf-graphic-metric-value">${escapeHtml(String(metricVal))}${escapeHtml(vd.metricSuffix || "")}</span>
             <span class="hf-graphic-metric-label">${escapeHtml(vd.metricLabel || "Verified")}</span>
           </div>`
        : "";
    const cardsHtml = pairs
      .map(
        (pair, idx) => `
          <div class="hf-graphic-node">
            <div class="hf-graphic-node-index">0${idx + 1}</div>
            <div class="hf-graphic-node-title">${escapeHtml(pair.label)}</div>
            ${pair.detail ? `<div class="hf-graphic-node-detail">${escapeHtml(pair.detail)}</div>` : ""}
          </div>`,
      )
      .join("\n");

    innerHtml = `
      <div class="hf-stage"${holdAttr}>
        <div class="hf-safe-frame">
          <div id="${safeId}-layer" class="hf-transition-layer hf-layout-full-graphic">
            <div class="hf-graphic-header">
              <div class="hf-graphic-title-group">
                <div class="hf-kicker"><span class="hf-kicker-rule" data-layout-ignore></span><span>${kicker}</span></div>
                <h1 id="${safeId}-title" class="hf-title">${title}</h1>
                ${subtitle ? `<p id="${safeId}-subtitle" class="hf-subtitle">${subtitle}</p>` : ""}
              </div>
              ${metricHtml}
            </div>
            <div id="${safeId}-board" class="hf-graphic-board">${cardsHtml}</div>
          </div>
        </div>
      </div>`;
    animScript = `
      window.LessonMotion.applyTransition(tl, "#${safeId}-layer", "${transition}", { at: 0 });
      window.LessonMotion.textEntrances(tl, ["#${safeId}-title"${subtitle ? `, "#${safeId}-subtitle"` : ""}], { at: 0, keepFrameZeroVisible: true });
      window.LessonMotion.cards(tl, "#${safeId}-board .hf-graphic-node", { at: 0.08, stagger: 0.08 });`;
  }

  return `<template>
  <style>
    #root {
      position: absolute;
      inset: 0;
    }
  </style>
  <div id="root" data-composition-id="${safeId}" data-width="${opts.width}" data-height="${opts.height}">
    ${innerHtml}
  </div>
  <script>
    (function () {
      var tl = window.LessonMotion.createTimeline("${safeId}");
      ${animScript}
      window.__timelines = window.__timelines || {};
      window.__timelines["${safeId}"] = tl;
    })();
  </script>
</template>
`;
}

function buildCaptionsSubComposition(captionGroups, width, height, theme) {
  const groupsHtml = captionGroups
    .map((group) => {
      const wordsHtml = group.words
        .map(
          (w) =>
            `<span id="${w.id}" class="hf-caption-word">${escapeHtml(w.text)}</span>`,
        )
        .join(" ");
      return `
        <div id="${group.id}" class="hf-caption-group" data-layout-allow-caption-zone>
          <div class="hf-caption-pill" data-layout-allow-caption-zone>${wordsHtml}</div>
        </div>`;
    })
    .join("\n");

  const payload = JSON.stringify(
    captionGroups.map((g) => ({
      selector: `#${g.id}`,
      start: g.start,
      end: g.end,
      words: g.words.map((w) => ({
        selector: `#${w.id}`,
        start: w.start,
        end: w.end,
      })),
    })),
  );

  return `<template>
  <style>
    #root {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }
  </style>
  <div id="root" data-composition-id="captions-layer" data-width="${width}" data-height="${height}">
    <div id="captions-anchor" class="hf-caption-anchor" data-layout-allow-caption-zone>
      ${groupsHtml}
    </div>
  </div>
  <script>
    (function () {
      var tl = window.LessonMotion.createTimeline("captions-layer");
      var groups = ${payload};
      window.LessonMotion.captions(tl, groups, { theme: "${theme}" });
      window.__timelines = window.__timelines || {};
      window.__timelines["captions-layer"] = tl;
    })();
  </script>
</template>
`;
}

function computeOverlayBoxes(beats, width, height) {
  const safeX = Math.round(width * 0.05);
  const safeY = Math.round(height * 0.05);
  const captionBox = {
    x: 260,
    y: height - 72 - 84,
    w: width - 520,
    h: 84,
  };
  const innerW = width - safeX * 2;
  const contentBottom = captionBox.y - 34; // 890px
  const contentH = contentBottom - safeY; // 836px

  const overlayBoxes = [];
  for (const beat of beats) {
    const start = Number(beat.start || 0);
    const end = Number((start + Number(beat.duration || 0)).toFixed(3));
    const layout = normalizeLayout(beat.scene_layout);
    const vd = beat.visual_data && typeof beat.visual_data === "object" ? beat.visual_data : {};

    if (layout === "full-screen") {
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: safeX,
        y: contentBottom - 200,
        w: Math.min(1040, innerW),
        h: 200,
        kind: "overlay_card",
      });
    } else if (layout === "panel") {
      const speakerRight = vd.speakerSide === "right";
      const speakerW = Math.round((innerW - 32) * 0.42);
      const panelW = innerW - 32 - speakerW;
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: speakerRight ? safeX + panelW + 32 : safeX,
        y: safeY,
        w: speakerW,
        h: contentH,
        kind: "speaker_panel",
      });
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: speakerRight ? safeX : safeX + speakerW + 32,
        y: safeY,
        w: panelW,
        h: contentH,
        kind: "panel_content",
      });
    } else if (layout === "centre") {
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: safeX,
        y: safeY,
        w: innerW,
        h: 96,
        kind: "header",
      });
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: safeX + 540 + 24,
        y: safeY + 120,
        w: 584,
        h: contentH - 120,
        kind: "speaker_centre",
      });
    } else if (layout === "circle") {
      const pipCorner = vd.pipCorner || "bottom-right";
      const pipX = pipCorner.includes("left") ? safeX + 24 : width - safeX - 24 - 240;
      const pipY = pipCorner.includes("top") ? safeY + 24 : contentBottom - 24 - 240;
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: safeX,
        y: safeY,
        w: innerW,
        h: contentH,
        kind: "circle_stage",
      });
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: pipX,
        y: pipY,
        w: 240,
        h: 240,
        kind: "speaker_pip",
      });
    } else {
      overlayBoxes.push({
        beat_id: beat.id,
        start,
        end,
        x: safeX,
        y: safeY,
        w: innerW,
        h: contentH,
        kind: "full_graphic",
      });
    }
  }

  return {
    width,
    height,
    safe_margin_x: safeX,
    safe_margin_y: safeY,
    caption_box: captionBox,
    overlay_boxes: overlayBoxes,
  };
}

function main() {
  const { values } = parseArgs({
    options: {
      storyboard: { type: "string" },
      manifest: { type: "string" },
      tokens: { type: "string" },
      theme: { type: "string", default: "dark" },
      out: { type: "string" },
      "media-dir": { type: "string" },
    },
    strict: true,
  });

  if (!values.storyboard || !values.manifest || !values.out) {
    console.error(
      "Usage: compose.mjs --storyboard <path> --manifest <path> --out <dir> [--tokens <tokens.css>] [--theme dark|light] [--media-dir <dir>]",
    );
    process.exit(2);
  }

  const storyboardPath = path.resolve(values.storyboard);
  const manifestPath = path.resolve(values.manifest);
  const tokensPath = path.resolve(values.tokens || DEFAULT_TOKENS_CSS);
  const outDir = path.resolve(values.out);
  const theme = values.theme === "light" ? "light" : "dark";
  const mediaDir = values["media-dir"] ? path.resolve(values["media-dir"]) : null;

  const storyboardRaw = JSON.parse(readFileSync(storyboardPath, "utf-8"));
  const manifestRaw = JSON.parse(readFileSync(manifestPath, "utf-8"));

  const beats = Array.isArray(storyboardRaw)
    ? storyboardRaw
    : Array.isArray(storyboardRaw.beats)
      ? storyboardRaw.beats
      : [];
  if (beats.length === 0) {
    throw new Error(`Storyboard contains no beats: ${storyboardPath}`);
  }

  const width = Number(manifestRaw.width || 1920);
  const height = Number(manifestRaw.height || 1080);
  const fps = Number(manifestRaw.fps || 30);
  const manifestDuration =
    manifestRaw.durationInFrames && fps > 0
      ? Number((manifestRaw.durationInFrames / fps).toFixed(3))
      : 0;
  const beatsEnd = Math.max(
    ...beats.map((b) => Number(b.start || 0) + Number(b.duration || 0)),
  );
  const totalDuration = Number(Math.max(manifestDuration, beatsEnd, 0.5).toFixed(3));

  const compositionsDir = path.join(outDir, "compositions");
  const vendorDir = path.join(outDir, "vendor");
  const outMediaDir = path.join(outDir, "media");
  mkdirSync(compositionsDir, { recursive: true });
  mkdirSync(vendorDir, { recursive: true });
  mkdirSync(outMediaDir, { recursive: true });

  // Copy design tokens, vendor GSAP, motion helpers, and stylesheets locally
  copyFileSync(tokensPath, path.join(outDir, "tokens.css"));
  copyFileSync(LOCAL_GSAP_MIN, path.join(vendorDir, "gsap.min.js"));
  copyFileSync(
    path.join(ASSETS_DIR, "motion", "transitions.css"),
    path.join(outDir, "transitions.css"),
  );
  copyFileSync(
    path.join(ASSETS_DIR, "motion", "mechanics.js"),
    path.join(outDir, "mechanics.js"),
  );
  copyFileSync(
    path.join(ASSETS_DIR, "layouts", "layouts.css"),
    path.join(outDir, "layouts.css"),
  );
  copyFileSync(
    path.join(ASSETS_DIR, "frameworks", "frameworks.css"),
    path.join(outDir, "frameworks.css"),
  );
  copyFileSync(
    path.join(ASSETS_DIR, "heroes", "engineering-section-deck.css"),
    path.join(outDir, "engineering-section-deck.css"),
  );

  const searchDirs = [
    mediaDir,
    path.dirname(manifestPath),
    path.dirname(storyboardPath),
    REPO_ROOT,
  ].filter(Boolean);

  const stagedCache = new Map();
  function stageMedia(ref) {
    const resolved = resolveExistingMedia(ref, searchDirs);
    if (!resolved) return null;
    if (stagedCache.has(resolved)) return stagedCache.get(resolved);
    const ext = path.extname(resolved).toLowerCase();
    const base = path.basename(resolved, ext).replace(/[^a-zA-Z0-9_-]+/g, "-");
    const uniqueName = `${base}-${stagedCache.size}${ext}`;
    const dest = path.join(outMediaDir, uniqueName);
    copyFileSync(resolved, dest);
    const entry = {
      relPath: `media/${uniqueName}`,
      absPath: dest,
      ext,
      isVideo: VIDEO_EXTS.has(ext),
      isImage: IMAGE_EXTS.has(ext),
      hasAudio: VIDEO_EXTS.has(ext) ? probeMediaHasAudio(dest) : false,
    };
    stagedCache.set(resolved, entry);
    return entry;
  }

  const globalVideo = stageMedia(manifestRaw.videoFile);
  const globalCamera = stageMedia(manifestRaw.cameraFile);

  const hostElements = [];
  const videoElements = [];
  const audioElements = [];

  if (globalVideo && globalVideo.isVideo && globalVideo.hasAudio) {
    audioElements.push(
      `<audio id="aroll-voice" src="${globalVideo.relPath}" data-start="0" data-duration="${totalDuration}" data-track-index="3" data-volume="1"></audio>`,
    );
  }

  const seenIds = new Set();
  beats.forEach((beat, idx) => {
    let safeId = sanitizeId(beat.id, `beat-${idx + 1}`);
    if (seenIds.has(safeId)) {
      safeId = `${safeId}-${idx + 1}`;
    }
    seenIds.add(safeId);

    const layout = normalizeLayout(beat.scene_layout);
    const vd = beat.visual_data && typeof beat.visual_data === "object" ? beat.visual_data : {};
    const beatMedia = stageMedia(beat.media_src);
    const beatCamera = stageMedia(beat.camera_src);

    let videoCandidate = null;
    if (layout !== "full-graphic") {
      if (beatCamera && beatCamera.isVideo) videoCandidate = beatCamera;
      else if (beatMedia && beatMedia.isVideo) videoCandidate = beatMedia;
      else if (globalCamera && globalCamera.isVideo) videoCandidate = globalCamera;
      else if (globalVideo && globalVideo.isVideo) videoCandidate = globalVideo;
    }
    const imageCandidate =
      beatMedia && beatMedia.isImage
        ? beatMedia.relPath
        : beatCamera && beatCamera.isImage
          ? beatCamera.relPath
          : null;

    if (videoCandidate) {
      let slotClass = "hf-video-slot--full-screen";
      if (layout === "panel") {
        slotClass =
          vd.speakerSide === "right" ? "hf-video-slot--panel-right" : "hf-video-slot--panel-left";
      } else if (layout === "centre") {
        slotClass = "hf-video-slot--centre";
      } else if (layout === "circle") {
        const corner = vd.pipCorner || "bottom-right";
        slotClass = `hf-video-slot--circle-${corner}`;
      }
      const mediaStart = beatMedia || beatCamera ? 0 : Number(beat.start || 0);
      const videoZ = layout === "circle" ? 20 : 1;
      videoElements.push(
        `<video id="${safeId}-video" class="clip hf-video-slot ${slotClass}" src="${videoCandidate.relPath}" data-start="${beat.start}" data-duration="${beat.duration}" data-media-start="${mediaStart}" data-track-index="0" playsinline muted style="z-index: ${videoZ};"></video>`,
      );
    }

    const subCompHtml = buildBeatSubComposition(beat, safeId, {
      width,
      height,
      videoSrc: videoCandidate ? videoCandidate.relPath : null,
      imageSrc: imageCandidate,
    });
    writeFileSync(path.join(compositionsDir, `${safeId}.html`), subCompHtml, "utf-8");

    hostElements.push(
      `<div id="${safeId}" data-composition-id="${safeId}" data-composition-src="compositions/${safeId}.html" data-start="${beat.start}" data-duration="${beat.duration}" data-track-index="1" data-width="${width}" data-height="${height}" style="z-index: 10;"></div>`,
    );
  });

  const captionsEnabled = manifestRaw.captionsEnabled !== false;
  const captionGroups = captionsEnabled ? groupCaptionWords(manifestRaw.captions || []) : [];
  if (captionGroups.length > 0) {
    const captionsHtml = buildCaptionsSubComposition(captionGroups, width, height, theme);
    writeFileSync(path.join(compositionsDir, "captions.html"), captionsHtml, "utf-8");
    hostElements.push(
      `<div id="captions-layer" data-composition-id="captions-layer" data-composition-src="compositions/captions.html" data-start="0" data-duration="${totalDuration}" data-track-index="2" data-track-kind="captions" data-width="${width}" data-height="${height}" style="z-index: 40;"></div>`,
    );
  }

  const indexHtml = `<!DOCTYPE html>
<html lang="en" data-theme="${theme}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${width}, height=${height}, initial-scale=1.0" />
    <title>${escapeHtml(storyboardRaw.title || "Lesson Studio Composition")}</title>
    <link rel="stylesheet" href="tokens.css" />
    <link rel="stylesheet" href="transitions.css" />
    <link rel="stylesheet" href="layouts.css" />
    <link rel="stylesheet" href="frameworks.css" />
    <link rel="stylesheet" href="engineering-section-deck.css" />
    <script src="vendor/gsap.min.js"></script>
    <script src="mechanics.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${totalDuration}" data-fps="${fps}" data-width="${width}" data-height="${height}">
      ${videoElements.join("\n      ")}
      ${audioElements.join("\n      ")}
      ${hostElements.join("\n      ")}
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = gsap.timeline({ paused: true });
    </script>
  </body>
</html>
`;

  writeFileSync(path.join(outDir, "index.html"), indexHtml, "utf-8");

  const domLayoutManifest = computeOverlayBoxes(beats, width, height);
  writeFileSync(
    path.join(outDir, "dom_layout_manifest.json"),
    JSON.stringify(domLayoutManifest, null, 2),
    "utf-8",
  );
}

main();
