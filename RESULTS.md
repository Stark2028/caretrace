# Results

## Validation audit

On 1 November 2026 the rule baseline was run on all 19 validation encounters (53 annotated orders). The preliminary run predicted 3 orders and matched 2 under the project's lexical proxy: precision 2/3, recall 2/53, and F1 7.14%. This is a narrow baseline and the sample is small. The result is not a clinical accuracy estimate or the official MEDIQA-OE score.

The local audit identified 12 validation orders with at least one evidence ID outside the transcript, so evidence scores require special caution. See [data audit](docs/DATA_AUDIT.md) and [methodology](docs/METHODOLOGY.md). The base-model and fine-tuned comparisons and held-out test results are pending; no improvement is claimed.
