# Home / Office manual plausibility review

Status: **protocol defined; sample execution is still a manual review task**.

GeoLife does not provide authoritative Home / Office ground-truth labels, so CP1 must not report supervised accuracy as if true labels existed.

The mentor-facing evaluation approach is:

1. sample a small set of users with enough recurring stay history;
2. inspect the temporal pattern of the inferred HOME location: repeated presence across multiple local dates and substantial overlap with the 21:00–06:00 HOME window;
3. inspect the temporal pattern of the inferred OFFICE location: repeated weekday presence and substantial overlap with the 09:00–17:00 OFFICE window;
4. inspect whether travel/out-of-region stays were excluded before local-time scoring;
5. inspect evidence fields (`relevant_dwell_share`, `share_margin`, `relevant_dates`) rather than treating `evidence_strength` as a probability;
6. record each sampled case as plausible / ambiguous / implausible with a short reason.

Do not publish precise inferred Home / Office coordinates or raw user trajectories in the repository. Use privacy-safe summaries or review exact coordinates only in a private notebook/cache.

This manual review complements, but does not replace, threshold sensitivity, notebook ↔ production parity, HTTP ↔ direct-model parity, and abstention analysis.

A completed sample-review table can be added here after mentor/manual review.
