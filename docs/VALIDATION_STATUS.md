# Validation status — v0.1.0

The actual [Font pipeline CI run 36701403539](https://github.com/yazzang-homelab/make-font-with-ai/actions/runs/36701403539) passed all **10 jobs** on tested code commit `a17922b9d566256a181a9844f0a4a5ff00a814e3`.

| Execution | Result |
|---|---|
| Windows/macOS/Linux × Python 3.11/3.13 | 62 tests per job; all six jobs passed |
| Native 16x16 pixel and SVG-path vector candidate builds | 12 actual write/reopen builds across the six environments |
| Full R36-derived Hangul template | Three actual builds, one on each OS, Python 3.13; 2350-character / 4700 raster cases plus five specialized profile checks per host |
| Full expanded-outline semantic agreement | Pixel, vector and Hangul fingerprints agreed exactly across their corresponding hosts |
| Plugin/marketplace manifests | Claude Code strict JSON validation passed without warnings |
| Wheel installation | Clean environment outside the repository; bundled schema, numeric module and brush data found |
| Final output path, not just a candidate | Pixel and vector demonstration projects were directly AI-reviewed and saved/reopened as final local TTFs |

Evidence: [validation JSON](evidence/v0.1.0-validation.json), [final demo exports](evidence/example-final-builds.json), [wheel check](evidence/wheel-installation.json).
No font binaries were uploaded in the repository or CI artifacts. CI visual-approval fixtures are tests, not production aesthetic approvals.

## Important distinctions

The R36 output includes 11172 modern syllables; the example's ordinary proof set contains 2350. Do not claim all encoded syllables received a new visual review. Actual target-game rendering and OS font installation remain untested. The reference engine is a specific authored family, not universal image-to-font AI.

The initial Windows UTF-8 failure and later macOS half-unit construction difference were corrected without weakening structural comparisons. See [CI corrections](CI_CORRECTIONS.md) and [arithmetic evidence](evidence/r36-rounding-investigation.json). Final coordinate comparisons still use zero tolerance.

The release's final evidence-only documentation commit may follow the tested commit. The engine, tests, examples and workflows are checked for identical Git diffs to that tested revision; changing those files requires another full CI run.
