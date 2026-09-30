# CI corrections

The first public run (36697810059, initial commit 39739e0) passed the core build/tests on Linux and macOS, but two Windows contract tests read UTF-8 Korean Markdown/JSON using the system cp1252 default. This was an actual Windows test failure, not a package or font-hash exception.
Explicit UTF-8 text reads were added to scripts/tests and the worker, and redirected CLI output uses UTF-8. Tests and font gates were not relaxed. The matrix is rerun on the corrected source. Earlier failed runs remain visible in Actions.
