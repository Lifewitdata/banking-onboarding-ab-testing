CREATE OR REPLACE TABLE user_metrics AS
SELECT *,
 CAST(coalesce(verified_at >= assigned_at AND verified_at < assigned_at + INTERVAL 7 DAY,FALSE) AS INTEGER) AS verified_7d,
 CAST(coalesce(funded_at >= assigned_at AND funded_at < assigned_at + INTERVAL 7 DAY,FALSE) AS INTEGER) AS funded_7d,
 CAST(coalesce(first_payment_at >= assigned_at AND first_payment_at < assigned_at + INTERVAL 7 DAY,FALSE) AS INTEGER) AS activated_7d,
 CAST(coalesce(first_contact_at >= assigned_at AND first_contact_at < assigned_at + INTERVAL 7 DAY,FALSE) AS INTEGER) AS support_7d,
 CAST(coalesce(failure_at >= assigned_at AND failure_at < assigned_at + INTERVAL 7 DAY,FALSE) AS INTEGER) AS failure_7d,
 CAST(coalesce(first_flag_at >= assigned_at AND first_flag_at < assigned_at + INTERVAL 30 DAY,FALSE) AS INTEGER) AS fraud_30d,
 least(coalesce(epoch(first_payment_at-assigned_at)/86400.0,7),7) AS restricted_days_to_payment
FROM lifecycle;
