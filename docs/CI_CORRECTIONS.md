# CI corrections

The first public run (36697810059, initial commit 39739e0) passed the core build/tests on Linux and macOS, but two Windows contract tests read UTF-8 Korean Markdown/JSON using the system cp1252 default. This was an actual Windows test failure, not a package or font-hash exception.
Explicit UTF-8 text reads were added to scripts/tests and the worker, and redirected CLI output uses UTF-8. Tests and font gates were not relaxed. The matrix is rerun on the corrected source. Earlier failed runs remain visible in Actions.

The corrected run 36698094162 passed all nine build/test jobs. Pixel and vector semantic fingerprints agreed across all six OS/Python combinations. R36 passed per-host gates on all three hosts, but the final agreement job detected a macOS-specific fingerprint difference. The diagnostic workflow exports only hashes/metadata and compares native arithmetic with an explicitly quantized construction trial. The semantic comparator is not relaxed and no different hash is allowlisted. This difference must be resolved or remain an explicit release limitation.
