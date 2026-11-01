# Results

## Validation audit

On 1 November 2026 the rule baseline was run on all 19 validation encounters (53 annotated orders). An exploratory run under an earlier token-overlap threshold of 0.5 predicted 3 orders and matched 2. The current evaluation uses a stricter 0.67 threshold and matching digit strings to reduce obvious false matches; do not compare the two settings directly. This is not a clinical accuracy estimate or the official MEDIQA-OE score.

The local audit identified 12 validation orders with at least one evidence ID outside the transcript. Manual inspection also found an in-range reference pointing to an unrelated turn. Reference-ID overlap is a diagnostic only; evidence accuracy is not established. See [data audit](docs/DATA_AUDIT.md) and [methodology](docs/METHODOLOGY.md).

An exploratory Qwen2.5 0.5B run failed schema validation on all 19 validation encounters. A one-epoch final-block fine-tune on 43 eligible training encounters returned valid schemas for all 19 but matched none of 53 reference orders under the lexical proxy. The initial model comparisons used an earlier prompt; the current prompt asks more explicitly for stated reasons and current orders. Neither run supports an accuracy improvement. The 3B comparison and held-out test results are pending.
