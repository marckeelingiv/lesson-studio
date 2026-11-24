# ADR-0002: Tool-Agnostic Two Engine Rooms Architecture

Status: accepted

We will separate the editing system into an invariant **Technical Engine Room** (deterministic rules for sifting, layouts, transitions, sound attachment, and automated QC gates) and a variable **Creative Engine Room** (per-video Creative Brief and persistent Taste Profile), stored in a tool-agnostic top-level `editing_system/` directory referenced from `AGENTS.md`. Existing harness-specific workflows (`.opencode/skills/post-production/`) remain intact during Phase 0 and will become thin wrappers pointing to `editing_system/` once Phase 1–4 implementation lands.

## Considered Options

- **Keep all rules and memory inside `.opencode/`**: Couples canonical rules, prompts, and Taste Profile memory to OpenCode and drifts when working in Claude Code, Codex, or Antigravity.
- **Target `.claude/` exclusively**: Breaks portability across the repo's multi-agent toolchain.
- **Maintain a separate parallel workflow alongside `.opencode/skills/post-production/`**: Duplicates agent guidance, schemas, and review gates across two competing systems.

## Consequences

- Any coding agent (Claude Code, OpenCode, Codex, Antigravity) reads and updates the exact same rules, Creative Brief templates, typed asset catalog, and `review_log.jsonl`.
- Keeping `.opencode/skills/post-production/` unchanged in Phase 0 avoids breaking existing skill contract tests until the unified pipeline code and thin harness adapters are built in Phases 1–4.
