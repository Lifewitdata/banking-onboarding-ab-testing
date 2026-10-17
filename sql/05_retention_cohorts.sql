-- Weekly return among all assigned users, not only successful activators.
WITH activity AS (
 SELECT DISTINCT p.user_id,CAST(floor(epoch(e.event_at-p.assigned_at)/86400/7) AS INTEGER) AS week
 FROM population p JOIN events e USING(user_id)
 WHERE e.event_name IN ('app_open','payment_succeeded')
   AND e.event_at >= p.assigned_at AND e.event_at < p.assigned_at+INTERVAL 28 DAY
), grid AS (
 SELECT p.user_id,p.variant,date_trunc('week',p.assigned_at)::DATE AS signup_week,w.range AS week
 FROM population p CROSS JOIN range(1,4) w CROSS JOIN observation o
 WHERE p.assigned_at+(w.range+1)*INTERVAL 7 DAY <= o.event_cutoff
)
SELECT g.variant,g.signup_week,g.week,count(*) AS eligible_users,
 count(a.user_id) AS returning_users,count(a.user_id)::DOUBLE/count(*) AS return_rate
FROM grid g LEFT JOIN activity a ON g.user_id=a.user_id AND g.week=a.week
GROUP BY ALL ORDER BY g.variant,g.signup_week,g.week;
