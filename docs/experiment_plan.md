# Experiment plan

**Synthetic study.** This plan is encoded in configuration before the final analysis. It is not a registered real-world experiment.

## Product question

Does a simplified onboarding journey improve first-payment activation? Treatment represents clearer instructions and progress visibility. This is a conceptual intervention; no UI or production service is deployed.

## Eligibility and assignment

- 250,000 newly signed-up synthetic adult users; no existing account holders.
- 84 days of enrolment starting 1 January 2026; independent Bernoulli 50:50 user assignment.
- Assignment occurs at signup, before first onboarding exposure, and never changes.
- All eligible assigned users are retained, including failed verification, inactivity and non-activation.
- No post-treatment exclusions or stopping when significance is reached.
- UTC timestamps. Seven-day windows use `[assignment, assignment + 7 days)`.
- Every user has a full 30 days of follow-up. Final snapshot includes up to 72 hours of ingestion delay after the observation period.

## Primary outcome and power

Primary: at least one successful payment in the first seven days, using the transaction table as the source of truth.

Planning baseline 45%, absolute MDE 1 percentage point, alpha .05 two-sided, power .80, equal allocation. `NormalIndPower` uses the arcsine difference in proportions. The sample calculation is approximate and does not account for clustering because this simulation assumes independent users. The chosen dataset is larger than this requirement to demonstrate scalable processing. There is one primary efficacy test.

Primary interval: Newcombe difference of independent proportions. Hypothesis test: pooled two-proportion z test. Both are reported because an effect estimate and uncertainty are more useful than a p-value alone.

## Decision rule

All must hold for the simulated launch criterion:

1. No blocking relational/data quality failure.
2. Overall sample-ratio-mismatch p >= .001.
3. The lower endpoint of the primary 95% CI exceeds +0.5 percentage points, the illustrative minimum worthwhile effect.
4. All three guardrail upper bounds are below their allowed increases.

This primary rule is deliberately stronger than p < .05. Real commercial thresholds require implementation cost and value estimates not available here.

## Guardrails

| Metric | Window | Maximum acceptable treatment increase |
| --- | --- | --- |
| Any support contact per assigned user | 7 days | 0.5 pp |
| Any recoverable onboarding error per assigned user | 7 days | 0.5 pp |
| Any fraud flag per assigned user | 30 days | 0.1 pp |

Use three one-sided upper bounds with Bonferroni alpha .05/3. These are non-inferiority-style harm thresholds, not proof of no harm. The margins are illustrative, not regulatory or Monzo risk limits. Fraud flags do not establish confirmed fraud or financial loss.

## Secondary and exploratory analyses

- Verification and funding within seven days: secondary efficacy outcomes with Holm adjustment across these two tests.
- Restricted mean time without first payment through day seven: exploratory, includes non-activators at the seven-day cap.
- Weekly return in days 7–13, 14–20, 21–27: all assigned users as denominator; app-open or successful-payment activity.
- Acquisition channel/device segments: descriptive only; no claims of significant treatment heterogeneity.
- Baseline categorical standardised differences: diagnostic. Investigate substantial imbalance rather than selectively adjusting until significance appears.
- Daily trends: descriptive; no daily significance tests or sequential stopping.

## Risks to validity

Real experiments can have interference, cross-device identity errors, attrition, novelty effects, delayed fraud outcomes and seasonality. This simulation omits these or models them simply. Its generator changes treatment behaviour by design; the analysis is a demonstration of methods, not evidence that an intervention works outside the simulation.
