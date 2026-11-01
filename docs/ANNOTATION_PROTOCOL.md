# Next experiment: independently reviewed order evidence

The current mirror's provenance labels are not suitable for an evidence-accuracy claim. This protocol is a plan, not a completed annotation study.

1. Freeze a new, independently collected simulated evaluation set before further model selection. The present test1 and test2 sets have already been scored and must not be reused as fresh holdouts.
2. Recruit two qualified reviewers. Preserve dataset permissions and record each example's source and consent status. Do not collect identifiable patient information for this public project.
3. Have each reviewer independently label current clinician actions, their types, exact supporting spans, and explicitly stated attributes. Separate patient history, hypothetical or declined actions, and ambiguities. A stop or dose change can be an action; a patient's report of stopping is not automatically one.
4. Measure agreement before adjudication. Keep original labels, disagreements, adjudications, and rationale in a controlled annotation store. Use a third reviewer where consensus fails.
5. Keep encounter-related examples in the same partition. Freeze label policy, train/validation/test manifests, model revisions, and scoring before testing. Report omissions and unsupported additions by action type, negation, temporality, and medication dose.
6. Report exact-span agreement separately from semantic order correctness and clinically important errors. A copied phrase or an existing turn ID does not prove correct intent. Estimate uncertainty at the encounter level and disclose sample size.

Only after this study should an evidence-grounding improvement be claimed. Clinical deployment would require a separate privacy, security, workflow, and clinical validation process.
