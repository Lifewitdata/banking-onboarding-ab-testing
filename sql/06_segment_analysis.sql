-- Descriptive, exploratory cuts; do not interpret subgroup differences as causal heterogeneity.
SELECT 'channel' AS dimension,channel AS segment,variant,count(*) AS users,sum(activated_7d) AS activated,
 avg(activated_7d) AS activation_rate FROM user_metrics WHERE mature_7d GROUP BY channel,variant
UNION ALL
SELECT 'device',device,variant,count(*),sum(activated_7d),avg(activated_7d)
FROM user_metrics WHERE mature_7d GROUP BY device,variant;
