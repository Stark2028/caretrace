# Source extractor check — 1 November 2026

After the frozen `test2` experiment, the source-preserving `source-v1` engine was developed as a lightweight review mode. Its descriptions are literal excerpts and its reason field is always null. These properties prevent generated text in those fields; they do not establish that a proposed action was correctly identified.

Development used the training and validation partitions. The prior `test2` results informed the decision to build an extractive mode, so test2 is not a fresh holdout for it. This document freezes source-v1 before scoring it on the still-unscored mirror `test1` partition (90 encounters). The manifest remains SHA-256 `cd4d16c602542b251806293d7494611a5e195efa4c3f5a561fcd60e96db4e5b5`, dataset revision `a5e570d7512cd36e64b6e4b03d2800ee6fcec86b`.

Compare source-v1 with rules-v1 on every test1 encounter with the same type/token-F1>=0.67/digit-string matcher. No threshold or rule changes will be made from these test results. Count input failures as zero predictions. Report literal source-span integrity separately from the order-matching proxy; neither is clinical accuracy.

The dataset parser was improved after the frozen test2 run to preserve patient guests and unlabelled or inaudible turns as guest/unknown roles. It never guesses that an unknown speaker is a clinician. Test2 numbers remain those of the earlier frozen commit, including its four parser failures. No replacement test2 result is claimed.
