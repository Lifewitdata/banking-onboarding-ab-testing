# Event tracking and source-of-truth plan

All event rows have an immutable event ID, pseudonymous synthetic user ID, event time and ingestion time. Assignment is server-side and separate from event collection.

| Event | Trigger in this simulation | Analytical use |
| --- | --- | --- |
| onboarding_started | One second after assignment | Exposure diagnostics |
| verification_attempted | Initial attempt, plus retry after a recoverable error | Attempt and friction analysis |
| verification_completed | Successful synthetic verification | Verification stage |
| account_funded | Successful funding timestamp | Event-side reconciliation |
| funding_confirmed | Funding transaction emitted | Transaction-event reconciliation; do not count both funding event names as distinct funded users |
| payment_succeeded | Successful payment transaction | Activity/retention; primary conversion uses transactions |
| payment_failed | Unsuccessful payment attempt | Payment friction; excluded from activation |
| onboarding_failed | Recoverable onboarding error | User-level error guardrail |
| support_contacted | Support record emitted | Event diagnostic; guardrail uses support table |
| app_open | Synthetic return visit | Weekly return metric |
| onboarding_view | Onboarding screen visit | Exploratory telemetry |
| help_view | Help screen visit | Exploratory telemetry |
| balance_view | Funded account screen visit | Exploratory telemetry |

## Data contracts

- `users.user_id`, `assignments.user_id`, `transactions.transaction_id`, contact and flag IDs are unique.
- Each assignment references an existing eligible user. Variant is control or treatment.
- Transactions, support contacts and flags reference users. Fraud flags also reference a successful payment transaction.
- An event cannot occur before signup or at/after the end of that user's 30-day follow-up.
- Business outcomes use event/transaction occurrence time, not ingestion time.
- First payment follows funding; funding follows completed verification.
- Failed payments never count toward activation. Multiple successful payments still count as one activated user.
- A payment exactly seven days after assignment is outside the primary window.
- Late ingestion is audited and retained when available by the final snapshot. In a live pipeline, metric finalisation would wait for the agreed watermark.

The project uses final complete synthetic partitions. It does not implement streaming infrastructure, identity stitching, production event delivery or a live observability service.
