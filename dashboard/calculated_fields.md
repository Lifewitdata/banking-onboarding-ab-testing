# Tableau calculated fields

Use the CSV's stored names and respect its row grain.

```text
Absolute Lift (pp) = [difference] * 100
CI Lower (pp) = [ci_low] * 100
CI Upper (pp) = [ci_high] * 100
Relative Lift = [treatment_rate] / [control_rate] - 1
Weighted Return Rate = SUM([returning_users]) / SUM([eligible_users])
Segment Activation = SUM([activated]) / SUM([users])
```

Format rates and relative lift as percentages. Format absolute lift and CI bounds as numbers with a ` pp` suffix. Guardrail CSV `upper_bound` and `margin` are proportions and must both be multiplied by 100 when displayed as percentage points.

For experiment results, each metric already contains one overall estimate: use `MIN` or `ATTR` when Tableau requires aggregation. Never sum rates across different metrics. For cohort retention, use weighted counts. For daily activation, weighted aggregation is `SUM([activation_rate]*[users])/SUM([users])`.
