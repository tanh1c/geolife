# Stage 06 — Routine / Habit Mining

## Question

After Stage 05c closed broad semantic WORK/OFFICE expansion, Stage 06 asks a behavior-only question:

> Which directed location-to-location routines repeat, when do they occur, and are they stable over time?

No Stage-06 output is a HOME/WORK label.

## Scope

Stage 06 uses the broader Stage-03a behavior representation:

- 5,821 frozen CP1 stays;
- 136 users with at least one stay;
- per-stay IANA local-time resolution;
- complete-link 200 m behavior locations;
- historical parity target: 104 users with at least one recurring location.

This scope is deliberately distinct from the 97-user Beijing semantic cohort used by Stage 05.

## Support first

Routine evidence is constructed only on days passing the existing Stage-03a `usable_for_motif` gate:

- at least one stay;
- stay-observed span at least 2 h.

A missing or unsupported day is not treated as evidence that a routine did not happen.

## Representation

For each supported user/day:

1. sort stays by UTC time;
2. collapse consecutive duplicate locations;
3. encode the location sequence;
4. emit each directed OD transition;
5. retain the origin's local departure clock.

Example:

```text
L0, L0, L1, L1, L0
→ L0 → L1 → L0
→ edges L0→L1 and L1→L0
```

Sequence order uses UTC timestamps. Departure habits use local time.

## Evidence axes

### Recurrence

Per user-edge:

- transition count;
- active-day count;
- active-day share over usable motif days;
- weekday/weekend active days.

Primary descriptive repeated-edge definition: same directed edge on at least two supported days.

### Departure-time regularity

Circular mean hour and resultant concentration in [0, 1] are measured separately from recurrence.

No recurrence/clock score is fused into a pseudo-confidence.

For edges with at least six transitions, Stage 06 fits 1–3 Gaussian components after circular unwrapping and selects the component count by BIC. This is descriptive departure-time multimodality, not semantic classification.

### Exact motif comparator

Stage 06 retains the earlier exact whole-day motif criterion (top exact motif on at least 50% of supported motif days) as a stricter comparator.

A repeated OD edge can survive small day-level detours that break exact motif equality.

### Split-half stability

Users with at least three supported dates in each half independently select a dominant directed edge in the first and second half.

The primary stability question is whether the same edge wins both halves.

## Sensitivity

The notebook reports a transparent sweep:

- repeated edge active days: 2 / 3 / 5;
- departure concentration: 0.3 / 0.5 / 0.7.

The sweep is not used to optimize a preferred result.

## Privacy

User-level sequences and edge tables remain private on the Modal Volume. Aggregate report tables contain no coordinates and no raw user IDs.

## Handoff to Stage 07

Stage 07 change detection should only proceed if Stage 06 shows enough routine coverage and test-retest stability.

Required ordering:

```text
coverage gate
→ routine representation
→ change detection
```

Sparse observation must not be interpreted as behavioral change.
