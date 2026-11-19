# Linux setup research

## Result and boundaries

Use the six exact assets in [manifest.json](manifest.json) for a separately authored, **download-only** setup command. Default to FilmCraft; make EffectCraft and SoundCraft explicit optional selections. This task researched and authored evidence only; it did not implement or run the downloader, extract archives, install dependencies, execute software, download models, or test native APIs.

All evidence lives here; [sources/provenance.md](sources/provenance.md) maps local captures to official requests.

## Stable release selection

Observed 2026-11-18. The first non-draft, non-prerelease entry in each official releases API response was selected, then independently fetched through its exact `/releases/tags/TAG` endpoint. All selected releases have both required architecture assets and GitHub `sha256:` digests matching their checksum files. These are stable by GitHub release flags, not a production-quality certification.

| Repository | Pinned release | Published UTC | Actual release commit |
| --- | --- | --- | --- |
| storytold/filmcraft | v0.20.1 | 2026-11-12 00:26:09 | cedf0c9bd060eb06a977d532402be2097c9ebe42 |
| storytold/effectcraft | v0.24.1 | 2026-11-12 00:23:40 | 582344dd4ef462362c02e56e3094de7af01847ab |
| storytold/soundcraft | v0.20.1 | 2026-11-12 00:57:13 | a52bbdccbe15342f44e0de1906bf71a621e7a68f |

The saved tag refs are lightweight refs directly to these commits; `/commits/TAG` agrees. GitHub reports the three commits verified. This does not independently verify release binaries or signatures.

### HEAD is not the release API contract

HEAD at lookup was respectively:

- FilmCraft: `f67d38b35cc5af6853ef5a6921ccba014512694b`
- EffectCraft: `665bfac0b33904b1dcda6de889f43f43a94ad3f8`
- SoundCraft: `a02d892f831f0a4e1220e0357c7b941030b9cd6f`

All differ from their releases. Existing skill/API references researched at HEAD must not be claimed to match these binaries. After a separately approved extraction/execution phase, rediscover each installed CLI's version, help and command schema at runtime and validate exact required commands and parameter types before using a project or executing any editing recipe. Download success is not runtime readiness.

## Asset manifest and disk/network requirements

Exact names, official download URLs, byte sizes and SHA-256 values are in [manifest.json](manifest.json); no floating `latest` belongs in the implemented downloader.

| App | x86_64 compressed bytes | aarch64 compressed bytes |
| --- | ---: | ---: |
| FilmCraft 0.20.1 | 112,162,847 | 108,309,163 |
| EffectCraft 0.24.1 | 81,826,579 | 76,125,337 |
| SoundCraft 0.20.1 | 21,894,484 | 20,185,891 |
| All three | 215,883,910 | 204,620,391 |

FilmCraft alone is about 107 MiB / 103 MiB; all three about 206 MiB / 195 MiB. Reserve at least the selected compressed total plus temporary-file/headroom space; atomic replacement alongside existing copies can require twice that total. Uncompressed size is **unknown**, since archives were not downloaded or inspected.

## Checksums and signatures

Full checksum content is saved as `sources/APP-SHA256SUMS.txt`; all six archive entries agree exactly with their GitHub asset digests.

| App | Checksum file bytes | Checksum file SHA-256 |
| --- | ---: | --- |
| FilmCraft | 5,076 | bd183d255069cd6c6f229e17d9ce683f103533a7249e6b8b3de9b8eb2c2800fb |
| EffectCraft | 5,170 | d732696ce893151f74447ea690fb0f01827b8fd72def9bdd7864f312f845541b |
| SoundCraft | 5,123 | a8e85fa2275e71afc730bd3b5db63839b768b7eaa129015093987e728e245256 |

These three downloaded text files were locally hashed and matched the API. Each release also publishes an ASCII-armored `SHA256SUMS.txt.asc` (228 bytes), both selected tarballs' `.asc` signatures (228 bytes each), and `release-signing-key.asc` (803 bytes), all saved here. Each public-key asset has SHA-256 `8e6925a173d6a7134118da099948de4d9eeec7c1c0770998aec33c9d3f484740`.

Detached signatures are **available, not cryptographically verified in this research**. A key downloaded beside an artifact is not an independently trusted identity. Pinned repository-reviewed asset hashes provide integrity against accidental corruption and subsequent substitution, but do not establish maintainer identity or binary/source reproducibility. Do not label basic SHA-256 checks as signature verification. Adding GPG verification needs a separately reviewed trust anchor/fingerprint rather than silently trusting the same release's key.

