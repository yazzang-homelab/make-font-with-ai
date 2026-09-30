---
name: make-font
description: Design reference-driven fonts through a use-case interview, context-aware glyph design, real raster review, and verified local exports. Use for vector display faces, text/UI faces, and native-grid pixel fonts.
---

# Make font with AI

## Stage 1 — Choose a reference, not yet a production format
Inspect the actual supplied reference. When a new reference is needed, use an available image-generation tool or request an upload; do not invent a completed image or a tool result. Keep reference text exact. Record its intended style, source and permission status.
A reference is a STYLE CANDIDATE. Do not commit to vectorization or reduce a detailed brush image to a tiny bitmap before the Stage 2 interview.

## Stage 2A — Mandatory purpose and usage interview
Before constructing glyphs, determine what the font is for and where it will actually run.
Reuse information already supplied. Do not ask the user to repeat it. Ask a few plain-language questions per turn rather than dumping a technical form.
Start with these three:
1. Where and for what role will this be used? Examples: retro-game dialogue, game title, UI labels, subtitles, print display or reading text.
2. What is the real display size or pixel cell? Is 16x16 a fixed cell, an approximate on-screen height, or a visual style? Distinguish source grid, ink bounds, character advance and line height.
3. Which languages/characters and target application/engine are required?
Then resolve only relevant details: target font loader, encoding/order, mono versus antialiased rendering, native and scaled display sizes, fixed/proportional spacing, baseline, maximum output size and required export format.
Ask users who do not know a technical setting about the engine or application they use. Propose clearly labeled defaults and ask for confirmation; never silently turn an unknown into an accepted constraint.

## Stage 2B — Confirm a machine-readable production brief
Write `design-brief.json` and show a compact plain-language summary. Obtain explicit user confirmation before glyph implementation starts. Approval must bind the current brief, not just set an unversioned `approved: true` flag.
Required decisions are purpose, typography role, production kind, target display/rendering, glyph coverage, spacing/metrics, export formats and acceptance criteria.
Build host OS (macOS/Linux/Windows) is NOT the same as the font's target runtime. A Linux-built font may target a retro engine; do not conflate the two.
Choose one of:
- `vector`: contour masters and contextual forms; inspect at the actual intended sizes.
- `bitmap`: draw/correct directly on the approved integer pixel grid; each native pixel is design data, not a preview effect.
- A hybrid request uses TWO independently approved projects (`bitmap` and `vector`) in v0.1; the CLI deliberately rejects a single `hybrid` production kind.
When the reference cannot satisfy the use case, explain the conflict and approve an adapted reference with the user before implementation. For example, preserve the pressure/direction cues that survive a 16x16 grid rather than promise all high-resolution ink detail will survive.
Any change to cell size, charset, metrics, target renderer or export contract invalidates prior acceptance and requires brief reconfirmation plus relevant regression tests.

## Stage 2C — Implement and review using the selected profile

### First prove the style and layout on a pilot
Before expanding a difficult reference to 2350/11172 characters, use an explicitly declared pilot project with representative letters and real words. Include vertical, horizontal and mixed vowels, no-final/single-final/cluster-final syllables, and confusing pairs. For brush Hangul, include ㄱ/ㅋ corners, ㅐ/ㅔ connections and ㄹ/ㄺ/ㄻ/ㄿ turns; compare high-resolution pressure AND small-size gaps. For pixel fonts, prove these at the actual grid before enlargement.
The pilot needs its own confirmed scope. Never silently delete failing characters from the full production brief or pass the pilot off as full coverage. Judge the reference's stroke mass, taper, direction, open counters, side bearings, upper/final balance and complete-word rhythm together. Do not change a bad ㄹ into three equal bars solely to satisfy a topology oracle.
If the pilot is not reference-faithful and readable, reject and correct the source before scaling up. A pilot approval does not approve the expanded family; generate full production proofs and perform a new review. Use the host's available independent reviewer when authorized, but do not claim a second reviewer or paid-model invocation that did not occur.

