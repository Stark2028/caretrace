# Aggregate experiment artifacts

Read [RESULTS.md](../RESULTS.md) before interpreting these files. They contain aggregate counts, settings, dataset encounter IDs, and hashes, not source transcripts or per-encounter generated orders.

- `*_test1_frozen.json`, `test1_comparison.json`: source extractor versus narrow rules, mirror test1.
- `*_test2_frozen.json`, `test2_comparison.json`: local 7B versus narrow rules, mirror test2 at the older frozen parser.
- `*_validation.json`, `validation_3b_vs_7b.json`: exploratory selection under the revised proxy.
- `exploratory/`: earlier 0.5B runs with a different prompt and matcher; not comparable to later scores.
- `manifest.json`: pinned dataset partitions and source fingerprints.
- `data_audit.json`: training/validation evidence-ID audit and exact-input overlap check.
- `partial_training_config.json`: partial fine-tuning settings, exclusions, and runtime observations.
- `source_span_repair.json`: post-test input-only verification of the whitespace-offset repair; original frozen results remain unchanged.
- `SHA256SUMS.json`: hashes of the exported artifacts.

Scores are lexical proxies, not clinical accuracy. Evidence-ID overlap is unvalidated because reference labels have known problems. These artifacts are observations from local runs, not independently certified measurements. Raw local artifacts are ignored under `runs/` and `checkpoints/`.
