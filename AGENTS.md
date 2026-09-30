# Agent instructions for this repository

## Scope
This project is a noncommercial source-available plugin and local CLI. Keep `README.md`, `README.en.md`, plugin metadata and package version consistent. Do not call it OSI open source or grant commercial use that the license does not grant.

## Required workflow
1. Inspect existing source and actual tests before changing behavior.
2. Begin every font-production stage with the user's confirmed use-case brief. Do not infer a pixel grid or engine from the reference aesthetic.
3. Construct real drawing data and actual font candidates. No generated screenshot can substitute for rendered-font evidence.
4. Do not record human approval for AI reviews. Do not blindly accept all proof pages after automated checks. CI review fixtures are not production visual approvals.
5. Preserve failed cases, create source/evidence checkpoints, and rerun tests after changes. Never weaken identity/geometry checks just to accept a new platform hash.
6. Report implemented capability, executed host tests, target-application tests and artistic limitations separately.

## Commands
- `python -m pip install -e ".[dev,brush,trace]"`
- `python -m pytest -q`
- `python scripts/ci_smoke.py --out _ci`
- `python scripts/ci_smoke.py --brush --out _ci`
- `python scripts/audit_repo.py`
- `claude plugin validate .claude-plugin/plugin.json --strict`
- `claude plugin validate .claude-plugin/marketplace.json --strict`

## Publication
Do not commit TTF/OTF/WOFF/FON binaries, private reference material, credentials, absolute personal-machine paths, generated `.mfai` approvals or virtual environments. CI artifacts contain only reports and real PNGs, never font files. R36 contour sources and authored example PNGs are intentionally included under the project license.
Do not force-push, rewrite unrelated repositories or configure global Git identity. Use a feature branch for changes after the initial release.
