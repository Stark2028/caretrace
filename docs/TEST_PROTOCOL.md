# Test protocol freeze — 1 November 2026

This document records the planned evaluation before scoring either selected engine on the mirror's `test2` split. The existence and total count of reference orders were checked (217); individual test references were not examined during model or prompt selection. Test input hashes were checked for exact overlap only.

| Item | Frozen choice |
| --- | --- |
| Dataset | `mkieffer/SIMORD`, revision `a5e570d7512cd36e64b6e4b03d2800ee6fcec86b` |
| Manifest SHA-256 | `cd4d16c602542b251806293d7494611a5e195efa4c3f5a561fcd60e96db4e5b5` |
| Test partition | Mirror `test2`: all 92 encounters, no limit; different split from the original shared task |
| Baseline | `rules-v1` |
| Selected candidate | Local Ollama `qwen2.5:7b`, artifact digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Selection | On 19 validation encounters, 7B scored 26.89% lexical F1 proxy versus 19.64% for 3B under the same prompt and revised matcher; this is exploratory and the sample is small |
| Tokenizer for context guard | `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775` |
| System prompt SHA-256 | `49d69858caa89bbac4662338347fe1ca0ba7b7ae3cfcdf09a7c65c5a4554a9d2` |
| Decoding | Ollama schema-constrained JSON, temperature 0, seed 42, context 8192, output limit 768 tokens |
| Order metric | Same type, token F1 >= 0.67 and identical digit strings; greedy one-to-one matching; micro precision/recall/F1 proxy |
| Comparison | Paired encounter bootstrap of proxy F1 difference, 1,000 samples, seed 42 |
| Failures | Count parsing and input failures as zero predicted orders; do not retry on test |
| Evidence | Count missing/invalid reference IDs. Reference-ID overlap is an unvalidated diagnostic only, not grounding accuracy |

The candidate was selected using the validation proxy, not fine-tuned on SIMORD. An exploratory 0.5B final-block fine-tune is documented separately and did not demonstrate an improvement under its earlier validation setup. The reference evidence labels in this mirror have known structural and semantic alignment problems; no clinical safety or evidence accuracy claim is supported. Dataset size, potential model pretraining contamination, and benchmark matching limitations constrain interpretation.
