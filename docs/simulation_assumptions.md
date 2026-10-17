# Simulation assumptions and provenance

All records are generated from seed 20261017. No real customer, Monzo, financial account or personal contact data are used. No external banking dataset is represented as the source.

## Behavioural model

- Signup times are uniform across 84 days. No weekday/seasonal shocks are modelled.
- Acquisition proportions: organic 34%, paid search 28%, referral 22%, social 16%. Device mix: iOS 43%, Android 49%, web 8%. These are invented teaching assumptions.
- A latent normally distributed motivation score creates correlated verification, funding and payment behaviour. It is never exposed as a predictor in analytical tables.
- Verification probability starts at 76%, varies by channel/device/motivation, and adds 3.5 pp in treatment before clipping. Verification times are lognormal and 15% shorter in treatment.
- Funding conditional on verification starts at 79% and adds 2 pp in treatment. Successful payment conditional on funding starts at 86%. Delays can push activation outside seven days.
- Recoverable onboarding errors have base probability 11.5%, plus 3 pp on Android and minus 1.4 pp in treatment. Error users generate a retry before the final verification timestamp. Errors are not necessarily terminal failures.
- Support probability starts at 5.5%, adds 13 pp for users with an error, and subtracts 0.7 pp in treatment. Contacts occur in the first seven days.
- Funded users deposit GBP 150–2,500. Payers make `1 + Poisson(3)` successful payments. Payment amounts are fractions of their initial funding; total payment value is bounded below their funding balance. A subset has a failed attempt before their first success.
- Background events use Poisson(17) counts per user, uniformly timed across 30 days. These are deliberately simple; retention results are not realistic banking benchmarks. Unfunded users cannot view balances.
- Each successful payment has a 0.18% chance of a fraud flag. Flags occur after that payment, within the 30-day user window. There is no direct treatment term, but more payments can increase per-user flag exposure.
- Exactly 30 days of user observation; fixed UTC time basis. We do not simulate account closures, refunds, interest, credit exposure or a full ledger.

## Injected tracking issues

Rates are applied per generation batch to the original event count and rounded down:

| Issue | Approximate added rows | Handling |
| --- | --- | --- |
| Duplicate event ID | 0.15% | Keep earliest ingestion |
| Missing user ID | 0.05% | Quarantine |
| Unknown user ID | 0.02% | Quarantine |
| Event before signup | 0.02% | Quarantine |
| Ingestion delayed 72 hours | 0.30% | Retain at final watermark |

Invalid records are additional copies of ancillary app-open events with distinct IDs except intentional duplicates. Original lifecycle and transaction records remain intact. Delayed records are valid extra app-open events, not duplicates of the same event ID. This design enables deterministic cleaning checks but does not simulate missing conversions. The tracking issue log is audit ground truth and is never consulted by the cleaning logic.

## Reproducibility limits

Use the pinned package versions and the same config for exact reproduction. Changing batch size changes the random number consumption order and therefore changes the generated dataset. Row counts and SHA-256 hashes are recorded in `data/manifest.json`. CSV samples show only the first 100 rows per table, not a representative random sample.
