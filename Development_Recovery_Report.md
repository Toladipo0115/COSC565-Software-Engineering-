# Original EngageTrace development cohort recovery

The exact recorded case membership, case order and scenario assignments were recovered from controlled_eval_cohort.json. All 300 saved injected sequences match CCC_2014J weekly activity exactly after the original injections; none is unmatched or ambiguous among available student-course records.

## Findings

- 300 scenario cases, comprising 283 distinct source students.
- Five groups of 60 cases each.
- 266 students appear once; 17 appear twice.
- 120 positive cases from 120 distinct students.
- 180 control cases from 177 distinct students.
- 14 source students appear in both a positive and a control scenario.
- Original cohort SHA-256: d1fabbe9a73ad6958ac3da043aace7c39ee98647b062fbc9b2332ea2d2acb361.

## Recovered versus missing

The saved keys encode source student IDs, scenario labels and case indices. Their corresponding source sequences and injections have been verified against the current database. This recovers the exact saved cohort as cases and allows deterministic replay of that cohort. It does not recover how the source students were selected in the first place.

No original sampling driver, eligibility-filter configuration, or sampling seed was found in the inspected original Python scripts, original code/database ZIP, available original document text, or local repository history searches. controlled_eval.py accepts seed=None in run_controlled_evaluation, but never uses that argument and receives the matrix and assignments from its caller. This is not evidence of a recorded selection seed. Later frozen-test scripts use seed 20261015; that seed must not be retroactively assigned to the original development selection.

Repeated IDs across scenario groups are consistent with several possible selection procedures. They do not prove sampling with replacement or any particular random seed. No new sample or guessed seed is presented as the original.

## Manuscript implication

Describe the original controlled development data as 300 scenario cases from 283 distinct CCC_2014J students, rather than 300 independent students. Case-level results remain reproducible, but repeated source students induce dependence, including across positive/control scenarios. This discovery does not change the later frozen test: its 2,400 sampled students were already verified distinct and separate from earlier evaluated presentations.

Suggested wording: "The original controlled development matrix preserves 300 scenario cases derived from 283 distinct students in CCC_2014J. Exact case identities and assignments are recoverable and all saved sequences replay from source data, but the original sampling driver, seed and selection filters remain unavailable. Seventeen students contribute two cases, including fourteen contributing to both positive and control scenarios; these cases are not independent student observations."

## Private recovery package

The CSV contains student-level identifiers and must not be uploaded to public GitHub. The recovery script reads inputs only and writes a private assignment CSV and aggregate findings. To repeat:

    python recover_development.py --cohort /path/controlled_eval_cohort.json --database /path/engagetrace.db --output /path/private_recovery
