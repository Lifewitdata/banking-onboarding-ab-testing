# Data quality report

Synthetic data; generated deliberately for analysis practice.

| table | rows | columns |
| --- | --- | --- |
| users | 250000 | 5 |
| assignments | 250000 | 4 |
| events | 5901194 | 5 |
| transactions | 698846 | 6 |
| support | 16517 | 5 |
| fraud | 982 | 5 |
| tracking_issues | 31675 | 2 |

## Event handling

| quality_status | len |
| --- | --- |
| before_signup | 1169 |
| missing_user | 2932 |
| orphan_user | 1169 |
| valid | 5887124 |

Removed 8,800 duplicate event rows. Retained 17,605 events arriving more than 48 hours late because the final ingestion watermark allows 72 hours. Missing users, unknown users and events before signup are quarantined.

The injection log is only used to audit detection; cleaning never reads the log. Corrupt additional records affect app-open telemetry; original lifecycle records and transaction truth are intact. Thus this dataset does not model missing business outcomes or differential instrumentation loss between arms.

## Relational and temporal checks

| check_name | failures |
| --- | --- |
| duplicate_users | 0 |
| duplicate_assignments | 0 |
| assignments_without_user | 0 |
| users_without_assignment | 0 |
| transaction_orphans | 0 |
| duplicate_transactions | 0 |
| funding_before_verification | 0 |
| payment_before_funding | 0 |
| negative_amount | 0 |
| fraud_transaction_orphans | 0 |
| transaction_before_assignment | 0 |
| transaction_after_followup | 0 |
| immature_primary_population | 0 |
| fraud_before_transaction | 0 |