For `bitmap`:
- Design in the native grid (for example 16x16), including explicit side space and baseline. Do not simply downsample a brush title and label it a completed pixel face.
- Build identity-correct small Hangul forms and counters for that grid. Check ㄱ/ㅋ, ㄷ/ㅌ, ㅏ/ㅐ, ㅓ/ㅔ and single/compound ㄹ finals at native size.
- Review 1x first, then nearest-neighbor integer enlargement for inspection. An attractive enlarged image cannot compensate for illegible native-size glyphs.
- Enforce the approved cell bounds, advances, line height, color/bit-depth and smoothing policy. Compare a target-size raster with the grid master when exporting TTF. A .ttf extension alone does not prove the target engine will reproduce the pixels.
- Review real dialogue/UI strings, wrapping and punctuation in the intended target environment when available. Otherwise label target-runtime compatibility untested.
For `vector`:
- Derive pressure, taper, counter geometry and contextual forms from the reference; rough edges alone are not style fidelity.
- Evaluate initial, vowel and final together; preserve clear glyph identity, optical balance and spacing at the intended sizes.
- For brush styles do not replace all curves by equal-width bars just to satisfy a topology test.
For every profile:
- Generate a real candidate font and render THAT file. Never replace proof images with generated illustrations.
- Choose coverage from the confirmed brief. Do not impose 2350 Hangul on an ASCII-only task or accept a small title sample as coverage of 2350/11172 Hangul.
- Keep technical gates and explicit visual approval separate. A failed gate, absent proof or exception is not a pass. Preserve rejected iterations and regression cases.
- Bind proof pages and review scope to the current glyph data. Do not silently reuse a prior candidate's visual approval.

## Stage 3 — Verified build and exports
Use the brief's output contract. TTF remains a supported build goal, but a bitmap engine may require an atlas and codepoint mapping instead of or in addition to TTF. Never claim an unimplemented exporter is supported.
Keep native bitmap appearance checks separate from vector outline correctness.
Cross-platform comparisons must distinguish harmless serialization metadata from glyph/metric/shaping changes. Do not accept a differing font merely by adding its byte hash to an allowlist.
Actually write, reopen and validate the requested local output. Record full path, size, semantic/structural identity, actual command and environment. `--verify-only` is not successful file delivery.
Do not call a platform tested merely because a CI matrix was configured for it.
Report output validity, review coverage, target-runtime testing and artistic limitations separately.


## Use the actual installed CLI
Read `docs/WORKFLOW.md`, `docs/QUALITY_GATES.md` and `docs/LICENSING.md` before the first production run. In Claude Code the repository is `${CLAUDE_PLUGIN_ROOT}`; quote this path when used in a shell. Other hosts should resolve the actual skill installation directory rather than invent that environment variable.

Run `mfai doctor` (or `python -m make_font_with_ai doctor`) first. If missing, explain the required local installation and obtain permission before creating a venv or installing dependencies. Plugin installation does NOT imply pip packages were installed. Never invoke a paid AI CLI, cloud generation service or privileged system package change as a fallback without explicit authorization.

1. `mfai init PROJECT --kind bitmap --cell 16` (or `--kind vector`) creates an unapproved draft.
2. Fill the current contract from the interview. `mfai check-brief PROJECT` must pass. After explicit user confirmation, `mfai confirm-brief PROJECT --by "actual confirmation record"` binds the current reference and specification.
3. Author `glyphs.json`; inspect the documented `bitmap-v1`/`vector-v1` formats. `import-atlas` requires an exact grid and approved row-major mapping. `trace-glyph --char ... --box ...` is only an explicitly mapped starting contour, not a complete font. The `r36-hangul` profile is a specific existing family; do not use it to pretend a different reference has been recreated.
4. `mfai snapshot PROJECT --label before-candidate`, then `mfai prepare PROJECT`. The command really writes a candidate and renders it. A nonzero result is a failure even if a candidate file exists.
5. Open the exact printed `proofs/index.html` and read the technical report. View all pages plus actual-size sentences. Compare brush pressure/curves/counters/spacing with the chosen reference. For pixel fonts inspect native 1x before enlargement. Correct source and loop as needed, taking checkpoints. Never blindly script a visual approval after an automatic pass.
6. Only after direct inspection, record `mfai review PROJECT --reviewer "actual reviewer" --reviewer-type ai --notes "scope and concrete findings" --accept --all-pages --reference-match --native-readable`. Use `human` only for real human review. A rejected style, uninspected pages or unreadable native output must not receive the corresponding flag.
7. `mfai build PROJECT` rebuilds, checks exact semantic identity, writes the requested output and reopens it. Read `output/build-receipt.json`. Report actual output path/size, source/review identity, build OS and target-runtime testing separately. Do not substitute verification-only mode for output delivery.

Do not run reviewed-project commands against examples merely to demonstrate installation: copy examples into a new workspace, confirm their demonstrative purpose, and inspect new outputs. Tests use synthetic approval fixtures to exercise code; those are not user-facing design approvals. No preapproved example, font binary, token or private machine path is shipped.

The project is noncommercial source-available under PolyForm Noncommercial 1.0.0, not OSI open source. Do not promise users a commercial-use grant or claim all their unrelated original outputs are automatically owned by this project. Consult the actual license and input/template rights documentation.
