SELECT 'duplicate_users' AS check_name, count(*)-count(DISTINCT user_id) AS failures FROM raw_users
UNION ALL SELECT 'duplicate_assignments',count(*)-count(DISTINCT user_id) FROM raw_assignments
UNION ALL SELECT 'assignments_without_user',count(*) FROM raw_assignments a ANTI JOIN raw_users u USING(user_id)
UNION ALL SELECT 'users_without_assignment',count(*) FROM raw_users u ANTI JOIN raw_assignments a USING(user_id)
UNION ALL SELECT 'transaction_orphans',count(*) FROM raw_transactions t ANTI JOIN raw_users u USING(user_id)
UNION ALL SELECT 'duplicate_transactions',count(*)-count(DISTINCT transaction_id) FROM raw_transactions
UNION ALL SELECT 'funding_before_verification',count(*) FROM lifecycle WHERE funded_at < verified_at OR (funded_at IS NOT NULL AND verified_at IS NULL)
UNION ALL SELECT 'payment_before_funding',count(*) FROM lifecycle WHERE first_payment_at < funded_at OR (first_payment_at IS NOT NULL AND funded_at IS NULL)
UNION ALL SELECT 'negative_amount',count(*) FROM raw_transactions WHERE amount_gbp < 0
UNION ALL SELECT 'fraud_transaction_orphans',count(*) FROM raw_fraud f ANTI JOIN raw_transactions t USING(transaction_id)
UNION ALL SELECT 'transaction_before_assignment',count(*) FROM raw_transactions t JOIN population p USING(user_id) WHERE t.transaction_at < p.assigned_at
UNION ALL SELECT 'transaction_after_followup',count(*) FROM raw_transactions t JOIN population p USING(user_id) WHERE t.transaction_at >= p.assigned_at + INTERVAL 30 DAY
UNION ALL SELECT 'immature_primary_population',count(*) FROM population WHERE NOT mature_7d
UNION ALL SELECT 'fraud_before_transaction',count(*) FROM raw_fraud f JOIN raw_transactions t USING(transaction_id) WHERE f.flag_at < t.transaction_at;
