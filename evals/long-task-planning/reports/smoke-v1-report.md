# Eval report — run `smoke-v1`

runs: 10 | variants: ablation-full-minus-integration, baseline-a, baseline-b, candidate

## Variant: `ablation-full-minus-integration` (1 runs)

| Metric | Direction | Mean | Min | Max | Measured | Worst run |
|---|---|---:|---:|---:|---|---|
| Contract completeness | higher | 1.00 | 1.00 | 1.00 | 1/1 | case-10-timeout-seam |
| Acceptance determinism | higher | 1.00 | 1.00 | 1.00 | 1/1 | case-10-timeout-seam |
| Context locality (amplification proxy) | lower | 4.00 | 4.00 | 4.00 | 1/1 | case-10-timeout-seam |
| Hazardous ownership collisions | lower | 0.00 | 0 | 0 | 1/1 | case-10-timeout-seam |
| Dependency precision (must-have hit rate) | higher | 0.00 | 0.00 | 0.00 | 1/1 | case-10-timeout-seam |
| Integration explicitness (case reqs met) | higher | 0.00 | 0.00 | 0.00 | 1/1 | case-10-timeout-seam |
| Phase-shaped leaves | lower | 0.00 | 0 | 0 | 1/1 | case-10-timeout-seam |
| Local recoverability | higher | n/m | n/m | n/m | 0/1 | — |
| Scope discipline | higher | 1.00 | 1.00 | 1.00 | 1/1 | case-10-timeout-seam |

### E vector (planning-phase proxies where noted)

| Dimension | Mean | n |
|---|---:|---:|
| success | 0.000 | 1 |
| wall_time | 1333.600 | 1 |
| tokens | n/a | 0 |
| context_read | 4.000 | 1 |
| rework | n/a | 0 |
| integration_defects | n/a | 0 |
| scope_creep | 0.000 | 1 |
| replans | 0.000 | 1 |
| compactions | n/a | 0 |
| local_recoverability | n/a | 0 |

## Variant: `baseline-a` (3 runs)

| Metric | Direction | Mean | Min | Max | Measured | Worst run |
|---|---|---:|---:|---:|---|---|
| Contract completeness | higher | 0.67 | 0.56 | 0.78 | 3/3 | case-06-payslip-summary |
| Acceptance determinism | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |
| Context locality (amplification proxy) | lower | 1.23 | 1.00 | 1.46 | 3/3 | case-10-timeout-seam |
| Hazardous ownership collisions | lower | 0.00 | 0 | 0 | 3/3 | case-04-audit-async |
| Dependency precision (must-have hit rate) | higher | 0.28 | 0.00 | 0.50 | 3/3 | case-10-timeout-seam |
| Integration explicitness (case reqs met) | higher | 0.17 | 0.00 | 0.50 | 3/3 | case-04-audit-async |
| Phase-shaped leaves | lower | 0.00 | 0 | 0 | 3/3 | case-04-audit-async |
| Local recoverability | higher | n/m | n/m | n/m | 0/3 | — |
| Scope discipline | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |

### E vector (planning-phase proxies where noted)

| Dimension | Mean | n |
|---|---:|---:|
| success | 1.000 | 3 |
| wall_time | 325.167 | 3 |
| tokens | n/a | 0 |
| context_read | 1.226 | 3 |
| rework | n/a | 0 |
| integration_defects | n/a | 0 |
| scope_creep | 0.000 | 3 |
| replans | n/a | 0 |
| compactions | n/a | 0 |
| local_recoverability | n/a | 0 |

### Gaming flags

- **G1_OVER_FRAGMENTED**
  - case-04-audit-async: 28 task lines > range max 6
  - case-06-payslip-summary: 50 task lines > range max 4
  - case-10-timeout-seam: 33 task lines > range max 5
- **G2_ALL_SERIAL**
  - case-04-audit-async: no parallelism mentioned anywhere in the plan
- **G3_CONTEXT_STARVATION**
  - case-04-audit-async: 27/28 task lines mention no repo file
  - case-06-payslip-summary: 41/50 task lines mention no repo file
  - case-10-timeout-seam: 22/33 task lines mention no repo file

### Judge-pending (not automated in V1)

- case-04-audit-async/baseline-a: recoverability — prose plans do not declare checkpoint/recovery structure
- case-06-payslip-summary/baseline-a: recoverability — prose plans do not declare checkpoint/recovery structure
- case-10-timeout-seam/baseline-a: recoverability — prose plans do not declare checkpoint/recovery structure

## Variant: `baseline-b` (3 runs)

| Metric | Direction | Mean | Min | Max | Measured | Worst run |
|---|---|---:|---:|---:|---|---|
| Contract completeness | higher | 0.67 | 0.56 | 0.78 | 3/3 | case-06-payslip-summary |
| Acceptance determinism | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |
| Context locality (amplification proxy) | lower | 1.31 | 1.00 | 1.82 | 3/3 | case-10-timeout-seam |
| Hazardous ownership collisions | lower | 0.00 | 0 | 0 | 3/3 | case-04-audit-async |
| Dependency precision (must-have hit rate) | higher | 0.17 | 0.00 | 0.50 | 3/3 | case-04-audit-async |
| Integration explicitness (case reqs met) | higher | 0.33 | 0.00 | 0.50 | 3/3 | case-06-payslip-summary |
| Phase-shaped leaves | lower | 0.33 | 0 | 1 | 3/3 | case-10-timeout-seam |
| Local recoverability | higher | n/m | n/m | n/m | 0/3 | — |
| Scope discipline | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |

