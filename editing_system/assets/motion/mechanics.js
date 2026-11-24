/* HyperFrames Starter Asset Pack v0.1 — Deterministic GSAP Motion Mechanics
 * All timelines use { paused: true }, explicit fromTo() bounds, and register on window.__timelines[compId].
 * Zero wall-clock timestamps, random calls, or network dependencies.
 */
(function (root) {
  "use strict";

  function parseDeclaredDefaults() {
    if (typeof document === "undefined" || !document.documentElement) {
      return {};
    }
    var raw = document.documentElement.getAttribute("data-composition-variables");
    if (!raw) return {};
    try {
      var list = JSON.parse(raw);
      if (!Array.isArray(list)) return {};
      var out = {};
      for (var i = 0; i < list.length; i += 1) {
        var item = list[i];
        if (item && typeof item.id === "string" && "default" in item) {
          out[item.id] = item.default;
        }
      }
      return out;
    } catch (_err) {
      return {};
    }
  }

  function getVariables(fallbackDefaults) {
    var base = Object.assign({}, parseDeclaredDefaults(), fallbackDefaults || {});
    if (root.__hyperframes && typeof root.__hyperframes.getVariables === "function") {
      try {
        var resolved = root.__hyperframes.getVariables();
        if (resolved && typeof resolved === "object") {
          return Object.assign({}, base, resolved);
        }
      } catch (_err) {
        return base;
      }
    }
    return base;
  }

  function applyTheme(theme) {
    if (typeof document === "undefined" || !document.documentElement) return;
    var next = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
  }

  function parseList(value, fallback) {
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      var trimmed = value.trim();
      if (!trimmed) return fallback || [];
      if (trimmed.charAt(0) === "[") {
        try {
          var parsed = JSON.parse(trimmed);
          if (Array.isArray(parsed)) return parsed;
        } catch (_err) {
          /* fall back to delimiter split */
        }
      }
      return trimmed
        .split("|")
        .map(function (part) {
          return part.trim();
        })
        .filter(Boolean);
    }
    return fallback || [];
  }

  function parsePairs(value, fallback) {
    return parseList(value, fallback).map(function (entry) {
      if (entry && typeof entry === "object") {
        return {
          label: String(entry.label || entry.title || entry.num || ""),
          detail: String(entry.detail || entry.summary || entry.body || "")
        };
      }
      var text = String(entry || "");
      var idx = text.indexOf("|");
      if (idx === -1) {
        idx = text.indexOf("::");
        if (idx !== -1) {
          return {
            label: text.slice(0, idx).trim(),
            detail: text.slice(idx + 2).trim()
          };
        }
      }
      var colonIdx = text.indexOf(":");
      if (colonIdx > 0 && colonIdx < 32) {
        return {
          label: text.slice(0, colonIdx).trim(),
          detail: text.slice(colonIdx + 1).trim()
        };
      }
      return { label: text, detail: "" };
    });
  }

  function resolveElements(target) {
    if (!target || typeof document === "undefined") return [];
    if (typeof target === "string") {
      return Array.prototype.slice.call(document.querySelectorAll(target));
    }
    if (Array.isArray(target)) return target.filter(Boolean);
    if (typeof target.length === "number" && target.nodeType === undefined) {
      return Array.prototype.slice.call(target).filter(Boolean);
    }
    return [target];
  }

  function readCssToken(name, fallback) {
    if (typeof document === "undefined" || !root.getComputedStyle) return fallback;
    var val = root.getComputedStyle(document.documentElement).getPropertyValue(name);
    var cleaned = val ? val.trim() : "";
    return cleaned || fallback;
  }

  function createFallbackTimeline() {
    return {
      paused: function () { return true; },
      set: function () { return this; },
      to: function () { return this; },
      fromTo: function () { return this; },
      seek: function () { return this; },
      duration: function () { return 0; }
    };
  }

  function createTimeline(compId) {
    root.__timelines = root.__timelines || {};
    var tl = typeof root.gsap !== "undefined"
      ? root.gsap.timeline({ paused: true })
      : createFallbackTimeline();
    if (compId) {
      root.__timelines[compId] = tl;
    }
    return tl;
  }

  function textEntrances(tl, targets, options) {
    var opts = options || {};
    var elements = resolveElements(targets);
    if (!elements.length || typeof root.gsap === "undefined") return tl;
    var at = typeof opts.at === "number" ? opts.at : 0;
    var duration = typeof opts.duration === "number" ? opts.duration : 0.28;
    var stagger = typeof opts.stagger === "number" ? opts.stagger : 0.08;
    var offsetY = typeof opts.y === "number" ? opts.y : 14;
    var startOpacity = opts.keepFrameZeroVisible && at === 0 ? 0.92 : 0;

    for (var i = 0; i < elements.length; i += 1) {
      var el = elements[i];
      var pos = at + i * stagger;
      var fromVars = { opacity: i === 0 && at === 0 ? Math.max(startOpacity, 0.92) : startOpacity, y: i === 0 && at === 0 ? 6 : offsetY };
      var toVars = { opacity: 1, y: 0, duration: duration, ease: opts.ease || "power3.out" };
      if (opts.mode === "blur" && !(i === 0 && at === 0)) {
        fromVars.filter = "blur(6px)";
        toVars.filter = "blur(0px)";
      }
      tl.fromTo(el, fromVars, toVars, pos);
    }
    return tl;
  }

  function slides(tl, target, options) {
    var opts = options || {};
    var elements = resolveElements(target);
    if (!elements.length || typeof root.gsap === "undefined") return tl;
    var at = typeof opts.at === "number" ? opts.at : 0;
    var duration = typeof opts.duration === "number" ? opts.duration : 0.34;
    var stagger = typeof opts.stagger === "number" ? opts.stagger : 0.07;
    var dx = typeof opts.x === "number" ? opts.x : 40;
    var dy = typeof opts.y === "number" ? opts.y : 0;
    var startOpacity = at === 0 ? 0.9 : 0;

    for (var i = 0; i < elements.length; i += 1) {
      tl.fromTo(
        elements[i],
        { x: dx, y: dy, opacity: i === 0 ? startOpacity : 0 },
        { x: 0, y: 0, opacity: 1, duration: duration, ease: opts.ease || "power3.out" },
        at + i * stagger
      );
    }
    return tl;
  }

  function liveNumbers(tl, target, options) {
    var opts = options || {};
    var elements = resolveElements(target);
    if (!elements.length) return tl;
    var fromVal = typeof opts.from === "number" ? opts.from : 0;
    var toVal = typeof opts.to === "number" ? opts.to : 100;
    var decimals = typeof opts.decimals === "number" ? opts.decimals : 0;
    var prefix = opts.prefix || "";
    var suffix = opts.suffix || "";
    var at = typeof opts.at === "number" ? opts.at : 0.1;
    var duration = typeof opts.duration === "number" ? opts.duration : 0.9;

    function formatValue(val) {
      return prefix + Number(val).toFixed(decimals) + suffix;
    }

    for (var i = 0; i < elements.length; i += 1) {
      (function (el) {
        var state = { value: fromVal };
        el.textContent = formatValue(fromVal);
        if (typeof root.gsap !== "undefined") {
          tl.fromTo(
            state,
            { value: fromVal },
            {
              value: toVal,
              duration: duration,
              ease: opts.ease || "power2.out",
              onUpdate: function () {
                el.textContent = formatValue(state.value);
              }
            },
            at
          );
        } else {
          el.textContent = formatValue(toVal);
        }
      })(elements[i]);
    }
    return tl;
  }

  function circlesAndMarks(tl, targets, options) {
    var opts = options || {};
    var elements = resolveElements(targets);
    if (!elements.length || typeof root.gsap === "undefined") return tl;
    var at = typeof opts.at === "number" ? opts.at : 0.15;
    var duration = typeof opts.duration === "number" ? opts.duration : 0.45;
    var stagger = typeof opts.stagger === "number" ? opts.stagger : 0.1;

    for (var i = 0; i < elements.length; i += 1) {
      var el = elements[i];
      var pos = at + i * stagger;
      if (typeof el.getTotalLength === "function") {
        var length = el.getTotalLength();
        if (length > 0) {
          tl.fromTo(
            el,
            { strokeDasharray: length, strokeDashoffset: length, opacity: 0.4 },
            { strokeDashoffset: 0, opacity: 1, duration: duration, ease: opts.ease || "power2.out" },
            pos
          );
          continue;
        }
      }
      tl.fromTo(
        el,
        { scale: 0.84, opacity: 0 },
        { scale: 1, opacity: 1, duration: duration, ease: opts.ease || "power3.out" },
        pos
      );
    }
    return tl;
  }

  function cards(tl, targets, options) {
    var opts = options || {};
    var elements = resolveElements(targets);
    if (!elements.length || typeof root.gsap === "undefined") return tl;
    var at = typeof opts.at === "number" ? opts.at : 0.08;
    var duration = typeof opts.duration === "number" ? opts.duration : 0.3;
    var stagger = typeof opts.stagger === "number" ? opts.stagger : 0.065;
    var startOpacity = at === 0 ? 0.92 : 0;

    for (var i = 0; i < elements.length; i += 1) {
      tl.fromTo(
        elements[i],
        { y: 16, opacity: i === 0 && at === 0 ? startOpacity : 0.15 },
        { y: 0, opacity: 1, duration: duration, ease: opts.ease || "power3.out" },
        at + i * stagger
      );
    }
    return tl;
  }

  function applyTransition(tl, target, family, options) {
    var opts = options || {};
    var elements = resolveElements(target);
    if (!elements.length || typeof root.gsap === "undefined") return tl;
    var at = typeof opts.at === "number" ? opts.at : 0;
    var mode = family || "subtle";

    for (var i = 0; i < elements.length; i += 1) {
      var el = elements[i];
      if (mode === "none" || mode === "hard_cut") {
        tl.set(el, { opacity: 1, x: 0, scale: 1 }, at);
      } else if (mode === "swipe") {
        tl.fromTo(
          el,
          { x: 72, opacity: 0.92 },
          { x: 0, opacity: 1, duration: 0.26, ease: "power3.out" },
          at
        );
      } else if (mode === "zoom") {
        tl.fromTo(
          el,
          { scale: 1.04, opacity: 0.92 },
          { scale: 1, opacity: 1, duration: 0.24, ease: "power3.out" },
          at
        );
      } else {
        tl.fromTo(
          el,
          { scale: 0.99, opacity: 0.85 },
          { scale: 1, opacity: 1, duration: 0.24, ease: "power2.out" },
          at
        );
      }
    }
    return tl;
  }

  function captions(tl, groups, options) {
    if (!Array.isArray(groups) || typeof root.gsap === "undefined") return tl;
    var opts = options || {};
    var theme = opts.theme || "dark";
    var baseColor = readCssToken(
      theme === "light" ? "--bg-surface" : "--text-primary",
      "currentColor"
    );
    var activeColor = readCssToken("--caption-active", "currentColor");

    groups.forEach(function (group) {
      var groupEl = typeof group.selector === "string"
        ? document.querySelector(group.selector)
        : group.el;
      if (!groupEl) return;

      tl.set(groupEl, { opacity: 0, visibility: "hidden" }, 0);
      tl.set(groupEl, { opacity: 1, visibility: "visible" }, group.start);

      var words = Array.isArray(group.words) ? group.words : [];
      words.forEach(function (word) {
        var wordEl = typeof word.selector === "string"
          ? document.querySelector(word.selector)
          : word.el;
        if (!wordEl) return;
        tl.fromTo(
          wordEl,
          { color: baseColor },
          { color: activeColor, duration: 0.02, ease: "none" },
          word.start
        );
      });

      tl.to(groupEl, { opacity: 0, duration: 0.05, ease: "none" }, Math.max(group.start, group.end - 0.05));
      tl.set(groupEl, { opacity: 0, visibility: "hidden" }, group.end);
    });
    return tl;
  }

  root.LessonMotion = {
    getVariables: getVariables,
    applyTheme: applyTheme,
    parseList: parseList,
    parsePairs: parsePairs,
    createTimeline: createTimeline,
    textEntrances: textEntrances,
    slides: slides,
    liveNumbers: liveNumbers,
    circlesAndMarks: circlesAndMarks,
    cards: cards,
    applyTransition: applyTransition,
    captions: captions
  };
})(typeof window !== "undefined" ? window : globalThis);
