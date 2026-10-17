-- User-level assignment is the experimental unit; no event-level denominators.
CREATE OR REPLACE VIEW population AS
SELECT u.*, a.variant, a.assigned_at,
       a.assigned_at + INTERVAL 7 DAY <= o.event_cutoff AS mature_7d,
       a.assigned_at + INTERVAL 30 DAY <= o.event_cutoff AS mature_30d
FROM raw_users u JOIN raw_assignments a USING(user_id)
CROSS JOIN observation o WHERE a.eligible;

CREATE OR REPLACE VIEW lifecycle AS
WITH ev AS (
  SELECT user_id,
    min(event_at) FILTER (WHERE event_name='verification_completed') AS verified_at,
    min(event_at) FILTER (WHERE event_name='onboarding_failed') AS failure_at
  FROM events GROUP BY user_id
), tx AS (
  SELECT user_id,
    min(transaction_at) FILTER (WHERE kind='funding' AND status='success') AS funded_at,
    min(transaction_at) FILTER (WHERE kind='payment' AND status='success') AS first_payment_at
  FROM raw_transactions GROUP BY user_id
), s AS (
  SELECT user_id,min(contact_at) AS first_contact_at FROM raw_support GROUP BY user_id
), f AS (
  SELECT user_id,min(flag_at) AS first_flag_at FROM raw_fraud GROUP BY user_id
)
SELECT p.*,ev.verified_at,ev.failure_at,tx.funded_at,tx.first_payment_at,
       s.first_contact_at,f.first_flag_at
FROM population p LEFT JOIN ev USING(user_id) LEFT JOIN tx USING(user_id)
LEFT JOIN s USING(user_id) LEFT JOIN f USING(user_id);
