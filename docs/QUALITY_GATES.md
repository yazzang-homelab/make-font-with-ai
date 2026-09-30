# Quality gates and what they do not prove

| Gate | Enforced behavior |
|---|---|
| Purpose | Incomplete purpose/engine/coverage/reference fields cannot be approved. |
| Current brief | Reference image bytes and entire current contract must match explicit confirmation. |
| Source/coverage | Exact required character set; no blank non-space, invalid coordinates, unsafe path or guessed mapping. |
| Actual font | Serialize, reopen, verify mapping, outline bounds, advances, native sizes and NFC/NFD shaping. |
| Native bitmap | Every selected size is an integer native scale; exact pixel equality, not a similarity score. |
| Identity flags | Duplicate visible glyphs and declared critical-pair collapse are failures. Missing-pair coverage is not silently ignored. |
| Optical flags | Real rendered mass/core center has a user-approved limit; intentionally asymmetric brush designs still need visual review. |
| R36 profile | Extra actual-ink rieul turns, ㄱ/ㅋ context, optical layout, specialized geometry and component visibility. |
| Real proofs | Candidate PNGs at approved sizes plus specimen text; enlarged pixel proof is clearly separate from 1x. |
| Review | All pages, reference style and native readability must be explicitly accepted with reviewer type and notes. |
| Staleness | Source, reference, brief, engine, candidate, report or proof changes invalidate previous review. |
| Output | Rebuild, exact semantic comparison, actual write, reopen, receipt; no success from `verify-only`. |

## Cross-platform identity

`fingerprint.py` compares complete expanded glyph contours, integer coordinates, point flags, winding, horizontal metrics, Unicode mapping, glyph order, names and functional font tables. Cyclic contour start and contour ordering are canonicalized; winding is NOT reversed or approximated. Container offsets, checksums and head timestamps are not interpreted as new glyph geometry.

This is deliberately conservative. Some harmless representations outside the current canonicalization may still be rejected. The solution is to diagnose the structural difference, not add an unverified raw byte hash or loosen coordinate tolerances. Identical inputs under CRLF vs LF JSON formatting do not cause an invented version failure.

### R36 construction arithmetic

The R36 adapter fixes its final integer-construction policy: round the construction value to 1e-7 font units, then round to an integer with ties to even. This prevents CPU-dependent floating-point approaches to an exact half-unit from choosing opposite integer pixels. It is not a tolerance in verification. A changed final coordinate still fails exact semantic identity. See `docs/evidence/r36-rounding-investigation.json` for the investigated records; the original unnormalized template and the deterministic port are not claimed to have identical byte programs.

## Negative tests

Tests corrupt native pixels, cmap, one coordinate, candidate bytes, proof PNG, report, coverage, renderer constraints and approvals. They also exercise string `"true"`, stale source, partially accepted review, symlink escape, duplicate JSON keys, invalid legacy encoding and no-overwrite. A process crash is not counted as the intended semantic detection.

CI tests contain explicit synthetic review fixtures solely to test state transitions. They are NOT production visual approvals. CI smoke projects do not get visual approval; they produce technical candidates and proof images.

## Reference quality

No automated metric certifies beauty or fully reproduces a reference. The R36 template carries a concrete earlier design, not a general image-to-alphabet model. New styles require new drawing data and review. A few reference letters do not supply all 2,350/11,172 Hangul forms automatically.

The full R36 font contains modern syllables beyond the selected proof set. The example records 2,350 reviewed-target characters and 11,172 encoded syllables separately. The automatic profile gates do not authorize an agent to claim a new independent 11,172-glyph visual review.

## Native pixel gate versus target application

Pixel TTFs are pixel-aligned outlines. The native gate uses no-hinting monochrome FreeType; the game/application may use different smoothing or metrics. Test its loader at the actual size. An atlas retains exported pixels but still needs correct texture filtering, mapping and placement in the engine. OS compilation success is not target-app installation success.
