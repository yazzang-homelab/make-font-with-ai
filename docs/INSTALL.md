# Installation and host compatibility

Python 3.11+ and pip are required. Use a dedicated virtual environment; do not replace system Python packages.

## Python CLI (macOS / Linux / Windows)

```sh
python -m venv .venv
python -m pip install -e ".[brush,trace]"
python -m make_font_with_ai doctor
```

Activate `.venv` before the install: `source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\Activate.ps1` in PowerShell, or `.venv\Scripts\activate.bat` in CMD. Python's `py -3` launcher can replace `python` on Windows.
The first interactive CLI run prints a one-time request (to stderr) to star the GitHub repository; it is recorded in `~/.config/make-font-with-ai/` (`%APPDATA%` on Windows) and never shown again. Set `MFAI_NO_STAR_NOTICE=1` to suppress it entirely. Command output on stdout is unaffected.
The core uses fontTools, Pillow, FreeType, HarfBuzz, NumPy and JSON Schema. `brush` adds Shapely/SciPy. `trace` adds scikit-image. No browser, cloud account or model API is required to compile a font. The AI host supplies image/vision/authoring capabilities separately.

## Claude Code plugin

```text
/plugin marketplace add yazzang-homelab/make-font-with-ai
/plugin install make-font-with-ai@make-font-with-ai
/make-font-with-ai:make-font
```

For local development, `claude --plugin-dir .`. Validate with `claude plugin validate .claude-plugin/plugin.json --strict` and `claude plugin validate .claude-plugin/marketplace.json --strict`.
The skill is at the plugin root's `skills/make-font/SKILL.md`, not inside `.claude-plugin`. The CLI installation is separate from loading a skill; do not assume plugin install performed pip operations.

## Portable Agent Skills

Give the host access to `SKILL.md`, the repository docs and the installed CLI. File and process permissions must be explicit. The skill cannot create images or execute builds when its host lacks those tools; it must explain that missing capability rather than invent a result.

## Tests

```sh
python -m pip install -e ".[dev,brush,trace]"
python -m pytest -q
python scripts/ci_smoke.py --out _ci
python scripts/ci_smoke.py --brush --out _ci
```

CI declares six core OS/Python jobs and three R36 jobs, followed by exact semantic-agreement checks. Actual results are recorded in GitHub Actions. Target application installation and game rendering are separate from host compilation.

Official interfaces consulted: [Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference), [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [Agent Skills](https://agentskills.io/specification).
