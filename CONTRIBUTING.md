# Contributing

The repository is noncommercial source-available under PolyForm Noncommercial 1.0.0, not MIT or OSI open source. Contributions must be yours to provide under compatible project terms.

Use a branch. Add a failing test for the original problem, fix it, and run `python -m pytest -q` plus relevant actual-font smoke tests. Changes to native-grid handling require exact 1x and integer-scale tests. Changes to the R36 engine require its profile smoke on the CI matrix.

Do not turn a failed glyph into a green build by lowering a threshold, dropping a character, accepting a new raw SHA, claiming that an exception is detection, or reusing old visual approval. Document legitimate oracle changes with both former false positives and real negative controls.

Images and drawing JSON may be submitted if you have rights. Generated font binaries, credentials, private machine paths and compiled dependency copies are not part of source contributions. Keep examples small and accurately label visual-review scope.

Run `claude plugin validate .claude-plugin/plugin.json --strict` and marketplace validation when editing plugin metadata. Keep Korean/English README capability claims aligned. Update CHANGELOG and plugin/package versions together for releases.
