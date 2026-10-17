-- All steps use the same seven-day observation window and assignment denominator.
WITH counts AS (
 SELECT variant,1 AS step_order,'Assigned' AS step,count(*) AS users FROM user_metrics WHERE mature_7d GROUP BY variant
 UNION ALL SELECT variant,2,'Verified',sum(verified_7d) FROM user_metrics WHERE mature_7d GROUP BY variant
 UNION ALL SELECT variant,3,'Funded',sum(funded_7d) FROM user_metrics WHERE mature_7d GROUP BY variant
 UNION ALL SELECT variant,4,'First payment',sum(activated_7d) FROM user_metrics WHERE mature_7d GROUP BY variant
)
SELECT *, users::DOUBLE / first_value(users) OVER(PARTITION BY variant ORDER BY step_order) AS overall_conversion,
 users::DOUBLE / lag(users) OVER(PARTITION BY variant ORDER BY step_order) AS step_conversion
FROM counts ORDER BY variant,step_order;
