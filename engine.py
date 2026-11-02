import duckdb
import mysql.connector

# --- Connections ---
duck = duckdb.connect('retail.duckdb')
mysql = mysql.connector.connect(
    host="localhost", user="root", password="root",
    database="retail"
)
cursor = mysql.cursor()

# --- Rules: each returns a list of (entity_id, transaction_id, store_id, amount_at_risk) ---
def rule_refund_exceeds_payment(duck):
    q = """
        SELECT r.return_id, r.transaction_id, f.store_id,
               r.refund_amount - f.line_total AS amount_at_risk
        FROM retail.fact_returns r
        JOIN retail.fact_sales f ON r.item_id = f.item_id
        WHERE r.refund_amount > f.line_total
    """
    return duck.sql(q).fetchall()

def rule_missing_reason(duck):
    q = """
        SELECT return_id, transaction_id, NULL AS store_id,
               refund_amount AS amount_at_risk
        FROM retail.fact_returns
        WHERE reason_code IS NULL
    """
    return duck.sql(q).fetchall()

def rule_repeat_item(duck):
    q = """
        SELECT r.return_id, r.transaction_id, f.store_id,
               r.refund_amount AS amount_at_risk
        FROM retail.fact_returns r
        JOIN retail.fact_sales f ON r.item_id = f.item_id
        WHERE r.item_id IN (
            SELECT item_id FROM retail.fact_returns
            GROUP BY item_id HAVING COUNT(*) > 1
        )
    """
    return duck.sql(q).fetchall()

def rule_out_of_window(duck):
    q = """
        SELECT r.return_id, r.transaction_id, f.store_id,
               r.refund_amount AS amount_at_risk
        FROM retail.fact_returns r
        JOIN retail.fact_sales f ON r.item_id = f.item_id
        WHERE DATEDIFF('day', CAST(f.transaction_date AS DATE),
                              CAST(r.return_date AS DATE)) > 30
    """
    return duck.sql(q).fetchall()

RULES = [
    (1, 'RETURN_REFUND_CHECK',   'Refund exceeds original payment', rule_refund_exceeds_payment),
    (2, 'RETURN_OUT_OF_WINDOW',  'Return outside 30-day window',    rule_out_of_window),
    (3, 'RETURN_MISSING_REASON', 'Return with no reason code',      rule_missing_reason),
    (4, 'RETURN_REPEAT_ITEM',    'Repeat return on same item',      rule_repeat_item),
]

# --- Run each rule ---
for task_id, task_code, rule_name, rule_fn in RULES:
    print(f"\n=== Running {task_code} ===")

    # 1. Open audit
    cursor.execute(
        "INSERT INTO reconciliation_audit (task_id, run_started_at, status) VALUES (%s, NOW(), 'running')",
        (task_id,)
    )
    mysql.commit()
    audit_id = cursor.lastrowid

    try:
        # 2. Detect
        results = rule_fn(duck)
        print(f"  Exceptions found: {len(results)}")

        # 3. Write exceptions
        for row in results:
            entity_id, trans_id, store_id, amount = row
            cursor.execute("""
                INSERT INTO reconciliation_exception
                (audit_id, task_id, rule_code, entity_type, entity_id,
                 transaction_id, store_id, amount_at_risk, severity)
                VALUES (%s, %s, %s, 'return', %s, %s, %s, %s, 'high')
            """, (audit_id, task_id, task_code, entity_id, trans_id, store_id, amount))

        # 4. Close audit
        total = sum(r[3] for r in results) if results else 0
        cursor.execute("""
            UPDATE reconciliation_audit
            SET status='success', run_finished_at=NOW(),
                exceptions_found=%s, total_at_risk=%s
            WHERE audit_id=%s
        """, (len(results), total, audit_id))
        mysql.commit()
        print(f"  Audit {audit_id} closed. Total at risk: {total:.2f}")

    except Exception as e:
        mysql.rollback()
        cursor.execute(
            "UPDATE reconciliation_audit SET status='failed', error_message=%s WHERE audit_id=%s",
            (str(e), audit_id)
        )
        mysql.commit()
        print(f"  FAILED: {e}")

cursor.close(); mysql.close(); duck.close()
print("\nAll rules complete.")