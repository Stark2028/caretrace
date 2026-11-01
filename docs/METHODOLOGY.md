# Methodology

## Task and scope

Identify proposed medication, lab, imaging, and follow-up orders in simulated doctor–patient text; return a description and supporting turn IDs. This is not clinical validation or medical advice. The SIMORD task includes nuanced or implicit orders; the rule baseline is intentionally narrow and should be expected to miss many.

## Data and split

The code pins `mkieffer/SIMORD` at `a5e570d7512cd36e64b6e4b03d2800ee6fcec86b`. Its corrected/repartitioned mirror has 81 train, 90 test1, and 92 test2 examples. An encounter ID's SHA-256 prefix modulo 5 determines validation (bucket 0) within those 81 training examples; this yielded 62 train and 19 validation examples. Test labels are held back during development and selection. Exact normalized-input hash checks are allowed to audit overlap, but do not prove absence of near-duplicates or author overlap. Report this split independently from published shared-task results.

The mirror's evidence IDs have significant structural errors; see `DATA_AUDIT.md`. Training excludes entire encounters with missing or out-of-range gold evidence. This excludes 19 of 62 training encounters before any token-length exclusions. A valid ID is only a range check and cannot verify semantic correctness.

## Model and comparisons

The transparent baseline uses conservative text patterns in clinician turns. It cannot cover all linguistic forms and currently makes no medication predictions. One experimental model is Qwen2.5 0.5B Instruct at pinned commit `7ae557604adf67be50417f59c2c2f167def9a775`. The training script freezes the model except the final Transformer block and final normalization layer; it uses the training partition only and saves skipped examples, configuration, GPU memory, code commit, and worktree status. It performs teacher-forced next-token loss over the JSON answer tokens only.

A separate optional comparison uses local Ollama `qwen2.5:3b` and `qwen2.5:7b` models with schema-constrained decoding, temperature 0, seed 42, 8,192 context tokens, and up to 768 output tokens. Their model digests are recorded. These are different models and decoding setups from the partial fine-tuning experiment; differences cannot be attributed to fine-tuning alone. An in-range source turn is not proof of support, and the schema cannot prevent hallucinated content. The tokenizer context check reserves 1,024 tokens for generation and template overhead.

The public service instead defaults to `source-v1`, a separate deterministic extractor developed after the test2 experiment. It identifies selected clinician action phrases, returns literal description spans and null reasons, and performs clause-level exclusion checks. This prevents generated wording in those fields but does not establish correct action intent or completeness. Its separate test1 protocol and the post-test whitespace-offset repair are disclosed in `RESULTS.md`.

Fix the prompt, model/checkpoint, maximum length, matching rules, and decoding settings before held-out evaluation. Model outputs that fail parsing or schema validation are counted as failures and yield no predicted orders for that encounter. Do not silently retry malformed outputs on test. Use the same settings for both models and record version/hash provenance.

## Metrics

For a transparent automated proxy, pairs of gold and predicted orders are eligible for matching when order types agree, token-overlap F1 on descriptions is at least 0.67, and digit strings agree. Eligible pairs are greedily matched in descending overlap order. Aggregate order precision, recall, and F1 are micro scores over these matches. This is neither the official shared-task metric nor clinical semantic correctness: paraphrases and written-out numbers may be missed, and misleading partial matches may count.

Reference-ID overlap is computed only as a diagnostic on matched orders with structurally valid reference evidence. Invalid reference evidence is counted separately. The mirror's offset-based correction also produces some wrong in-range IDs, so this diagnostic is not a trustworthy evidence-accuracy score. Independently reannotate and adjudicate evidence before claiming grounding performance.

Inspect errors by order type, historical/stopped medication, negation, follow-up, missing evidence, and unsupported inferred attributes. The dataset is small and synthetic; uncertainty estimates and real-world performance require more data and expert validation. Never report an improvement that was not measured.
