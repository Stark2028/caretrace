# Evaluation results

Measured 1 November 2026. These experiments do **not** establish clinically reliable order extraction. Aggregate machine-readable artifacts are in [results/](results/README.md). Raw predictions and transcripts remain local and ignored by Git.

## Frozen model experiment: mirror test2

Selection used only 19 validation encounters. The 7B model's validation F1 proxy was 26.89%, versus 19.64% for 3B; the paired difference's 95% bootstrap interval included zero (-6.59 to +21.11 percentage points). Selection was exploratory, not evidence of a stable 7B advantage.

[Pre-test protocol](docs/TEST_PROTOCOL.md), frozen code `1d7801ef7328f3d9a8a69747af5ba950812c6852`, clean worktree. All 92 test2 encounters and 217 reference orders were included.

| Engine | Predicted | Matched | Precision proxy | Recall proxy | F1 proxy | Failed encounters |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rules-v1 | 24 | 0 | 0.00% | 0.00% | 0.00% | 4 |
| Ollama Qwen2.5 7B | 294 | 46 | 15.65% | 21.20% | 18.00% | 5 |

The paired encounter bootstrap difference was +18.00 percentage points, 95% interval **+12.00 to +24.25**, 1,000 samples, seed 42. This comparison is against a very weak baseline; the candidate's low absolute precision and recall are the more consequential finding. It is not an 18% clinical accuracy result.

Four input failures were shared: two patient-guest labels, one bracketed inaudible label, and one initial numbered line without a speaker. The 7B run also had one output failure. Failures were kept as zero predictions with all reference orders in the denominator; there were no test retries. The evaluator recorded 67 unusable reference-evidence lists, including references in the unparsed encounters; this is not a count of 67 independently verified bad annotations.

Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`. Temperature 0, seed 42, context 8,192, output limit 768. Prompt SHA-256: `49d69858caa89bbac4662338347fe1ca0ba7b7ae3cfcdf09a7c65c5a4554a9d2`. Evaluation elapsed 918.91 seconds on the local laptop setup; this is a whole-run observation, not a service latency guarantee.

## Frozen source-mode experiment: mirror test1

After test2, a source-preserving mode was developed using training/validation inputs. Test2 could no longer serve as a fresh holdout for this change. The [source protocol](docs/SOURCE_PROTOCOL.md) froze it before scoring the previously unscored test1 partition: 90 encounters, 226 reference orders, code `bde7d434456d0d2ff45bfd330364703b4a2edb2b`, clean worktree.

The parser now preserves guest and unknown roles instead of rejecting them. Unknown speakers are never guessed to be clinicians. These improvements do not replace the older test2 results.

| Engine | Predicted | Matched | Precision proxy | Recall proxy | F1 proxy | Failed encounters |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rules-v1 | 19 | 0 | 0.00% | 0.00% | 0.00% | 0 |
| source-v1 | 166 | 29 | 17.47% | 12.83% | 14.80% | 0 |

The paired bootstrap difference was +14.80 percentage points, 95% interval **+9.18 to +20.91**, under the same proxy and resampling settings. Seventy reference orders had unusable evidence IDs. Test1 and test2 differ, so the source and 7B results are not a head-to-head model comparison.

**Post-test offset repair:** the frozen source run had 155/166 exact character spans. Eleven follow-up spans included trailing whitespace that their displayed descriptions had trimmed. The fix changes offsets only. An input-only replay on all 90 encounters confirmed that every non-offset prediction field was identical to the frozen output and that **166/166 repaired spans** exactly matched their displayed descriptions. The frozen metrics are retained unchanged alongside a separate [repair audit](results/source_span_repair.json). This is a text-integrity check, not evidence or intent accuracy. No rule or metric was tuned from test1 labels.

## Partial fine-tuning: a negative result

An earlier Qwen2.5 0.5B base run failed schema validation on all 19 validation encounters. Updating only the final Transformer block and normalization layer returned valid schemas on all 19, but produced only four orders and zero matches out of 53 references. This demonstrates formatting recovery in this run, not useful extraction or an accuracy gain.

Training used 43 eligible encounters after excluding 19 of 62 training encounters with missing/out-of-range reference evidence: one epoch, learning rate 2e-5, accumulation 4, max length 4,096, seed 42, 14,913,280 trainable parameters, peak GPU allocation 2,031,804,928 bytes on an RTX 4050 Laptop GPU. It was partial fine-tuning, not LoRA. Code, model revision, and exclusions are recorded in [training metadata](results/partial_training_config.json).

This earlier exploratory comparison used a different prompt and a token threshold of 0.5 without the current digit-string constraint. It cannot be compared numerically with the later experiments. Its original artifacts are preserved under `results/exploratory/`.

## What the scores mean

A predicted/reference pair is eligible when types agree, description token F1 is at least 0.67, and extracted digit strings agree. Eligible pairs are greedily matched one-to-one; precision, recall, and F1 are micro-aggregated. Paraphrases and written-out numbers can be missed, while semantically wrong partial matches can pass. This is not the official shared-task metric.

Reference-ID overlap is only a diagnostic on lexically matched orders with in-range IDs. The mirror acknowledges imperfect offset correction, and manual validation inspection found a wrong in-range link. We cannot claim grounding accuracy. Remaining in-range training labels are also unverified. The [data audit](docs/DATA_AUDIT.md) describes structural and semantic concerns.

Bootstrap intervals describe sampling variation of this proxy over encounters; related encounters may violate independence. They exclude annotation error, model contamination, distribution shift, and clinical risk. No result supports unattended clinical use.

## Reproducibility boundary

Dataset revision `a5e570d7512cd36e64b6e4b03d2800ee6fcec86b`; manifest SHA-256 `cd4d16c602542b251806293d7494611a5e195efa4c3f5a561fcd60e96db4e5b5`. Aggregate files record commits, clean/dirty state, package versions, settings, and artifact hashes. Current code includes the disclosed parser and offset repairs; check out the stated frozen commit to reproduce a historical method. Even with model digests and seeds, exact generation across runtimes/devices is not guaranteed.