## CLI inclusion: explicit source evidence

For each release, `packaging/linux/package.sh` builds the GUI and CLI, copies both into `$STAGE/usr/bin`, and copies `$STAGE/usr` to the tarball root before `tar -czf`. Therefore the packaging recipe explicitly includes these paths (ARCH is x86_64 or aarch64):

| App | Intended CLI archive member | Source lines |
| --- | --- | --- |
| FilmCraft | `filmcraft-0.20.1-linux-ARCH/bin/filmcraft-cli` | `sources/filmcraft-packaging_linux_package.sh` 54–68, 89–93 |
| EffectCraft | `effectcraft-0.24.1-linux-ARCH/bin/effectcraft-cli` | `sources/effectcraft-packaging_linux_package.sh` 51–64, 92–96 |
| SoundCraft | `soundcraft-0.20.1-linux-ARCH/bin/soundcraft-cli` | `sources/soundcraft-packaging_linux_package.sh` 54–69, 114–118 |

Each also includes `bin/APP` and staged `share/` resources; SoundCraft stages CLI man pages/completions when generated. FilmCraft additionally copies `install.sh` into its tarball root. Its installer defaults to `~/.local`, copies binaries and desktop resources, rewrites desktop entries and may refresh desktop/MIME/icon caches (`sources/filmcraft-packaging_linux_install.sh` 11, 29–60). It is **not** appropriate to execute it in a download-only command. EffectCraft and SoundCraft's pinned tar recipes do not add an installer; do not invent `./install.sh` instructions for them.

These statements are source-supported packaging intentions. No tar listing or binary execution was performed, so actual archive-member verification remains deferred.

The release workflows use a mutable shared `@main` workflow. The release commits and packaging text are pinned, but this research cannot reconstruct the exact shared workflow revision that built the binaries or claim supply-chain attestation.

## Minimum command requirements

Implement the smallest reviewed downloader with:

1. A fixed, reviewed manifest (the six entries above). Select `Linux` plus `uname -m` `x86_64`/`aarch64`, rejecting everything else; allow an explicit supported architecture for cross-download if clearly labeled. No opportunistic newest-release selection.
2. A caller-selected private writable download directory, HTTPS/TLS verification, network access to GitHub and its official release redirect/CDN endpoints. Use existing standard-library downloading/hashing if the repository's approved Python runtime is used; otherwise Bash + curl + SHA-256 tooling is sufficient. Do not auto-install prerequisites or require root. A download-only command does not need Rust, FFmpeg, a GPU, a display, tar, or audio libraries.
3. Print selected versions, names, sizes, destination and download-only behavior before transfer; keep optional tools opt-in. No models, plugins or unrelated assets.
4. Download each exact URL to a unique temporary file in the destination, with failed-HTTP/TLS/transfer errors fatal. Validate exact byte count and the hard-coded SHA-256 before atomic promotion to the final filename; a mismatch must never be presented as a ready artifact. Match cached files against both checks before reuse. Refuse unsafe/symlink destinations and avoid overwriting unrelated files.
5. Offline/mocked tests for architecture selection, pins/URLs, optional selection, size/hash failures, HTTP failures, cache behavior and absence of execution/extraction/config writes. Store a receipt with version, URL, bytes, digest and verification status. A plan/dry-run is useful without networking.

Recommend **no extraction option in the first command**. Safe extraction requires a separate archive-member policy (absolute paths, `..`, links, devices, conflicting output paths), a fresh private destination, preserved `share/` resources, verified expected CLI members and an expanded-size limit. Keeping this out avoids pretending that download authorization also permits installation or execution.

### Later runtime prerequisites (not download prerequisites)

Pinned package metadata declares glibc >= 2.35 and libgcc_s for all three, with ALSA runtime libraries additionally required for SoundCraft. FilmCraft/EffectCraft metadata says windowing and GPU libraries load at runtime; package dependencies include xkbcommon and Vulkan-or-EGL, with X11/Wayland/driver recommendations. SoundCraft similarly needs audio/windowing/GPU dependencies for corresponding features. See the captured `sources/APP-packaging_linux_nfpm.yaml`, especially dependency comments and `overrides.deb.depends`.

These are packaging declarations, not a tested minimal headless dependency set. Do not claim the tarballs are statically linked or guaranteed to run on this machine. Runtime environment, feature-specific models/fonts, schema compatibility and native export/reopen behavior remain separate capability gates.
