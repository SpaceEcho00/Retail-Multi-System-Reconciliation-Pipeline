# Retail Multi-System Reconciliation Pipeline

A Python pipeline that reconciles data across five independent retail 
systems — POS, accounting, inventory, purchase orders, and cashier 
shifts — to detect financial and operational discrepancies.

## 🎯 Problem

Retailers run multiple disconnected systems. POS logs sales, accounting 
records payments, inventory tracks stock, purchase orders track suppliers, 
and shift logs track cashiers. **When these systems disagree, money and 
trust leak out of the business.**

This project simulates that environment and builds an automated 
reconciliation pipeline that surfaces:
- Missing or phantom payments
- Amount mismatches between POS and accounting
- Inventory variances (shrinkage, supplier shortfalls)
- Transactions made outside cashier shifts
- Status conflicts (Completed vs Pending vs Refunded)

## 🔍 Sample Findings

From the included dataset:

| Category | Count | Financial Impact |
|----------|-------|------------------|
| Missing Payments | 1 | $99.95 |
| Phantom Payments | 0 | $0 |
| Amount Mismatches | 1 | $59.98 |
| Status Mismatches | 1 | Revenue recognition risk |
| Inventory Variances | 8 | ~$4,445 estimated loss |
| Orphan Transactions | 0 | — |

**Root causes identified:**
- **TXN016 (missing payment):** Transaction was cancelled → no payment expected ✅
- **TXN008 (amount mismatch):** Refund of $29.99 recorded as -$29.99 → sign convention issue ✅
- **TXN017 (status mismatch):** POS shows Completed, accounting shows Pending → **real concern: revenue recognized but cash not collected**
- **PO004 (partial shipment):** Supplier short-shipped 2 units → explains inventory variance
- **P007 (Smart Watch):** 0 on hand, 15 expected → stockout or loss

## 🛠️ Technical Stack

- **Python 3.12**
- **pandas** — data manipulation, joins, groupby aggregation
- **numpy** — numeric operations
- **Jupyter** — interactive exploration

## 🚀 How to Run

```bash
git clone <your-repo>
cd retail-reconciliation-pipeline
pip install -r requirements.txt
jupyter notebook notebooks/01_reconciliation.ipynb
