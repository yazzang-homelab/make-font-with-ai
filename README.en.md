# make-font-with-ai

**A reference-first font engineering skill, plugin and CLI. Interview the intended use before designing; review actual font output before release.**

[Korean README](README.md) · [Installation](docs/INSTALL.md) · [Quality gates](docs/QUALITY_GATES.md) · [License](docs/LICENSING.md)

Licensed under **PolyForm Noncommercial 1.0.0**. This is noncommercial source-available software, **not OSI open source**, because commercial use is restricted. The unmodified license and its organization/purpose provisions govern.

## Workflow

1. Choose a supplied or host-generated style reference. Record permission and provenance. No paid image API is silently invoked.
2. Interview purpose, typography role, actual size/grid, target engine/renderer, character coverage, encoding, metrics and exports. Confirm the current `design-brief.json` before implementation.
3. Author native bitmap pixels or vector path/polygon data, or start from the included R36-derived Korean brush engine.
4. Build a real candidate; inspect all native-size/contact-sheet/sentence PNGs. Fix failures and repeat without weakening tests to make a badge green.
5. Record explicit human or AI review, then rebuild, save and reopen the final TTF and optional PNG atlas.

The 16x16 route designs native pixels. It does **not** downsample a high-resolution brush logo and call it a finished pixel face. The R36 engine is a specific authored Hangul family with contextual forms and specialized regression checks, not a universal model that infers a complete alphabet from one image.

## Install

```sh
git clone https://github.com/yazzang-homelab/make-font-with-ai.git
cd make-font-with-ai
python -m pip install -e ".[brush,trace]"
claude --plugin-dir .
```

Use `/make-font-with-ai:make-font` in Claude Code. Other Agent Skills hosts can read `skills/make-font/SKILL.md` and run the same Python CLI. This is not a hosted ChatGPT MCP integration.

```sh
mfai init my-font --kind bitmap --cell 16
# Supply reference.png; complete the interview and design-brief.json.
mfai confirm-brief my-font --by "Confirmed with the user"
# Create glyphs.json, or import an explicitly mapped native-grid atlas.
mfai prepare my-font
# Open the printed proofs/index.html and inspect every page and specimen.
mfai review my-font --reviewer "Reviewer" --reviewer-type human --notes "Actual findings and scope" --accept --all-pages --reference-match --native-readable
mfai build my-font
```

Change `human` to `ai` for AI review. Review records are attestations, not authenticated identities or aesthetic certificates. A changed brief/reference/source/engine or altered proof invalidates the old approval.

## What is tested

Real glyph coverage, bounds, advances, duplicate renders, native pixel equality, NFC/NFD shaping, source/proof bindings, stale approvals, explicit booleans, output non-overwrite and exact semantic fingerprints. The template adds R36 corner, rieul, optical allocation and component-visibility checks.

CI builds on Windows, macOS and Linux. It compares full expanded-glyph semantic fingerprints, not just a font-file SHA. Candidate artifacts are local; CI uploads **reports and PNG only**, not fonts. CI setup is not a claim of completed OS testing; inspect the actual workflow runs.

Examples are deliberately unapproved: 10 native 16x16 glyphs, a three-glyph vector study, and the Hangul brush review profile. The brush output contains 11,172 modern syllables; the example's normal proof coverage is the 2,350 KS X 1001 syllables. This distinction is recorded rather than pretending every extra glyph received visual approval.

## Limits

Static TTF and PNG atlas+Unicode mapping only. Pixel TTFs use pixel-aligned outlines, not embedded bitmap font tables. Actual game-engine appearance needs target-runtime testing. No variable/color fonts, OTF/CFF, BDF/FON, old-Hangul generator or legacy-byte-encoding exporter. A hybrid request is two independently approved projects in v0.1.

Commercial use of this software is not granted. Your unrelated original inputs remain yours; do not infer that owning an input authorizes commercial use of the tool or that every output is automatically relicensed. Derived template material and third-party reference rights require separate attention. See [LICENSING](docs/LICENSING.md).
