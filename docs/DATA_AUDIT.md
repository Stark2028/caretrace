# Dataset and evidence audit

The [SIMORD source dataset](https://huggingface.co/datasets/microsoft/SIMORD) describes simulated consultations derived from ACI-Bench and PriMock57. It declares CDLA-Permissive-2.0; ACI-Bench is separately listed as CC BY 4.0 in the [NLM dataset catalog](https://datasetcatalog.nlm.nih.gov/dataset?q=0002386055). Check each underlying source's terms before redistributing examples or weights. This repository downloads the data at runtime and does not commit transcripts or dataset-derived predictions.

The experiment uses [`mkieffer/SIMORD`](https://huggingface.co/datasets/mkieffer/SIMORD), revision `a5e570d7512cd36e64b6e4b03d2800ee6fcec86b`, a third-party mirror that changes split assignments to align ACI-Bench training encounters and includes numbered transcripts. Results use this mirror's partitions and are not directly comparable to the original leaderboard.

## Local audit

On 1 November 2026, the manifest contained 62 train, 19 validation, 90 test1, and 92 test2 encounters. Encounter IDs were unique and no exact normalized input-transcript hashes overlapped across the four partitions. This check does not rule out related or near-duplicate encounters. Test input hashes were read only for overlap checking; test order labels were not used for model selection.

| Partition | Encounters | Orders | Orders with unknown evidence IDs | Encounters affected |
| --- | ---: | ---: | ---: | ---: |
| Training | 62 | 154 | 39 | 19 |
| Validation | 19 | 53 | 12 | 6 |

Examples of the structural problem include negative IDs and IDs larger than the number of transcript turns. Empty source turns and multiline utterances are preserved by the parser. No training/validation examples lacked a provenance list, but a list can still contain invalid IDs. The cause of the mismatch has not been established. We do not assume that remaining in-range references are semantically correct. Evidence supervision excludes affected training encounters; evidence comparisons exclude invalid gold references and report their count.

Generate the audit with `python -m caretrace.audit --manifest runs/manifest.json --out runs/audit.json`. Local artifacts are intentionally ignored by Git.
