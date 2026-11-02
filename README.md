# Retail Reconciliation & Analytics Pipeline

An end-to-end data application that detects money leaks in a retail returns
process and surfaces them — alongside business performance analytics — through
a web dashboard.

## What It Does

A rule-based reconciliation engine scans retail transaction data for refund
anomalies, records every finding with a full audit trail, and presents the
results in an 8-tab dashboard where a finance user can review and resolve
exceptions.

**Four reconciliation rules:**

| Rule | Detects | Findings |
|---|---|---|
| Refund exceeds original payment | Refunds larger than the original line payment | 0 (data clean) |
| Return outside 30-day window | Returns processed after the policy window | 126 |
| Return with no reason code | Refunds issued without recorded justification | 396 |
| Repeat return on same item | Items returned more than once | 175+ |

## Architecture
