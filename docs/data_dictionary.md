# Data dictionary

All timestamps are UTC, represented as timezone-naive Parquet datetimes. All data are synthetic.

## users

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| user_id | Int64 | 0 | Synthetic user key; joins users, assignment and activity. |
| signup_at | Datetime(time_unit='us', time_zone=None) | 0 | Signup timestamp, UTC. |
| channel | String | 0 | Synthetic acquisition channel. |
| device | String | 0 | Primary synthetic signup device. |
| age_band | String | 0 | Synthetic adult age band; no actual personal data. |

## assignments

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| user_id | Int64 | 0 | Synthetic user key; joins users, assignment and activity. |
| variant | String | 0 | Randomised control/treatment assignment. |
| assigned_at | Datetime(time_unit='us', time_zone=None) | 0 | Assignment time, before onboarding exposure. |
| eligible | Boolean | 0 | True for every generated user; defines the ITT population. |

## events

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| event_id | Int64 | 0 | Event identifier; raw data contain deliberate duplicate IDs. |
| user_id | Int64 | 2932 | Synthetic user key; joins users, assignment and activity. |
| event_name | String | 0 | Instrumented action; see event tracking plan. |
| event_at | Datetime(time_unit='us', time_zone=None) | 0 | Occurrence timestamp, UTC. |
| ingested_at | Datetime(time_unit='us', time_zone=None) | 0 | Arrival timestamp, UTC; may be delayed. |

## transactions

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| transaction_id | Int64 | 0 | Transaction key, referenced by fraud flags. |
| user_id | Int64 | 0 | Synthetic user key; joins users, assignment and activity. |
| transaction_at | Datetime(time_unit='us', time_zone=None) | 0 | Transaction timestamp, UTC. |
| kind | String | 0 | funding or payment. |
| status | String | 0 | success or failed; only successful payments activate. |
| amount_gbp | Float64 | 0 | Synthetic GBP amount; two decimal places. |

## support

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| contact_id | Int64 | 0 | Unique support contact key. |
| user_id | Int64 | 0 | Synthetic user key; joins users, assignment and activity. |
| contact_at | Datetime(time_unit='us', time_zone=None) | 0 | Support contact timestamp, UTC. |
| reason | String | 0 | Synthetic contact reason. |
| resolution_hours | Float64 | 0 | Synthetic time to resolve contact in hours. |

## fraud

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| flag_id | Int64 | 0 | Unique fraud flag key. |
| transaction_id | Int64 | 0 | Transaction key, referenced by fraud flags. |
| user_id | Int64 | 0 | Synthetic user key; joins users, assignment and activity. |
| flag_at | Datetime(time_unit='us', time_zone=None) | 0 | Flag timestamp, after linked payment. |
| flag_type | String | 0 | Synthetic alert category; not confirmed fraud. |

## tracking_issues

| column | dtype | null_count | description |
| --- | --- | --- | --- |
| event_id | Int64 | 0 | Event identifier; raw data contain deliberate duplicate IDs. |
| issue | String | 0 | Injected tracking issue label; audit only, excluded from cleaning and outcome calculation. |

## Derived analytical tables

`user_metrics` is one row per assigned user. Seven-day binary outcomes are integer 0/1, fraud uses a 30-day window, and maturity flags determine eligibility for each observation horizon. `restricted_days_to_payment` is the smaller of first-payment delay and seven days, assigning seven days to non-payers. Lifecycle timestamps are nullable for users who never reach the stage.

Dashboard CSV grains: funnel = variant × step; experiment_results = metric; guardrails = metric; segments = dimension × segment × variant; retention = variant × signup week × return week; daily_activation = variant × signup date; baseline_balance = dimension × category.