### E vector (planning-phase proxies where noted)

| Dimension | Mean | n |
|---|---:|---:|
| success | 1.000 | 3 |
| wall_time | 277.100 | 3 |
| tokens | n/a | 0 |
| context_read | 1.310 | 3 |
| rework | n/a | 0 |
| integration_defects | n/a | 0 |
| scope_creep | 0.000 | 3 |
| replans | n/a | 0 |
| compactions | n/a | 0 |
| local_recoverability | n/a | 0 |

### Gaming flags

- **G1_OVER_FRAGMENTED**
  - case-04-audit-async: 58 task lines > range max 6
  - case-06-payslip-summary: 52 task lines > range max 4
  - case-10-timeout-seam: 49 task lines > range max 5
- **G2_ALL_SERIAL**
  - case-04-audit-async: no parallelism mentioned anywhere in the plan
- **G3_CONTEXT_STARVATION**
  - case-04-audit-async: 49/58 task lines mention no repo file
  - case-06-payslip-summary: 41/52 task lines mention no repo file
  - case-10-timeout-seam: 38/49 task lines mention no repo file

### Judge-pending (not automated in V1)

- case-04-audit-async/baseline-b: recoverability — prose plans do not declare checkpoint/recovery structure
- case-06-payslip-summary/baseline-b: recoverability — prose plans do not declare checkpoint/recovery structure
- case-10-timeout-seam/baseline-b: recoverability — prose plans do not declare checkpoint/recovery structure

## Variant: `candidate` (3 runs)

| Metric | Direction | Mean | Min | Max | Measured | Worst run |
|---|---|---:|---:|---:|---|---|
| Contract completeness | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |
| Acceptance determinism | higher | 0.91 | 0.88 | 0.94 | 3/3 | case-04-audit-async |
| Context locality (amplification proxy) | lower | 3.17 | 2.25 | 5.00 | 3/3 | case-10-timeout-seam |
| Hazardous ownership collisions | lower | 0.00 | 0 | 0 | 3/3 | case-04-audit-async |
| Dependency precision (must-have hit rate) | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |
| Integration explicitness (case reqs met) | higher | 0.67 | 0.00 | 1.00 | 3/3 | case-06-payslip-summary |
| Phase-shaped leaves | lower | 0.00 | 0 | 0 | 3/3 | case-04-audit-async |
| Local recoverability | higher | 1.00 | 1.00 | 1.00 | 1/3 | case-04-audit-async |
| Scope discipline | higher | 1.00 | 1.00 | 1.00 | 3/3 | case-04-audit-async |

### E vector (planning-phase proxies where noted)

| Dimension | Mean | n |
|---|---:|---:|
| success | 1.000 | 3 |
| wall_time | 2068.600 | 3 |
| tokens | n/a | 0 |
| context_read | 13.500 | 3 |
| rework | 0.015 | 1 |
| integration_defects | 0.000 | 1 |
| scope_creep | 0.000 | 3 |
| replans | 0.333 | 3 |
| compactions | n/a | 0 |
| local_recoverability | 1.000 | 2 |

## Per-case matrix (key constraints)

| Case | ablation-full-minus-integration | baseline-a | baseline-b | candidate |
|---|---|---|---|---|
| case-04-audit-async | — | mnh✓ count✗ | mnh✗ 1/1 count✗ | lint mnh✓ count✓ |
| case-06-payslip-summary | — | count✗ | count✗ | lint count✓ |
| case-10-timeout-seam | LINT-FAIL count✓ | count✗ | count✗ | lint count✓ |


## How to read this report (do not read single metrics)

- **Context locality (amplification proxy) ↓ can be gamed** by omitting required
  context. Read it TOGETHER with contract completeness and dependency precision:
  a plan with low context but missing must-have dependencies is not "local",
  it is starved (see gaming flag G3_CONTEXT_STARVATION).
- **Task count ↓ can be gamed** by one giant task. Read it TOGETHER with
  leaf boundedness (phase-shaped leaves) and integration explicitness.
- **Integration explicitness ↑ can be gamed** by one mega integration task
  owning all fixes (flag G5_MEGA_INTEGRATION).
- **Recoverability ↑ can be gamed** by blanket checkpoint_required on trivial
  tasks; V1 records the structure, the execution smoke validates the payoff.
- **Scope discipline ↑ must be checked against the case traps**, not the
  plan's self-description: the scorer checks repo files, not prose.
- **Per-case matrix legend**: `lint`/`LINT-FAIL` = deterministic gate exit;
  `mnh✓` = no forbidden edge present, `mnh✗ v/t` = v of t forbidden edges
  present (a violation); `CREEP×n` = n scope-creep items found in the plan;
  `count✓`/`count✗` = task count inside/outside the case's acceptable range;
  `—` = that variant was not run for this case.
- **Coverage legend**: `assessed` = fully programmatic; `partial` = `partial` =
  keyword/structural proxy (baselines); `n/m` = not measurable from the
  artifact form — a `n/m` cell is NOT a zero.
- **E vector is the primary result** (bootstrap §2.4): the composite tables
  above are conveniences; per-run E vectors are in the JSON report.
