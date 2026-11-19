# Download the pinned Craft software

Run from the repository root. The [setup command](../scripts/setup.py) uses
Python's standard library and the reviewed [release manifest](../scripts/releases.json).
FilmCraft is the default; optional apps are separate choices.

```sh
# Preview the exact version, platform, official URL, size, hash and destination.
# Preview performs no network calls or filesystem writes.
uv --project video_pipeline run python .opencode/skills/post-production-artcraft/scripts/setup.py

# Explicitly download and verify FilmCraft.
uv --project video_pipeline run python .opencode/skills/post-production-artcraft/scripts/setup.py --download

# Optional: only for an approved unmet visual or audio need.
uv --project video_pipeline run python .opencode/skills/post-production-artcraft/scripts/setup.py --app effectcraft --download
uv --project video_pipeline run python .opencode/skills/post-production-artcraft/scripts/setup.py --app soundcraft --download
```

## What this does

- Selects a pinned official Linux archive for the detected architecture
  (`x86_64` or `aarch64`); `--arch` explicitly selects a different supported target.
- Stores verified archives in `video_pipeline/workspace/artcraft-setup/downloads/`
  by default. Use `--destination` for another explicitly authorized location.
- Checks expected size and SHA-256 before publishing a complete archive.
  Matching existing archives may be reused; mismatches are preserved and fail.
- Fails on unsupported platforms, absent verified releases or invalid downloads.
  It does not silently select another version, architecture, source or backend.

Downloads require Linux with accessible `/proc/self/fd` and filesystem support
for hard-link publication; unsupported environments fail closed. Destination
components cannot be symlinks, and the destination directory must belong to the
current user and not be group/world writable. Newly created directories use
mode `0700`; downloaded files use `0600`.

Downloads allow at most five redirects and 2 GiB per artifact, require pinned
size plus 64 MiB available disk space, and use a 15-second socket timeout plus a
600-second parent-enforced transfer timeout covering DNS and response headers.
The transfer timeout excludes destination preparation and parent verification/
publication. A timed-out worker is killed and reaped before staging cleanup.

## Reviewed release pins

Official release metadata and `SHA256SUMS.txt` agreed for both supported
architectures during setup research:

| App | Release | Release source commit | x86_64 archive bytes |
| --- | --- | --- | ---: |
| FilmCraft | [v0.20.1](https://github.com/storytold/filmcraft/releases/tag/v0.20.1) | `cedf0c9bd060eb06a977d532402be2097c9ebe42` | 112,162,847 |
| EffectCraft | [v0.24.1](https://github.com/storytold/effectcraft/releases/tag/v0.24.1) | `582344dd4ef462362c02e56e3094de7af01847ab` | 81,826,579 |
| SoundCraft | [v0.20.1](https://github.com/storytold/soundcraft/releases/tag/v0.20.1) | `a52bbdccbe15342f44e0de1906bf71a621e7a68f` | 21,894,484 |

Each release's packaging source stages its GUI, CLI and shared resources into
the tarball. Actual archive contents have not been downloaded or inspected in
this build. These release commits differ from the API-reference commits.
Rediscover commands on the installed release; source examples are not proof
that this binary exposes the same features.

## What remains separate

This is a **download-only setup command**, not an unattended installer. It does
not extract archives, execute downloaded code/install scripts, edit PATH or
desktop configuration, install dependencies/plugins, or acquire Whisper models.
Review the official release/installation instructions before authorizing those
steps. A verified download is not evidence of runtime safety or compatibility.
FilmCraft's packaging supplies an installer; the other two tar recipes do not
establish one. Do not assume a common `install.sh` exists across apps.

Release builds can differ from the pinned source used by the API references.
Record actual binary version, build features, available commands and schemas
after separately authorized installation. Do not assume native Whisper is
enabled or that speech weights are included. The [capability gate](handoff.md#capability-gate-disposable-sample)
still blocks production until the required native operations are tested.

## Updating the download pins

The manifest is reviewed trust material, not a live `latest` resolver. Maintain
each app's official release tag, matching architecture filename, exact byte size,
SHA-256, asset URL and upstream provenance together. Verify the checksum against
official release metadata/checksum text before changing the pin; a missing or
unverifiable artifact stays unavailable. Review packaging changes and rerun
downloader tests. Digest verification binds bytes to this manifest; it does not
establish a publisher signature, an independent audit or API compatibility.
