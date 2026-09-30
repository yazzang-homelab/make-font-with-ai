# Troubleshooting

| Message | What to do |
|---|---|
| `INTERVIEW_INCOMPLETE` / `BRIEF_SCHEMA` | Complete actual purpose/engine/metric/reference fields. Do not edit the approval JSON to force a pass. |
| `BRIEF_NOT_APPROVED` | Confirm the current brief again after the user approves changes. |
| `DRAWING_COVERAGE` | Every declared character must have a drawing entry. A title image is not a full alphabet. |
| `ATLAS_DIMENSIONS` | Check exact native cell dimensions, explicit character order and columns. The importer deliberately refuses resizing. |
| `NATIVE_PIXEL_MISMATCH` | Inspect the actual native output, baseline and cell metrics; do not accept only a large preview. |
| `DUPLICATE_VISIBLE_GLYPH` | Two required characters render identically. Correct the drawings or narrow the agreed charset; do not relabel duplicates as tests passed. |
| `STALE_CANDIDATE` / `STALE_REVIEW` | Prepare new proofs and inspect them after source/engine/reference edits. |
| `PROOF_CHANGED` / `REPORT_CHANGED` | The stored evidence no longer matches. Regenerate, recheck and review; don't update hashes blindly. |
| `STRUCTURAL_MISMATCH` | This is more than a raw-byte mismatch. Compare actual coordinates/metrics/mapping/tables. No epsilon or raw-SHA allowlist is applied. |
| `OUTPUT_EXISTS` | Select a fresh output folder rather than overwrite a different font. Identical semantic output is idempotent. |
| `R36_METRICS` | The template requires UPM 1000, ascent 1040, descent -200 and advance 1000. New metrics require a newly designed source, not a silent scale. |
| Optional package missing | Install `.[brush]` for the R36 profile or `.[trace]` for image tracing. Run `mfai doctor`. |

The R36 build includes thousands of contextual outlines and can take several minutes. Do not infer a dead process merely because a source-building stage is CPU-heavy. Timeouts terminate with failure rather than produce a success receipt.

Use Python 3.11+ in a clean venv on macOS/Linux/Windows. A `--version` string is not the only reproducibility condition. CI compares exact structural identities across hosts; PNG antialiasing differences are a separate review question.

When reporting a bug, attach sanitized `mfai doctor` output, the failure code and a minimal non-sensitive brief/drawing sample you have rights to share. Do not attach tokens, private paths, proprietary font binaries or whole home directories.
