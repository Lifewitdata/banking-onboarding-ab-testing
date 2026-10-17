# Experiment readout: digital banking onboarding

**SYNTHETIC PORTFOLIO STUDY — not a Monzo experiment or real customer evidence.**

## Decision

**SIMULATED LAUNCH CRITERIA MET.** Within the configured simulation, seven-day activation was 48.43% in control and 52.31% in treatment. The estimated effect was **3.88 percentage points** (95% Newcombe CI 3.48 to 4.27 pp), or 8.00% relative lift.

This corresponds to about 3,876 additional activations per 100,000 assigned users under these synthetic assumptions. It is not a revenue estimate, realised business impact, or forecast for Monzo.

## Design and integrity

- Randomisation unit: user; treatment assigned before onboarding; analysis retains all eligible assigned users.
- Population: 250,000 users (124,902 control; 125,098 treatment). No post-treatment filtering.
- Enrolment: 84 days; 30-day follow-up per user; ingestion watermark allows an additional 72 hours.
- Planning assumptions: 45% baseline, 1 pp detectable improvement, two-sided alpha .05, 80% power. Required sample: 38,926 per arm. The 250,000-user design exceeds this to support learning with large data, not because this many users are necessary for the primary test.
- Sample-ratio mismatch p=0.69506; alert threshold 0.001. Baseline categorical balance is available in the dashboard extracts.
- Primary activation comes from successful payment transactions, not client event counts.

## Results

Rates and differences below are proportions; multiply differences by 100 for percentage points.

| metric | control_rate | treatment_rate | difference | ci_low | ci_high | p_value | holm_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| activated_7d | 0.48435 | 0.52311 | 0.03876 | 0.03484 | 0.04268 | 0.00000 | — |
| verified_7d | 0.74208 | 0.77913 | 0.03705 | 0.03370 | 0.04039 | 0.00000 | 0.00000 |
| funded_7d | 0.58712 | 0.63342 | 0.04630 | 0.04248 | 0.05012 | 0.00000 | 0.00000 |
| support_7d | 0.07031 | 0.06183 | -0.00848 | -0.01043 | -0.00653 | 0.00000 | — |
| failure_7d | 0.12889 | 0.11561 | -0.01329 | -0.01586 | -0.01072 | 0.00000 | — |
| fraud_30d | 0.00383 | 0.00401 | 0.00019 | -0.00030 | 0.00068 | 0.45714 | — |

Primary efficacy uses a pooled two-proportion z test and Newcombe confidence interval. Verification and funding use Holm-adjusted secondary p-values; their displayed intervals are unadjusted descriptive intervals. Guardrail decision-making uses the separate simultaneous upper bounds below, not their two-sided p-values.

## Guardrails

| metric | difference | upper_bound | margin | passes |
| --- | --- | --- | --- | --- |
| support_7d | -0.00848 | -0.00637 | 0.00500 | True |
| failure_7d | -0.01329 | -0.01050 | 0.00500 | True |
| fraud_30d | 0.00019 | 0.00072 | 0.00100 | True |

Three one-sided upper bounds use Bonferroni alpha .05/3, providing at least 95% family-wise coverage. Passing means the upper bound is below a predeclared acceptable increase: support and onboarding failure 0.5 pp; fraud flags 0.1 pp. These thresholds are illustrative assumptions, not approved bank risk limits. A nonsignificant difference alone does not establish safety.

## Time to first payment

Mean time without a first payment, restricted to seven days, was 4.970 days in control and 4.789 in treatment. Difference: -0.181 days (large-sample 95% CI -0.200, -0.163). Non-activators contribute seven days; this avoids comparing only the selected users who activated. This is an exploratory endpoint.

## Product interpretation and next action

The simulated treatment changes verification completion, funding propensity and verification speed. Funnel movement is consistent with those programmed mechanisms. It does not independently discover that clearer instructions cause these outcomes in real banking customers.

For a real pilot, validate the instrumentation, agree risk margins with product and risk teams, and run a fixed-horizon randomised experiment. Continue monitoring confirmed fraud losses, support costs and longer-term customer value. Cohort return rates and channel/device cuts here are exploratory; no segment-specific rollout is justified by these cuts alone.

## Limits

- Synthetic mechanisms encode the treatment effect; this project demonstrates analysis and engineering, not product validation.
- Fraud flags are transaction-linked proxy alerts, not confirmed fraud or financial loss. More payments can produce more flags; the per-user measure captures total assigned-user exposure.
- Thirty days cannot establish long-term profitability, losses or lifetime value.
- Background app visits are simplified; weekly return rates should not be interpreted as realistic banking benchmarks.
- Injected corrupt records are ancillary telemetry. The study does not simulate unobserved business outcomes or differential missingness.
- No operational deployment, real-user experiment, Tableau workbook or GitHub publication has occurred.
